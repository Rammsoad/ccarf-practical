"""
comun.py · Ayudantes que comparten los 5 labs (no necesitas tocar esto)

Aquí están, una sola vez, las funciones que usan todos los labs: llamar_claude(), mostrar_request(),
mostrar_respuesta(), correr_agente(), los contadores de tokens y costo, etc.

Cada lab hace  comun.instalar(globals())  después de su configuración. Eso define estas funciones DENTRO
del lab, como si estuvieran escritas ahí: usan el MODELO, el DETALLE y demás variables de ese lab (y las
que el panel cambie). Por eso abajo hay valores "de relleno": solo sirven para que este archivo se lea solo.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
import threading
import time
import types
from pathlib import Path

from rich.json import JSON as RichJSON
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

import idioma
import visual

# Valores de relleno: cada lab tiene los suyos (instalar() hace que las funciones usen los del lab).
MODELO = "claude-haiku-5-5"
DETALLE = "basico"
VER_JSON_COMPLETO = False
VER_THINKING = False
RECORTAR_VISTA_PREVIA = True
TOPE_USD_AGENT_SDK = 0.30
consola = None
DEMOS: dict = {}
GUIAS: dict = {}

# Precios aproximados por millón de tokens (entrada, salida) para el estimado de costo que se imprime al
# final. Verifícalos en la página de precios de Anthropic si necesitas exactitud.
PRECIOS = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}

MODELOS_SIN_TOOL_CHOICE_FORZADO = {
    "claude-sonnet-5-5", "claude-opus-5-5",
    "claude-fable-5-1", "claude-mythos-5-1", "claude-fable-5-2", "claude-mythos-5-2",
}

USO_TOTAL = {"entrada": 0, "salida": 0, "llamadas": 0, "costo": 0.0}

CANDADO_USO = threading.Lock()   # en demos con hilos (1.3 en paralelo) las sumas no se pisan

USO_SDK = {"entrada": 0, "salida": 0, "cache": 0, "turnos": 0, "costo": 0.0}   # lo que reporta el Agent SDK / claude -p


def titulo(texto: str) -> None:
    texto = idioma.salida(texto)
    consola.print()
    consola.print(Rule(f"[bold white on dark_blue] {escape(texto)} [/]", style="blue"))
    consola.print()


def paso(texto: str) -> None:
    texto = idioma.salida(texto)
    consola.print(f"\n[bold cyan]▶ {escape(texto)}[/]")


def concepto(texto: str, titulo_panel: str = "💡 Concepto del examen") -> None:
    texto, titulo_panel = idioma.salida(texto), idioma.salida(titulo_panel)
    consola.print(Panel(escape(texto), title=titulo_panel, border_style="yellow", padding=(1, 2)))


def ok(texto: str) -> None:
    texto = idioma.salida(texto)
    consola.print(f"[bold green]   ✔ {escape(texto)}[/]")


def alerta(texto: str) -> None:
    texto = idioma.salida(texto)
    consola.print(f"[bold red]   ✘ {escape(texto)}[/]")


def nota(texto: str) -> None:
    texto = idioma.salida(texto)
    consola.print(f"[dim]   {escape(texto)}[/]")


def recortar(texto: str, n: int = 300) -> str:
    texto = str(texto)
    if not RECORTAR_VISTA_PREVIA:
        return texto
    return texto if len(texto) <= n else texto[:n] + f"… (+{len(texto) - n} caracteres)"


def a_dict(obj):
    """Convierte objetos del SDK (pydantic/dataclass) a dict para imprimirlos."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    if isinstance(obj, list):
        return [a_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: a_dict(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        return {k: a_dict(getattr(obj, k)) for k in obj.__dataclass_fields__}
    return obj


def texto_de(resp) -> str:
    return "\n".join(b.text for b in resp.content if b.type == "text").strip()


def mostrar_json(obj, titulo_panel: str = "", estilo: str = "white") -> None:
    texto = json.dumps(a_dict(obj), ensure_ascii=False, indent=2, default=str)
    vista = RichJSON(texto)
    vista.text.no_wrap, vista.text.overflow = False, "fold"   # que las líneas largas no se corten
    consola.print(Panel(vista, title=escape(idioma.salida(titulo_panel)), border_style=estilo))


def cliente():
    """Crea el cliente de Anthropic una sola vez (lee ANTHROPIC_API_KEY)."""
    global _cliente
    if _cliente is None:
        import anthropic
        _cliente = anthropic.Anthropic()
    return _cliente


def verificar_api_key() -> None:
    try:
        from dotenv import load_dotenv
        # override=True: la key del .env le gana a una key vieja exportada en la terminal
        load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
        load_dotenv()
    except ImportError:
        pass
    if not os.environ.get("ANTHROPIC_API_KEY"):
        consola.print(Panel(
            "No encontré la variable ANTHROPIC_API_KEY.\n\n"
            "Opción 1 (terminal):\n"
            "   macOS/Linux:  export ANTHROPIC_API_KEY=\"tu-key\"\n"
            "   Windows:      setx ANTHROPIC_API_KEY \"tu-key\"   (abre otra terminal después)\n\n"
            "Opción 2: crea un archivo .env junto a este script con la línea:\n"
            "   ANTHROPIC_API_KEY=tu-key",
            title="🔑 Falta la API key", border_style="red"))
        sys.exit(1)


def tool_choice_forzado(nombre: str | None = None) -> dict:
    """Devuelve tool_choice forzado si el modelo lo acepta; si no, 'auto'."""
    if MODELO in MODELOS_SIN_TOOL_CHOICE_FORZADO:
        nota(f"{MODELO} no acepta tool_choice forzado: se usa 'auto' + instrucción en el prompt.")
        return {"type": "auto"}
    return {"type": "tool", "name": nombre} if nombre else {"type": "any"}


def mostrar_request(etiqueta: str, kw: dict) -> None:
    etiqueta = idioma.salida(etiqueta)
    if DETALLE == "basico":
        tools = ", ".join(t["name"] for t in kw.get("tools", []) if isinstance(t, dict) and "name" in t)
        consola.print(f"\n[bold magenta]→ Llamada a Claude[/] [magenta]({escape(etiqueta)})[/] [dim]· "
                      f"{len(kw.get('messages', []))} mensajes en el historial{' · tools: ' + escape(tools) if tools else ''}[/]")
        return
    consola.print(f"\n[bold magenta]→ REQUEST a Claude[/] [magenta]({escape(etiqueta)})[/]")
    nota(f"modelo: {kw.get('model')}   max_tokens: {kw.get('max_tokens')}")
    if kw.get("system"):
        nota(f"system: {recortar(kw['system'], 160)}")
    if kw.get("tools"):
        nota("tools disponibles: " + ", ".join(t["name"] for t in kw["tools"]))
    if kw.get("tool_choice"):
        nota(f"tool_choice: {kw['tool_choice']}")
    msgs = kw.get("messages", [])
    nota(f"mensajes en el historial: {len(msgs)}  (la API no guarda nada: se manda TODO cada vez)")
    if msgs:
        ultimo = msgs[-1]
        contenido = ultimo["content"]
        if isinstance(contenido, str):
            vista = contenido
        else:
            partes = []
            for b in a_dict(contenido):
                if b.get("type") == "tool_result":
                    partes.append(f"[tool_result de {b.get('tool_use_id', '')[-6:]}] {recortar(b.get('content', ''), 120)}")
                elif b.get("type") == "text":
                    partes.append(b.get("text", ""))
                else:
                    partes.append(f"[{b.get('type')}]")
            vista = " | ".join(partes)
        nota(f"último mensaje ({ultimo['role']}): {recortar(vista, 220)}")
    if VER_JSON_COMPLETO:
        mostrar_json(kw, "JSON del request", "magenta")


def mostrar_respuesta(resp, segundos: float) -> None:
    if DETALLE == "basico":
        color = {"end_turn": "green", "tool_use": "yellow", "max_tokens": "red"}.get(resp.stop_reason, "white")
        pide = [b.name for b in resp.content if b.type == "tool_use"]
        texto = " ".join(b.text for b in resp.content if b.type == "text").strip()
        consola.print(f"[bold {color}]← stop_reason = '{resp.stop_reason}'[/]"
                      + (f"  · {idioma.salida('pide:')} [yellow]{escape(', '.join(pide))}[/]" if pide else "")
                      + (f"  · {idioma.salida('dice:')} [dim]“{escape(texto[:90])}{'…' if len(texto) > 90 else ''}”[/]" if texto else ""))
        return
    color = {"end_turn": "green", "tool_use": "yellow", "max_tokens": "red"}.get(resp.stop_reason, "white")
    consola.print(
        f"[bold {color}]← RESPUESTA  stop_reason = '{resp.stop_reason}'[/]"
        f"   [dim]({segundos:.1f}s · {resp.usage.input_tokens} tokens entrada · {resp.usage.output_tokens} salida)[/]"
    )
    for i, bloque in enumerate(resp.content, 1):
        if bloque.type == "text":
            consola.print(Panel(escape(bloque.text), title=f"bloque {i}: text", border_style="green"))
        elif bloque.type == "tool_use":
            consola.print(Panel(
                RichJSON(json.dumps(bloque.input, ensure_ascii=False)),
                title=f"bloque {i}: tool_use → {escape(bloque.name)}  (id …{bloque.id[-6:]})",
                border_style="yellow",
            ))
        elif bloque.type == "thinking":
            if VER_THINKING:
                consola.print(Panel(escape(recortar(bloque.thinking, 800)), title=f"bloque {i}: thinking", border_style="dim"))
            else:
                nota(f"bloque {i}: thinking (razonamiento interno, oculto; pon VER_THINKING=True para verlo)")
        else:
            nota(f"bloque {i}: {bloque.type}")
    if VER_JSON_COMPLETO:
        mostrar_json(resp, "JSON de la respuesta", "green")


def llamar_claude(etiqueta: str, silencioso: bool = False, **kw):
    """Llama a messages.create imprimiendo todo lo que pasa."""
    kw.setdefault("model", MODELO)
    kw.setdefault("max_tokens", 1024)
    visual.registrar_request(etiqueta, kw)   # para el inspector "lo que se le mandó a Claude"
    if not silencioso:
        mostrar_request(etiqueta, kw)
    t0 = time.time()
    try:
        resp = cliente().messages.create(**kw)
    except Exception as e:  # muestra el error de la API de forma legible
        alerta(f"La API respondió con error: {e}")
        raise
    sumar_uso_api(resp)
    visual.registrar_respuesta(resp)
    if not silencioso:
        mostrar_respuesta(resp, time.time() - t0)
    return resp


def sumar_uso_api(resp, factor: float = 1.0) -> None:
    """Suma tokens y costo de una respuesta de la Messages API con el precio del modelo que la contestó
    (factor=0.5 para la Batch API)."""
    modelo = str(getattr(resp, "model", "") or MODELO)
    p_in, p_out = next((v for k, v in PRECIOS.items() if modelo.startswith(k)), PRECIOS.get(MODELO, (0, 0)))
    with CANDADO_USO:
        USO_TOTAL["entrada"] += resp.usage.input_tokens
        USO_TOTAL["salida"] += resp.usage.output_tokens
        USO_TOTAL["llamadas"] += 1
        USO_TOTAL["costo"] += (resp.usage.input_tokens * p_in + resp.usage.output_tokens * p_out) / 1e6 * factor


def sumar_uso_sdk(costo, uso, turnos) -> None:
    """Suma lo que reporta el Agent SDK (ResultMessage) o claude -p (JSON): costo real, tokens y turnos."""
    uso = uso or {}
    USO_SDK["costo"] += costo or 0
    USO_SDK["entrada"] += uso.get("input_tokens", 0) or 0
    USO_SDK["cache"] += sum(uso.get(k, 0) or 0 for k in ("cache_creation_input_tokens", "cache_read_input_tokens"))
    USO_SDK["salida"] += uso.get("output_tokens", 0) or 0
    USO_SDK["turnos"] += turnos or 0


def stderr_cli(linea: str) -> None:
    """stderr del CLI de Claude Code: se muestra todo menos el aviso de conectores de claude.ai (aquí no aplica)."""
    if "connectors are disabled" not in linea:
        print(linea, file=sys.stderr)


def uso_y_costo(p_in: float, p_out: float) -> dict:
    """Uso y costo de la corrida para el panel: Messages API (por precio) + Agent SDK (costo que reporta)."""
    costo = USO_TOTAL["costo"] + USO_SDK["costo"]
    uso = {"entrada": USO_TOTAL["entrada"] + USO_SDK["entrada"], "salida": USO_TOTAL["salida"] + USO_SDK["salida"],
           "cache": USO_SDK["cache"], "llamadas": USO_TOTAL["llamadas"] + USO_SDK["turnos"]}
    return {"uso": uso, "costo": round(costo, 6)}


def resumen_costo() -> None:
    costo = USO_TOTAL["costo"]
    consola.print(Panel(
        f"Llamadas a la API: {USO_TOTAL['llamadas']}\n"
        f"Tokens de entrada: {USO_TOTAL['entrada']:,}\n"
        f"Tokens de salida:  {USO_TOTAL['salida']:,}\n"
        f"Costo estimado (con el precio de cada modelo usado): ~${costo:.4f} USD"
        + (f"\nAgent SDK / claude -p: {USO_SDK['turnos']} turnos · {USO_SDK['entrada'] + USO_SDK['salida']:,} tokens · "
           f"${USO_SDK['costo']:.4f} USD (costo que reporta)" if USO_SDK["turnos"] else ""),
        title="📊 Uso de la Messages API en esta corrida", border_style="blue",
    ))


def guardar_html(eleccion: str) -> None:
    visual.guardar_html(eleccion, visual.config_de_demo(eleccion, globals(), DEMOS, MODELO), DEMOS, GUIAS)


def mostrar_estado_html() -> None:
    texto, color = visual.panel_estado()
    consola.print(Panel(texto, title="🌐 Modo HTML", border_style=color))


async def correr_agente(prompt: str, options, etiqueta: str = "agente"):
    """Corre query() del Agent SDK e imprime cada mensaje del stream."""
    from claude_agent_sdk import ResultError, query
    etiqueta = idioma.salida(etiqueta)
    consola.print(f"\n[bold magenta]→ Agent SDK ({escape(etiqueta)})[/] prompt: {escape(recortar(prompt, 800))}")
    resultado = None
    try:
        async for msg in query(prompt=prompt, options=options):
            resultado = imprimir_msg_agente(msg) or resultado
    except ResultError as e:
        # El SDK primero entrega el ResultMessage (ya impreso arriba) y luego lanza este error.
        alerta(f"La corrida terminó con error: subtype={e.subtype}. "
               "Si es error_max_turns o error_max_budget_usd, sube max_turns o TOPE_USD_AGENT_SDK.")
    return resultado


def imprimir_msg_agente(msg):
    """Imprime un mensaje del stream. Devuelve el ResultMessage si es el final."""
    from claude_agent_sdk import (AssistantMessage, ResultMessage, SystemMessage, TextBlock,
                                  ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage)
    sangria = "   ↳ [subagente] " if getattr(msg, "parent_tool_use_id", None) else ""
    if isinstance(msg, SystemMessage) and msg.subtype == "init":
        datos = msg.data
        nota(f"{sangria}sesión iniciada · session_id={datos.get('session_id')} · modelo={datos.get('model')}")
        nota(f"{sangria}tools disponibles: {', '.join(datos.get('tools', []))}")
    elif isinstance(msg, AssistantMessage):
        for b in msg.content:
            if isinstance(b, TextBlock):
                consola.print(Panel(escape(b.text), title=f"{sangria}texto del agente", border_style="green"))
            elif isinstance(b, ToolUseBlock):
                if not any(t["id"] == b.id for t in visual.TRAZA):   # para el diagrama de la corrida
                    visual.registrar_tool_use(b.id, b.name, b.input)
                consola.print(Panel(RichJSON(json.dumps(b.input, ensure_ascii=False)),
                                    title=f"{sangria}tool_use → {escape(b.name)}", border_style="yellow"))
            elif isinstance(b, ThinkingBlock):
                if VER_THINKING:
                    consola.print(Panel(escape(recortar(b.thinking, 600)), title="thinking", border_style="dim"))
                else:
                    nota(f"{sangria}(thinking oculto)")
    elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
        for b in msg.content:
            if isinstance(b, ToolResultBlock):
                if isinstance(b.content, list):   # lista de bloques {"type": "text", "text": ...}
                    contenido = "\n".join(x.get("text", json.dumps(x, ensure_ascii=False)) if isinstance(x, dict) else str(x)
                                          for x in b.content)
                else:
                    contenido = b.content if isinstance(b.content, str) else json.dumps(b.content, ensure_ascii=False)
                visual.registrar_tool_result(b.tool_use_id, bool(b.is_error), contenido)
                bloqueo_hook = bool(b.is_error) and "hook" in contenido.lower()
                consola.print(Panel(escape(recortar(contenido, 600)),
                                    title=f"{sangria}tool_result{' (is_error)' if b.is_error else ''}"
                                          + (" · 🛡 bloqueado por tu hook" if bloqueo_hook else ""),
                                    border_style="red" if b.is_error else "cyan"))
                if bloqueo_hook:
                    consola.print(f"{sangria}[green]✅ No es una falla de la demo: es tu hook PreToolUse bloqueando la tool. "
                                  "Claude recibe el motivo como tool_result con is_error y debe explicarlo al cliente.[/]")
    elif isinstance(msg, ResultMessage):
        sumar_uso_sdk(msg.total_cost_usd, msg.usage, msg.num_turns)
        costo = f"${msg.total_cost_usd:.4f}" if msg.total_cost_usd is not None else "n/d"
        consola.print(Panel(
            f"subtype: {msg.subtype}\nturnos: {msg.num_turns}\nsession_id: {msg.session_id}\n"
            f"costo reportado: {costo} USD\nerror: {msg.is_error}",
            title="🏁 ResultMessage (fin de la corrida)", border_style="blue"))
        return msg
    return None


def opciones_base(**extra):
    from claude_agent_sdk import ClaudeAgentOptions
    visual.aislar_claude_code()   # sus sesiones van a una carpeta temporal, no a tu ~/.claude
    base = dict(model=MODELO, setting_sources=[], max_budget_usd=TOPE_USD_AGENT_SDK, stderr=stderr_cli)
    base.update(extra)
    return ClaudeAgentOptions(**base)


def entrada_tool(resp, nombre: str | None = None) -> dict:
    """Devuelve el input del primer tool_use (o del que se llame 'nombre')."""
    for b in resp.content:
        if b.type == "tool_use" and (nombre is None or b.name == nombre):
            return b.input
    return {}


def tabla_simple(titulo_tabla: str, columnas: list[str], filas: list[list]) -> None:
    tabla = Table(title=titulo_tabla, show_lines=True)
    for c in columnas:
        tabla.add_column(c)
    for f in filas:
        tabla.add_row(*[str(x) for x in f])
    consola.print(tabla)


def crear_proyecto(archivos: dict[str, str], prefijo: str = "tiendita_proyecto_") -> Path:
    """Crea un proyecto de prueba en una carpeta temporal y devuelve su ruta."""
    raiz = visual.carpeta_temporal(prefijo)
    for ruta, contenido in archivos.items():
        archivo = raiz / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(textwrap.dedent(contenido).lstrip("\n"), encoding="utf-8")
    return raiz


def mostrar_archivo(raiz: Path, ruta: str, lenguaje: str = "markdown") -> None:
    from rich.syntax import Syntax
    texto = (raiz / ruta).read_text(encoding="utf-8")
    consola.print(Panel(Syntax(texto, lenguaje, word_wrap=True), title=ruta, border_style="blue"))


# ---------------------------------------------------------------------
#  instalar(): define las funciones de arriba dentro del lab
# ---------------------------------------------------------------------
COMPARTIDAS = ["titulo", "paso", "concepto", "ok", "alerta", "nota", "recortar", "a_dict", "texto_de", "mostrar_json", "cliente", "verificar_api_key", "tool_choice_forzado", "mostrar_request", "mostrar_respuesta", "llamar_claude", "sumar_uso_api", "sumar_uso_sdk", "stderr_cli", "uso_y_costo", "resumen_costo", "guardar_html", "mostrar_estado_html", "correr_agente", "imprimir_msg_agente", "opciones_base", "entrada_tool", "tabla_simple", "crear_proyecto", "mostrar_archivo"]
MODULOS = ["json", "os", "sys", "textwrap", "threading", "time", "Path", "RichJSON", "escape", "Panel", "Rule",
           "Table", "visual", "idioma"]


def instalar(espacio: dict) -> None:
    """Copia las funciones compartidas al espacio de nombres del lab (globals()), ligadas a SU configuración."""
    for nombre in ("PRECIOS", "MODELOS_SIN_TOOL_CHOICE_FORZADO", "USO_TOTAL", "CANDADO_USO", "USO_SDK") + tuple(MODULOS):
        espacio.setdefault(nombre, globals()[nombre])
    espacio.setdefault("_cliente", None)   # cliente() de la API, se crea la primera vez que se usa
    if os.environ.get("CCARF_IDIOMA") == "en":   # el panel en inglés (o CCARF_IDIOMA=en en la terminal)
        idioma.fijar("en")
        idioma.parchar_rich()
    for nombre in COMPARTIDAS:
        f = globals()[nombre]
        if espacio.get(nombre) not in (None, f):
            continue   # el lab definió su propia versión: se respeta
        g = types.FunctionType(f.__code__, espacio, f.__name__, f.__defaults__, f.__closure__)
        g.__kwdefaults__, g.__doc__, g.__qualname__ = f.__kwdefaults__, f.__doc__, f.__qualname__
        g.__annotations__, g.__module__ = dict(f.__annotations__), espacio.get("__name__", f.__module__)
        espacio[nombre] = g

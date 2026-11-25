"""
=====================================================================
 CCAR-F · LAB DEL DOMINIO 2: Tool Design & MCP Integration
=====================================================================

Demos ejecutables, una por subdominio. Todas usan el caso de
"La Tiendita" (tienda en línea) con datos FALSOS.

CÓMO CORRERLO
-------------
  1) pip install -r requirements.txt
  2) Copia .env.example como .env y pega ahí tu API key (ver README).
     Si no hay .env, se usa la variable de entorno ANTHROPIC_API_KEY.
  3) python lab_dominio2.py          -> muestra el menú
     python lab_dominio2.py 2.1      -> corre directo la demo 2.1

CÓMO MODIFICARLO
----------------
  * Arriba está la CONFIGURACIÓN GENERAL (modelo, nivel de detalle).
  * Cada demo tiene su propio bloque "🔧 CAMBIA AQUÍ" con variables
    comentadas: cámbialas, vuelve a correr y compara la salida.

DEMOS
-----
  2.1  Descripciones de tools y selección     (Messages API)
  2.2  Errores estructurados vs genéricos      (Messages API)
  2.3  Demasiadas tools y tool_choice          (Messages API)
  2.4  Servidor MCP propio + Agent SDK         (MCP + Agent SDK)
  2.5  Tools built-in: Grep, Glob, Read, Edit  (Agent SDK)
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import textwrap
from pathlib import Path

# =====================================================================
#  CONFIGURACIÓN GENERAL  (puedes cambiar esto)
# =====================================================================

# Modelo para todas las demos. Haiku 5.5 es el más barato y acepta
# tool_choice "any"/"tool". Sonnet 5.5 y Opus 5.5 rechazan esos dos
# modos con error 400 (las demos lo manejan y te lo explican).
MODELO = "claude-haiku-5-5"

# Nivel de detalle de la salida:
#   VER_JSON_COMPLETO  -> imprime el JSON crudo de cada request/response
#   VER_THINKING       -> muestra el razonamiento interno si el modelo lo devuelve
VER_JSON_COMPLETO = False
VER_THINKING = False

# La línea "último mensaje (...)" del REQUEST es solo una VISTA PREVIA de lo que
# se le reenvía a Claude, y se recorta para no llenar la pantalla
# ("… (+54 caracteres)"). El resultado completo de cada tool ya se imprimió
# antes, en su propio panel. Pon False para ver todo sin recortar.
RECORTAR_VISTA_PREVIA = True

# Cuánto detalle imprime cada llamada: "basico" (una línea por paso, para empezar) o "completo" (todo)
DETALLE = "basico"

# Guía de cada demo: antes de correrla se imprime qué hace, qué se le manda a
# Claude, dónde está en el código y qué esperar. Para leer TODAS las guías sin
# correr nada (ni gastar):  python lab_dominio2.py guia      (o: guia 2.1)
MOSTRAR_GUIA = True
PAUSA_DESPUES_DE_GUIA = True   # espera un Enter después de la guía (ideal para explicar antes de correr)

# Modo HTML: además de la terminal, cada corrida se guarda como página web con un diagrama
# de lo que pasó, en salidas_html/dominio2/. Cada corrida es un archivo nuevo (no se sobrescribe)
# y salidas_html/dominio2/index.html las recorre con Anterior / Siguiente para comparar: cambia una
# variable, vuelve a correr la demo y compara los diagramas. Ejemplos de lo que vas a ver, sin correr
# nada: ejemplos_html/dominio2/index.html
#   True  -> encendido (para apagarlo en una sola corrida:  python lab_dominio2.py 2.1 --sin-html)
#   False -> solo terminal  (para encenderlo en una sola corrida:  python lab_dominio2.py 2.1 --html)
MODO_HTML = True

# Límite de reembolso de La Tiendita (pesos mexicanos)
LIMITE_REEMBOLSO = 10_000

# Tope de gasto por cada corrida del Agent SDK (dólares), por seguridad
TOPE_USD_AGENT_SDK = 0.30


# =====================================================================
#  IMPRESIÓN BONITA Y VERBOSA  (no necesitas tocar esto)
# =====================================================================

try:
    from rich.console import Console
    from rich.markup import escape
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("Falta la librería 'rich'. Corre: pip install -r requirements.txt")
    sys.exit(1)

# Modo HTML (diagramas, páginas por corrida e índice): todo vive en visual.py, junto a este archivo.
# MODO_HTML (arriba) lo decide; --html y --sin-html lo cambian solo para esta corrida.
import idioma  # noqa: E402
import visual  # noqa: E402
from visual import agregar_diagrama, corto, diagrama_seguro, subtitulo, svg_barras, svg_grafo  # noqa: E402
GUARDAR_HTML = visual.configurar(dominio=2, modo_html=MODO_HTML)
consola = Console(record=GUARDAR_HTML)
visual.usar_consola(consola)
# Ayudantes compartidos (llamar_claude, mostrar_request, correr_agente, contadores de costo…): viven en
# comun.py y comun.instalar() los define aquí mismo, con la configuración de este lab.
import comun  # noqa: E402
from comun import (  # noqa: E402
    PRECIOS, USO_TOTAL, USO_SDK, titulo, paso, concepto,
    ok, alerta, nota, recortar, texto_de, mostrar_json,
    verificar_api_key, tool_choice_forzado, llamar_claude, uso_y_costo, resumen_costo, guardar_html,
    mostrar_estado_html, correr_agente, opciones_base,
)
comun.instalar(globals())


def mostrar_guia(clave: str, forzar: bool = False, pausa: bool = True) -> None:
    """Imprime la guía (markdown) de una demo. Las guías están arriba de cada demo: GUIA_x_y."""
    if not (MOSTRAR_GUIA or forzar):
        return
    if DETALLE == "basico" and not forzar:
        consola.print(f"[dim]📖 Guía de esta demo: python lab_dominio2.py guia {clave}  ·  "
                      f"más detalle: pon DETALLE = \"completo\" arriba del archivo[/]")
        return
    from rich.markdown import Markdown
    consola.print(Panel(Markdown(idioma.guia(clave, GUIAS[clave])), title=f"📖 Guía de la demo {clave}: qué vas a ver",
                        border_style="cyan", padding=(1, 2)))
    if pausa and PAUSA_DESPUES_DE_GUIA and sys.stdin.isatty():
        consola.input("[bold cyan]   Presiona Enter para correr la demo… [/]")


# =====================================================================
#  AYUDANTES COMUNES PARA LAS DEMOS DE SELECCIÓN DE TOOLS
# =====================================================================


def primera_tool(resp) -> tuple[str | None, dict]:
    """Devuelve (nombre, input) del primer bloque tool_use, o (None, {})."""
    for b in resp.content:
        if b.type == "tool_use":
            return b.name, b.input
    return None, {}


def _recibe(tool: dict) -> str:
    """Los parámetros del input_schema en una línea: nombre (descripción)."""
    props = tool.get("input_schema", {}).get("properties", {})
    return "\n".join(f"{k}" + (f" ({v['description']})" if v.get("description") else " (texto libre)") for k, v in props.items())


def tabla_tools(tools: list[dict], titulo_tabla: str) -> None:
    """Imprime las tools tal como las ve Claude: nombre, descripción y lo que recibe (input_schema)."""
    tabla = Table(title=titulo_tabla, show_lines=True)
    tabla.add_column("name", style="yellow", no_wrap=True)
    tabla.add_column("description (lo que más pesa para decidir)")
    tabla.add_column("recibe (input_schema)", style="magenta")
    for t in tools:
        tabla.add_row(t["name"], escape(t["description"]), escape(_recibe(t)))
    consola.print(tabla)


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 2.1  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio2.py guia 2.1)
# ---------------------------------------------------------------------
GUIA_2_1 = """
#### De qué trata
Claude elige una tool leyendo solo tres cosas: su **name**, su **description** y su **input_schema**. No ve tu
código ni sabe qué hace la función por dentro. Si dos descripciones se parecen, la selección se vuelve una moneda
al aire. Mejorar las descripciones es el **primer arreglo**, antes que ejemplos few-shot o un clasificador.

#### Qué pasa al correrla, paso a paso
1. Se imprime la tabla con las 4 tools y sus descripciones **mínimas**: `get_customer`, `lookup_order`,
   `get_shipping_rates` y `search_products`.
2. Se mandan las 6 consultas de `D21_CONSULTAS`, una por una. Por cada una ves qué tool eligió Claude (✔/✘) y
   el input que armó.
3. Se repite todo con las descripciones **completas**.
4. La tabla final compara las dos rondas y cuenta los aciertos.
5. En la página de la corrida (y en el ejemplo), la tarjeta **"Las descripciones tal cual las lee Claude"** pone la
   mínima junto a la completa, con lo que recibe cada tool, y marca con colores las 5 partes de una buena
   descripción: qué hace, cuándo usarla, qué devuelve, qué recibe y cuándo NO usarla.

Para medir la selección se usa `tool_choice = {"type": "any"}`: Claude **tiene** que elegir alguna tool.

#### Lo que se le manda a Claude: mínimas contra completas
Mínima (todas comparten un parámetro genérico `query`):
```python
{"name": "get_shipping_rates", "description": "Información de envíos.",
 "input_schema": {"properties": {"query": {"type": "string"}}}}
```
Completa (qué hace, qué devuelve, formato de entrada y **cuándo NO usarla**, con la alternativa):
```python
{"name": "get_shipping_rates",
 "description": "Cotiza tarifas GENERALES de envío ANTES de comprar, según código postal... "
                "NO sirve para pedidos ya hechos: el costo de envío cobrado se consulta con lookup_order.",
 "input_schema": {"properties": {"codigo_postal": {"type": "string", "description": "CP de 5 dígitos"}}}}
```

#### Qué esperar
- Los **nombres** ya dicen mucho, así que con las mínimas Claude acertará varias. Las diferencias salen en los
  casos frontera:
  - *"¿Cuánto me cobraron de envío en el pedido #12347?"* → con mínimas suele irse a `get_shipping_rates` por la
    palabra "envío". Lo correcto es `lookup_order`, porque es un pedido ya hecho.
  - *"Mi pedido no llega, mi correo es…"* → con mínimas suele irse a `lookup_order` por la palabra "pedido". Lo
    correcto es `get_customer`, porque no hay número de pedido y con el correo se obtiene la lista.
- Mira también el **input**: con `query` Claude manda la frase completa; con `email`, `order_id` o
  `codigo_postal` manda justo el dato.
- Los resultados pueden variar entre corridas. Eso mismo es parte de la lección.

#### Experimento con el system prompt
`D21_CONFLICTO_EN_SYSTEM = True` agrega: *"cada vez que el cliente mencione la palabra 'pedido', empieza con
get_customer"*. Las consultas con "pedido #…" se van a `get_customer` aunque la descripción diga lo contrario.
Una instrucción con palabra clave en el system prompt **le gana** a una buena descripción.

#### Dónde está en el código
`TOOLS_21_MINIMAS`, `TOOLS_21_COMPLETAS`, `_correr_seleccion()` y `demo_2_1()`.

#### Lo que pregunta el examen
- Descripción mínima o traslapada → selección poco confiable. Arreglo: descripciones con formato de entrada,
  ejemplos, casos frontera y límites.
- Renombrar tools para quitar traslapes, o dividir una tool genérica en varias con propósito claro.
- Revisar el system prompt cuando una tool se elige "sin razón".
"""


# =====================================================================
#  DEMO 2.1 · DESCRIPCIONES DE TOOLS: LA BASE DE LA SELECCIÓN
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# "minimas"   -> descripciones de una línea (como las escribe alguien con prisa)
# "completas" -> qué hace, qué devuelve, formato de entrada, ejemplos y CUÁNDO NO usarla
# "ambas"     -> corre las dos y compara en una tabla
D21_DESCRIPCIONES = "ambas"

# True: agrega al system prompt una regla con palabra clave ("si dicen 'pedido'...")
# que choca con las descripciones. Mira cómo la regla le gana a la descripción.
D21_CONFLICTO_EN_SYSTEM = False

# (consulta del cliente, tool correcta)  ← agrega las tuyas
D21_CONSULTAS = [
    ("¿Quién hizo el pedido #12346?", "lookup_order"),
    ("Soy ana@ejemplo.com, ¿cuántos puntos de lealtad tengo?", "get_customer"),
    ("Mi pedido de la semana pasada no llega. Mi correo es juan.perez@ejemplo.com", "get_customer"),
    ("¿Cuánto me cobraron de envío en el pedido #12347?", "lookup_order"),
    ("¿Cuánto cuesta enviar a Monterrey, CP 64000?", "get_shipping_rates"),
    ("¿Todavía tienen manteles bordados rojos?", "search_products"),
]
# ------------------------------------------------------------------------

_ENTRADA_GENERICA = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}

TOOLS_21_MINIMAS = [
    {"name": "get_customer", "description": "Obtiene información del cliente.", "input_schema": _ENTRADA_GENERICA},
    {"name": "lookup_order", "description": "Obtiene información de pedidos.", "input_schema": _ENTRADA_GENERICA},
    {"name": "get_shipping_rates", "description": "Información de envíos.", "input_schema": _ENTRADA_GENERICA},
    {"name": "search_products", "description": "Busca información.", "input_schema": _ENTRADA_GENERICA},
]

TOOLS_21_COMPLETAS = [
    {
        "name": "get_customer",
        "description": (
            "Busca a UN cliente por su email y devuelve: id, nombre, puntos de lealtad y la LISTA de sus pedidos "
            "(número, fecha, estado). Úsala cuando el cliente se identifica con su correo, pregunta por su cuenta "
            "o puntos, o habla de 'mi pedido' SIN dar el número #NNNNN (aquí obtienes sus números de pedido). "
            "Entrada: email completo, p. ej. 'ana@ejemplo.com'. NO la uses si ya tienes el número de pedido: "
            "para eso está lookup_order."
        ),
        "input_schema": {"type": "object", "properties": {
            "email": {"type": "string", "description": "Email completo del cliente, p. ej. ana@ejemplo.com"}},
            "required": ["email"]},
    },
    {
        "name": "lookup_order",
        "description": (
            "Devuelve el detalle de UN pedido YA REALIZADO a partir de su número (formato '#NNNNN'): cliente que lo "
            "hizo, artículos, total, costo de envío COBRADO y estado de entrega. Úsala siempre que la consulta "
            "incluya un número de pedido. NO sirve para cotizar envíos futuros (usa get_shipping_rates) ni para "
            "buscar pedidos sin número (usa get_customer)."
        ),
        "input_schema": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "Número de pedido con #, p. ej. #12345"}},
            "required": ["order_id"]},
    },
    {
        "name": "get_shipping_rates",
        "description": (
            "Cotiza tarifas GENERALES de envío ANTES de comprar, según código postal destino. Devuelve precio y días "
            "estimados por paquetería. NO sirve para pedidos ya hechos: el costo de envío cobrado en un pedido "
            "existente se consulta con lookup_order."
        ),
        "input_schema": {"type": "object", "properties": {
            "codigo_postal": {"type": "string", "description": "CP de 5 dígitos, p. ej. 64000"}},
            "required": ["codigo_postal"]},
    },
    {
        "name": "search_products",
        "description": (
            "Busca en el CATÁLOGO de La Tiendita por texto libre (nombre, color, material) y devuelve SKU, precio y "
            "disponibilidad. Úsala para preguntas de '¿tienen…?', '¿cuánto cuesta el producto…?'. NO devuelve "
            "datos de clientes ni de pedidos."
        ),
        "input_schema": {"type": "object", "properties": {
            "texto": {"type": "string", "description": "Lo que busca el cliente, p. ej. 'mantel bordado rojo'"}},
            "required": ["texto"]},
    },
]


# Las 5 partes de una buena descripción, marcadas en las descripciones completas (para la tarjeta del HTML)
PARTES_21 = {
    "hace": ("Qué hace", "#9cc9ff"), "cuando": ("Cuándo usarla", "#8fe0a0"), "devuelve": ("Qué devuelve", "#ffd27a"),
    "recibe": ("Qué recibe", "#d2a8ff"), "no": ("Cuándo NO usarla (y cuál usar)", "#ff9b9b"),
}
MARCAS_21 = {
    "get_customer": [
        ("hace", "Busca a UN cliente por su email"),
        ("devuelve", "devuelve: id, nombre, puntos de lealtad y la LISTA de sus pedidos (número, fecha, estado)"),
        ("cuando", "Úsala cuando el cliente se identifica con su correo, pregunta por su cuenta o puntos, o habla de 'mi pedido' SIN dar el número #NNNNN"),
        ("recibe", "Entrada: email completo, p. ej. 'ana@ejemplo.com'"),
        ("no", "NO la uses si ya tienes el número de pedido: para eso está lookup_order")],
    "lookup_order": [
        ("hace", "Devuelve el detalle de UN pedido YA REALIZADO"),
        ("recibe", "a partir de su número (formato '#NNNNN')"),
        ("devuelve", "cliente que lo hizo, artículos, total, costo de envío COBRADO y estado de entrega"),
        ("cuando", "Úsala siempre que la consulta incluya un número de pedido"),
        ("no", "NO sirve para cotizar envíos futuros (usa get_shipping_rates) ni para buscar pedidos sin número (usa get_customer)")],
    "get_shipping_rates": [
        ("hace", "Cotiza tarifas GENERALES de envío"),
        ("cuando", "ANTES de comprar"),
        ("recibe", "según código postal destino"),
        ("devuelve", "Devuelve precio y días estimados por paquetería"),
        ("no", "NO sirve para pedidos ya hechos: el costo de envío cobrado en un pedido existente se consulta con lookup_order")],
    "search_products": [
        ("hace", "Busca en el CATÁLOGO de La Tiendita"),
        ("recibe", "por texto libre (nombre, color, material)"),
        ("devuelve", "devuelve SKU, precio y disponibilidad"),
        ("cuando", "Úsala para preguntas de '¿tienen…?', '¿cuánto cuesta el producto…?'"),
        ("no", "NO devuelve datos de clientes ni de pedidos")],
}


def _marcar_21(nombre: str, descripcion: str) -> str:
    """La descripción completa en HTML, con cada parte subrayada con su color."""
    texto = visual.xml(descripcion)
    for parte, fragmento in MARCAS_21.get(nombre, []):
        frag = visual.xml(fragmento)
        if frag in texto:
            color = PARTES_21[parte][1]
            texto = texto.replace(frag, f'<span style="color:{color};border-bottom:2px solid {color}" '
                                        f'title="{PARTES_21[parte][0]}">{frag}</span>', 1)
    return texto


def tarjeta_descripciones_2_1() -> None:
    """Tarjeta del HTML: cada tool con su descripción mínima y la completa, tal cual se mandan a Claude."""
    x = visual.xml
    leyenda = "".join(f'<span style="margin-right:14px;white-space:nowrap"><span style="color:{c};border-bottom:2px solid {c}">'
                      f'{x(idioma.salida(t))}</span></span>' for t, c in PARTES_21.values())
    caja = "background:#24251f;border:1px solid #444;border-radius:8px;padding:10px 12px;vertical-align:top"
    filas = []
    for minima, completa in zip(TOOLS_21_MINIMAS, TOOLS_21_COMPLETAS):
        filas.append(
            f'<tr><td colspan="2" style="padding:14px 0 4px;font-family:monospace;font-size:16px;color:#ffd27a">{x(completa["name"])}</td></tr>'
            f'<tr><td style="{caja};width:32%">“{x(minima["description"])}”'
            f'<div style="margin-top:8px;color:#aaa;font-size:13px">{idioma.salida("Recibe:")} <code>{x(_recibe(minima))}</code></div></td>'
            f'<td style="{caja}">“{_marcar_21(completa["name"], completa["description"])}”'
            f'<div style="margin-top:8px;color:#aaa;font-size:13px">{idioma.salida("Recibe:")} <code>{x(_recibe(completa))}</code></div></td></tr>')
    html = (f'<div style="font-size:14px;margin-bottom:8px">{leyenda}</div>'
            '<table style="width:100%;border-collapse:separate;border-spacing:8px 4px;font-size:15px;line-height:1.5">'
            f'<tr><th style="text-align:left;color:#ff9b9b">{idioma.salida("❌ Mínima")}</th><th style="text-align:left;color:#8fe0a0">{idioma.salida("✅ Completa")}</th></tr>'
            + "".join(filas) + "</table>")
    agregar_diagrama("Demo 2.1 · Las descripciones tal cual las lee Claude", html,
                     "Las mismas 4 tools en las dos rondas. Solo cambia el texto de la descripción y lo que recibe (input_schema). "
                     "En la completa, cada parte de una buena descripción está subrayada con su color; pasa el mouse para ver cuál es.",
                     "La parte roja (cuándo NO usarla y cuál usar en su lugar) es la que resuelve los casos frontera: "
                     "“¿cuánto me cobraron de envío en el pedido #12347?” ya no se va a get_shipping_rates.")


def _correr_seleccion(tools: list[dict], etiqueta: str, system: str) -> list[dict]:
    filas = []
    for consulta, esperada in D21_CONSULTAS:
        resp = llamar_claude(
            f"{etiqueta}", silencioso=True, max_tokens=300, system=system, tools=tools,
            tool_choice=tool_choice_forzado(), messages=[{"role": "user", "content": consulta}],
        )
        elegida, entrada = primera_tool(resp)
        acierto = elegida == esperada
        consola.print(f"\n[bold]🗣  {escape(consulta)}[/]")
        if elegida:
            (ok if acierto else alerta)(f"eligió {elegida}  (esperada: {esperada})")
            nota(f"input que armó: {json.dumps(entrada, ensure_ascii=False)}")
        else:
            alerta(f"no eligió ninguna tool, respondió texto: {recortar(texto_de(resp), 120)}")
        filas.append({"consulta": consulta, "esperada": esperada, "elegida": elegida or "—", "acierto": acierto})
    return filas


def demo_2_1():
    titulo("DEMO 2.1 · Descripciones de tools: lo que Claude usa para elegir")
    mostrar_guia("2.1")
    concepto(
        "Claude elige una tool leyendo su NOMBRE, su DESCRIPCIÓN y su input_schema. Nada más.\n"
        "Descripciones mínimas o parecidas entre sí = selección poco confiable.\n"
        "Una buena descripción dice: qué hace, qué devuelve, formato de entrada, un ejemplo y CUÁNDO NO usarla "
        "(con la alternativa). Es el arreglo de primer paso, antes de few-shot o de un clasificador."
    )
    system = "Eres el agente de soporte de La Tiendita. Elige la tool más adecuada para la consulta."
    if D21_CONFLICTO_EN_SYSTEM:
        system += " REGLA: cada vez que el cliente mencione la palabra 'pedido', empieza con get_customer."
        alerta("System prompt con regla de palabra clave activada: 'pedido' → get_customer")
    nota(f"system: {system}")
    nota(f"tool_choice: {tool_choice_forzado()}  (forzamos a que elija alguna tool para medir la selección)")

    modos = ["minimas", "completas"] if D21_DESCRIPCIONES == "ambas" else [D21_DESCRIPCIONES]
    diagrama_seguro(tarjeta_descripciones_2_1)
    resultados = {}
    for modo in modos:
        tools = TOOLS_21_MINIMAS if modo == "minimas" else TOOLS_21_COMPLETAS
        paso(f"Ronda con descripciones {modo.upper()}")
        tabla_tools(tools, f"Tools con descripciones {modo}")
        resultados[modo] = _correr_seleccion(tools, modo, system)

    tabla = Table(title="Resultado: ¿eligió la tool correcta?")
    tabla.add_column("Consulta"); tabla.add_column("Esperada", style="cyan")
    for modo in modos:
        tabla.add_column(f"Elegida ({modo})")
    for i, (consulta, esperada) in enumerate(D21_CONSULTAS):
        celdas = []
        for modo in modos:
            f = resultados[modo][i]
            celdas.append(f"[green]✔ {f['elegida']}[/]" if f["acierto"] else f"[red]✘ {f['elegida']}[/]")
        tabla.add_row(escape(consulta), esperada, *celdas)
    tabla.add_row("", "[bold]Aciertos[/]", *[
        f"[bold]{sum(f['acierto'] for f in resultados[m])}/{len(D21_CONSULTAS)}[/]" for m in modos])
    consola.print(tabla)
    diagrama_seguro(diagrama_2_1, modos, resultados)
    nota("Fíjate también en el INPUT: con input_schema genérico ('query') Claude manda texto libre; "
         "con campos específicos (email, order_id, codigo_postal) manda justo el dato que necesitas.")
    concepto(
        "1) Cambia una descripción completa para que se parezca a otra y mira cómo bajan los aciertos.\n"
        "2) Pon D21_CONFLICTO_EN_SYSTEM = True: una regla con palabra clave en el system prompt le gana a la "
        "descripción. En el examen: revisa el system prompt cuando una tool se elige 'sin razón'.\n"
        "3) Agrega tus propias consultas ambiguas a D21_CONSULTAS.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 2.2  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio2.py guia 2.2)
# ---------------------------------------------------------------------
GUIA_2_2 = """
#### De qué trata
Qué le regresa tu tool a Claude **cuando algo sale mal**. Hay dos errores clásicos:
1. **Error genérico** (`"Operation failed"`): Claude no sabe si reintentar, pedir otro dato o escalar.
2. **Error silenciado**: el sistema falló, pero la tool devuelve una lista vacía. Claude cree que la consulta
   funcionó y le dice al cliente algo **falso** ("no tienes pedidos").

La solución es un **error estructurado**: `is_error: true` y en el contenido `errorCategory` (`transient`,
`validation`, `business` o `permission`), `isRetryable` y una `description` legible. Y un resultado vacío que sí
es válido **no** es un error.

#### Qué pasa al correrla, paso a paso
Una sola tool, `buscar_pedidos_cliente(email, anio)`. Por cada escenario corre un mini agentic loop (máximo
`D22_MAX_ITERACIONES` vueltas) y ves la llamada, el `tool_result` (rojo si es error) y lo que Claude le dice al
cliente. Primero todo en formato **genérico**, luego en **estructurado**.

| Escenario | Qué pasa en el "sistema" | Genérico devuelve | Estructurado devuelve |
|---|---|---|---|
| `caido` | timeout la 1.ª vez, luego funciona | `{"pedidos": []}` sin error | `transient`, `isRetryable: true` |
| `sin_pedidos` | cliente sin pedidos (válido) | `{"pedidos": []}` | éxito, `total: 0` y una nota |
| `email_invalido` | `ana@ejemplo` sin dominio | `"Operation failed"` | `validation`, no reintentar |
| `sin_permiso` | pide pedidos de otra persona | `"Operation failed"` | `permission`, no reintentar |
| `historico` | pedidos de 2019 archivados | `"Operation failed"` | `business` + cómo solicitarlos |

#### Qué esperar
- **`caido · generico`** es el momento clave: Claude dice que no hay pedidos, cuando en realidad el sistema
  estaba caído. En **estructurado** reintenta y en el 2.º intento obtiene los pedidos.
- Con el genérico, Claude a veces adivina bien (por ejemplo, nota que `ana@ejemplo` está mal escrito), pero lo
  hace por su cuenta: la tool no le dio esa información.
- La tabla final pone lado a lado las llamadas, la respuesta y **lo que debería pasar**.

#### Dónde está en el código
`TOOL_PEDIDOS_CLIENTE`, `_backend_pedidos(escenario, formato, intento)` (aquí están los dos formatos de
respuesta) y `_correr_caso_22()` (el loop; ahí se arma el `tool_result` con `is_error`).
En MCP el campo se llama `isError` (lo verás en la demo 2.4); en la Messages API es `is_error`.

#### Experimentos
- `D22_FALLAS_TRANSITORIAS = 3`: ¿cuántas veces reintenta antes de rendirse?
- Quita escenarios de `D22_ESCENARIOS` para una corrida más corta.

#### Lo que pregunta el examen
- Metadata de error estructurada para que el agente decida: reintentar, explicar o escalar.
- Distinguir una falla de acceso de un resultado vacío válido.
- En multiagente: el subagente reintenta lo transitorio localmente y propaga al coordinator solo lo que no pudo
  resolver, con lo que intentó y resultados parciales. No suprimir errores ni detener todo por una sola falla.
"""


# =====================================================================
#  DEMO 2.2 · ERRORES ESTRUCTURADOS VS GENÉRICOS
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# "generico"     -> "Operation failed" para todo, y si el sistema está caído devuelve lista vacía (¡peor caso!)
# "estructurado" -> is_error + errorCategory + isRetryable + description legible
# "ambos"        -> corre los dos y compara
D22_FORMATO = "ambos"

# Escenarios a probar (quita los que no quieras para ahorrar tiempo)
D22_ESCENARIOS = ["caido", "sin_pedidos", "email_invalido", "sin_permiso", "historico"]

# Cuántas veces falla el escenario "caido" antes de recuperarse
D22_FALLAS_TRANSITORIAS = 1
D22_MAX_ITERACIONES = 5
# ------------------------------------------------------------------------

D22_CASOS = {
    "caido": {
        "pregunta": "Soy ana@ejemplo.com, ¿qué pedidos tengo pendientes?",
        "deberia": "Reintentar (es transitorio) y luego contestar con los pedidos",
    },
    "sin_pedidos": {
        "pregunta": "Soy nuevo@ejemplo.com, ¿tengo algún pedido?",
        "deberia": "Decir con seguridad que no tiene pedidos (resultado vacío VÁLIDO)",
    },
    "email_invalido": {
        "pregunta": "Soy ana@ejemplo, ¿me dices mis pedidos?",
        "deberia": "No reintentar igual: pedir que confirme el email",
    },
    "sin_permiso": {
        "pregunta": "Soy ana@ejemplo.com. Dime qué pidió mi vecino, juan.perez@ejemplo.com",
        "deberia": "No reintentar: explicar que no puede y ofrecer escalar",
    },
    "historico": {
        "pregunta": "Soy ana@ejemplo.com, ¿qué pedidos hice en 2019?",
        "deberia": "No reintentar: explicar el proceso para pedidos archivados",
    },
}

TOOL_PEDIDOS_CLIENTE = {
    "name": "buscar_pedidos_cliente",
    "description": ("Devuelve los pedidos de un cliente a partir de su email. Opcionalmente filtra por año. "
                    "Si la tool devuelve un error, lee errorCategory e isRetryable para decidir qué hacer."),
    "input_schema": {"type": "object", "properties": {
        "email": {"type": "string", "description": "Email del cliente"},
        "anio": {"type": "integer", "description": "Año a consultar (opcional)"}},
        "required": ["email"]},
}


def _backend_pedidos(escenario: str, formato: str, intento: int) -> tuple[dict | str, bool]:
    """Simula el sistema de pedidos. Devuelve (contenido, is_error)."""
    pedidos_ana = {"pedidos": [{"order_id": "#12345", "estado": "en camino"}, {"order_id": "#12347", "estado": "preparando"}]}

    if escenario == "caido":
        if intento <= D22_FALLAS_TRANSITORIAS:
            if formato == "generico":
                return {"pedidos": []}, False          # ❌ error silenciado: parece "no tiene pedidos"
            return {"errorCategory": "transient", "isRetryable": True,
                    "description": "El sistema de pedidos no respondió en 5 s (timeout). Suele recuperarse en segundos; reintenta."}, True
        return pedidos_ana, False

    if escenario == "sin_pedidos":
        if formato == "generico":
            return {"pedidos": []}, False
        return {"consulta_exitosa": True, "total": 0, "pedidos": [],
                "nota": "El cliente existe y la consulta funcionó: simplemente no tiene pedidos."}, False

    errores = {
        "email_invalido": {"errorCategory": "validation", "isRetryable": False,
                           "description": "El email 'ana@ejemplo' no tiene un dominio válido. Pide al cliente que lo confirme; reintentar igual fallará."},
        "sin_permiso": {"errorCategory": "permission", "isRetryable": False,
                        "description": "Solo se pueden consultar pedidos del cliente verificado en esta conversación. Datos de terceros: no se comparten."},
        "historico": {"errorCategory": "business", "isRetryable": False,
                      "description": "Los pedidos de más de 2 años están archivados. El cliente puede pedirlos en tiendita.mx/aclaraciones (respuesta en 3 a 5 días hábiles)."},
    }
    if formato == "generico":
        return "Operation failed", True
    return errores[escenario], True


def _correr_caso_22(escenario: str, formato: str) -> dict:
    caso = D22_CASOS[escenario]
    consola.print(f"\n[bold]🗣  [{escape(escenario)} · {formato}] {escape(caso['pregunta'])}[/]")
    mensajes = [{"role": "user", "content": caso["pregunta"]}]
    llamadas, errores_enviados = 0, 0
    devolvio = []   # resumen de cada tool_result (para el diagrama)
    system = "Eres el agente de soporte de La Tiendita. Responde en español, breve y claro."
    for _ in range(D22_MAX_ITERACIONES):
        resp = llamar_claude(f"2.2 {escenario}", silencioso=True, max_tokens=400, system=system,
                             tools=[TOOL_PEDIDOS_CLIENTE], messages=mensajes)
        mensajes.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        resultados = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            llamadas += 1
            contenido, es_error = _backend_pedidos(escenario, formato, llamadas)
            errores_enviados += es_error
            devolvio.append(_resumen_resultado_22(contenido, es_error))
            texto = contenido if isinstance(contenido, str) else json.dumps(contenido, ensure_ascii=False)
            nota(f"llamada #{llamadas} → {b.name}({json.dumps(b.input, ensure_ascii=False)})")
            consola.print(Panel(escape(texto), title=f"tool_result  is_error={es_error}",
                                border_style="red" if es_error else "cyan"))
            resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": texto, "is_error": es_error})
        mensajes.append({"role": "user", "content": resultados})
    final = texto_de(resp)
    consola.print(Panel(escape(final or "(sin texto)"), title="Lo que le dice Claude al cliente", border_style="green"))
    return {"escenario": escenario, "formato": formato, "llamadas": llamadas, "errores": errores_enviados, "final": final,
            "devolvio": devolvio}


def tarjeta_errores_2_2() -> None:
    """Tarjeta del HTML: lo que devuelve la tool en cada escenario, genérico contra estructurado, tal cual."""
    def texto(contenido, es_error):
        cuerpo = contenido if isinstance(contenido, str) else json.dumps(contenido, ensure_ascii=False, indent=1)
        return f"is_error: {str(es_error).lower()}\n{cuerpo}"
    filas = [(f"{e} · {D22_CASOS[e]['deberia']}", [texto(*_backend_pedidos(e, "generico", 1)),
                                                    texto(*_backend_pedidos(e, "estructurado", 1))])
             for e in D22_ESCENARIOS]
    visual.tarjeta_tal_cual(
        "Demo 2.2 · Los errores tal cual los recibe Claude",
        [("❌ Genérico", "#ff9b9b"), ("✅ Estructurado", "#8fe0a0")], filas,
        "Lo que la tool le regresa a Claude en el primer intento de cada escenario. Claude solo sabe lo que dice este texto.",
        "En «caido», el genérico devuelve una lista vacía sin error: Claude no tiene forma de saber que el sistema falló. "
        "El estructurado dice qué pasó (errorCategory), si sirve reintentar (isRetryable) y qué hacer (description).")


def demo_2_2():
    titulo("DEMO 2.2 · Errores estructurados: que Claude sepa QUÉ falló y QUÉ hacer")
    mostrar_guia("2.2")
    concepto(
        "Un error genérico ('Operation failed') no le dice a Claude si conviene reintentar, pedir otro dato o "
        "escalar. Peor aún: devolver lista vacía cuando el sistema falló hace que Claude diga algo FALSO "
        "('no tienes pedidos').\n"
        "Error estructurado = is_error: true + errorCategory (transient / validation / business / permission) "
        "+ isRetryable + description legible. Y un resultado vacío válido NO es un error.\n"
        "En MCP el campo se llama isError en el resultado de la tool; en la Messages API es is_error en el "
        "bloque tool_result. Misma idea."
    )
    mostrar_json(TOOL_PEDIDOS_CLIENTE, "La tool que usaremos", "yellow")
    formatos = ["generico", "estructurado"] if D22_FORMATO == "ambos" else [D22_FORMATO]
    diagrama_seguro(tarjeta_errores_2_2)
    filas = []
    for formato in formatos:
        paso(f"Formato de errores: {formato.upper()}")
        for escenario in D22_ESCENARIOS:
            filas.append(_correr_caso_22(escenario, formato))

    tabla = Table(title="Comparación por escenario", show_lines=True)
    tabla.add_column("Escenario", style="cyan"); tabla.add_column("Formato")
    tabla.add_column("Llamadas\na la tool", justify="center"); tabla.add_column("Respuesta final (recortada)")
    tabla.add_column("Lo que DEBERÍA pasar", style="dim")
    for f in filas:
        tabla.add_row(f["escenario"], f["formato"], str(f["llamadas"]), escape(recortar(f["final"], 140)),
                      D22_CASOS[f["escenario"]]["deberia"])
    consola.print(tabla)
    diagrama_seguro(diagrama_2_2, filas)
    caidas = {f["formato"]: f for f in filas if f["escenario"] == "caido"}
    if len(formatos) > 1:
        final = "comparacion"
    elif caidas:
        final = "maneja" if caidas[formatos[0]]["llamadas"] >= 2 else "confunde"
    else:
        final = "maneja" if formatos[0] == "estructurado" else "confunde"
    visual.registrar_resultado(final=final, texto=" · ".join(
        f"caído con {f}: {c['llamadas']} llamada{'s' if c['llamadas'] != 1 else ''} a la tool" for f, c in caidas.items())
        or f"Escenarios: {', '.join(D22_ESCENARIOS)}")
    concepto(
        "Compara 'caido · generico' con 'caido · estructurado': con la lista vacía Claude no tiene forma de "
        "saber que hubo una falla.\n"
        "Sube D22_FALLAS_TRANSITORIAS a 3 y mira cuántas veces reintenta.\n"
        "En un sistema multiagente, el subagente reintenta lo transitorio localmente y solo propaga al "
        "coordinator lo que no pudo resolver, con lo que intentó y resultados parciales.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 2.3  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio2.py guia 2.3)
# ---------------------------------------------------------------------
GUIA_2_3 = """
#### De qué trata
Dos decisiones de diseño: **cuántas tools** darle a cada agente (parte A) y **cómo obligarlo a usar una**
(parte B, `tool_choice`).

#### Parte A, paso a paso: 4 tools contra 18
1. **Ronda 1:** 4 tools del rol de soporte (`get_customer`, `lookup_order`, `process_refund`, `escalar_a_humano`).
2. **Ronda 2:** esas 4 + 14 distractoras que se traslapan (`get_customer_profile`, `fetch_client_record`,
   `get_order_history`, `get_shipping_status`, `refund_preview`, `create_support_ticket`…).
3. Las mismas 4 consultas en cada ronda. Por cada una ves la tool elegida y los **tokens de entrada**.
4. Tabla: aciertos y tokens promedio por request.

Qué esperar:
- Con 4 tools, casi siempre 4/4.
- Con 18 suelen aparecer elecciones "razonables pero no las esperadas": `get_shipping_status` en vez de
  `lookup_order`, `create_support_ticket` en vez de `escalar_a_humano`, `refund_preview` en vez de `process_refund`.
- Los **tokens de entrada** suben mucho: cada definición de tool viaja en **cada** request.

#### Parte B, paso a paso: tool_choice
Mismo mensaje (*"¿a qué hora abren la tienda física?"*), con dos tools (`extraer_metadatos` y `get_customer`)
y tres modos:

| `tool_choice` | Significa | Qué esperar |
|---|---|---|
| `{"type": "auto"}` | Claude decide (default) | Texto, `stop_reason: "end_turn"` |
| `{"type": "any"}` | Debe llamar **alguna** tool | `tool_use` aunque no haga falta |
| `{"type": "tool", "name": "extraer_metadatos"}` | Debe llamar **esa** | `tool_use` de `extraer_metadatos` |

Con `auto`, fíjate si Claude inventa un horario o reconoce que no lo sabe.

#### Parte C, paso a paso: tool_choice en un caso real
Llega un documento y no sabes si es factura, recibo o contrato; hay una tool (un schema) por tipo.

| Paso | `tool_choice` | Para qué |
|---|---|---|
| 1 | `{"type": "tool", "name": "extraer_metadatos"}` | Garantiza que ese paso va **primero** |
| 2 | `{"type": "any"}` con las 3 tools de extracción | Claude **debe** elegir un schema; no puede contestar en texto |
| 3 | `{"type": "auto"}` | Ya con los datos, Claude decide (puede contestar en texto) |

Qué esperar con el ticket de ejemplo: `extraer_recibo` en el paso 2. Cambia `D23_DOCUMENTO_C` por una factura
(con RFC y folio) o un contrato y mira qué schema elige.

#### Examen contra producto actual
Con `D23_MODELO_B = "claude-sonnet-5-5"`, los modos `any` y `tool` responden **error 400**. La demo lo atrapa y
lo explica. El examen evalúa el **concepto**; en la API actual, con Sonnet y Opus 5.5 se usa `auto` + una
instrucción clara + `strict: true` en la tool, o Haiku 5.5, que sí lo acepta.

#### Dónde está en el código
`TOOLS_23_NUCLEO`, `TOOLS_23_DISTRACTORAS`, `TOOLS_23_EXTRACCION`, `demo_2_3_parte_a()`, `demo_2_3_parte_b()`,
`demo_2_3_parte_c()`. El helper `_tool()`
arma cada definición en una línea.

#### Experimentos
- `D23_TOOLS_A = "18"` (o `"4"`): corre la parte A solo con esa configuración.

#### Lo que pregunta el examen
- 18 tools en vez de 4 o 5 → peor selección. Cada subagente recibe solo las tools de su rol.
- Reemplazar tools genéricas por versiones restringidas; dar una tool compartida acotada (p. ej. `verify_fact`)
  cuando un rol la necesita seguido.
- `tool_choice: any` garantiza una llamada; forzar una tool garantiza el orden (p. ej. extraer metadatos primero).
"""


# =====================================================================
#  DEMO 2.3 · DEMASIADAS TOOLS Y TOOL_CHOICE
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D23_PARTE = "todas"          # "A" (4 vs 18 tools), "B" (tool_choice), "C" (tool_choice en un caso real) o "todas"
D23_TOOLS_A = "ambas"        # parte A: "4" (solo las del rol), "18" (todas juntas) o "ambas"
D23_CONSULTAS = [
    ("Soy ana@ejemplo.com, ¿me confirman mis datos de cuenta?", "get_customer"),
    ("¿En qué va el pedido #12345?", "lookup_order"),
    ("Reembolsen $450 del pedido #12345, llegó roto.", "process_refund"),
    ("Quiero hablar con una persona, ya me cansé.", "escalar_a_humano"),
]
# Parte B: cambia a "claude-sonnet-5-5" para ver el error 400 con tool_choice any/tool
D23_MODELO_B = MODELO
D23_PREGUNTA_B = "Hola 👋 ¿a qué hora abren la tienda física?"
# Parte C: un documento que no sabes de qué tipo es (factura, recibo o contrato)
D23_MODELO_C = MODELO
D23_DOCUMENTO_C = ("TICKET A-2231 · Cafetería El Puerto · 14/03/2026 13:40\n"
                   "2 x Café americano  $90.00\n1 x Pan dulce  $35.00\nTOTAL  $125.00\nPagado con tarjeta ****4821")
# ------------------------------------------------------------------------


def _tool(nombre: str, descripcion: str, campo: str = "query") -> dict:
    return {"name": nombre, "description": descripcion,
            "input_schema": {"type": "object", "properties": {campo: {"type": "string"}}, "required": [campo]}}


TOOLS_23_NUCLEO = [
    _tool("get_customer", "Busca un cliente por email y devuelve su cuenta y sus pedidos.", "email"),
    _tool("lookup_order", "Detalle y estado de un pedido existente por número (#NNNNN).", "order_id"),
    _tool("process_refund", "Ejecuta un reembolso de un pedido existente.", "order_id"),
    _tool("escalar_a_humano", "Transfiere la conversación a un agente humano con un resumen del caso.", "resumen"),
]

TOOLS_23_DISTRACTORAS = [
    _tool("get_customer_profile", "Perfil del cliente: datos de contacto y preferencias.", "email"),
    _tool("fetch_client_record", "Registro completo del cliente en el CRM.", "email"),
    _tool("search_orders", "Busca pedidos por texto libre.", "texto"),
    _tool("get_order_history", "Historial de pedidos y sus estados.", "email"),
    _tool("get_shipping_status", "Estado del envío de un pedido.", "order_id"),
    _tool("refund_preview", "Calcula cuánto se reembolsaría en un pedido.", "order_id"),
    _tool("issue_store_credit", "Da crédito en tienda como compensación por un pedido.", "order_id"),
    _tool("cancel_order", "Cancela un pedido.", "order_id"),
    _tool("create_support_ticket", "Crea un ticket para que el equipo lo revise después.", "resumen"),
    _tool("notify_customer_email", "Envía un correo al cliente.", "mensaje"),
    _tool("check_inventory", "Consulta inventario de un producto.", "sku"),
    _tool("update_shipping_address", "Cambia la dirección de envío de un pedido.", "order_id"),
    _tool("apply_coupon", "Aplica un cupón a un pedido.", "codigo"),
    _tool("get_loyalty_points", "Puntos de lealtad del cliente.", "email"),
]


def demo_2_3_parte_a():
    paso("Parte A · 4 tools enfocadas vs 18 tools que se traslapan")
    concepto(
        "Darle a un agente 18 tools en vez de 4-5 baja la confiabilidad de la selección: hay más opciones "
        "parecidas entre sí y el agente puede usar tools fuera de su rol. Además, cada definición de tool "
        "viaja en CADA request y cuesta tokens de entrada.\n"
        "Patrón: cada subagente recibe solo las tools de su rol (scoped tool access).",
        "💡 Concepto: tool distribution")
    configs = {"4 tools (rol de soporte)": TOOLS_23_NUCLEO,
               "18 tools (todo junto)": TOOLS_23_NUCLEO + TOOLS_23_DISTRACTORAS}
    if D23_TOOLS_A in ("4", "18"):
        configs = {k: v for k, v in configs.items() if k.startswith(D23_TOOLS_A + " ")}
    resumen = []
    for etiqueta, tools in configs.items():
        consola.print(f"\n[bold cyan]  ── {etiqueta} ──[/]")
        nota("tools: " + ", ".join(t["name"] for t in tools))
        aciertos, tokens = 0, []
        for consulta, esperada in D23_CONSULTAS:
            resp = llamar_claude(etiqueta, silencioso=True, max_tokens=300, tools=tools,
                                 tool_choice=tool_choice_forzado(),
                                 system="Eres el agente de soporte de La Tiendita.",
                                 messages=[{"role": "user", "content": consulta}])
            elegida, _ = primera_tool(resp)
            tokens.append(resp.usage.input_tokens)
            aciertos += elegida == esperada
            (ok if elegida == esperada else alerta)(
                f"{recortar(consulta, 50)}  →  {elegida or 'texto'}  (esperada {esperada}) · {resp.usage.input_tokens} tokens entrada")
        resumen.append((etiqueta, aciertos, sum(tokens) / len(tokens)))
    tabla = Table(title="4 vs 18 tools")
    tabla.add_column("Configuración"); tabla.add_column("Aciertos", justify="center")
    tabla.add_column("Tokens de entrada promedio por request", justify="right")
    for etiqueta, aciertos, prom in resumen:
        tabla.add_row(etiqueta, f"{aciertos}/{len(D23_CONSULTAS)}", f"{prom:,.0f}")
    consola.print(tabla)
    diagrama_seguro(diagrama_2_3a, resumen)
    nota("Aunque Claude acierte con 18, mira cuántas distractoras eran opciones 'razonables' (get_customer_profile, "
         "get_order_history…). En producción eso se traduce en elecciones inconsistentes.")


def demo_2_3_parte_b():
    paso("Parte B · tool_choice: auto, any y tool forzada")
    concepto(
        "tool_choice controla SI Claude debe llamar una tool:\n"
        "  auto  → Claude decide; puede contestar con texto (default).\n"
        "  any   → DEBE llamar alguna tool (útil para garantizar salida estructurada).\n"
        "  tool  → DEBE llamar ESA tool, p. ej. forzar extraer_metadatos antes de cualquier otro paso.\n"
        "  none  → no puede usar tools.",
        "💡 Concepto: tool_choice")
    tools = [
        _tool("extraer_metadatos", "Extrae idioma, intención y datos de contacto del mensaje del cliente.", "mensaje"),
        TOOLS_23_NUCLEO[0],
    ]
    nota(f"modelo para esta parte: {D23_MODELO_B}")
    nota(f"mensaje del cliente: {D23_PREGUNTA_B}")
    import anthropic
    filas = []
    for modo in ({"type": "auto"}, {"type": "any"}, {"type": "tool", "name": "extraer_metadatos"}):
        consola.print(f"\n[bold cyan]  ── tool_choice = {json.dumps(modo)} ──[/]")
        try:
            resp = llamar_claude(f"tool_choice {modo['type']}", model=D23_MODELO_B, max_tokens=300, tools=tools,
                                 tool_choice=modo, messages=[{"role": "user", "content": D23_PREGUNTA_B}])
            elegida, _ = primera_tool(resp)
            filas.append((modo["type"], resp.stop_reason, elegida or "(texto)"))
        except anthropic.BadRequestError as e:
            alerta("Error 400 del modelo con este tool_choice.")
            consola.print(Panel(
                f"{escape(str(e)[:400])}\n\n"
                "Examen vs producto actual: el examen evalúa el CONCEPTO de any/tool (forzar una llamada). "
                f"En la API actual, {D23_MODELO_B} rechaza 'any' y 'tool'. Alternativa: tool_choice 'auto' + "
                "una instrucción clara en el prompt + 'strict': true en la tool para garantizar el esquema, "
                "o usar Haiku 5.5 donde sí se acepta.",
                title="📌 Por qué falló", border_style="red"))
            filas.append((modo["type"], "error 400", "—"))
    tabla = Table(title="Mismo mensaje, distinto tool_choice")
    tabla.add_column("tool_choice"); tabla.add_column("stop_reason"); tabla.add_column("¿Qué hizo?")
    for fila in filas:
        tabla.add_row(*fila)
    consola.print(tabla)
    diagrama_seguro(diagrama_2_3b, filas)


def _schema(**campos) -> dict:
    """Schema de extracción: todos los campos son string o null (para no obligar a inventar)."""
    return {"type": "object", "properties": {k: {"type": ["string", "null"], "description": v} for k, v in campos.items()},
            "required": list(campos)}


TOOLS_23_EXTRACCION = [
    {"name": "extraer_factura", "description": "Extrae una FACTURA fiscal (tiene RFC del emisor y del receptor y folio fiscal).",
     "input_schema": _schema(rfc_emisor="RFC de quien factura", rfc_receptor="RFC del cliente", folio="Folio fiscal",
                             total="Total con impuestos")},
    {"name": "extraer_recibo", "description": "Extrae un RECIBO o TICKET de compra (comercio, fecha, conceptos y total; sin RFC del cliente).",
     "input_schema": _schema(comercio="Nombre del comercio", fecha="Fecha de la compra", total="Total pagado",
                             forma_pago="Efectivo, tarjeta, etc.")},
    {"name": "extraer_contrato", "description": "Extrae un CONTRATO (partes, objeto, vigencia y monto).",
     "input_schema": _schema(partes="Quiénes firman", objeto="De qué trata", vigencia="Desde / hasta", monto="Monto pactado")},
]
TOOL_23_METADATOS = {
    "name": "extraer_metadatos", "description": "Primer paso con cualquier documento: idioma, tipo probable y si se lee completo.",
    "input_schema": {"type": "object", "properties": {
        "idioma": {"type": "string"}, "tipo_probable": {"type": "string", "enum": ["factura", "recibo", "contrato", "otro"]},
        "legible": {"type": "boolean"}}, "required": ["idioma", "tipo_probable", "legible"]},
}


def demo_2_3_parte_c():
    paso("Parte C · tool_choice en un caso real: documento de tipo desconocido")
    concepto(
        "Llega un documento y no sabes si es factura, recibo o contrato. Tienes un schema (una tool) por tipo.\n"
        "  1. tool forzada (extraer_metadatos) → garantiza que ese paso va PRIMERO.\n"
        "  2. any con las 3 tools de extracción → Claude DEBE elegir un schema; no puede contestar en texto.\n"
        "  3. auto → ya con los datos, Claude decide: puede contestar en texto.",
        "💡 Concepto: tool_choice para ordenar pasos y garantizar estructura")
    nota(f"modelo para esta parte: {D23_MODELO_C}")
    consola.print(Panel(escape(D23_DOCUMENTO_C), title="📄 Documento (no sabemos de qué tipo es)", border_style="dim"))
    import anthropic
    mensajes = [{"role": "user", "content": "Procesa este documento:\n\n" + D23_DOCUMENTO_C}]
    pasos_c = [
        ("1 · tool forzada", {"type": "tool", "name": "extraer_metadatos"}, [TOOL_23_METADATOS] + TOOLS_23_EXTRACCION),
        ("2 · any", {"type": "any"}, TOOLS_23_EXTRACCION),
        ("3 · auto", {"type": "auto"}, TOOLS_23_EXTRACCION),
    ]
    filas = []
    for etiqueta, modo, tools in pasos_c:
        consola.print(f"\n[bold cyan]  ── Paso {etiqueta}: tool_choice = {json.dumps(modo)} ──[/]")
        try:
            resp = llamar_claude(f"Parte C · paso {etiqueta}", model=D23_MODELO_C, max_tokens=400, tools=tools,
                                 tool_choice=modo, messages=mensajes)
        except anthropic.BadRequestError:
            alerta(f"Error 400: {D23_MODELO_C} no acepta tool_choice {modo['type']}.")
            nota("En la API actual usa Haiku 5.5 para esta parte, o auto + instrucción clara + strict: true.")
            filas.append((etiqueta, "error 400", "—"))
            break
        bloques = [b for b in resp.content if b.type == "tool_use"]
        hizo = bloques[0].name if bloques else "(texto)"
        filas.append((etiqueta, resp.stop_reason, hizo))
        if hizo != "(texto)":
            datos = json.dumps(bloques[0].input, ensure_ascii=False)
            ok(f"llamó {hizo}: {recortar(datos, 150)}")
            mensajes += [{"role": "assistant", "content": resp.content},
                         {"role": "user", "content": [{"type": "tool_result", "tool_use_id": b.id, "content": "guardado"}
                                                      for b in bloques]}]
        else:
            ok("contestó con texto: " + recortar(texto_de(resp), 150))
    tabla = Table(title="Parte C · un documento, tres pasos")
    tabla.add_column("Paso"); tabla.add_column("stop_reason"); tabla.add_column("¿Qué hizo?")
    for fila in filas:
        tabla.add_row(*fila)
    consola.print(tabla)
    diagrama_seguro(diagrama_2_3c, filas)
    hizo = [h for _, _, h in filas]
    if any(stop == "error 400" for _, stop, _ in filas):
        final_c = "error400"
    elif len(hizo) == 3 and hizo[0] == "extraer_metadatos" and hizo[1].startswith("extraer_") and hizo[2] == "(texto)":
        final_c = "schema"
    else:
        final_c = None
    visual.registrar_resultado(parte="C", final=final_c, texto="Pasos: " + " → ".join(hizo))
    nota("Con este documento lo esperado es extraer_recibo en el paso 2. Cambia D23_DOCUMENTO_C por una factura "
         "(con RFC y folio) o un contrato y mira qué schema elige.")


def demo_2_3():
    titulo("DEMO 2.3 · Distribución de tools y tool_choice")
    mostrar_guia("2.3")
    if D23_PARTE in ("A", "ambas", "todas"):
        demo_2_3_parte_a()
    if D23_PARTE in ("B", "ambas", "todas"):
        demo_2_3_parte_b()
    if D23_PARTE in ("C", "todas"):
        demo_2_3_parte_c()
    concepto("Parte A: agrega más distractoras o hazlas aún más parecidas.\n"
             "Parte B: cambia D23_MODELO_B a 'claude-sonnet-5-5' y mira el manejo del error 400.\n"
             "Parte C: cambia D23_DOCUMENTO_C por una factura o un contrato.",
             "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 2.4  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio2.py guia 2.4)
# ---------------------------------------------------------------------
GUIA_2_4 = """
#### De qué trata
**MCP (Model Context Protocol)**: un estándar para que un agente descubra y use tools y datos de sistemas
externos. Un **servidor MCP** ofrece:
- **Tools**: acciones que Claude puede llamar.
- **Resources**: datos que se pueden leer, como un catálogo o documentación.

La demo crea un servidor propio, primero le habla **sin Claude** y luego se lo conecta a un agente.

#### El servidor (`servidor_inventario_mcp.py`, se genera junto al script)
```python
app = MCPServer("inventario")

@app.tool(description="Busca productos en el catálogo...")
def buscar_producto(texto: str) -> CallToolResult: ...

@app.tool(description="Devuelve las piezas disponibles de UN producto por su SKU...")
def consultar_stock(sku: str) -> CallToolResult: ...        # SKU inexistente → is_error=True

@app.resource("inventario://catalogo", description="Catálogo completo...")
def catalogo() -> str: ...

app.run()   # stdio: el agente lo arranca como subproceso
```
- La `description` es lo que Claude lee. Los **type hints** (`texto: str`) se convierten en el `input_schema`.
- `respuesta(datos, es_error=True)` regresa un `CallToolResult` con `isError: true` y el error estructurado
  (lo mismo de la demo 2.2). En MCP los 3 campos (`errorCategory`, `isRetryable`, `description`) van en
  `structuredContent`; con la Messages API (demo 2.2) van en el `content` del `tool_result`.

#### Qué pasa al correrla, paso a paso
**Parte A · cliente MCP directo (sin Claude):**
1. Se conecta al servidor por stdio con `ClientSession`.
2. `tools/list`: ves las dos tools **tal como Claude las recibirá** y su nombre final, `mcp__inventario__…`.
3. `resources/list` y `resources/read`: el catálogo completo.
4. `tools/call` con un SKU válido (`isError=False`) y uno inventado (`isError=True` + error estructurado).

**Parte B · el mismo servidor conectado a un agente (Agent SDK):**
```python
mcp_servers = {"inventario": {"type": "stdio", "command": "python", "args": [".../servidor_inventario_mcp.py"]}}
allowed_tools = ["mcp__inventario__buscar_producto", "mcp__inventario__consultar_stock"]
```
Qué esperar: el agente busca "manteles bordados", consulta el stock de `MAN-ROJ-01` (4 piezas) y `MAN-AZL-01`
(agotado), y al revisar `MAN-VER-01` recibe el error de validación. Entonces le dice al cliente que ese SKU no existe.

**Parte C · configuración en Claude Code:** se imprime un `.mcp.json` de ejemplo y una tabla de alcances.

| Archivo | Alcance | Para qué |
|---|---|---|
| `.mcp.json` (en el repo) | Proyecto: todo el equipo, va a git | Servidores compartidos |
| `~/.claude.json` | Usuario: solo tú | Servidores personales o de prueba |

Los secretos van como `${GITHUB_TOKEN}`: cada persona tiene su variable de entorno y el token nunca va a git.

#### Dónde está en el código
`SERVIDOR_MCP_CODIGO` (el servidor completo como texto), `_cliente_mcp_directo()`, `MCP_JSON_EJEMPLO`, `demo_2_4()`.

#### Experimentos
- `D24_USAR_RESOURCES = True`: el agente también recibe `ListMcpResourcesTool` y `ReadMcpResourceTool`, y puede
  leer el catálogo completo en vez de buscar a ciegas.
- Empeora la descripción de `buscar_producto` (por ejemplo, `"Busca."`) y compara.
- Abre `servidor_inventario_mcp.py` y agrega una tool nueva. El lab **no sobrescribe** tu versión si el archivo
  ya existe; bórralo para volver al original.
- `D24_SECRETO = "en_archivo"`: el token queda escrito en el `.mcp.json` que va a git.
- `D24_ALCANCE = "usuario"`: el servidor queda en `~/.claude.json` y tu compañero no lo tiene.

#### Lo que pregunta el examen
- `.mcp.json` del proyecto contra `~/.claude.json` del usuario, y expansión de variables `${VAR}` para secretos.
- Las tools de todos los servidores configurados se descubren al conectar y quedan disponibles a la vez.
- Mejorar la descripción de las tools MCP para que el agente no las ignore y use built-ins como Grep en su lugar.
- Resources como catálogo de contenido para ahorrar llamadas exploratorias.
- Servidores de la comunidad para integraciones estándar; uno propio solo para flujos específicos del equipo.
"""


# =====================================================================
#  DEMO 2.4 · SERVIDOR MCP PROPIO + AGENT SDK
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D24_PARTE = "todas"          # "A" (cliente MCP directo), "B" (Agent SDK), "C" (.mcp.json) o "todas"
D24_PREGUNTA = ("¿Tienen manteles bordados rojos y azules? Dame el SKU y cuántos quedan de cada uno. "
                "Revisa también el SKU MAN-VER-01 que me pasó una amiga.")
# True: además de las tools, el agente puede LISTAR y LEER resources MCP (catálogo completo)
D24_USAR_RESOURCES = False
# True: guarda el código del servidor junto a este script (servidor_inventario_mcp.py) para que lo abras
D24_GUARDAR_SERVIDOR = True
# Parte C · dónde queda la configuración de Claude Code:
# "proyecto" → .mcp.json en el repo (lo recibe todo el equipo)   ·   "usuario" → ~/.claude.json (solo tú)
D24_ALCANCE = "proyecto"
# "variable" → "${GITHUB_TOKEN}" (cada quien lo pone en su entorno)   ·   "en_archivo" → el token escrito en el JSON
D24_SECRETO = "variable"
# ------------------------------------------------------------------------

SERVIDOR_MCP_CODIGO = textwrap.dedent('''
    """Servidor MCP de inventario de La Tiendita (stdio). Generado por lab_dominio2.py."""
    import json

    from mcp.server.mcpserver import MCPServer
    from mcp.types import CallToolResult, TextContent

    app = MCPServer("inventario", log_level="CRITICAL")


    def respuesta(datos: dict, es_error: bool = False) -> CallToolResult:
        """Empaqueta el resultado: texto JSON (lo que lee el modelo) y structuredContent (los mismos datos como
        objeto, para el cliente). es_error=True → isError: true, con los 3 campos del error en structuredContent."""
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(datos, ensure_ascii=False))],
                              structured_content=datos, is_error=es_error)

    CATALOGO = {
        "MAN-ROJ-01": {"nombre": "Mantel bordado rojo 180x240", "precio": 890, "stock": 4},
        "MAN-AZL-01": {"nombre": "Mantel bordado azul 180x240", "precio": 890, "stock": 0},
        "TAZ-TAL-06": {"nombre": "Juego de 6 tazas de talavera", "precio": 650, "stock": 12},
        "VAJ-BAR-24": {"nombre": "Vajilla de barro 24 piezas", "precio": 3200, "stock": 2},
    }


    @app.tool(description=(
        "Busca productos en el catálogo de La Tiendita por texto libre (nombre, color, material). "
        "Devuelve SKU, nombre y precio de cada coincidencia. Una lista vacía es un resultado VÁLIDO "
        "(no hay coincidencias). Para saber cuántas piezas quedan usa consultar_stock con el SKU."))
    def buscar_producto(texto: str) -> CallToolResult:
        palabras = [p for p in texto.lower().split() if len(p) > 2]
        hallados = [{"sku": sku, "nombre": p["nombre"], "precio": p["precio"]}
                    for sku, p in CATALOGO.items()
                    if any(w.rstrip("s") in p["nombre"].lower() for w in palabras)]
        return respuesta({"total": len(hallados), "resultados": hallados})


    @app.tool(description=(
        "Devuelve las piezas disponibles de UN producto por su SKU exacto (formato AAA-AAA-00, "
        "p. ej. MAN-ROJ-01). Si el SKU no existe, devuelve un error de validación estructurado."))
    def consultar_stock(sku: str) -> CallToolResult:
        producto = CATALOGO.get(sku.upper())
        if producto is None:
            # Error ESTRUCTURADO: isError=True + categoría + si conviene reintentar + qué hacer
            error = {"errorCategory": "validation", "isRetryable": False,
                     "description": f"El SKU '{sku}' no existe en el catálogo. Usa buscar_producto para encontrar el SKU correcto."}
            return respuesta(error, es_error=True)
        return respuesta({"sku": sku.upper(), "stock": producto["stock"], "disponible": producto["stock"] > 0})


    @app.resource("inventario://catalogo", name="catalogo", mime_type="application/json",
                  description="Catálogo completo de La Tiendita (SKU, nombre, precio). Léelo para no hacer búsquedas a ciegas.")
    def catalogo() -> str:
        return json.dumps(CATALOGO, ensure_ascii=False)


    if __name__ == "__main__":
        app.run()   # transporte stdio: Claude Code / Agent SDK lo arrancan como subproceso
''').lstrip()

MCP_JSON_EJEMPLO = {
    "mcpServers": {
        "inventario": {
            "command": "python",
            "args": ["servidor_inventario_mcp.py"],
        },
        "github": {
            "type": "http",
            "url": "https://api.githubcopilot.com/mcp/",
            "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
        },
    }
}


def _ruta_servidor_mcp() -> Path:
    if D24_GUARDAR_SERVIDOR:
        ruta = Path(__file__).resolve().parent / "servidor_inventario_mcp.py"
        if ruta.exists():
            nota("servidor_inventario_mcp.py ya existe: se usa TU versión (bórralo para regenerar el original).")
            return ruta
    else:
        ruta = visual.carpeta_temporal("lab_mcp_") / "servidor_inventario_mcp.py"
    ruta.write_text(SERVIDOR_MCP_CODIGO, encoding="utf-8")
    return ruta


async def _cliente_mcp_directo(ruta: Path) -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    parametros = StdioServerParameters(command=sys.executable, args=[str(ruta)])
    async with stdio_client(parametros) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            info = await sesion.initialize()
            ok(f"Conectado por stdio al servidor '{info.server_info.name}'")

            nota("tools/list  → esto es lo que Claude recibe como definiciones de tools:")
            for t in (await sesion.list_tools()).tools:
                consola.print(Panel(
                    f"[yellow]description:[/] {escape(t.description or '')}\n\n[yellow]input_schema:[/] "
                    f"{escape(json.dumps(t.input_schema, ensure_ascii=False))}",
                    title=f"tool: {escape(t.name)}  → en Claude se llamará mcp__inventario__{escape(t.name)}",
                    border_style="yellow"))

            nota("resources/list  → datos que el cliente puede LEER sin llamar tools:")
            for r in (await sesion.list_resources()).resources:
                nota(f"   {r.uri}  ·  {r.name}  ·  {r.description}")
            contenido = (await sesion.read_resource("inventario://catalogo")).contents[0].text
            mostrar_json(json.loads(contenido), "resources/read inventario://catalogo", "cyan")

            for args in ({"sku": "MAN-ROJ-01"}, {"sku": "XYZ-999"}):
                r = await sesion.call_tool("consultar_stock", args)
                texto = "".join(getattr(c, "text", "") for c in r.content)
                consola.print(Panel(escape(texto), title=f"tools/call consultar_stock{json.dumps(args)} → isError={r.is_error}",
                                    border_style="red" if r.is_error else "cyan"))


def demo_2_4():
    titulo("DEMO 2.4 · MCP: tu propio servidor de tools + Agent SDK")
    mostrar_guia("2.4")
    concepto(
        "MCP (Model Context Protocol) estandariza cómo un agente descubre y usa tools y datos externos.\n"
        "  • Tools = acciones que Claude puede llamar.  • Resources = datos que se pueden leer (catálogos, docs).\n"
        "  • Un servidor stdio corre como subproceso; Claude Code / Agent SDK lo arrancan.\n"
        "  • En Claude las tools MCP se llaman mcp__<servidor>__<tool>.\n"
        "  • Configuración: .mcp.json en el repo (compartida con el equipo, va a git) o ~/.claude.json "
        "(personal). Los secretos van como ${VARIABLE}, nunca escritos en el archivo."
    )
    ruta = _ruta_servidor_mcp()
    ok(f"Servidor MCP: {ruta}")
    from rich.syntax import Syntax
    consola.print(Panel(Syntax(ruta.read_text(encoding="utf-8"), "python", line_numbers=True, word_wrap=True),
                        title="servidor_inventario_mcp.py", border_style="blue"))

    if D24_PARTE in ("A", "todas"):
        paso("Parte A · Hablamos con el servidor SIN Claude (cliente MCP directo)")
        nota("Así puedes probar un servidor MCP antes de conectarlo a un agente.")
        try:
            asyncio.run(_cliente_mcp_directo(ruta))
            visual.registrar_resultado(parte="A", final="tools", texto="Cliente MCP directo: listó y llamó las tools del servidor")
        except Exception as e:  # p. ej. si editaste el servidor y quedó con un error
            alerta(f"No se pudo hablar con el servidor MCP: {e!r}")
            nota(f"Pruébalo solo con:  python {ruta}   (debe quedarse esperando, sin errores; sal con Ctrl+C)")
            return

    if D24_PARTE in ("B", "todas"):
        paso("Parte B · El mismo servidor conectado a un agente (Agent SDK)")
        config_mcp = {"inventario": {"type": "stdio", "command": sys.executable, "args": [str(ruta)]}}
        permitidas = ["mcp__inventario__buscar_producto", "mcp__inventario__consultar_stock"]
        builtin = []
        if D24_USAR_RESOURCES:
            builtin = ["ListMcpResourcesTool", "ReadMcpResourceTool"]
            permitidas += builtin
        mostrar_json(config_mcp, "mcp_servers (lo que le pasamos al Agent SDK)", "magenta")
        nota(f"allowed_tools: {permitidas}")
        opciones = opciones_base(
            system_prompt="Eres el agente de ventas de La Tiendita. Responde en español y breve." + (
                " Si el servidor ofrece resources (por ejemplo, un catálogo), revísalos primero para no buscar a ciegas."
                if D24_USAR_RESOURCES else ""),
            mcp_servers=config_mcp, tools=builtin, allowed_tools=permitidas, max_turns=10,
        )
        visual.limpiar_traza()
        asyncio.run(correr_agente(D24_PREGUNTA, opciones, "ventas con MCP"))
        diagrama_seguro(diagrama_2_4, list(visual.TRAZA), D24_USAR_RESOURCES)
        leyo = any("Resource" in str(t.get("nombre", "")) for t in visual.TRAZA)
        visual.registrar_resultado(parte="B", final="resources" if leyo else "tools",
                                   texto=f"Llamadas a tools: {len(visual.TRAZA)} · leyó resources: {'sí' if leyo else 'no'}")
        nota("Fíjate en el tool_result del SKU inexistente: llega con is_error y la descripción estructurada "
             "que definimos en el servidor, así el agente sabe que debe usar buscar_producto.")

    if D24_PARTE in ("C", "todas"):
        paso("Parte C · Cómo se configura en Claude Code: .mcp.json")
        ejemplo = json.loads(json.dumps(MCP_JSON_EJEMPLO))
        if D24_SECRETO == "en_archivo":
            ejemplo["mcpServers"]["github"]["headers"]["Authorization"] = "Bearer ghp_EJEMPLO_no_es_real_1234567890"
        texto = json.dumps(ejemplo, indent=2, ensure_ascii=False)
        from rich.syntax import Syntax
        donde = ".mcp.json (raíz del repo, se sube a git)" if D24_ALCANCE == "proyecto" else "~/.claude.json (solo en tu máquina)"
        consola.print(Panel(Syntax(texto, "json"), title=donde, border_style="blue"))
        if D24_SECRETO == "en_archivo":
            alerta("El token quedó escrito en el archivo. En un .mcp.json va a git: cualquiera que clone el repo lo ve.")
        if D24_ALCANCE == "usuario":
            alerta("El servidor quedó en ~/.claude.json: funciona para ti, pero tu compañero que clona el repo no lo tiene.")
        final = ("token_expuesto" if D24_SECRETO == "en_archivo" else
                 "companero_sin_servidor" if D24_ALCANCE == "usuario" else "config")
        visual.registrar_resultado(parte="C", final=final, texto=f"Alcance: {D24_ALCANCE} · secreto: {D24_SECRETO}")
        tabla = Table(title="¿Dónde va la configuración MCP?")
        tabla.add_column("Archivo"); tabla.add_column("Alcance"); tabla.add_column("Úsalo para")
        tabla.add_row(".mcp.json (en el repo)", "Proyecto: todo el equipo", "Servidores que el equipo comparte")
        tabla.add_row("~/.claude.json", "Usuario: solo tú", "Servidores personales o experimentales")
        consola.print(tabla)
        nota("${GITHUB_TOKEN} se expande desde las variables de entorno de cada persona: el token NO va en git.")
        nota("Para algo estándar (GitHub, Jira) usa un servidor MCP de la comunidad; crea uno propio solo "
             "para flujos específicos de tu equipo.")

    concepto("1) Empeora la descripción de buscar_producto (p. ej. 'Busca.') y mira si el agente se confunde.\n"
             "2) Pon D24_USAR_RESOURCES = True: el agente puede leer el catálogo completo en vez de buscar a ciegas.\n"
             "3) Abre servidor_inventario_mcp.py y agrega una tool nueva (p. ej. precio_con_descuento).",
             "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 2.5  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio2.py guia 2.5)
# ---------------------------------------------------------------------
GUIA_2_5 = """
#### De qué trata
Las tools **built-in** de Claude Code y cuándo usar cada una:

| Tool | Para qué |
|---|---|
| **Grep** | Buscar **contenido** dentro de archivos (quién llama a una función, un mensaje de error) |
| **Glob** | Buscar **archivos** por patrón de nombre o ruta (`**/*.test.ts`); no mira el contenido |
| **Read** | Leer un archivo |
| **Edit** | Cambio puntual: reemplaza un texto que debe ser **único**; si no lo es, falla |
| **Write** | Sobrescribir el archivo completo (respaldo cuando Edit no puede) |

#### El repo de ejemplo y sus trampas
Se crea en una carpeta temporal con archivos TypeScript de La Tiendita:
- `src/reembolsos/index.ts` re-exporta `processRefund as submitRefund`, y `src/admin/panel.ts` lo renombra
  otra vez (`submitRefund as reembolsoManual`). Si solo buscas "processRefund", te faltan archivos.
- En `config/limites.json` el valor `10000` aparece **dos veces** (`limite_reembolso` y `limite_credito`). Un
  Edit de solo `"10000"` no es único.

#### Qué pasa al correrla, paso a paso
La tarea pide 3 cosas: encontrar todos los usos de `processRefund` (incluidos los alias), listar los
`*.test.ts` y cambiar **solo** el límite de reembolso a 8000. Un flujo típico:
1. **Grep** `processRefund` → `procesar.ts`, `index.ts` y el test.
2. **Read** `index.ts` → descubre el alias `submitRefund`.
3. **Grep** `submitRefund` → `pago.ts` y `panel.ts`.
4. **Glob** `**/*.test.ts` → los 2 archivos de prueba.
5. **Read** `limites.json` → **Edit** con un texto que incluya la clave (`"limite_reembolso": 10000`).
   Si intenta solo `10000`, verás el error de Edit y cómo se corrige con más contexto.

Cada llamada aparece en un panel **"🪝 llamada #N"** con la explicación de la tool. Al final:
- `limites.json` antes y después;
- chequeo de que `limite_credito` siga en 10000;
- cuántos de los 5 archivos reales reportó;
- tabla de qué tools usó y cuántas veces.

#### Dónde se configuran tools, permisos y hooks
```python
opciones_base(
    tools=D25_TOOLS, allowed_tools=D25_TOOLS,      # qué built-ins tiene y cuáles se aprueban solas
    cwd=str(repo), permission_mode="acceptEdits",  # trabaja en el repo y acepta ediciones sin preguntar
    hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[hook_registro, hook_solo_repo])]},
)
```
- `matcher=None` significa que los hooks corren para **todas** las tools.
- `hook_registro` solo imprime y cuenta.
- `hook_solo_repo` hace **deny** si una ruta sale de la carpeta del repo (enforcement, como en la demo 1.5).

#### Experimentos
- Quita `"Grep"` de `D25_TOOLS`: tendrá que abrir archivo por archivo con Read (más turnos y tokens).
- `D25_EDIT_RESPALDO = "read_write"` (con `"Write"` en `D25_TOOLS`): el Edit de solo `10000` falla por texto repetido y
  el agente usa Read + Write, que es lo que espera el examen.
- Quita `"Glob"`: encontrar los `*.test.ts` se vuelve más difícil.
- Cambia `D25_TAREA` para pedir que cambie "el 10000" sin decir cuál y observa el error de Edit.

#### Lo que pregunta el examen
- Grep para contenido, Glob para rutas, Edit para cambios puntuales con texto único, y Read + Write como respaldo.
- Explorar de forma incremental: Grep para encontrar puntos de entrada y Read para seguir imports, en lugar de leer todo.
- Rastrear una función a través de módulos que la re-exportan: identificar los nombres exportados y buscar cada uno.
"""


# =====================================================================
#  DEMO 2.5 · TOOLS BUILT-IN: GREP, GLOB, READ, EDIT
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# Tools built-in que tendrá el agente. Prueba quitar "Grep" o "Glob" y compara.
D25_TOOLS = ["Read", "Grep", "Glob", "Edit"]
D25_NUEVO_LIMITE = 8000
D25_TAREA = (
    "Trabajas en el repo de La Tiendita que está en {repo}\n"
    "1) Encuentra TODOS los archivos de código que usan la función processRefund, incluyendo donde se usa "
    "con otro nombre (alias o re-export).\n"
    "2) Lista los archivos de pruebas (*.test.ts).\n"
    "3) En config/limites.json cambia SOLO el límite de reembolso de 10000 a {nuevo}. No toques el límite de crédito.\n"
    "Responde al final con una lista corta de archivos para 1) y 2)."
)
# Respaldo cuando un Edit falla porque el texto no es único:
#   "ninguno"    -> como hoy: el agente suele ampliar old_string (lo que hace el producto)
#   "read_write" -> se le pide un Edit de solo "10000" (falla: aparece dos veces) y, al fallar, Read + Write:
#                   la respuesta que espera el EXAMEN. Agrega "Write" a D25_TOOLS.
D25_EDIT_RESPALDO = "ninguno"
# ------------------------------------------------------------------------

REPO_25 = {
    "src/reembolsos/procesar.ts": """\
        import limites from '../../config/limites.json';

        export function processRefund(orderId: string, amount: number): boolean {
          if (amount > limites.limite_reembolso) {
            throw new Error('Requiere aprobación humana');
          }
          return true;
        }
        """,
    "src/reembolsos/index.ts": """\
        // Punto de entrada del módulo: se re-exporta con OTRO nombre
        export { processRefund as submitRefund } from './procesar';
        """,
    "src/checkout/pago.ts": """\
        import { submitRefund } from '../reembolsos';

        export function revertirCobro(orderId: string, total: number) {
          return submitRefund(orderId, total);
        }
        """,
    "src/admin/panel.ts": """\
        import { submitRefund as reembolsoManual } from '../reembolsos';

        export const botonReembolso = (id: string, monto: number) => reembolsoManual(id, monto);
        """,
    "src/carrito/total.ts": """\
        export function calcularTotal(precios: number[]): number {
          return precios.reduce((a, b) => a + b, 0);
        }
        """,
    "tests/reembolsos.test.ts": """\
        import { processRefund } from '../src/reembolsos/procesar';
        test('rechaza montos altos', () => { expect(() => processRefund('#1', 99999)).toThrow(); });
        """,
    "tests/carrito.test.ts": """\
        import { calcularTotal } from '../src/carrito/total';
        test('suma', () => { expect(calcularTotal([1, 2])).toBe(3); });
        """,
    "config/limites.json": """\
        {
          "limite_reembolso": 10000,
          "limite_credito": 10000,
          "moneda": "MXN"
        }
        """,
    "README.md": "# La Tiendita\nRepo de ejemplo para el lab del Dominio 2.\n",
}

# Archivos de código que realmente usan processRefund (directo o por alias)
USOS_REALES_25 = {"src/reembolsos/procesar.ts", "src/reembolsos/index.ts", "src/checkout/pago.ts",
                  "src/admin/panel.ts", "tests/reembolsos.test.ts"}

EXPLICACION_TOOLS_25 = {
    "Grep": "busca CONTENIDO dentro de archivos (nombres de funciones, imports, mensajes de error)",
    "Glob": "busca ARCHIVOS por patrón de nombre/ruta (**/*.test.ts), no mira el contenido",
    "Read": "lee un archivo completo (o un rango de líneas)",
    "Edit": "reemplaza un texto que debe ser ÚNICO en el archivo; si no es único, falla",
    "Write": "sobrescribe el archivo completo (respaldo cuando Edit no encuentra texto único)",
    "Bash": "ejecuta comandos de terminal",
}


def _crear_repo_25() -> Path:
    raiz = visual.carpeta_temporal("tiendita_repo_")
    for ruta, contenido in REPO_25.items():
        archivo = raiz / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(textwrap.dedent(contenido), encoding="utf-8")
    return raiz


def demo_2_5():
    titulo("DEMO 2.5 · Tools built-in: Grep vs Glob, Read y Edit")
    mostrar_guia("2.5")
    concepto(
        "Grep = buscar DENTRO de archivos (¿quién llama a processRefund?).\n"
        "Glob = buscar archivos por NOMBRE o ruta (¿cuáles son los *.test.ts?).\n"
        "Read = leer un archivo.  Edit = cambio puntual con texto único (si no es único, falla → Read + Write).\n"
        "Exploración incremental: primero Grep para encontrar puntos de entrada, luego Read para seguir imports "
        "(como el re-export processRefund → submitRefund). Leer todo el repo de golpe gasta contexto."
    )
    repo = _crear_repo_25()
    ok(f"Repo de ejemplo creado en: {repo}")
    arbol = Table(title="Archivos del repo", show_header=False)
    for ruta in sorted(REPO_25):
        arbol.add_row(ruta)
    consola.print(arbol)
    nota("Trampa 1: index.ts re-exporta processRefund como submitRefund, y panel.ts lo renombra otra vez.")
    nota("Trampa 2: en limites.json el valor 10000 aparece DOS veces: un Edit de solo '10000' no es único.")

    llamadas: list[tuple[str, dict]] = []

    async def hook_registro(input_data, tool_use_id, context):
        nombre = input_data.get("tool_name", "?")
        entrada = input_data.get("tool_input", {})
        llamadas.append((nombre, entrada))
        consola.print(Panel(
            f"[bold]{escape(nombre)}[/]: {escape(EXPLICACION_TOOLS_25.get(nombre, ''))}\n"
            f"input: {escape(json.dumps(entrada, ensure_ascii=False))}",
            title=f"🪝 llamada #{len(llamadas)}", border_style="magenta"))
        return {}

    async def hook_solo_repo(input_data, tool_use_id, context):
        """Seguridad: bloquea leer o editar archivos fuera del repo de ejemplo."""
        entrada = input_data.get("tool_input", {})
        ruta = entrada.get("file_path") or entrada.get("path")
        if ruta and not Path(ruta).is_absolute():
            ruta = str(repo / ruta)   # las rutas relativas son relativas al cwd del agente (el repo)
        patron = str(entrada.get("pattern") or "") if input_data.get("tool_name") == "Glob" else ""
        if patron.startswith(("/", "~")) or ".." in Path(patron).parts:
            ruta = patron   # un patrón de Glob absoluto o con .. también sale del repo
        if ruta and (ruta == patron or not Path(ruta).resolve().is_relative_to(repo.resolve())):
            alerta(f"PreToolUse → DENY: {ruta} está fuera del repo")
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": f"Solo puedes trabajar dentro de {repo}"}}
        return {}

    from claude_agent_sdk import HookMatcher
    opciones = opciones_base(
        system_prompt="Eres un asistente de código. Responde en español y breve.",
        tools=D25_TOOLS, allowed_tools=D25_TOOLS, cwd=str(repo), permission_mode="acceptEdits",
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[hook_registro, hook_solo_repo])]},
        max_turns=20,
    )
    nota(f"tools built-in habilitadas: {D25_TOOLS}   ·   cwd: {repo}")
    antes = (repo / "config/limites.json").read_text(encoding="utf-8")
    visual.limpiar_traza()
    tarea = D25_TAREA.format(repo=repo, nuevo=D25_NUEVO_LIMITE)
    if D25_EDIT_RESPALDO == "read_write":
        tarea += ("\nPara el paso 3 haz primero un Edit con old_string exactamente \"10000\". Si falla porque el texto no es "
                  "único, NO amplíes old_string: lee el archivo completo con Read y reescríbelo completo con Write.")
        if "Write" not in D25_TOOLS:
            alerta("D25_EDIT_RESPALDO = \"read_write\" necesita \"Write\" en D25_TOOLS.")
    resultado = asyncio.run(correr_agente(tarea, opciones, "explorar repo"))

    paso("Verificación")
    despues = (repo / "config/limites.json").read_text(encoding="utf-8")
    tabla = Table(title="config/limites.json")
    tabla.add_column("Antes"); tabla.add_column("Después")
    tabla.add_row(escape(antes), escape(despues))
    consola.print(tabla)
    try:
        datos = json.loads(despues)
        (ok if datos.get("limite_reembolso") == D25_NUEVO_LIMITE else alerta)(
            f"limite_reembolso = {datos.get('limite_reembolso')} (esperado {D25_NUEVO_LIMITE})")
        (ok if datos.get("limite_credito") == 10000 else alerta)(
            f"limite_credito = {datos.get('limite_credito')} (debe seguir en 10000)")
    except json.JSONDecodeError:
        alerta("El JSON quedó inválido después de la edición.")

    texto_final = getattr(resultado, "result", "") or ""
    encontrados = {r for r in USOS_REALES_25 if Path(r).name in texto_final}
    faltantes = USOS_REALES_25 - encontrados
    (ok if not faltantes else alerta)(
        f"Usos de processRefund reportados: {len(encontrados)}/{len(USOS_REALES_25)}"
        + (f"  · faltaron: {', '.join(sorted(faltantes))}" if faltantes else ""))

    try:
        datos_fin = json.loads(despues)
    except json.JSONDecodeError:
        datos_fin = {}
    diagrama_seguro(diagrama_2_5, list(visual.TRAZA), len(encontrados), len(USOS_REALES_25),
                    datos_fin.get("limite_reembolso") == D25_NUEVO_LIMITE, datos_fin.get("limite_credito") == 10000)
    if D25_EDIT_RESPALDO == "read_write":
        uso_write = any(n == "Write" for n, _ in llamadas)
        bien = datos_fin.get("limite_reembolso") == D25_NUEVO_LIMITE and datos_fin.get("limite_credito") == 10000
        (ok if uso_write and bien else alerta)(f"Respaldo Read + Write: {'sí' if uso_write else 'no'} · límites bien: {'sí' if bien else 'no'}")
        visual.registrar_resultado(final="read_write" if uso_write and bien else "usos_perdidos",
                                   texto=f"Edit no único → Write: {'sí' if uso_write else 'no'} · límites bien: {'sí' if bien else 'no'}")
    conteo = Table(title="¿Qué tools usó y cuántas veces?")
    conteo.add_column("Tool", style="yellow"); conteo.add_column("Veces", justify="center"); conteo.add_column("Para qué sirve")
    for nombre in dict.fromkeys(n for n, _ in llamadas):
        conteo.add_row(nombre, str(sum(1 for n, _ in llamadas if n == nombre)), EXPLICACION_TOOLS_25.get(nombre, ""))
    consola.print(conteo)
    concepto(
        "1) Quita 'Grep' de D25_TOOLS: el agente tendrá que abrir archivo por archivo con Read (más turnos y tokens).\n"
        "2) Quita 'Glob': encontrar los *.test.ts se vuelve más difícil.\n"
        "3) Cambia la tarea para que edite un texto repetido y observa el error de Edit por texto no único.\n"
        f"El repo queda en {repo} por si quieres revisarlo.", "🧪 Experimenta")


# =====================================================================
#  DIAGRAMAS DE LA CORRIDA (modo HTML)
# =====================================================================
# Cada demo, al terminar, arma un diagrama con lo que pasó en ESA corrida. Las funciones para dibujar
# (svg_grafo, svg_barras, agregar_diagrama…) están en visual.py. Aquí solo se decide QUÉ dibujar.

def diagrama_2_1(modos: list[str], resultados: dict) -> None:
    columnas = 1 + len(modos)
    nodos = [{"id": "h0", "fila": 0, "col": 0, "tipo": "nota", "texto": "Consulta del cliente\n(tool esperada)"}]
    for j, modo in enumerate(modos, start=1):
        nodos.append({"id": f"h{j}", "fila": 0, "col": j, "tipo": "codigo", "texto": f"Descripciones {modo}\ntool que eligió Claude"})
    aristas = []
    for i, (consulta, esperada) in enumerate(D21_CONSULTAS, start=1):
        nodos.append({"id": f"q{i}", "fila": i, "col": 0, "tipo": "nota", "texto": f"{corto(consulta, 70)}\n(esperada: {esperada})"})
        for j, modo in enumerate(modos, start=1):
            f = resultados[modo][i - 1]
            nodos.append({"id": f"r{i}_{j}", "fila": i, "col": j, "tipo": "ok" if f["acierto"] else "bloqueo",
                          "texto": ("✔ " if f["acierto"] else "✘ ") + f["elegida"]})
    aciertos = {m: sum(f["acierto"] for f in resultados[m]) for m in modos}
    n = len(D21_CONSULTAS)
    if len(modos) == 2:
        visual.registrar_resultado(final="comparacion", texto=f"Mínimas {aciertos['minimas']}/{n} · completas {aciertos['completas']}/{n}")
        conclusion = (f"Con descripciones mínimas acertó {aciertos['minimas']}/{n}; con completas, {aciertos['completas']}/{n}. "
                      "Los errores suelen estar en los casos frontera: ahí es donde la descripción (con sus límites) decide.")
    else:
        conclusion = f"Acertó {aciertos[modos[0]]}/{n} con descripciones {modos[0]}."
        a = aciertos[modos[0]]
        visual.registrar_resultado(final="acierta" if a == n else ("regla_gana" if D21_CONFLICTO_EN_SYSTEM else "confunde"),
                                   texto=f"Eligió la tool correcta en {a}/{n} consultas")
    if D21_CONFLICTO_EN_SYSTEM:
        conclusion += " Ojo: el system prompt tiene una regla con palabra clave que puede ganarle a las descripciones."
    agregar_diagrama("Demo 2.1 · ¿Qué tool eligió Claude en cada consulta?", svg_grafo(nodos, aristas, columnas=columnas),
                     "Cada fila es una consulta. Verde: eligió la tool correcta. Rojo: eligió otra.", conclusion)


def _resumen_resultado_22(contenido, es_error: bool) -> str:
    if isinstance(contenido, str):
        return contenido
    if "errorCategory" in contenido:
        return f"is_error · {contenido['errorCategory']} · reintentar: {'sí' if contenido.get('isRetryable') else 'no'}"
    pedidos = contenido.get("pedidos", [])
    if contenido.get("consulta_exitosa"):
        return f"éxito · {len(pedidos)} pedidos (vacío válido)"
    return f"{len(pedidos)} pedidos, sin error" if pedidos else "lista vacía, sin error"


def diagrama_2_2(filas: list[dict]) -> None:
    formatos = list(dict.fromkeys(f["formato"] for f in filas))
    escenarios = list(dict.fromkeys(f["escenario"] for f in filas))
    columnas = 2 + len(formatos)
    nodos = [{"id": "h0", "fila": 0, "col": 0, "tipo": "nota", "texto": "Escenario"}]
    for j, formato in enumerate(formatos, start=1):
        nodos.append({"id": f"h{j}", "fila": 0, "col": j, "tipo": "codigo", "texto": f"Error {formato}\nlo que recibió Claude"})
    nodos.append({"id": "hd", "fila": 0, "col": columnas - 1, "tipo": "codigo", "texto": "Lo que debería pasar"})
    aristas = []
    for i, esc in enumerate(escenarios, start=1):
        nodos.append({"id": f"e{i}", "fila": i, "col": 0, "tipo": "nota", "texto": esc})
        for j, formato in enumerate(formatos, start=1):
            f = next(x for x in filas if x["escenario"] == esc and x["formato"] == formato)
            primero = f["devolvio"][0] if f["devolvio"] else "sin llamada a la tool"
            if formato == "estructurado":
                tipo = "ok"
            elif esc == "sin_pedidos":
                tipo = "nota"     # vacío válido, pero indistinguible de una falla
            else:
                tipo = "bloqueo"
            nodos.append({"id": f"c{i}_{j}", "fila": i, "col": j, "tipo": tipo,
                          "texto": f"{corto(primero, 46)}\nllamadas a la tool: {f['llamadas']}"})
        nodos.append({"id": f"d{i}", "fila": i, "col": columnas - 1, "tipo": "codigo",
                      "texto": corto(D22_CASOS[esc]["deberia"], 70)})
    conclusion = ("Con el formato genérico, en 'caido' Claude recibe una lista vacía sin error: no tiene cómo saber que el "
                  "sistema falló y le dice al cliente algo falso. Con errores estructurados, cada respuesta trae la "
                  "categoría y si conviene reintentar." if "generico" in formatos else
                  "Cada respuesta trae errorCategory e isRetryable: Claude sabe si reintentar, pedir otro dato o escalar.")
    agregar_diagrama("Demo 2.2 · Qué recibió Claude en cada escenario", svg_grafo(nodos, aristas, columnas=columnas),
                     "Rojo: Claude no puede saber qué pasó. Amarillo: vacío válido, pero se ve igual que una falla. "
                     "Verde: el error (o el vacío) viene explicado.", conclusion)


def diagrama_2_3a(resumen: list[tuple]) -> None:
    n = len(D23_CONSULTAS)
    aciertos = [(etq, a, "ok" if a == n else "bloqueo", f"{a}/{n}") for etq, a, _ in resumen]
    base = resumen[0][2]
    tokens = [(etq, prom, "bloqueo" if prom > base * 1.2 else "codigo", f"{prom:,.0f} tokens") for etq, _, prom in resumen]
    svg = subtitulo("Aciertos (eligió la tool esperada)", svg_barras(aciertos, maximo=n)) + \
        subtitulo("Tokens de entrada promedio por request", svg_barras(tokens))
    if len(resumen) == 1:
        etq, a, prom = resumen[0]
        visual.registrar_resultado(parte="A", final=("confunde_18" if a < n else "gasta_18") if etq.startswith("18") else "menos_mejor",
                                   texto=f"{etq}: aciertos {a}/{n} · {prom:,.0f} tokens de entrada promedio")
        agregar_diagrama(f"Demo 2.3 · Parte A: {etq}", svg,
                         "Más tools = más opciones parecidas para confundirse, y más tokens en cada llamada.",
                         f"Con {etq} acertó {a}/{n} y cada request llevó {prom:,.0f} tokens de entrada. "
                         "Compara con la otra configuración (D23_TOOLS_A).")
        return
    (_, a4, t4), (_, a18, t18) = resumen[0], resumen[-1]
    visual.registrar_resultado(parte="A", final="menos_mejor" if a18 < a4 else "gasta_18",
                               texto=f"Aciertos: {a4}/{n} con 4 tools y {a18}/{n} con 18")
    conclusion = (f"Con 18 tools acertó {a18}/{n} contra {a4}/{n} con 4, y cada request costó "
                  f"{t18 / t4:.1f} veces más tokens de entrada: cada definición de tool viaja en cada request." if t4 else "")
    agregar_diagrama("Demo 2.3 · Parte A: 4 tools enfocadas vs. 18 que se traslapan", svg,
                     "Más tools = más opciones parecidas para confundirse, y más tokens en cada llamada.", conclusion)


def diagrama_2_3b(filas: list[tuple]) -> None:
    errores = [modo for modo, stop, _ in filas if stop == "error 400"]
    visual.registrar_resultado(parte="B", final="error400" if errores else "fuerza",
                               texto=("Error 400 con: " + ", ".join(errores)) if errores else "any y tool forzaron una llamada a tool")
    nodos = [{"id": "m", "fila": 0, "completo": True, "tipo": "nota", "texto": "Mensaje del cliente\n" + corto(D23_PREGUNTA_B, 90)}]
    aristas = []
    for i, (modo, stop, hizo) in enumerate(filas):
        if stop == "error 400":
            tipo, texto = "bloqueo", f"tool_choice = {modo}\nerror 400: este modelo no lo acepta"
        elif hizo == "(texto)":
            tipo, texto = "claude", f"tool_choice = {modo}\nrespondió con texto ({stop})"
        else:
            tipo, texto = "codigo", f"tool_choice = {modo}\nllamó {hizo} ({stop})"
        nodos.append({"id": f"r{i}", "fila": 1, "tipo": tipo, "texto": texto})
        aristas.append(("m", f"r{i}", ""))
    agregar_diagrama("Demo 2.3 · Parte B: el mismo mensaje con 3 modos de tool_choice", svg_grafo(nodos, aristas),
                     "auto: Claude decide. any: debe usar alguna tool. tool: debe usar esa tool.",
                     "auto puede contestar con texto; any y tool garantizan una llamada (aunque no haga falta). "
                     "Para salida estructurada garantizada en el examen: any o tool forzada.")


def diagrama_2_3c(filas: list[tuple]) -> None:
    nodos = [{"id": "d", "fila": 0, "completo": True, "tipo": "nota", "texto": "Documento de tipo desconocido\n" + corto(D23_DOCUMENTO_C.splitlines()[0], 80)}]
    aristas, previo = [], "d"
    for i, (etiqueta, stop, hizo) in enumerate(filas):
        if stop == "error 400":
            tipo, texto = "bloqueo", f"Paso {etiqueta}\nerror 400: este modelo no lo acepta"
        elif hizo == "(texto)":
            tipo, texto = "claude", f"Paso {etiqueta}\ncontestó con texto"
        else:
            tipo, texto = "codigo", f"Paso {etiqueta}\nllamó {hizo}"
        nodos.append({"id": f"p{i}", "fila": i + 1, "tipo": tipo, "texto": texto, "paso": i + 1})
        aristas.append((previo, f"p{i}", "")); previo = f"p{i}"
    agregar_diagrama("Demo 2.3 · Parte C: tool forzada → any → auto con un documento real", svg_grafo(nodos, aristas),
                     "Forzar una tool ordena los pasos; any obliga a elegir un schema; auto deja contestar en texto.",
                     "Uso real de tool_choice: no sabes el tipo de documento, pero sí quieres que SIEMPRE salga en uno de tus schemas.")


def diagrama_2_4(traza: list[dict], con_resources: bool) -> None:
    nodos = [{"id": "ag", "fila": 0, "col": 0, "tipo": "claude", "texto": "Agente (Agent SDK)\nClaude decide qué tool usar"},
             {"id": "cl", "fila": 0, "col": 1, "tipo": "codigo", "texto": "Cliente MCP\n(lo maneja el SDK)"},
             {"id": "sv", "fila": 0, "col": 2, "tipo": "hook", "texto": "Servidor inventario\n(stdio, subproceso)"}]
    aristas = [("ag", "cl", ""), ("cl", "sv", "stdio")]
    previo = "ag"
    for k, t in enumerate(traza, start=1):
        nombre = t["nombre"].replace("mcp__inventario__", "")
        entrada = ", ".join(f"{a}={corto(b, 18)}" for a, b in (t["entrada"] or {}).items())
        nodos.append({"id": f"t{k}", "fila": k, "col": 0, "tipo": "claude", "texto": f"pide {nombre}\n{corto(entrada, 40)}"})
        res = "is_error: " + corto(t["resultado"], 60) if t["error"] else corto(t["resultado"], 70) or "(sin resultado)"
        nodos.append({"id": f"r{k}", "fila": k, "col": 1, "completo": False, "tipo": "bloqueo" if t["error"] else "ok", "texto": res})
        aristas += [(previo, f"t{k}", ""), (f"t{k}", f"r{k}", "")]
        previo = f"t{k}"
    errores = sum(1 for t in traza if t["error"])
    conclusion = (f"El agente hizo {len(traza)} llamadas por MCP"
                  + (f"; {errores} regresaron con is_error y la descripción estructurada del servidor, así sabe qué corregir."
                     if errores else ".")
                  + (" Con resources, puede leer el catálogo completo en vez de buscar a ciegas." if con_resources else ""))
    agregar_diagrama("Demo 2.4 · El agente usando tu servidor MCP", svg_grafo(nodos, aristas, columnas=3),
                     "Arriba: quién habla con quién. Abajo: cada llamada que hizo el agente y lo que regresó el servidor.",
                     conclusion)


def diagrama_2_5(traza: list[dict], encontrados: int, total: int, limite_ok: bool, credito_ok: bool) -> None:
    visual.registrar_resultado(final="completo" if encontrados == total and limite_ok and credito_ok else "usos_perdidos",
                               texto=f"Usos encontrados: {encontrados}/{total} · límite editado bien: {'sí' if limite_ok and credito_ok else 'no'}")
    nodos, aristas, previo = [], [], None
    for k, t in enumerate(traza, start=1):
        e = t["entrada"] or {}
        detalle = re.sub(r".*/tiendita_repo_[^/]+/", "", str(e.get("pattern") or e.get("file_path") or e.get("path") or ""))
        if t["nombre"] == "Edit":
            detalle = f"old_string: {corto(e.get('old_string', ''), 40)}"
        nodos.append({"id": f"c{k}", "fila": k, "col": 0, "tipo": "claude", "texto": f"{k} · {t['nombre']}\n{corto(detalle, 44)}"})
        if t["error"]:
            res_tipo, res = "bloqueo", "error: " + corto(t["resultado"], 70)
        else:
            res_tipo, res = "codigo", corto(re.sub(r"/\S*/tiendita_repo_[^/]+/", "", t["resultado"]), 80) or "(sin salida)"
        nodos.append({"id": f"r{k}", "fila": k, "col": 1, "tipo": res_tipo, "texto": res})
        aristas.append((f"c{k}", f"r{k}", ""))
        if previo:
            aristas.append((previo, f"c{k}", ""))
        previo = f"c{k}"
    fila = len(traza) + 1
    nodos.append({"id": "v1", "fila": fila, "col": 0, "tipo": "ok" if encontrados == total else "bloqueo",
                  "texto": f"Usos de processRefund reportados\n{encontrados}/{total}"})
    nodos.append({"id": "v2", "fila": fila, "col": 1, "tipo": "ok" if (limite_ok and credito_ok) else "bloqueo",
                  "texto": f"limite_reembolso: {'✔' if limite_ok else '✘'} · limite_credito intacto: {'✔' if credito_ok else '✘'}"})
    if previo:
        aristas.append((previo, "v1", ""))
    conteo = {}
    for t in traza:
        conteo[t["nombre"]] = conteo.get(t["nombre"], 0) + 1
    usadas = ", ".join(f"{n} ×{c}" for n, c in conteo.items())
    errores_edit = sum(1 for t in traza if t["nombre"] == "Edit" and t["error"])
    conclusion = (f"Tools usadas: {usadas}. Reportó {encontrados}/{total} usos de processRefund"
                  + (" (le faltaron los que llegan por el alias del barrel)" if encontrados < total else "")
                  + (f". {errores_edit} Edit fallaron por texto no único y tuvo que ampliar el anchor" if errores_edit else "")
                  + ".")
    agregar_diagrama("Demo 2.5 · La exploración paso a paso", svg_grafo(nodos, aristas, columnas=2),
                     "Izquierda: cada tool built-in que pidió Claude, en orden. Derecha: lo que regresó. Abajo: la verificación.",
                     conclusion)


# =====================================================================
#  MENÚ
# =====================================================================

GUIAS = {
    "2.1": GUIA_2_1,
    "2.2": GUIA_2_2,
    "2.3": GUIA_2_3,
    "2.4": GUIA_2_4,
    "2.5": GUIA_2_5,
}


DEMOS = {
    "2.1": ("Descripciones de tools y selección", demo_2_1),
    "2.2": ("Errores estructurados vs genéricos", demo_2_2),
    "2.3": ("Demasiadas tools y tool_choice", demo_2_3),
    "2.4": ("Servidor MCP propio + Agent SDK", demo_2_4),
    "2.5": ("Tools built-in: Grep, Glob, Read, Edit (Agent SDK)", demo_2_5),
}


def main() -> None:
    visual.aplicar_ajustes(globals())   # si lo corre el panel web (panel.py), aplica sus ajustes a esta corrida
    eleccion = sys.argv[1] if len(sys.argv) > 1 else None
    if eleccion in ("guia", "guía"):
        # Solo leer: no necesita API key ni llama a Claude
        claves = [sys.argv[2]] if len(sys.argv) > 2 and sys.argv[2] in GUIAS else list(GUIAS)
        for clave in claves:
            titulo(f"Demo {clave} · {DEMOS[clave][0]}")
            mostrar_guia(clave, forzar=True, pausa=False)
        return
    if eleccion not in DEMOS and eleccion != "todas":
        tabla = Table(title="CCAR-F · Lab del Dominio 2")
        tabla.add_column("Demo"); tabla.add_column("Tema")
        for clave, (nombre, _) in DEMOS.items():
            tabla.add_row(clave, nombre)
        tabla.add_row("todas", "Correr todas en orden")
        tabla.add_row("guia", "Solo leer las guías (no llama a Claude)")
        consola.print(tabla)
        mostrar_estado_html()
        eleccion = consola.input("[bold]¿Qué demo quieres correr? [/]").strip()
        if eleccion in ("guia", "guía"):
            sys.argv[1:] = ["guia"]
            return main()
    verificar_api_key()
    nota(f"Modelo: {MODELO}")
    nota(f"Modo HTML: {idioma.salida('encendido') + ' → ' + visual.carpeta_relativa() + '/' if GUARDAR_HTML else idioma.salida('apagado')}")
    try:
        if eleccion == "todas":
            for _, funcion in DEMOS.values():
                visual.correr_demo(funcion)
        elif eleccion in DEMOS:
            visual.correr_demo(DEMOS[eleccion][1])
        else:
            alerta(f"No existe la demo '{eleccion}'.")
    finally:
        p_in, p_out = PRECIOS.get(MODELO, (0, 0))   # tokens y costo de la corrida (el panel los muestra)
        visual.registrar_resultado(**uso_y_costo(p_in, p_out))
        if USO_TOTAL["llamadas"] or USO_SDK["turnos"]:
            resumen_costo()
        if GUARDAR_HTML:
            guardar_html(eleccion)


if __name__ == "__main__":
    main()

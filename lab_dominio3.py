"""
=====================================================================
 CCAR-F · LAB DEL DOMINIO 3: Claude Code Configuration & Workflows
=====================================================================

Demos ejecutables, una por subdominio. Todas usan el caso de
"La Tiendita" (tienda en línea) con datos FALSOS. Cada demo crea un
proyecto de prueba en una carpeta temporal y corre Claude Code ahí.

CÓMO CORRERLO
-------------
  1) pip install -r requirements.txt   (dentro de tu entorno virtual)
  2) Copia .env.example como .env y pega ahí tu API key (ver README).
     Si no hay .env, se usa la variable de entorno ANTHROPIC_API_KEY.
  3) python lab_dominio3.py          -> muestra el menú
     python lab_dominio3.py 3.1      -> corre directo la demo 3.1
     python lab_dominio3.py guia     -> solo lee las guías (no llama a la API)

CÓMO MODIFICARLO
----------------
  * Arriba está la CONFIGURACIÓN GENERAL (modelo, nivel de detalle).
  * Cada demo tiene su propio bloque "🔧 CAMBIA AQUÍ" con variables
    comentadas: cámbialas, vuelve a correr y compara la salida.

DEMOS
-----
  3.1  Jerarquía de CLAUDE.md                 (Agent SDK)
  3.2  Slash commands y skills                (Agent SDK)
  3.3  Reglas por ruta en .claude/rules       (Agent SDK)
  3.4  Plan mode vs ejecución directa         (Agent SDK)
  3.5  Refinamiento iterativo: ejemplos y TDD (Messages API)
  3.6  CI/CD con claude -p                    (CLI de Claude Code)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
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
# correr nada (ni gastar):  python lab_dominio3.py guia      (o: guia 3.1)
MOSTRAR_GUIA = True
PAUSA_DESPUES_DE_GUIA = True   # espera un Enter después de la guía (ideal para explicar antes de correr)

# Modo HTML: además de la terminal, cada corrida se guarda como página web con un diagrama
# de lo que pasó, en salidas_html/dominio3/. Cada corrida es un archivo nuevo (no se sobrescribe)
# y salidas_html/dominio3/index.html las recorre con Anterior / Siguiente para comparar: cambia una
# variable, vuelve a correr la demo y compara los diagramas. Ejemplos de lo que vas a ver, sin correr
# nada: ejemplos_html/dominio3/index.html
#   True  -> encendido (para apagarlo en una sola corrida:  python lab_dominio3.py 3.1 --sin-html)
#   False -> solo terminal  (para encenderlo en una sola corrida:  python lab_dominio3.py 3.1 --html)
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
GUARDAR_HTML = visual.configurar(dominio=3, modo_html=MODO_HTML)
consola = Console(record=GUARDAR_HTML)
visual.usar_consola(consola)
# Ayudantes compartidos (llamar_claude, mostrar_request, correr_agente, contadores de costo…): viven en
# comun.py y comun.instalar() los define aquí mismo, con la configuración de este lab.
import comun  # noqa: E402
from comun import (  # noqa: E402
    PRECIOS, USO_TOTAL, USO_SDK, titulo, paso, concepto,
    ok, alerta, nota, texto_de, mostrar_json, verificar_api_key,
    llamar_claude, sumar_uso_sdk, uso_y_costo, resumen_costo, guardar_html, mostrar_estado_html,
    correr_agente, opciones_base, crear_proyecto, mostrar_archivo,
)
comun.instalar(globals())


def mostrar_guia(clave: str, forzar: bool = False, pausa: bool = True) -> None:
    """Imprime la guía (markdown) de una demo. Las guías están arriba de cada demo: GUIA_x_y."""
    if not (MOSTRAR_GUIA or forzar):
        return
    if DETALLE == "basico" and not forzar:
        consola.print(f"[dim]📖 Guía de esta demo: python lab_dominio3.py guia {clave}  ·  "
                      f"más detalle: pon DETALLE = \"completo\" arriba del archivo[/]")
        return
    from rich.markdown import Markdown
    consola.print(Panel(Markdown(idioma.guia(clave, GUIAS[clave])), title=f"📖 Guía de la demo {clave}: qué vas a ver",
                        border_style="cyan", padding=(1, 2)))
    if pausa and PAUSA_DESPUES_DE_GUIA and sys.stdin.isatty():
        consola.input("[bold cyan]   Presiona Enter para correr la demo… [/]")


# =====================================================================
#  AYUDANTES DEL DOMINIO 3: PROYECTOS DE PRUEBA Y TRANSCRIPCIONES
# =====================================================================


def mostrar_arbol(raiz: Path, titulo_tabla: str = "Archivos del proyecto") -> None:
    tabla = Table(title=titulo_tabla, show_header=False)
    for archivo in sorted(p for p in raiz.rglob("*") if p.is_file()):
        tabla.add_row(str(archivo.relative_to(raiz)))
    consola.print(tabla)


def ruta_transcripcion(session_id: str | None) -> Path | None:
    """Claude Code guarda cada sesión en ~/.claude/projects/<carpeta>/<session_id>.jsonl."""
    if not session_id:
        return None
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"
    encontrados = list(base.glob(f"*/{session_id}.jsonl"))
    return encontrados[0] if encontrados else None


def instrucciones_cargadas(session_id: str | None, raiz: Path) -> list[dict]:
    """Lee la transcripción y devuelve qué instrucciones cargó Claude Code y en qué momento.

    Nota: el formato de la transcripción es interno de Claude Code y puede cambiar entre
    versiones. Si cambia, esta función simplemente no encuentra nada.
    """
    ruta = ruta_transcripcion(session_id)
    if ruta is None:
        return []
    eventos, ultimo_leido = [], None
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "assistant":
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Read":
                    ultimo_leido = b.get("input", {}).get("file_path")
        adj = d.get("attachment") if d.get("type") == "attachment" else None
        if not isinstance(adj, dict):
            continue
        if adj.get("type") == "instructions":
            for f in adj.get("files", []):
                eventos.append({"momento": "al iniciar la sesión", "archivo": f.get("path", ""),
                                "tipo": f.get("type", ""), "globs": None})
        elif adj.get("type") == "nested_memory":
            contenido = adj.get("content") or {}
            leido = Path(ultimo_leido).name if ultimo_leido else "un archivo"
            eventos.append({"momento": f"después de leer {leido}", "archivo": adj.get("path", ""),
                            "tipo": contenido.get("type", ""), "globs": contenido.get("globs")})
    for e in eventos:
        try:
            e["archivo"] = str(Path(e["archivo"]).resolve().relative_to(raiz))
        except ValueError:
            pass
    return eventos


def mostrar_instrucciones(session_id: str | None, raiz: Path) -> list[dict]:
    eventos = instrucciones_cargadas(session_id, raiz)
    if not eventos:
        alerta("No encontré la transcripción de la sesión (o su formato cambió). La demo sigue igual: "
               "fíjate en la respuesta del agente.")
        return []
    tabla = Table(title="📂 Qué instrucciones cargó Claude Code y cuándo (leído de la transcripción)")
    tabla.add_column("Momento", style="cyan"); tabla.add_column("Archivo", style="yellow")
    tabla.add_column("Tipo"); tabla.add_column("Se activa con")
    for e in eventos:
        tabla.add_row(e["momento"], e["archivo"], e["tipo"], ", ".join(e["globs"]) if e["globs"] else "—")
    consola.print(tabla)
    nota(f"Transcripción: {ruta_transcripcion(session_id)}")
    return eventos


def hook_solo_proyecto(raiz: Path):
    """PreToolUse de seguridad: niega Read/Glob/Grep/Edit/Write fuera del proyecto de prueba."""
    raiz = raiz.resolve()

    async def hook(input_data, tool_use_id, context):
        entrada = input_data.get("tool_input") or {}
        rutas = [entrada.get(k) for k in ("file_path", "path", "notebook_path") if entrada.get(k)]
        patron = str(entrada.get("pattern") or "") if input_data.get("tool_name") == "Glob" else ""
        fuera = patron.startswith(("/", "~")) or ".." in Path(patron).parts
        for r in rutas:
            r = Path(str(r)).expanduser()
            fuera = fuera or not (r if r.is_absolute() else raiz / r).resolve().is_relative_to(raiz)
        if fuera:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": "Solo puedes trabajar dentro del proyecto de prueba."}}
        return {}
    return hook


def opciones_claude_code(raiz: Path, fuentes: list[str], herramientas: list[str], **extra):
    """Opciones parecidas a Claude Code real: prompt de Claude Code + configuración del proyecto."""
    from claude_agent_sdk import HookMatcher
    hooks = dict(extra.pop("hooks", None) or {})
    hooks["PreToolUse"] = [HookMatcher(matcher=None, hooks=[hook_solo_proyecto(raiz)])] + list(hooks.get("PreToolUse", []))
    extra["hooks"] = hooks
    return opciones_base(
        cwd=str(raiz), setting_sources=fuentes,
        system_prompt={"type": "preset", "preset": "claude_code",
                       "append": "Responde en español y de forma breve."},
        tools=herramientas, allowed_tools=herramientas, **extra,
    )


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 3.1  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio3.py guia 3.1)
# ---------------------------------------------------------------------
GUIA_3_1 = """
#### De qué trata
Claude Code junta instrucciones de **varios archivos CLAUDE.md** y cada uno tiene un alcance distinto. La pregunta
del examen siempre es la misma: **¿dónde vive esta instrucción y quién la recibe?**

| Archivo | Alcance | ¿Va a git? |
|---|---|---|
| `~/.claude/CLAUDE.md` | Solo tú, en todos tus proyectos | No |
| `CLAUDE.md` (raíz del repo) | Todo el equipo | Sí |
| `CLAUDE.local.md` | Solo tú, en este repo | No (`.gitignore`) |
| `src/api/CLAUDE.md` (subcarpeta) | Quien trabaje en esa carpeta | Sí |
| `@docs/estilo.md` dentro de un CLAUDE.md | Importa otro archivo | Según dónde esté |

La demo no toca tu `~/.claude/CLAUDE.md`. El caso "personal" se muestra con `CLAUDE.local.md`.

#### Qué pasa al correrla, paso a paso
1. Se crea un proyecto de prueba en una carpeta temporal y se imprimen sus 4 archivos de instrucciones:
   - `CLAUDE.md`: español neutro; importa `@docs/estilo.md`.
   - `docs/estilo.md`: montos en MXN con dos decimales y funciones en inglés.
   - `CLAUDE.local.md`: preferencia personal (viñetas cortas).
   - `src/api/CLAUDE.md`: forma de las respuestas de la API.
2. Corre Claude Code con el Agent SDK (prompt de Claude Code + `setting_sources=["project", "local"]` + solo la tool `Read`).
3. Le pregunta qué reglas conoce y le pide leer `src/api/reembolsos.ts`.
4. La tabla **"📂 Qué instrucciones cargó Claude Code y cuándo"** sale de la **transcripción** de la sesión, no de lo
   que diga el modelo:
   - **al iniciar la sesión**: `CLAUDE.md`, `docs/estilo.md` y `CLAUDE.local.md`;
   - **después de leer reembolsos.ts**: `src/api/CLAUDE.md`.
5. Al final, un ✔/✘ por archivo explica por qué se cargó o no.

#### Lo que se le manda a Claude
- `setting_sources` decide qué configuración lee Claude Code: `"project"` = CLAUDE.md, `.claude/` y lo que importen;
  `"local"` = `CLAUDE.local.md`; `"user"` = tu `~/.claude` (la demo **no** lo usa).
- `system_prompt={"type": "preset", "preset": "claude_code"}`: el mismo system prompt que usa Claude Code.

#### Dónde está en el código
- `crear_proyecto()` arma la carpeta temporal.
- `opciones_claude_code()` arma las opciones del agente.
- `instrucciones_cargadas()` lee la transcripción (`~/.claude/projects/.../<session_id>.jsonl`). Ese formato es
  interno de Claude Code: si cambia en una versión futura, la tabla no aparece, pero la demo sigue funcionando.

#### Experimentos
- `D31_USAR_IMPORT = False`: `docs/estilo.md` ya no se carga y el agente deja de conocer la regla de montos.
- `D31_SIMULAR_COMPANERO = True`: corre como alguien nuevo del equipo (`setting_sources=["project"]`).
  `CLAUDE.local.md` desaparece. Es el caso clásico del examen: la regla del equipo estaba en un archivo personal.
  El arreglo es moverla al `CLAUDE.md` del repo.
- Pide leer `src/carrito/total.ts` en vez de `reembolsos.ts`: `src/api/CLAUDE.md` no se carga.

#### Lo que pregunta el examen
- Un compañero nuevo no recibe una instrucción → estaba en `~/.claude/CLAUDE.md` (personal). Va en el CLAUDE.md del repo.
- Importar con `@ruta` (no existe `@import`) para mantener CLAUDE.md modular; `.claude/rules/` para separar por tema.
- `/memory` para ver qué archivos de memoria están cargados y diagnosticar comportamientos inconsistentes.
"""


# =====================================================================
#  DEMO 3.1 · JERARQUÍA DE CLAUDE.md
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# True: el CLAUDE.md raíz importa docs/estilo.md con @docs/estilo.md
D31_USAR_IMPORT = True
# True: corre como un compañero NUEVO del equipo: no tiene tu CLAUDE.local.md
# (equivale a setting_sources=["project"]). Mira qué instrucciones pierde.
D31_SIMULAR_COMPANERO = False
D31_PREGUNTA = ("Antes de hacer nada: ¿qué reglas de este proyecto conoces? Luego lee src/api/reembolsos.ts "
                "y dime qué regla adicional aplica a ese archivo.")
# ------------------------------------------------------------------------


def demo_3_1():
    titulo("DEMO 3.1 · Jerarquía de CLAUDE.md: ¿dónde vive cada instrucción?")
    mostrar_guia("3.1")
    concepto(
        "Claude Code junta instrucciones de varios archivos:\n"
        "  • ~/.claude/CLAUDE.md → personal, en TU máquina (no va a git; tu equipo no lo ve).\n"
        "  • CLAUDE.md en la raíz del repo → del equipo, va a git.\n"
        "  • CLAUDE.local.md → personal para este repo (va en .gitignore).\n"
        "  • CLAUDE.md en subcarpetas → se carga SOLO cuando Claude trabaja con archivos de esa carpeta.\n"
        "  • @ruta/archivo.md dentro de un CLAUDE.md → importa otro archivo (modular).\n"
        "Pregunta clásica: 'un compañero nuevo no recibe las instrucciones' → estaban en un archivo personal."
    )
    raiz_md = "# Proyecto La Tiendita\n- Responde siempre en español neutro.\n"
    if D31_USAR_IMPORT:
        raiz_md += "- Estilo de código y montos: ver @docs/estilo.md\n"
    proyecto = crear_proyecto({
        "CLAUDE.md": raiz_md,
        "docs/estilo.md": "- Los montos van en MXN con dos decimales (p. ej. $1,850.00).\n- Nombres de funciones en inglés.\n",
        "CLAUDE.local.md": "- (Personal de Rafa) Prefiero respuestas en viñetas cortas.\n",
        "src/api/CLAUDE.md": "- Toda respuesta de la API tiene la forma {ok, data, error}.\n",
        "src/api/reembolsos.ts": "export function refund(orderId: string, amount: number) {\n  return { ok: true, data: { orderId, amount }, error: null };\n}\n",
        "src/carrito/total.ts": "export const total = (xs: number[]) => xs.reduce((a, b) => a + b, 0);\n",
    })
    ok(f"Proyecto de prueba: {proyecto}")
    mostrar_arbol(proyecto)
    for ruta in ("CLAUDE.md", "docs/estilo.md", "CLAUDE.local.md", "src/api/CLAUDE.md"):
        mostrar_archivo(proyecto, ruta)

    fuentes = ["project"] if D31_SIMULAR_COMPANERO else ["project", "local"]
    if D31_SIMULAR_COMPANERO:
        alerta("Simulando a un compañero nuevo: setting_sources=['project'] → no ve CLAUDE.local.md.")
    nota(f"setting_sources = {fuentes}   ·   tools = ['Read']")
    opciones = opciones_claude_code(proyecto, fuentes, ["Read"], max_turns=6)
    resultado = asyncio.run(correr_agente(D31_PREGUNTA, opciones, "Claude Code en el proyecto"))

    paso("¿Qué cargó realmente Claude Code?")
    eventos = mostrar_instrucciones(getattr(resultado, "session_id", None), proyecto)
    if eventos:
        cargados = {e["archivo"] for e in eventos}
        for ruta, explicacion in [
            ("CLAUDE.md", "raíz del proyecto, siempre al iniciar"),
            ("docs/estilo.md", "solo si el CLAUDE.md raíz lo importa con @"),
            ("CLAUDE.local.md", "solo si setting_sources incluye 'local'"),
            ("src/api/CLAUDE.md", "solo cuando lee un archivo de src/api/"),
        ]:
            (ok if ruta in cargados else alerta)(f"{ruta}: {'cargado' if ruta in cargados else 'NO cargado'} ({explicacion})")
        visual.registrar_resultado(
            final="pierde_estilo" if "docs/estilo.md" not in cargados else ("pierde_local" if "CLAUDE.local.md" not in cargados else "todas"),
            texto="Cargados: " + ", ".join(sorted(cargados)))
    concepto("1) D31_USAR_IMPORT = False → docs/estilo.md deja de cargarse y el agente ya no conoce la regla de montos.\n"
             "2) D31_SIMULAR_COMPANERO = True → desaparece la preferencia personal: así le pasa a alguien nuevo cuando "
             "la regla del equipo está en un archivo personal. Arreglo: moverla al CLAUDE.md del repo.\n"
             "3) Cambia la pregunta para que lea src/carrito/total.ts: src/api/CLAUDE.md no se carga.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 3.2  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio3.py guia 3.2)
# ---------------------------------------------------------------------
GUIA_3_2 = """
#### De qué trata
Dos formas de empaquetar un flujo para reutilizarlo:

| | Slash command | Skill |
|---|---|---|
| Quién lo dispara | **Tú**: `/revisar-reembolso #12346` | **Claude**, cuando la tarea coincide con la descripción |
| Dónde vive | `.claude/commands/<nombre>.md` | `.claude/skills/<nombre>/SKILL.md` |
| Personal | `~/.claude/commands/` | `~/.claude/skills/` |
| Contexto | Se manda completo al invocarlo | Al inicio solo nombre + descripción; el cuerpo se carga al usarlo |

Regla para decidir: lo que **siempre** aplica va en CLAUDE.md; lo que **tú** invocas, en un command; lo que
**Claude** debe decidir usar, en un skill.

#### Qué pasa al correrla, paso a paso
**Parte A · slash command**
1. Se imprime `.claude/commands/revisar-reembolso.md` con su frontmatter (`description`, `argument-hint`) y su cuerpo.
2. Se manda el prompt `/revisar-reembolso #12346`. Claude Code reemplaza `$ARGUMENTS` por `#12346` y lo envía como
   si tú lo hubieras escrito.
3. El agente lee `politica_reembolsos.md` y `pedidos.json`. Respuesta esperada: **NO CUMPLE**, porque $12,500 supera
   los $10,000.

**Parte B · skill**
1. Se imprime `SKILL.md` con su `description`.
2. Se manda una petición normal: *"¿Qué tal nos fue con los clientes esta semana? Sus comentarios están en resenas.txt…"*.
3. Si Claude decide usar el skill, un hook muestra **"🪝 Skill invocado"**: ahí se carga el cuerpo completo de SKILL.md.
4. Normalmente entrega la tabla de sentimiento y "Atender primero: envío", porque es el problema más repetido.
5. Al final: ✔ o ✘ según si usó el skill.

#### Dónde está en el código
- Los archivos del proyecto están en el diccionario que recibe `crear_proyecto()`, dentro de `demo_3_2()`.
- `DESCRIPCIONES_SKILL_32` tiene la descripción buena y la vaga.
- `hook_skill` es un `PreToolUse` con `matcher="Skill"`: solo registra la invocación.
- Las tools son `Read`, `Glob` y `Skill`; sin la tool `Skill`, Claude no puede invocar skills.

#### Experimentos
- `D32_DESCRIPCION_SKILL = "vaga"` (*"Utilidades varias."*): es probable que Claude **no** use el skill. Es la misma
  lección de la demo 2.1: la descripción decide.
- `D32_PEDIDO = "#12345"`: $1,850 con foto → debería salir CUMPLE.
- Abre la carpeta del proyecto (la ruta sale en pantalla) y crea tu propio comando.

#### Lo que pregunta el examen
- Comando del equipo → `.claude/commands/` (va a git). Personal → `~/.claude/commands/`.
- Frontmatter de skills: `context: fork` corre el skill en un subagente aislado; `allowed-tools` limita qué tools
  usa; `argument-hint` indica qué argumento espera.
- Skill = a demanda; CLAUDE.md = siempre cargado.
"""


# =====================================================================
#  DEMO 3.2 · SLASH COMMANDS Y SKILLS
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D32_PARTE = "ambas"           # "A" (slash command), "B" (skill) o "ambas"
D32_PEDIDO = "#12346"         # argumento que recibe el comando como $ARGUMENTS
# "buena" → la descripción del skill dice cuándo usarlo; "vaga" → "Utilidades varias."
D32_DESCRIPCION_SKILL = "buena"
D32_PREGUNTA_SKILL = "¿Qué tal nos fue con los clientes esta semana? Sus comentarios están en resenas.txt. ¿Qué atiendo primero?"
# ------------------------------------------------------------------------

DESCRIPCIONES_SKILL_32 = {
    "buena": ("Analiza reseñas de clientes de La Tiendita: clasifica sentimiento, detecta problemas repetidos "
              "y sugiere qué atender primero. Úsalo cuando el usuario pida revisar, resumir o priorizar reseñas."),
    "vaga": "Utilidades varias.",
}


def demo_3_2():
    titulo("DEMO 3.2 · Slash commands y skills: flujos reutilizables")
    mostrar_guia("3.2")
    concepto(
        "Slash command = un prompt guardado que TÚ invocas: /revisar-reembolso #12346.\n"
        "  .claude/commands/<nombre>.md (del equipo, va a git) · ~/.claude/commands/ (personal).\n"
        "  $ARGUMENTS se reemplaza por lo que escribes después del comando.\n"
        "Skill = carpeta con SKILL.md que CLAUDE decide usar cuando la tarea coincide con su descripción.\n"
        "  .claude/skills/<nombre>/SKILL.md · Al inicio Claude solo ve nombre + descripción; el cuerpo se carga "
        "cuando lo invoca (progressive disclosure).\n"
        "Regla del examen: siempre aplica → CLAUDE.md · lo invocas tú → command · Claude decide → skill."
    )
    proyecto = crear_proyecto({
        "politica_reembolsos.md": "- Reembolso máximo automático: $10,000 MXN.\n- Más de 30 días desde la entrega: no aplica.\n- Producto dañado con foto: reembolso completo.\n",
        "pedidos.json": json.dumps({"#12345": {"total": 1850, "entregado": "2026-10-28", "motivo": "taza rota, con foto"},
                                     "#12346": {"total": 12500, "entregado": "2026-10-30", "motivo": "vajilla dañada, con foto"}},
                                    ensure_ascii=False, indent=2),
        "resenas.txt": ("1. Me encantó el mantel, llegó rapidísimo.\n2. La taza llegó rota y nadie contesta.\n"
                        "3. Bonita vajilla pero el envío tardó 3 semanas.\n4. El envío tardó muchísimo, otra vez.\n"
                        "5. Todo perfecto, volveré a comprar.\n"),
        ".claude/commands/revisar-reembolso.md": """\
            ---
            description: Revisa si el reembolso de un pedido cumple la política
            argument-hint: <order_id>
            ---
            Lee politica_reembolsos.md y pedidos.json. Dime si el reembolso del pedido $ARGUMENTS
            cumple la política. Responde con CUMPLE o NO CUMPLE, el motivo y el siguiente paso.
            """,
        ".claude/skills/analizar-resenas/SKILL.md": f"""\
            ---
            name: analizar-resenas
            description: {DESCRIPCIONES_SKILL_32[D32_DESCRIPCION_SKILL]}
            ---
            # Analizar reseñas
            1. Clasifica cada reseña: positiva, neutral o negativa.
            2. Agrupa los problemas repetidos (envío, producto dañado, atención).
            3. Entrega una tabla y al final "Atender primero: ..." con el problema más repetido.
            """,
    })
    ok(f"Proyecto de prueba: {proyecto}")
    mostrar_arbol(proyecto)
    herramientas = ["Read", "Glob", "Skill"]

    if D32_PARTE in ("A", "ambas"):
        paso("Parte A · Slash command: lo invocas tú")
        mostrar_archivo(proyecto, ".claude/commands/revisar-reembolso.md")
        nota(f"Al escribir /revisar-reembolso {D32_PEDIDO}, Claude Code reemplaza $ARGUMENTS por '{D32_PEDIDO}' "
             "y manda ese texto como si tú lo hubieras escrito.")
        opciones = opciones_claude_code(proyecto, ["project"], herramientas, max_turns=6)
        res_a = asyncio.run(correr_agente(f"/revisar-reembolso {D32_PEDIDO}", opciones, "slash command"))
        texto_a = (getattr(res_a, "result", "") or "").upper()
        veredicto = "NO CUMPLE" if "NO CUMPLE" in texto_a else ("CUMPLE" if "CUMPLE" in texto_a else "sin veredicto")
        visual.registrar_resultado(parte="A", final="comando", texto=f"/revisar-reembolso {D32_PEDIDO} → {veredicto}")

    if D32_PARTE in ("B", "ambas"):
        paso("Parte B · Skill: Claude decide usarlo según su descripción")
        visual.diagrama_seguro(visual.tarjeta_tal_cual, "Demo 3.2 · La descripción del skill tal cual la lee Claude",
            [("❌ Vaga", "#ff9b9b"), ("✅ Buena", "#8fe0a0")],
            [("description en .claude/skills/reseñas/SKILL.md", [DESCRIPCIONES_SKILL_32["vaga"], DESCRIPCIONES_SKILL_32["buena"]])],
            "Al iniciar la sesión, Claude solo ve el nombre y la description de cada skill; el cuerpo de SKILL.md se carga "
            "cuando decide usarlo. La petición del usuario: «" + D32_PREGUNTA_SKILL + "»",
            "La buena dice qué hace y CUÁNDO usarlo («cuando el usuario pida revisar, resumir o priorizar reseñas»). "
            "Con la vaga, nada le dice que ese skill sirve para esta petición.")
        mostrar_archivo(proyecto, ".claude/skills/analizar-resenas/SKILL.md")
        nota(f"Descripción del skill: '{D32_DESCRIPCION_SKILL}'. Lo único que Claude ve al inicio es nombre + descripción.")
        usos_skill = []

        async def hook_skill(input_data, tool_use_id, context):
            usos_skill.append(input_data.get("tool_input", {}))
            consola.print(Panel(f"Claude decidió invocar el skill: {escape(json.dumps(input_data.get('tool_input', {}), ensure_ascii=False))}\n"
                                "Ahora sí se carga el cuerpo completo de SKILL.md.",
                                title="🪝 Skill invocado", border_style="magenta"))
            return {}

        from claude_agent_sdk import HookMatcher
        opciones = opciones_claude_code(proyecto, ["project"], herramientas, max_turns=8,
                                        hooks={"PreToolUse": [HookMatcher(matcher="Skill", hooks=[hook_skill])]})
        asyncio.run(correr_agente(D32_PREGUNTA_SKILL, opciones, "¿usará el skill?"))
        (ok if usos_skill else alerta)(
            f"¿Usó el skill analizar-resenas? {'Sí' if usos_skill else 'No'} (descripción '{D32_DESCRIPCION_SKILL}')")
        visual.registrar_resultado(parte="B", final="usa_skill" if usos_skill else "no_usa",
                                   texto=f"Usó el skill: {'sí' if usos_skill else 'no'}")
    concepto("1) D32_DESCRIPCION_SKILL = 'vaga' → es probable que Claude NO use el skill: la descripción es lo que "
             "decide (igual que con las tools de la demo 2.1).\n"
             "2) Cambia D32_PEDIDO a '#12345' y compara la respuesta del comando.\n"
             "3) Abre la carpeta del proyecto y agrega tu propio comando en .claude/commands/.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 3.3  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio3.py guia 3.3)
# ---------------------------------------------------------------------
GUIA_3_3 = """
#### De qué trata
Las **reglas por ruta** son archivos en `.claude/rules/` con un frontmatter `paths:` que contiene globs. Claude Code
carga cada regla **solo** cuando trabaja con archivos que coinciden. Así las convenciones de pruebas no ocupan
contexto cuando editas la API, y al revés.

```markdown
---
paths:
  - "**/*.test.ts"
---
# Reglas de pruebas
- Usa describe/it.
```

**¿Por qué no un CLAUDE.md en una subcarpeta?** Porque los tests están **regados por todo el repo**. Un glob
`**/*.test.ts` los alcanza a todos; un CLAUDE.md solo cubre su carpeta.

#### Qué pasa al correrla, paso a paso
1. Se crea un proyecto con dos reglas: `api.md` (`paths: src/api/**/*.ts`) y `tests.md` (`paths: **/*.test.ts`).
2. Se le pide a Claude leer `src/api/reembolsos.ts` y luego `src/carrito/carrito.test.ts`, y decir qué convenciones
   aplican a cada uno.
3. La tabla de la transcripción muestra cuándo se cargó cada regla:
   - `CLAUDE.md` → al iniciar;
   - `.claude/rules/api.md` → después de leer `reembolsos.ts`;
   - `.claude/rules/tests.md` → después de leer `carrito.test.ts`.
   La columna **"Se activa con"** muestra el glob.

#### Dónde está en el código
`demo_3_3()`: las variables `encabezado_api` y `encabezado_tests` agregan o quitan el frontmatter `paths:`.
La tabla sale de `mostrar_instrucciones()`, la misma de la demo 3.1.

#### Experimentos
- `D33_CON_PATHS = False`: las dos reglas aparecen **al iniciar la sesión**, aunque no toques esos archivos.
  Funciona, pero gasta contexto en todo momento.
- Cambia `D33_PREGUNTA` para leer solo `src/carrito/total.ts`: no se carga ninguna regla.

#### Lo que pregunta el examen
- Convenciones para un tipo de archivo regado por el repo → `.claude/rules/` con `paths` (glob), no un CLAUDE.md por carpeta.
- Ventaja: se cargan solo cuando aplican, así que reducen tokens y ruido.
"""


# =====================================================================
#  DEMO 3.3 · REGLAS POR RUTA (.claude/rules con paths)
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# True: cada regla tiene "paths:" en su frontmatter (se carga solo con esos archivos)
# False: las reglas no tienen paths → se cargan SIEMPRE, al iniciar
D33_CON_PATHS = True
D33_PREGUNTA = ("Lee src/api/reembolsos.ts y luego src/carrito/carrito.test.ts. "
                "Para cada archivo dime qué convenciones del proyecto aplican.")
# ------------------------------------------------------------------------


def demo_3_3():
    titulo("DEMO 3.3 · Reglas por ruta: convenciones solo para ciertos archivos")
    mostrar_guia("3.3")
    concepto(
        ".claude/rules/*.md con frontmatter 'paths:' (globs) → la regla se carga SOLO cuando Claude trabaja con "
        "archivos que coinciden. Ahorra contexto y evita ruido.\n"
        "¿Por qué no un CLAUDE.md en una subcarpeta? Porque los tests (*.test.ts) están regados por todo el repo: "
        "un glob los alcanza a todos; un CLAUDE.md solo cubre su carpeta."
    )
    encabezado_api = '---\npaths:\n  - "src/api/**/*.ts"\n---\n' if D33_CON_PATHS else ""
    encabezado_tests = '---\npaths:\n  - "**/*.test.ts"\n---\n' if D33_CON_PATHS else ""
    proyecto = crear_proyecto({
        "CLAUDE.md": "# La Tiendita\n- Código en TypeScript.\n",
        ".claude/rules/api.md": encabezado_api + "# Reglas de la API\n- Valida montos con zod antes de usarlos.\n- Nunca regreses errores sin código HTTP.\n",
        ".claude/rules/tests.md": encabezado_tests + "# Reglas de pruebas\n- Usa describe/it.\n- Solo datos falsos, nunca de clientes reales.\n",
        "src/api/reembolsos.ts": "export function refund(orderId: string, amount: number) {\n  return { ok: true };\n}\n",
        "src/carrito/carrito.test.ts": "import { total } from './total';\ntest('suma', () => expect(total([1, 2])).toBe(3));\n",
        "src/carrito/total.ts": "export const total = (xs: number[]) => xs.reduce((a, b) => a + b, 0);\n",
    })
    ok(f"Proyecto de prueba: {proyecto}")
    mostrar_arbol(proyecto)
    mostrar_archivo(proyecto, ".claude/rules/api.md")
    mostrar_archivo(proyecto, ".claude/rules/tests.md")
    opciones = opciones_claude_code(proyecto, ["project"], ["Read"], max_turns=6)
    resultado = asyncio.run(correr_agente(D33_PREGUNTA, opciones, "reglas por ruta"))
    paso("¿Cuándo se cargó cada regla?")
    eventos = mostrar_instrucciones(getattr(resultado, "session_id", None), proyecto)
    reglas = [e for e in eventos if ".claude/rules/" in e["archivo"].replace("\\", "/")]
    if reglas:
        al_inicio = all(e["momento"] == "al iniciar la sesión" for e in reglas)
        visual.registrar_resultado(final="siempre" if al_inicio else "por_archivo", texto=" · ".join(
            f"{Path(e['archivo']).name}: {idioma.salida(e['momento'])}" for e in reglas))
    nota("Con paths: api.md aparece después de leer reembolsos.ts y tests.md después de leer carrito.test.ts. "
         "Sin paths: ambas aparecen 'al iniciar la sesión'.")
    concepto("1) D33_CON_PATHS = False → las dos reglas se cargan desde el inicio, aunque no toques esos archivos.\n"
             "2) Cambia la pregunta para leer solo src/carrito/total.ts → ninguna regla se carga.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 3.4  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio3.py guia 3.4)
# ---------------------------------------------------------------------
GUIA_3_4 = """
#### De qué trata
**Plan mode** (`permission_mode="plan"`): Claude explora y propone un plan, pero **no puede editar** archivos.
Úsalo cuando la tarea es **grande o ambigua**: conviene ver el plan antes de que se edite nada.
**Plan mode** es para cambios grandes (una migración de 45 archivos), con varias formas válidas o con decisiones de arquitectura. Un cambio claro y acotado (cambiar un valor en 3 archivos) va con **ejecución directa**. El patrón **híbrido** combina ambas: planear → revisar/aprobar → ejecutar.

#### Qué pasa al correrla, paso a paso
El proyecto tiene el límite de reembolso (10000) en 3 lugares: `config/limites.json`, `src/reembolsos.ts` y
`docs/politica.md`. La tarea es cambiarlo a 8000 en todos.

- **`"plan"`**: el agente busca con Grep, lee y propone un plan. Si intenta editar, Claude Code lo bloquea
  (*"Cannot write … while in plan mode"*). Al final verás **"Archivos modificados en plan mode: ninguno"**.
- **`"directo"`**: con `acceptEdits` edita directo.
- **`"hibrido"`** (por defecto): fase 1 en plan mode; fase 2 **en la misma sesión** (`resume`) con `acceptEdits`
  y el mensaje *"Plan aprobado. Impleméntalo."*.

La tabla final muestra qué archivos cambiaron.

#### Dónde está en el código
`demo_3_4()`: `permission_mode="plan"` y luego `permission_mode="acceptEdits"` con `resume=resultado.session_id`.
Las tools son `Read`, `Glob`, `Grep` y `Edit`; aun con `Edit` en `allowed_tools`, plan mode no deja escribir.

#### Experimentos
- Corre los 3 valores de `D34_MODO` y compara la tabla final.
- Lee el plan de la fase 1: ¿encontró los 3 lugares? Si no, el valor del plan es que tú lo notas antes de que se edite nada.
- `D34_TIPO_TAREA = "clara"` o `"ambigua"`: plan mode conviene si hay varias formas válidas o el cambio es grande; un cambio claro y acotado va directo.

#### Lo que pregunta el examen
- Migraciones, cambios de arquitectura o tareas con varias soluciones posibles → plan mode.
- Bug con causa clara en un solo archivo → ejecución directa.
- Explorar con un subagente para no llenar el contexto principal; planear antes de ejecutar.
"""


# =====================================================================
#  DEMO 3.4 · PLAN MODE VS EJECUCIÓN DIRECTA
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# "plan"    → permission_mode="plan": explora y propone, NO puede editar
# "directo" → permission_mode="acceptEdits": edita sin preguntar
# "hibrido" → primero plan; luego se "aprueba" y se ejecuta en la misma sesión
D34_MODO = "hibrido"
# "clara"   → un cambio con una sola forma correcta (bajar un límite en 3 archivos)
# "ambigua" → hay varias formas válidas de hacerlo: conviene elegir con un plan antes de editar
D34_TIPO_TAREA = "ambigua"
D34_TAREA = ("Queremos cambiar el límite de reembolso de 10000 a 8000 en todo el proyecto. "
             "Revisa dónde se usa y hazlo de forma consistente.")
D34_TAREA_AMBIGUA = ("Queremos que los reembolsos grandes necesiten aprobación de una persona. Hay varias formas "
                     "válidas: un flag en config/limites.json, una cola de revisión o un límite por cliente. Hazlo.")
# ------------------------------------------------------------------------


def demo_3_4():
    titulo("DEMO 3.4 · Plan mode vs ejecución directa")
    mostrar_guia("3.4")
    concepto(
        "Plan mode = Claude explora y propone un plan, pero NO puede editar archivos ni ejecutar cambios.\n"
        "Úsalo cuando la tarea es AMBIGUA: hay varias formas válidas de hacerla y conviene elegir antes de editar.\n"
        "Plan mode: cambios grandes, con varias formas válidas o de arquitectura. Directo: un cambio claro y acotado.\n"
        "Patrón híbrido: planear → revisar/aprobar → ejecutar."
    )
    tarea = D34_TAREA if D34_TIPO_TAREA == "clara" else D34_TAREA_AMBIGUA
    nota(f"Tarea {D34_TIPO_TAREA}: {tarea}")
    proyecto = crear_proyecto({
        "config/limites.json": '{\n  "limite_reembolso": 10000,\n  "limite_credito": 10000\n}\n',
        "src/reembolsos.ts": "export const LIMITE = 10000; // debe coincidir con config/limites.json\n",
        "docs/politica.md": "Reembolsos automáticos hasta $10,000 MXN.\n",
    }, prefijo="tiendita_repo_")
    ok(f"Proyecto de prueba: {proyecto}")
    mostrar_arbol(proyecto)
    antes = {p: (proyecto / p).read_text(encoding="utf-8") for p in ("config/limites.json", "src/reembolsos.ts", "docs/politica.md")}
    herramientas = ["Read", "Glob", "Grep", "Edit"]

    if D34_MODO in ("plan", "hibrido"):
        paso("Fase 1 · permission_mode = 'plan'")
        opciones = opciones_claude_code(proyecto, [], herramientas, max_turns=10, permission_mode="plan")
        resultado = asyncio.run(correr_agente(tarea + " Primero propón un plan.", opciones, "plan mode"))
        cambios = [p for p in antes if (proyecto / p).read_text(encoding="utf-8") != antes[p]]
        (ok if not cambios else alerta)(f"Archivos modificados en plan mode: {cambios or 'ninguno'}")
        denegados = getattr(resultado, "permission_denials", None) or []
        if denegados:
            nota(f"Intentos de edición bloqueados por plan mode: {len(denegados)}")
        if D34_MODO == "hibrido" and resultado is not None:
            paso("Fase 2 · Revisaste el plan y lo apruebas → misma sesión, ahora con acceptEdits")
            opciones = opciones_claude_code(proyecto, [], herramientas, max_turns=12, permission_mode="acceptEdits",
                                            resume=resultado.session_id)
            asyncio.run(correr_agente("Plan aprobado. Impleméntalo.", opciones, "ejecución tras aprobar"))
    else:
        paso("Ejecución directa · permission_mode = 'acceptEdits'")
        opciones = opciones_claude_code(proyecto, [], herramientas, max_turns=12, permission_mode="acceptEdits")
        asyncio.run(correr_agente(tarea, opciones, "directo"))

    tabla = Table(title="¿Qué archivos cambiaron?")
    tabla.add_column("Archivo"); tabla.add_column("¿Cambió?")
    cambiados = []
    for p in antes:
        cambio = (proyecto / p).read_text(encoding="utf-8") != antes[p]
        cambiados += [p] if cambio else []
        tabla.add_row(p, "[green]sí[/]" if cambio else "no")
    consola.print(tabla)
    if D34_MODO != "directo" and D34_TIPO_TAREA == "clara":
        final = "innecesario"
    elif D34_MODO == "plan":
        final = "no_edita"
    elif D34_MODO == "hibrido":
        final = "plan_luego"
    else:
        final = "edita_sin_plan" if D34_TIPO_TAREA == "clara" else "elige_solo"
    if D34_MODO != "plan" and not cambiados:
        final = None   # debía editar y no cambió nada: el ticket no inventa un resultado
    elif D34_MODO == "plan" and cambiados:
        final = None
    visual.registrar_resultado(final=final, texto=f"Tarea {D34_TIPO_TAREA} · archivos que cambiaron: {', '.join(cambiados) or 'ninguno'}")
    concepto("Compara los 3 modos. En 'plan' ningún archivo cambia aunque el agente lo intente: el bloqueo lo hace "
             "Claude Code, no el prompt. En 'hibrido' el cambio ocurre solo después de aprobar.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 3.5  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio3.py guia 3.5)
# ---------------------------------------------------------------------
GUIA_3_5 = """
#### De qué trata
Cómo corregir un resultado que no sale como quieres. Las técnicas del examen:
- **Ejemplos concretos** de entrada → salida, en lugar de describir con adjetivos.
- **TDD**: primero las pruebas; luego pides el código y le compartes **las pruebas que fallaron**.
- **Interview pattern**: en tareas poco claras, que Claude te haga preguntas antes de implementar.
- Arreglos **relacionados** en un solo mensaje; **independientes**, uno por uno.

#### Qué pasa al correrla, paso a paso
La tarea es escribir `normalizar_telefono(texto)` para teléfonos mexicanos. Hay 8 pruebas en `CASOS_35`, incluidos
casos frontera: `044 664…`, `52 664…` sin `+`, `"123"` → `None` y un texto con prefijo `tel:`.

- **`"vago"`**: solo se describe en una frase. Una ronda.
- **`"ejemplos"`**: la misma frase + 3 ejemplos de entrada → salida, elegidos entre los casos frontera (paréntesis, `044` y uno inválido). Una ronda. La guía pide 2–3 ejemplos: más no es mejor.
- **`"tdd"`** (por defecto): empieza vago y, en cada ronda, le manda a Claude solo las pruebas que fallaron, con
  entrada, obtenido y esperado. Hasta `D35_MAX_RONDAS`.

En cada ronda verás el código que escribió Claude, la tabla de pruebas (✔/✘) y "Pasaron X/8". Al final, una tabla
con el progreso por ronda.

#### Seguridad: el código se ejecuta
El código que escribe Claude se ejecuta en **un proceso aparte** (`python -I`), con **límite de 10 segundos**,
dentro de una carpeta temporal. Si prefieres solo verlo, pon `D35_EJECUTAR_CODIGO = False`.

#### Dónde está en el código
`CASOS_35`, `PETICION_VAGA_35`, `PETICION_EJEMPLOS_35`, `_extraer_codigo()`, `_correr_pruebas()` y `demo_3_5()`
(el `for ronda`, donde se arma el mensaje con las fallas).

#### Experimentos
- Corre los 3 modos y compara. Lo usual: `"vago"` falla en los casos frontera, `"ejemplos"` acierta más desde la
  primera ronda y `"tdd"` converge en 2 o 3 rondas.
- Agrega un caso nuevo a `CASOS_35` (por ejemplo, con extensión `ext. 12`) y mira cómo lo resuelve TDD.

#### Lo que pregunta el examen
- Las descripciones en prosa se interpretan de forma inconsistente → da 2 o 3 ejemplos concretos.
- Iterar compartiendo las pruebas que fallan (entrada, obtenido y esperado) converge mejor que "no funciona, arréglalo".
"""


# =====================================================================
#  DEMO 3.5 · REFINAMIENTO ITERATIVO
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# "vago"     → solo una descripción en palabras
# "ejemplos" → descripción + ejemplos concretos de entrada → salida
# "tdd"      → empieza vago y en cada ronda le pasa las pruebas que FALLARON
D35_MODO = "tdd"
D35_MAX_RONDAS = 3
# Seguridad: el código que escribe Claude se ejecuta en un proceso aparte, con
# tiempo límite, dentro de una carpeta temporal. Pon False para solo verlo.
D35_EJECUTAR_CODIGO = True
# ------------------------------------------------------------------------

CASOS_35 = [
    ("664 123 4567", "+52 664 123 4567"),
    ("(664) 123-4567", "+52 664 123 4567"),
    ("6641234567", "+52 664 123 4567"),
    ("+52 664 123 4567", "+52 664 123 4567"),
    ("52 6641234567", "+52 664 123 4567"),
    ("044 664 123 4567", "+52 664 123 4567"),
    ("123", None),
    ("tel: 55-1234-5678", "+52 551 234 5678"),
]

PETICION_VAGA_35 = "Escribe una función Python normalizar_telefono(texto) que normalice teléfonos mexicanos."
PETICION_EJEMPLOS_35 = (PETICION_VAGA_35 + "\nEjemplos de entrada → salida:\n" +
                        "\n".join(f"  {e!r} → {s!r}" for e, s in (CASOS_35[1], CASOS_35[5], CASOS_35[6])))   # 2–3 casos frontera, como pide la guía

PRUEBAS_35 = """
import json, sys
sys.path.insert(0, sys.argv[1])
from candidato import normalizar_telefono
casos = json.loads(sys.argv[2])
res = []
for entrada, esperado in casos:
    try:
        obtenido = normalizar_telefono(entrada)
    except Exception as e:
        obtenido = f"ERROR: {type(e).__name__}: {e}"
    res.append({"entrada": entrada, "esperado": esperado, "obtenido": obtenido, "ok": obtenido == esperado})
print(json.dumps(res, ensure_ascii=False))
"""


def _extraer_codigo(texto: str) -> str | None:
    import re
    bloques = re.findall(r"```(?:python)?\n(.*?)```", texto, re.S)
    codigo = max(bloques, key=len) if bloques else texto
    return codigo if "def normalizar_telefono" in codigo else None


def _correr_pruebas(codigo: str) -> list[dict]:
    import subprocess
    carpeta = visual.carpeta_temporal("lab35_")
    (carpeta / "candidato.py").write_text(codigo, encoding="utf-8")
    (carpeta / "pruebas.py").write_text(PRUEBAS_35, encoding="utf-8")
    try:
        # Entorno mínimo: el código que escribió el modelo NO recibe tu API key ni tus otras variables
        entorno = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
        if os.name == "nt":
            entorno["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")
        r = subprocess.run([sys.executable, "-I", str(carpeta / "pruebas.py"), str(carpeta), json.dumps(CASOS_35)],
                           capture_output=True, text=True, timeout=10, cwd=carpeta, stdin=subprocess.DEVNULL, env=entorno)
        return json.loads(r.stdout) if r.stdout.strip() else [{"entrada": "(todas)", "esperado": "-", "obtenido": r.stderr[-300:], "ok": False}]
    except subprocess.TimeoutExpired:
        return [{"entrada": "(todas)", "esperado": "-", "obtenido": "TIMEOUT (más de 10 s)", "ok": False}]


def _tabla_pruebas(resultados: list[dict], ronda: int) -> int:
    tabla = Table(title=f"Ronda {ronda}: resultado de las pruebas")
    tabla.add_column("Entrada"); tabla.add_column("Esperado"); tabla.add_column("Obtenido"); tabla.add_column("")
    for r in resultados:
        tabla.add_row(escape(repr(r["entrada"])), escape(repr(r["esperado"])), escape(repr(r["obtenido"])),
                      "[green]✔[/]" if r["ok"] else "[red]✘[/]")
    consola.print(tabla)
    pasaron = sum(r["ok"] for r in resultados)
    consola.print(f"[bold]Pasaron {pasaron}/{len(resultados)}[/]")
    return pasaron


def demo_3_5():
    titulo("DEMO 3.5 · Refinamiento iterativo: ejemplos y pruebas")
    mostrar_guia("3.5")
    concepto(
        "Cuando el resultado no sale como quieres, la descripción en prosa suele ser el problema.\n"
        "  • Ejemplos concretos de entrada → salida comunican mejor que adjetivos.\n"
        "  • TDD: escribe primero las pruebas, pide el código y comparte las pruebas que FALLAN para iterar.\n"
        "  • Interview pattern: para tareas poco claras, pide a Claude que te haga preguntas antes de implementar.\n"
        "  • Arreglos relacionados → en un solo mensaje; independientes → uno por uno."
    )
    peticion = PETICION_EJEMPLOS_35 if D35_MODO == "ejemplos" else PETICION_VAGA_35
    sistema = "Responde SOLO con un bloque ```python``` que contenga la función. Sin explicaciones."
    mensajes = [{"role": "user", "content": peticion}]
    rondas = D35_MAX_RONDAS if D35_MODO == "tdd" else 1
    historial = []
    for ronda in range(1, rondas + 1):
        paso(f"Ronda {ronda}")
        resp = llamar_claude(f"ronda {ronda}", system=sistema, messages=mensajes, max_tokens=1200)
        mensajes.append({"role": "assistant", "content": resp.content})
        codigo = _extraer_codigo(texto_de(resp))
        if not codigo:
            alerta("No encontré una función normalizar_telefono en la respuesta.")
            break
        if not D35_EJECUTAR_CODIGO:
            nota("D35_EJECUTAR_CODIGO = False: no se ejecuta el código.")
            break
        resultados = _correr_pruebas(codigo)
        pasaron = _tabla_pruebas(resultados, ronda)
        historial.append(pasaron)
        if pasaron == len(resultados) or D35_MODO != "tdd":
            break
        fallas = "\n".join(f"- normalizar_telefono({r['entrada']!r}) devolvió {r['obtenido']!r}, se esperaba {r['esperado']!r}"
                           for r in resultados if not r["ok"])
        mensajes.append({"role": "user", "content": f"Estas pruebas fallaron:\n{fallas}\nCorrige la función."})
        nota("Se le mandan a Claude SOLO las pruebas que fallaron, con entrada, obtenido y esperado.")
    if historial:
        tabla = Table(title=f"Progreso ({D35_MODO})")
        tabla.add_column("Ronda"); tabla.add_column("Pruebas que pasaron")
        for i, p in enumerate(historial, 1):
            tabla.add_row(str(i), f"{p}/{len(CASOS_35)}")
        consola.print(tabla)
        final = historial[-1]
        visual.registrar_resultado(
            final=("pasa" if final == len(CASOS_35) else "falla_frontera") if D35_MODO != "ejemplos" else
                  ("mejor" if final == len(CASOS_35) else "falla_frontera"),
            texto=f"Pruebas que pasaron al final: {final}/{len(CASOS_35)} en {len(historial)} ronda(s)")
    concepto("Corre los 3 modos y compara: 'vago' suele fallar en los casos frontera (044, 52 sin +, '123'); "
             "'ejemplos' acierta más desde la primera; 'tdd' converge compartiendo las fallas.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 3.6  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio3.py guia 3.6)
# ---------------------------------------------------------------------
GUIA_3_6 = """
#### De qué trata
Claude Code en un pipeline de CI/CD, donde **no hay nadie** para contestar. Sin `-p`, Claude Code abre una sesión
interactiva y el job se queda colgado esperando.

| Flag | Para qué |
|---|---|
| `-p "prompt"` (`--print`) | Corre, imprime el resultado y termina |
| `--output-format json` | Salida que el pipeline puede leer: `result`, `total_cost_usd`, `session_id`… |
| `--json-schema '<schema>'` | La respuesta se valida contra tu schema y llega en `structured_output` |
| `--allowedTools`, `--tools` | Qué puede usar (aquí solo `Read`) |
| `--max-turns`, `--max-budget-usd` | Límites de turnos y de gasto |

#### Qué pasa al correrla, paso a paso
1. Se crea un repo de prueba con un `CLAUDE.md` (*"reembolsos automáticos hasta $10,000"*) y un `cambios.diff` que
   sube el límite a 100000.
2. Se imprime el **comando completo** y se ejecuta el CLI de Claude Code (el que viene dentro de `claude-agent-sdk`)
   como un proceso aparte.
3. Con `"json"` + schema verás:
   - los campos útiles del JSON (`subtype`, `num_turns`, `total_cost_usd`, `session_id`);
   - `structured_output` con `aprobado` y la lista de `problemas` (archivo, severidad, descripción);
   - la decisión del pipeline: **BLOQUEAR el merge**, porque viola la regla de CLAUDE.md.
4. Se imprime un ejemplo de workflow de GitHub Actions.

#### Dónde está en el código
`SCHEMA_36`, `GITHUB_ACTIONS_36`, `_ruta_cli()` (busca el CLI dentro de `claude-agent-sdk`) y `demo_3_6()`, que arma
la lista `comando` y la corre con `subprocess.run`.

#### Experimentos
- `D36_FORMATO = "text"`: la salida es prosa y el pipeline no puede decidir nada con ella.
- `D36_CON_SCHEMA = False`: hay JSON, pero `result` sigue siendo texto libre.
- Edita `cambios.diff` en la demo para que respete el límite: debería aprobar.

#### Lo que pregunta el examen
- El job de CI se cuelga → falta `-p`.
- Salida para procesar → `--output-format json` + `--json-schema`.
- El revisor debe ser una sesión **independiente** de la que generó el código: no se autorrevisa.
- CLAUDE.md da contexto del proyecto también en CI. Incluye hallazgos previos para no repetir comentarios en cada push.
- `claude -p` para revisiones bloqueantes antes del merge; Message Batches API (Dominio 4) para trabajos que pueden esperar.
"""


# =====================================================================
#  DEMO 3.6 · CI/CD: CLAUDE CODE SIN NADIE ENFRENTE (-p)
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D36_FORMATO = "json"          # "text" o "json"
D36_CON_SCHEMA = True         # True: --json-schema → salida validada (structured_output)
D36_MAX_TURNOS = 6
# ------------------------------------------------------------------------

SCHEMA_36 = {
    "type": "object",
    "properties": {
        "aprobado": {"type": "boolean"},
        "problemas": {"type": "array", "items": {"type": "object", "properties": {
            "archivo": {"type": "string"}, "severidad": {"type": "string", "enum": ["alta", "media", "baja"]},
            "descripcion": {"type": "string"}}, "required": ["archivo", "severidad", "descripcion"]}},
    },
    "required": ["aprobado", "problemas"],
}

GITHUB_ACTIONS_36 = """\
name: Revisión con Claude
on: pull_request
jobs:
  revisar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # trae la historia completa: sin esto, origin/main no existe y el diff falla
      - run: npm install -g @anthropic-ai/claude-code
      - name: Revisar el PR
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          git diff origin/main...HEAD > cambios.diff
          claude -p "Revisa cambios.diff según CLAUDE.md" \\
            --output-format json --json-schema "$(cat schema.json)" \\
            --allowedTools Read --max-turns 4 > revision.json
          jq -e '.structured_output.aprobado' revision.json
"""


def _ruta_cli() -> str | None:
    import shutil
    try:
        import claude_agent_sdk
        carpeta = Path(claude_agent_sdk.__file__).parent / "_bundled"
        for nombre in ("claude", "claude.exe"):
            if (carpeta / nombre).exists():
                return str(carpeta / nombre)
    except ImportError:
        pass
    return shutil.which("claude")


def demo_3_6():
    titulo("DEMO 3.6 · CI/CD: Claude Code en modo no interactivo (-p)")
    mostrar_guia("3.6")
    concepto(
        "En CI no hay nadie que conteste: sin -p (--print) Claude Code abre una sesión interactiva y el job se cuelga.\n"
        "  • -p 'prompt' → corre, imprime y termina.\n"
        "  • --output-format json → salida que tu pipeline puede leer (resultado, costo, session_id).\n"
        "  • --json-schema → la respuesta se valida contra tu schema (campo structured_output).\n"
        "  • --allowedTools, --max-turns → limita lo que puede hacer en el pipeline.\n"
        "  • El revisor debe ser una sesión INDEPENDIENTE de la que escribió el código, y CLAUDE.md le da el contexto del proyecto."
    )
    cli = _ruta_cli()
    if not cli:
        alerta("No encontré el CLI de Claude Code (viene dentro de claude-agent-sdk). Revisa la instalación.")
        return
    ok(f"CLI: {cli}")
    proyecto = crear_proyecto({
        "CLAUDE.md": "# La Tiendita\n- Reembolsos automáticos hasta $10,000 MXN; más que eso requiere aprobación humana.\n",
        "cambios.diff": """\
            --- a/src/reembolsos.ts
            +++ b/src/reembolsos.ts
            @@ -1,5 +1,5 @@
             export function refund(orderId: string, amount: number) {
            -  if (amount > 10000) throw new Error('Requiere aprobación');
            +  if (amount > 100000) throw new Error('Requiere aprobación');
               return { ok: true };
             }
            """,
    }, prefijo="tiendita_ci_")
    ok(f"Repo de prueba: {proyecto}")
    mostrar_archivo(proyecto, "cambios.diff", "diff")

    prompt = f"Revisa {proyecto / 'cambios.diff'} contra las reglas de CLAUDE.md. Sé breve."
    comando = [cli, "-p", prompt, "--output-format", D36_FORMATO, "--model", MODELO,
               "--max-turns", str(D36_MAX_TURNOS), "--tools", "Read", "--allowedTools", "Read",
               "--setting-sources", "project", "--max-budget-usd", str(TOPE_USD_AGENT_SDK)]
    if D36_CON_SCHEMA:
        comando += ["--json-schema", json.dumps(SCHEMA_36, ensure_ascii=False)]
    vista = " ".join(f"'{c}'" if " " in c or "{" in c else c for c in comando[1:])
    consola.print(Panel(escape("claude " + vista), title="Comando que corre el pipeline", border_style="magenta"))

    import subprocess
    visual.aislar_claude_code()   # la sesión de claude -p va a una carpeta temporal, no a tu ~/.claude
    t0 = time.time()
    try:
        r = subprocess.run(comando, cwd=proyecto, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        alerta("El comando tardó más de 180 s.")
        return
    nota(f"Terminó en {time.time() - t0:.1f}s con código de salida {r.returncode}")
    if r.returncode != 0:
        alerta(f"stderr: {r.stderr[-500:]}")
    if D36_FORMATO == "text":
        consola.print(Panel(escape(r.stdout), title="stdout (texto libre: difícil de procesar en un pipeline)", border_style="yellow"))
        visual.registrar_resultado(final="no_parseable", texto="Salida en prosa: el pipeline no puede decidir nada con ella")
    else:
        try:
            datos = json.loads(r.stdout)
        except json.JSONDecodeError:
            alerta("La salida no fue JSON válido.")
            visual.registrar_resultado(final="no_parseable", texto="La salida no fue JSON válido")
            consola.print(escape(r.stdout[-800:]))
            return
        sumar_uso_sdk(datos.get("total_cost_usd"), datos.get("usage"), datos.get("num_turns"))
        resumen = {k: datos.get(k) for k in ("subtype", "is_error", "num_turns", "total_cost_usd", "session_id")}
        mostrar_json(resumen, "Campos útiles del JSON de salida", "cyan")
        validado = D36_CON_SCHEMA and datos.get("structured_output") is not None
        visual.registrar_resultado(final="validado" if validado else "json_libre",
                                   texto="structured_output validado contra el schema" if validado else
                                   "JSON con 'result' en texto libre: la forma no está garantizada")
        if validado:
            mostrar_json(datos["structured_output"], "structured_output (validado contra tu --json-schema)", "green")
            aprobado = datos["structured_output"].get("aprobado")
            (ok if aprobado else alerta)(f"Decisión del pipeline: {'aprobar' if aprobado else 'BLOQUEAR el merge'} "
                                         "(en CI: exit code distinto de 0 si no se aprueba)")
        else:
            if D36_CON_SCHEMA:
                alerta("No llegó structured_output (¿se acabaron los turnos? sube D36_MAX_TURNOS).")
            consola.print(Panel(escape(str(datos.get("result", ""))), title="result", border_style="green"))
    paso("Así se vería en GitHub Actions")
    from rich.syntax import Syntax
    consola.print(Panel(Syntax(GITHUB_ACTIONS_36, "yaml"), title=".github/workflows/revision.yml", border_style="blue"))
    concepto("1) D36_FORMATO = 'text' → la salida es prosa: tu pipeline no puede decidir nada con ella.\n"
             "2) D36_CON_SCHEMA = False → hay JSON con 'result', pero el contenido sigue siendo texto libre.\n"
             "3) Lee el YAML: la API key va como secret, nunca en el repo.", "🧪 Experimenta")


# =====================================================================
#  MENÚ
# =====================================================================

GUIAS = {
    "3.1": GUIA_3_1,
    "3.2": GUIA_3_2,
    "3.3": GUIA_3_3,
    "3.4": GUIA_3_4,
    "3.5": GUIA_3_5,
    "3.6": GUIA_3_6,
}


DEMOS = {
    "3.1": ("Jerarquía de CLAUDE.md (Agent SDK)", demo_3_1),
    "3.2": ("Slash commands y skills (Agent SDK)", demo_3_2),
    "3.3": ("Reglas por ruta en .claude/rules (Agent SDK)", demo_3_3),
    "3.4": ("Plan mode vs ejecución directa (Agent SDK)", demo_3_4),
    "3.5": ("Refinamiento iterativo: ejemplos y TDD", demo_3_5),
    "3.6": ("CI/CD con claude -p (Claude Code)", demo_3_6),
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
        tabla = Table(title="CCAR-F · Lab del Dominio 3")
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

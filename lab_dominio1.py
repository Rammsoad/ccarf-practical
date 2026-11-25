"""
=====================================================================
 CCAR-F · LAB DEL DOMINIO 1: Agentic Architecture & Orchestration
=====================================================================

Demos ejecutables, una por subdominio. Todas usan el caso de
"La Tiendita" (tienda en línea) con datos FALSOS.

CÓMO CORRERLO
-------------
  1) pip install -r requirements.txt
  2) Copia .env.example como .env y pega ahí tu API key (ver README).
     Si no hay .env, se usa la variable de entorno ANTHROPIC_API_KEY.
  3) python lab_dominio1.py          -> muestra el menú
     python lab_dominio1.py 1.1      -> corre directo la demo 1.1

CÓMO MODIFICARLO
----------------
  * Arriba está la CONFIGURACIÓN GENERAL (modelo, nivel de detalle).
  * Cada demo tiene su propio bloque "🔧 CAMBIA AQUÍ" con variables
    comentadas: cámbialas, vuelve a correr y compara la salida.

DEMOS
-----
  1.1  Agentic loop y stop_reason          (Messages API)
  1.2  Coordinator + subagentes (hub-and-spoke)
  1.3  Context passing y subagentes en paralelo
  1.4  Enforcement: prerequisite gate + handoff estructurado
  1.5  Hooks PreToolUse / PostToolUse      (Agent SDK)
  1.6  Prompt chaining y multi-pass review
  1.7  Sesiones: resume, fork y contexto obsoleto (Agent SDK + API)
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

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
# correr nada (ni gastar):  python lab_dominio1.py guia      (o: guia 1.2)
MOSTRAR_GUIA = True
PAUSA_DESPUES_DE_GUIA = True   # espera un Enter después de la guía, para que la leas antes de que empiece la demo

# Modo HTML: además de la terminal, cada corrida se guarda como página web con un diagrama
# de lo que pasó, en salidas_html/dominio1/. Cada corrida es un archivo nuevo (no se sobrescribe)
# y salidas_html/dominio1/index.html las pone lado a lado para comparar: cambia una variable,
# vuelve a correr la demo y compara los diagramas.
#   True  -> encendido (para apagarlo en una sola corrida:  python lab_dominio1.py 1.1 --sin-html)
#   False -> solo terminal  (para encenderlo en una sola corrida:  python lab_dominio1.py 1.1 --html)
MODO_HTML = True

# Límite de reembolso de La Tiendita (pesos mexicanos)
LIMITE_REEMBOLSO = 10_000

# Tope de gasto por cada corrida del Agent SDK (dólares), por seguridad
TOPE_USD_AGENT_SDK = 0.25


# =====================================================================
#  IMPRESIÓN BONITA Y VERBOSA  (no necesitas tocar esto)
# =====================================================================

try:
    from rich.console import Console
    from rich.json import JSON as RichJSON
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
from visual import agregar_diagrama, corto, diagrama_seguro, svg_barras_tiempo, svg_grafo  # noqa: E402
GUARDAR_HTML = visual.configurar(dominio=1, modo_html=MODO_HTML)
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
        consola.print(f"[dim]📖 Guía de esta demo: python lab_dominio1.py guia {clave}  ·  "
                      f"más detalle: pon DETALLE = \"completo\" arriba del archivo[/]")
        return
    from rich.markdown import Markdown
    consola.print(Panel(Markdown(idioma.guia(clave, GUIAS[clave])), title=f"📖 Guía de la demo {clave}: qué vas a ver",
                        border_style="cyan", padding=(1, 2)))
    if pausa and PAUSA_DESPUES_DE_GUIA and sys.stdin.isatty():
        consola.input("[bold cyan]   Presiona Enter para correr la demo… [/]")


# =====================================================================
#  DATOS FALSOS DE LA TIENDITA + TOOLS
# =====================================================================

CLIENTES = {
    "C-001": {"id": "C-001", "nombre": "Ana López", "email": "ana@ejemplo.com"},
    "C-002": {"id": "C-002", "nombre": "Juan Pérez", "email": "juan@ejemplo.com"},
    "C-003": {"id": "C-003", "nombre": "Juan Pérez", "email": "jperez@ejemplo.com"},
}

PEDIDOS = {
    "#12345": {"id": "#12345", "cliente": "C-001", "total": 1850.00, "estado": "entregado",
               "fecha": "2026-10-28", "articulos": ["Taza artesanal x2", "Mantel bordado"]},
    "#12346": {"id": "#12346", "cliente": "C-002", "total": 12500.00, "estado": "entregado",
               "fecha": "2026-10-30", "articulos": ["Vajilla completa de barro"]},
    "#12347": {"id": "#12347", "cliente": "C-001", "total": 630.00, "estado": "en camino",
               "fecha": "2026-11-10", "articulos": ["Mantel bordado x3"]},
}

TOOL_GET_CUSTOMER = {
    "name": "get_customer",
    "description": (
        "Busca a un cliente de La Tiendita por su correo electrónico y devuelve su id y nombre. "
        "Úsala para VERIFICAR LA IDENTIDAD antes de cualquier reembolso. "
        "NO la uses para consultar pedidos: para eso está lookup_order."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"email": {"type": "string", "description": "Correo del cliente, ej. ana@ejemplo.com"}},
        "required": ["email"],
    },
}

TOOL_LOOKUP_ORDER = {
    "name": "lookup_order",
    "description": (
        "Busca un pedido por su número (formato #NNNNN) y devuelve cliente, total, estado y artículos. "
        "NO verifica identidad: para eso usa get_customer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "Número de pedido, ej. #12345"}},
        "required": ["order_id"],
    },
}

TOOL_PROCESS_REFUND = {
    "name": "process_refund",
    "description": (
        "Procesa un reembolso de un pedido. Requiere haber verificado al cliente con get_customer "
        f"y que el monto no supere ${LIMITE_REEMBOLSO:,} MXN."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "amount": {"type": "number", "description": "Monto en pesos mexicanos"},
            "reason": {"type": "string"},
        },
        "required": ["order_id", "amount", "reason"],
    },
}

TOOLS_SOPORTE = [TOOL_GET_CUSTOMER, TOOL_LOOKUP_ORDER, TOOL_PROCESS_REFUND]

REEMBOLSOS_HECHOS: list[dict] = []


def get_customer(email: str) -> dict:
    for c in CLIENTES.values():
        if c["email"].lower() == email.lower():
            return {"encontrado": True, **c}
    return {"encontrado": False, "mensaje": f"No hay cliente con el correo {email}"}


def lookup_order(order_id: str) -> dict:
    order_id = order_id if order_id.startswith("#") else f"#{order_id}"
    pedido = PEDIDOS.get(order_id)
    return {"encontrado": True, **pedido} if pedido else {"encontrado": False, "mensaje": f"No existe el pedido {order_id}"}


def process_refund(order_id: str, amount: float, reason: str) -> dict:
    registro = {"order_id": order_id, "amount": amount, "reason": reason, "folio": f"RF-{len(REEMBOLSOS_HECHOS) + 1:04d}"}
    REEMBOLSOS_HECHOS.append(registro)
    return {"ok": True, "mensaje": "Reembolso procesado", **registro}


FUNCIONES_TOOLS = {"get_customer": get_customer, "lookup_order": lookup_order, "process_refund": process_refund}


def ejecutar_tool(nombre: str, entrada: dict) -> tuple[str, bool]:
    """Ejecuta la tool en NUESTRO código y devuelve (resultado_json, es_error)."""
    funcion = FUNCIONES_TOOLS.get(nombre)
    if funcion is None:
        return json.dumps({"error": f"Tool desconocida: {nombre}"}), True
    try:
        resultado = funcion(**entrada)
        return json.dumps(resultado, ensure_ascii=False), False
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False), True


def mostrar_resultado_tool(nombre: str, resultado: str, es_error: bool) -> None:
    if DETALLE == "basico":
        consola.print(f"[{'red' if es_error else 'cyan'}]⚙ tu código ejecutó {escape(nombre)} → tool_result"
                      f"{' (error)' if es_error else ''}[/] [dim]{escape(resultado[:80])}[/]")
        return
    estilo = "red" if es_error else "cyan"
    try:
        cuerpo = RichJSON(resultado)
    except Exception:
        cuerpo = escape(resultado)
    consola.print(Panel(cuerpo, title=f"⚙ tu código ejecutó {escape(nombre)} → tool_result{' (is_error)' if es_error else ''}",
                        border_style=estilo))


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 1.1  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio1.py guia 1.1)
# ---------------------------------------------------------------------
GUIA_1_1 = """
#### De qué trata
El **agentic loop**: el ciclo con el que cualquier agente trabaja. Claude **nunca ejecuta** las tools: solo
**pide** una (bloque `tool_use`). Tu código la ejecuta, le regresa el resultado (`tool_result`) y vuelve a llamar
a Claude. El ciclo termina cuando `stop_reason` es `"end_turn"`.

#### Qué pasa al correrla, paso a paso
1. Se manda la pregunta de Ana (`D11_PREGUNTA`): pedido #12345, taza rota, quiere $450.
2. Claude responde con `stop_reason = "tool_use"` y pide `get_customer` (verificar identidad).
3. Tu código ejecuta la función Python `get_customer()` con los datos falsos y devuelve un `tool_result`
   dentro de un mensaje con rol `user`. Lo ves en el panel **"⚙ tu código ejecutó…"**.
4. Se repite: `lookup_order("#12345")` (total $1,850, es de Ana) y luego `process_refund(450)`.
5. Claude responde con `stop_reason = "end_turn"` y un texto para el cliente. Fin del loop.
6. Tabla resumen: iteraciones, tools en orden y el reembolso registrado (folio `RF-0001`).

Normalmente son 3 o 4 iteraciones. A veces Claude pide 2 tools en la misma respuesta: las verás en una sola
iteración y sus 2 `tool_result` viajan juntos en **un** mensaje `user`.

#### Lo que se le manda a Claude
- `system`: rol de agente de soporte y el orden esperado (verificar → revisar pedido → reembolsar).
- `tools`: la lista `TOOLS_SOPORTE`. Cada tool es un diccionario con **name**, **description** e **input_schema**:

```python
TOOL_PROCESS_REFUND = {
    "name": "process_refund",
    "description": "Procesa un reembolso de un pedido. Requiere haber verificado...",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "amount":   {"type": "number", "description": "Monto en pesos mexicanos"},
            "reason":   {"type": "string"},
        },
        "required": ["order_id", "amount", "reason"],
    },
}
```
- `messages`: **todo** el historial en cada llamada. La API no guarda nada entre llamadas.
- `max_tokens`: `D11_MAX_TOKENS`.

#### Dónde está en el código
- Definición de tools: `TOOL_GET_CUSTOMER`, `TOOL_LOOKUP_ORDER`, `TOOL_PROCESS_REFUND`.
- Funciones reales: `get_customer()`, `lookup_order()`, `process_refund()`.
- `FUNCIONES_TOOLS` conecta el nombre que pide Claude con la función Python; `ejecutar_tool()` la ejecuta.
- El loop: el `for iteracion in ...` dentro de `demo_1_1()`.

#### Experimentos: qué cambiar y qué esperar
- `D11_MODO_PARADA = "hay_texto"` (antipatrón): el loop se corta en cuanto la respuesta trae texto. Como Claude
  suele escribir "Déjame revisar…" **junto con** un `tool_use`, verás la alerta *"Quedaron tools pedidas SIN
  ejecutar"* y no habrá reembolso. Si en esa corrida Claude no escribió texto, repítela.
- `D11_MAX_TOKENS = 40`: la respuesta se corta y `stop_reason` es `"max_tokens"`. No terminó, se quedó sin espacio.
- `D11_MAX_ITERACIONES = 2`: la red de seguridad corta el loop antes de terminar.

#### Lo que pregunta el examen
- Continuar mientras `stop_reason == "tool_use"`; terminar con `"end_turn"`.
- Antipatrones: decidir por el texto de la respuesta, o usar un tope de iteraciones como forma **normal** de parar.
- Los resultados de las tools se agregan al historial para que Claude razone el siguiente paso.
"""


# =====================================================================
#  DEMO 1.1 · AGENTIC LOOP Y STOP_REASON
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D11_PREGUNTA = "Hola, soy ana@ejemplo.com. Mi pedido #12345 llegó con una taza rota. ¿Me pueden reembolsar $450?"
D11_MAX_ITERACIONES = 10     # red de seguridad, NO la condición normal de salida
D11_MAX_TOKENS = 1024        # pon 40 para provocar stop_reason = "max_tokens"
# Cómo decide el loop que terminó:
#   "stop_reason" -> CORRECTO: sigue mientras stop_reason == "tool_use"
#   "hay_texto"   -> ANTIPATRÓN: se detiene en cuanto la respuesta trae texto
D11_MODO_PARADA = "stop_reason"
# ------------------------------------------------------------------------


def demo_1_1():
    titulo("DEMO 1.1 · Agentic loop: ¿cuándo termina el agente?")
    mostrar_guia("1.1")
    concepto(
        "El loop agéntico: mandas el historial → Claude responde → si stop_reason es 'tool_use', TU código "
        "ejecuta las tools y devuelve tool_result → repites. Solo terminas cuando stop_reason es 'end_turn'.\n"
        "Antipatrón del examen: decidir que terminó porque la respuesta trae texto. Claude puede escribir "
        "'Déjame revisar…' Y pedir una tool en la misma respuesta."
    )
    REEMBOLSOS_HECHOS.clear()
    nota(f"Modo de parada configurado: {D11_MODO_PARADA}")
    mensajes = [{"role": "user", "content": D11_PREGUNTA}]
    sistema = (
        "Eres el agente de soporte de La Tiendita. Verifica la identidad con get_customer antes de reembolsar, "
        "revisa el pedido con lookup_order y usa process_refund cuando proceda. Responde en español y breve."
    )
    tools_ejecutadas = []
    eventos, final = [], "tope"   # para el diagrama de la corrida (--html)
    for iteracion in range(1, D11_MAX_ITERACIONES + 1):
        paso(f"Iteración {iteracion} del loop")
        resp = llamar_claude(f"iteración {iteracion}", system=sistema, tools=TOOLS_SOPORTE,
                             messages=mensajes, max_tokens=D11_MAX_TOKENS)
        mensajes.append({"role": "assistant", "content": resp.content})
        eventos.append({"n": iteracion, "stop": resp.stop_reason, "ejecutadas": [],
                        "tools": [b.name for b in resp.content if b.type == "tool_use"]})

        if D11_MODO_PARADA == "hay_texto" and texto_de(resp):
            alerta("ANTIPATRÓN: el loop se detuvo porque vio texto en la respuesta.")
            pendientes = [b.name for b in resp.content if b.type == "tool_use"]
            if pendientes:
                alerta(f"¡Quedaron tools pedidas SIN ejecutar!: {pendientes}  (stop_reason era '{resp.stop_reason}')")
            final = "hay_texto"
            break

        if resp.stop_reason == "tool_use":
            resultados = []
            for bloque in resp.content:
                if bloque.type == "tool_use":
                    resultado, es_error = ejecutar_tool(bloque.name, bloque.input)
                    mostrar_resultado_tool(bloque.name, resultado, es_error)
                    tools_ejecutadas.append(bloque.name)
                    eventos[-1]["ejecutadas"].append(bloque.name)
                    resultados.append({"type": "tool_result", "tool_use_id": bloque.id,
                                       "content": resultado, "is_error": es_error})
            nota(f"Devolvemos {len(resultados)} tool_result en UN solo mensaje 'user' y seguimos el loop.")
            mensajes.append({"role": "user", "content": resultados})
            continue

        final = resp.stop_reason
        if resp.stop_reason == "end_turn":
            ok("stop_reason = 'end_turn' → Claude terminó. Salimos del loop.")
        elif resp.stop_reason == "max_tokens":
            alerta("stop_reason = 'max_tokens' → la respuesta se cortó por max_tokens. No terminó de verdad.")
        else:
            nota(f"stop_reason = '{resp.stop_reason}' → otro motivo; en producción se maneja aparte.")
        break
    else:
        alerta(f"Se alcanzó D11_MAX_ITERACIONES={D11_MAX_ITERACIONES}: la red de seguridad cortó el loop.")

    diagrama_seguro(diagrama_1_1, eventos, final)
    resultados_1_1 = {   # lo usa el panel: compara con tu predicción y escribe la nota automática
        "end_turn": idioma.salida(f"terminó bien con end_turn ({iteracion} vueltas, {len(tools_ejecutadas)} tools ejecutadas)."),
        "hay_texto": idioma.salida("el loop se detuvo al ver texto (antipatrón) y quedaron tools sin ejecutar."),
        "max_tokens": idioma.salida("la respuesta se cortó por max_tokens: Claude no terminó."),
        "tope": idioma.salida(f"la red de seguridad cortó el loop a las {D11_MAX_ITERACIONES} vueltas."),
    }
    visual.registrar_resultado(demo="1.1", final=final, iteraciones=iteracion, tools=tools_ejecutadas,
                               texto=resultados_1_1.get(final, f"terminó con stop_reason = {final}."))
    tabla = Table(title="Resumen de la demo 1.1")
    tabla.add_column("Dato"); tabla.add_column("Valor")
    tabla.add_row("Iteraciones", str(iteracion))
    tabla.add_row("Tools ejecutadas (en orden)", " → ".join(tools_ejecutadas) or "ninguna")
    tabla.add_row("Reembolsos registrados", str(REEMBOLSOS_HECHOS) if REEMBOLSOS_HECHOS else "ninguno")
    consola.print(tabla)
    concepto("Prueba: D11_MODO_PARADA = 'hay_texto' y compara cuántas tools se ejecutan. "
             "Luego D11_MAX_TOKENS = 40 para ver stop_reason = 'max_tokens'.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 1.2  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio1.py guia 1.2)
# ---------------------------------------------------------------------
GUIA_1_2 = """
#### De qué trata
El patrón **hub-and-spoke**: un **coordinator** divide la tarea, le manda cada parte a un **subagente**, recibe
los resultados y escribe la síntesis. Los subagentes no hablan entre sí: todo pasa por el coordinator.

Aquí cada subagente es una llamada **nueva** a la Messages API con historial vacío. Eso es justo lo que define
a un subagente: **no hereda la conversación** del coordinator, solo ve lo que el coordinator le escribe.
(En el Agent SDK esto se hace con la tool `Agent`, antes llamada `Task`, y un `AgentDefinition`.)

#### Qué pasa al correrla, paso a paso
1. El coordinator recibe el tema (`D12_TEMA`) y un system prompt con el contexto del negocio: artesanías
   mexicanas, presupuesto de $40,000, envíos a todo México.
2. Responde con 3 a 5 llamadas a la tool `delegar_subagente` **en la misma respuesta**, cada una con
   `subtema` y `contexto`.
3. Por cada llamada, tu código ejecuta `correr_subagente()`. El panel azul
   **"📦 ESTO es TODO lo que ve el subagente"** muestra literalmente su único mensaje.
4. Las respuestas de los subagentes regresan al coordinator como `tool_result`.
5. El coordinator escribe el reporte final.
6. La tabla **"¿El reporte final cubre todas las áreas?"** busca en el reporte las palabras de
   `D12_AREAS_ESPERADAS` (inventario, logística, precios, marketing, atención).

#### Lo que se le manda a Claude
- **Al coordinator:** system prompt + la tool `TOOL_DELEGAR`:
  - `subtema` (string): qué investigar.
  - `contexto` (string): los datos del negocio que el subagente necesita, porque no ve nada más.
- **A cada subagente:** otro system prompt ("máximo 4 viñetas") y **un solo** mensaje con subtema + contexto.
  Sin tools y sin historial.

#### Por qué "divide mal las asignaciones" (modo `"estrecha"`)
Con `D12_DESCOMPOSICION = "estrecha"` el código agrega al system prompt del coordinator:

> *"Divide el tema SOLO en subtemas de marketing digital (redes sociales, anuncios, influencers)."*

Qué vas a ver:
- Los subagentes hacen **bien** su trabajo: sus viñetas sobre redes sociales o anuncios son buenas.
- Pero nadie investigó inventario, logística, precios ni atención al cliente, porque **nunca se los asignaron**.
- El reporte final sale incompleto y la tabla de cobertura marca varias áreas en rojo.

La falla está en la **descomposición del coordinator**, no en los subagentes. En la vida real nadie escribe "solo
marketing" a propósito. Pasa por cosas más sutiles: el prompt del coordinator da ejemplos de una sola área, o
interpreta el tema de forma estrecha ("vender más" = "hacer publicidad").

#### Cómo corregirlo
1. **Arreglar el prompt del coordinator**: pedir explícitamente que cubra todas las dimensiones del problema
   (o listarlas) y no sesgarlo con ejemplos de una sola área. Es el modo `"amplia"`.
2. **Agregar un paso de verificación de cobertura**: antes de escribir el reporte, el coordinator revisa los
   resultados contra lo que debería cubrir y **vuelve a delegar** lo que falte (refinamiento iterativo).
   La tabla de esta demo es una versión simple de ese chequeo.
3. **No "arreglar" a los subagentes** (otro modelo, más tokens, prompts más largos): no son el problema.

Nota: el chequeo de cobertura busca palabras exactas. Si el reporte dice "envíos" en vez de "logística", la tabla
dirá NO aunque sí lo cubra. Léelo con calma.

#### Dónde está en el código
- `TOOL_DELEGAR`, `correr_subagente()` y `demo_1_2()`. El sesgo está en la variable `sesgo` dentro de `demo_1_2()`.

#### Lo que pregunta el examen
- Si al reporte final le falta un tema entero, la causa raíz suele ser la **descomposición del coordinator**.
- El subagente no hereda el historial: el contexto se le pasa **explícito** en su prompt.
- El coordinator decide qué subagentes invocar según la consulta, en lugar de pasar siempre por todos.
"""


# =====================================================================
#  DEMO 1.2 · COORDINATOR + SUBAGENTES (HUB-AND-SPOKE)
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D12_TEMA = "Cómo puede La Tiendita vender más en la temporada navideña de este año"
# "amplia"   -> el coordinator cubre todas las áreas del negocio
# "estrecha" -> su prompt lo sesga a SOLO marketing digital (error de descomposición)
D12_DESCOMPOSICION = "amplia"
# Áreas que un buen reporte debería cubrir (para revisar la cobertura al final)
D12_AREAS_ESPERADAS = ["inventario", "logística", "precios", "marketing", "atención"]
# ------------------------------------------------------------------------

TOOL_DELEGAR = {
    "name": "delegar_subagente",
    "description": (
        "Envía UN subtema a un subagente investigador. El subagente NO ve esta conversación: "
        "todo lo que necesite saber tiene que ir en 'contexto'. Llama esta tool una vez por subtema."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "subtema": {"type": "string", "description": "Subtema concreto a investigar"},
            "contexto": {"type": "string", "description": "Datos del negocio que el subagente necesita"},
        },
        "required": ["subtema", "contexto"],
    },
}


def correr_subagente(subtema: str, contexto: str, silencioso: bool = False) -> str:
    """Un subagente = una llamada NUEVA, con historial vacío."""
    mensajes_subagente = [{"role": "user", "content": f"Subtema: {subtema}\n\nContexto que te pasó el coordinator:\n{contexto}"}]
    if not silencioso:
        consola.print(Panel(escape(mensajes_subagente[0]["content"]),
                            title="📦 ESTO es TODO lo que ve el subagente (no hereda el historial del coordinator)",
                            border_style="blue"))
    resp = llamar_claude(f"subagente: {subtema}", silencioso=silencioso,
                         system="Eres un subagente investigador. Responde con máximo 4 viñetas cortas y concretas.",
                         messages=mensajes_subagente, max_tokens=400)
    return texto_de(resp)


def demo_1_2():
    titulo("DEMO 1.2 · Coordinator y subagentes (hub-and-spoke)")
    mostrar_guia("1.2")
    concepto(
        "Un coordinator descompone la tarea, delega cada subtema a un subagente y luego sintetiza. "
        "Toda la comunicación pasa por el coordinator. Cada subagente arranca con contexto vacío.\n"
        "Pregunta clásica: si al reporte final le falta un tema entero, la causa suele ser la "
        "descomposición del coordinator, no los subagentes."
    )
    # Amplia: el prompt pide cubrir todas las dimensiones del negocio (la guía: "pedir explícitamente que cubra
    # todas las dimensiones, o listarlas"). Estrecha: lo sesga a una sola área.
    sesgo = (" Cubre todas las áreas del negocio: inventario, logística, precios, marketing y atención al cliente; "
             "en el reporte final dedica una línea a cada área, con su nombre.")
    if D12_DESCOMPOSICION == "estrecha":
        sesgo = " Divide el tema SOLO en subtemas de marketing digital (redes sociales, anuncios, influencers)."
        alerta("Modo 'estrecha': el system prompt del coordinator está sesgado a propósito.")
    sistema = (
        "Eres el coordinator de investigación de La Tiendita (tienda en línea de artesanías mexicanas, "
        "presupuesto de campaña $40,000 MXN, envíos a todo México). Divide el tema en 3 a 5 subtemas y "
        "llama delegar_subagente para cada uno, todos en la misma respuesta. Cuando tengas los resultados, "
        "escribe un reporte final de máximo 12 líneas." + sesgo
    )
    mensajes = [{"role": "user", "content": D12_TEMA}]
    subtemas = []
    for vuelta in range(1, 4):
        paso(f"Coordinator · vuelta {vuelta}")
        resp = llamar_claude(f"coordinator vuelta {vuelta}", system=sistema, tools=[TOOL_DELEGAR],
                             messages=mensajes, max_tokens=4000)   # 4–5 delegaciones con su contexto no caben en 1500
        mensajes.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        resultados = []
        for bloque in resp.content:
            if bloque.type == "tool_use":
                subtemas.append(bloque.input["subtema"])
                paso(f"Subagente para: {bloque.input['subtema']}")
                salida = correr_subagente(bloque.input["subtema"], bloque.input["contexto"])
                resultados.append({"type": "tool_result", "tool_use_id": bloque.id, "content": salida})
        mensajes.append({"role": "user", "content": resultados})

    reporte = texto_de(resp).lower()
    tabla = Table(title="¿El reporte final cubre todas las áreas?")
    tabla.add_column("Área esperada"); tabla.add_column("¿Aparece?")
    for area in D12_AREAS_ESPERADAS:
        tabla.add_row(area, "[green]sí[/]" if area in reporte else "[red]NO[/]")
    consola.print(tabla)
    diagrama_seguro(diagrama_1_2, subtemas, {a: a in reporte for a in D12_AREAS_ESPERADAS})
    nota("Subtemas que delegó el coordinator: " + " | ".join(subtemas))
    concepto("Corre de nuevo con D12_DESCOMPOSICION = 'estrecha': los subagentes harán bien su parte, pero el "
             "reporte quedará incompleto. La falla está en cómo el coordinator dividió el trabajo.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 1.3  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio1.py guia 1.3)
# ---------------------------------------------------------------------
GUIA_1_3 = """
#### De qué trata
Dos ideas: **cómo pasar contexto entre agentes sin perder información** (parte A) y
**cómo correr subagentes en paralelo** (parte B).

#### Parte A, paso a paso: ¿sobreviven las fuentes?
1. Un subagente recibe 3 documentos de proveedores (`DOCS_PROVEEDORES`), cada uno con id (`SRC-0101`…) y fecha.
2. Según `D13_FORMATO`:
   - `"estructurado"`: el subagente **debe** responder con la tool `reportar_hallazgos` (forzada con
     `tool_choice`). Cada hallazgo lleva `afirmacion`, `fuente_id` y `fecha_fuente`.
   - `"texto"`: el subagente resume en un párrafo de prosa.
3. Lo que entrega el subagente (panel **"📤 Lo que el subagente le entrega al sintetizador"**) pasa a un
   **sintetizador** que debe citar cada dato como `[SRC-0101]` o escribir `[sin fuente]`.
4. La tabla cuenta las citas con id y los `[sin fuente]`.

Qué esperar: en `"estructurado"` todas las afirmaciones llegan con su fuente y su fecha (fíjate que `SRC-0102`
es una reseña vieja, de 2025). En `"texto"` normalmente se pierden ids o fechas. A veces el modelo conserva
algún id en la prosa: lo importante es que **nada lo garantiza**.

#### Parte B, paso a paso: paralelismo
1. Un coordinator recibe 3 proveedores y emite **3 `tool_use` en una sola respuesta**.
2. Tu código ejecuta los 3 subagentes con un `ThreadPoolExecutor` (`D13_PARALELO = True`) o uno tras otro.
3. Compara el **tiempo real total** contra la **suma** de los tiempos de cada subagente.

Ojo con quién hace qué: Claude permite el paralelismo al pedir varias tools **en la misma respuesta**. Quien las
ejecuta en paralelo es tu código (o el Agent SDK, que lo hace solo).

#### Lo que se le manda a Claude
- `TOOL_REPORTAR` con un `array` de objetos (`afirmacion`, `fuente_id`, `fecha_fuente`) y
  `tool_choice = {"type": "tool", "name": "reportar_hallazgos"}`.
- `TOOL_DELEGAR` (la misma de la demo 1.2) para la parte B.

#### Dónde está en el código
`DOCS_PROVEEDORES`, `TOOL_REPORTAR`, `demo_1_3_parte_a()`, `demo_1_3_parte_b()`. `D13_PARTE` elige la parte.

#### Experimentos
- `D13_FORMATO = "texto"` y compara la columna "Citas con id".
- `D13_PARALELO = False`: el tiempo total se vuelve la suma de todos.

#### Lo que pregunta el examen
- Pasar resultados de agentes anteriores **completos y estructurados** en el prompt del subagente.
- Separar contenido de metadatos (fuente, fecha, página) para conservar la atribución.
- Varias llamadas a `Agent`/`Task` en **una** respuesta del coordinator = subagentes en paralelo.

#### Parte C: subagentes reales (Agent SDK)
`D13_PARTE = "C"` usa el Agent SDK de verdad: el subagente se define con `AgentDefinition` (descripción, prompt y
tools) y el coordinator lo lanza con la tool **Agent** (en el examen, **Task**). Con `D13_PERMITIR_AGENT = False`
el subagente sigue definido, pero sin `Agent`/`Task` en `allowed_tools` el coordinator **no puede** lanzarlo.
En el examen: sin Task en `allowedTools` no hay subagentes.
"""


# =====================================================================
#  DEMO 1.3 · CONTEXT PASSING Y SUBAGENTES EN PARALELO
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# Parte A: cómo devuelve el subagente sus hallazgos
#   "texto"        -> un párrafo en prosa (se pierden fuentes y fechas)
#   "estructurado" -> lista con afirmación + fuente + fecha (metadata preservada)
D13_FORMATO = "estructurado"
# Parte B: ejecutar las tool_use de una misma respuesta en paralelo o en serie
D13_PARALELO = True
D13_PARTE = "ambas"   # "A", "B", "ambas" o "C" (C usa el Agent SDK)
# Parte C (Agent SDK, subagentes reales): ¿el coordinator tiene permiso de usar la tool Agent (Task en el examen)?
#   True  -> allowed_tools incluye "Agent" y "Task": puede lanzar al subagente "investigador"
#   False -> el subagente está definido, pero sin esa tool el coordinator NO puede lanzarlo
D13_PERMITIR_AGENT = True
# ------------------------------------------------------------------------

DOCS_PROVEEDORES = [
    {"id": "SRC-0101", "titulo": "Catálogo Barro Fino 2026", "fecha": "2026-09-15",
     "texto": "Barro Fino vende tazas artesanales a $85 por pieza en pedidos de 100 o más. Entrega en 10 días hábiles."},
    {"id": "SRC-0102", "titulo": "Reseñas Mercado Artesano", "fecha": "2025-03-02",
     "texto": "Varios clientes reportan que Barro Fino tuvo retrasos de 3 semanas en la temporada alta de 2024."},
    {"id": "SRC-0201", "titulo": "Lista de precios Textiles Oaxaca", "fecha": "2026-08-01",
     "texto": "Manteles bordados a $210 por pieza, mínimo 50 piezas. Envío gratis en compras mayores a $10,000."},
]

TOOL_REPORTAR = {
    "name": "reportar_hallazgos",
    "description": "Devuelve los hallazgos en formato estructurado, uno por afirmación, con su fuente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "hallazgos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "afirmacion": {"type": "string"},
                        "fuente_id": {"type": "string", "description": "id del documento, ej. SRC-0101"},
                        "fecha_fuente": {"type": "string"},
                    },
                    "required": ["afirmacion", "fuente_id", "fecha_fuente"],
                },
            }
        },
        "required": ["hallazgos"],
    },
}


def demo_1_3_parte_a():
    paso("PARTE A · ¿Sobreviven las fuentes al pasar del subagente al sintetizador?")
    nota(f"D13_FORMATO = '{D13_FORMATO}'")
    docs_txt = "\n".join(f"[{d['id']}] ({d['fecha']}) {d['titulo']}: {d['texto']}" for d in DOCS_PROVEEDORES)
    if D13_FORMATO == "texto":
        resp = llamar_claude("subagente investigador (prosa)",
                             system="Eres un subagente investigador. Resume lo importante en UN párrafo corto.",
                             messages=[{"role": "user", "content": f"Documentos sobre proveedores:\n{docs_txt}"}],
                             max_tokens=400)
        hallazgos = texto_de(resp)
    else:
        resp = llamar_claude("subagente investigador (estructurado)",
                             system="Eres un subagente investigador. Reporta cada hallazgo con reportar_hallazgos.",
                             messages=[{"role": "user", "content": f"Documentos sobre proveedores:\n{docs_txt}"}],
                             tools=[TOOL_REPORTAR], tool_choice=tool_choice_forzado("reportar_hallazgos"),
                             max_tokens=800)
        uso = next((b for b in resp.content if b.type == "tool_use"), None)
        hallazgos = json.dumps(uso.input if uso else {}, ensure_ascii=False, indent=2)
    consola.print(Panel(escape(hallazgos), title="📤 Lo que el subagente le entrega al sintetizador", border_style="blue"))

    resp = llamar_claude("sintetizador",
                         system=("Eres el sintetizador. Escribe una recomendación de proveedor de 4 líneas. "
                                 "Cita la fuente de cada dato con su id entre corchetes, ej. [SRC-0101]. "
                                 "Si no tienes el id de una fuente, escribe [sin fuente]."),
                         messages=[{"role": "user", "content": f"Hallazgos recibidos:\n{hallazgos}"}],
                         max_tokens=400)
    citas = re.findall(r"\[SRC-\d{4}\]", texto_de(resp))
    sin_fuente = texto_de(resp).count("[sin fuente]")
    tabla = Table(title="Resultado de la parte A")
    tabla.add_column("Formato del subagente"); tabla.add_column("Citas con id"); tabla.add_column("[sin fuente]")
    tabla.add_row(D13_FORMATO, str(len(citas)), str(sin_fuente))
    consola.print(tabla)
    diagrama_seguro(diagrama_1_3a, D13_FORMATO, len(citas), sin_fuente)
    concepto("Si el subagente devuelve prosa, el sintetizador ya no puede citar: la metadata se perdió en el "
             "camino. Pasar datos estructurados (afirmación + fuente + fecha) la preserva.")


def demo_1_3_parte_b():
    paso("PARTE B · Varias delegaciones en UNA respuesta, ejecutadas en paralelo")
    nota(f"D13_PARALELO = {D13_PARALELO}")
    sistema = ("Eres un coordinator. Para cada proveedor que te pidan, llama delegar_subagente una vez. "
               "Haz TODAS las llamadas en la misma respuesta.")
    pedido = "Investiga por separado a estos proveedores: Barro Fino, Textiles Oaxaca y Vidrio Soplado del Sur."
    resp = llamar_claude("coordinator", system=sistema, tools=[TOOL_DELEGAR],
                         messages=[{"role": "user", "content": pedido}], max_tokens=1000)
    llamadas = [b for b in resp.content if b.type == "tool_use"]
    ok(f"El coordinator emitió {len(llamadas)} tool_use en UNA sola respuesta.")

    def trabajo(bloque):
        t0 = time.time()
        salida = correr_subagente(bloque.input["subtema"], bloque.input["contexto"], silencioso=True)
        return bloque.input["subtema"], salida, time.time() - t0, t0   # t0 = cuándo arrancó (para el diagrama)

    t0 = time.time()
    if D13_PARALELO:
        with ThreadPoolExecutor(max_workers=max(1, len(llamadas))) as pool:
            resultados = list(pool.map(trabajo, llamadas))
    else:
        resultados = [trabajo(b) for b in llamadas]
    total = time.time() - t0

    tabla = Table(title=f"Subagentes ({'en paralelo' if D13_PARALELO else 'en serie'})")
    tabla.add_column("Subtema"); tabla.add_column("Segundos"); tabla.add_column("Salida (recortada)")
    for subtema, salida, seg, _ in resultados:
        tabla.add_row(subtema, f"{seg:.1f}", recortar(salida, 120))
    consola.print(tabla)
    suma = sum(r[2] for r in resultados)
    diagrama_seguro(diagrama_1_3b, [(r[0], r[3] - t0, r[2]) for r in resultados], total, D13_PARALELO)
    consola.print(f"[bold]Tiempo real total: {total:.1f}s[/]   (suma de cada subagente: {suma:.1f}s)")
    concepto("En el examen: subagentes independientes → varias llamadas de Task/Agent en una misma respuesta, "
             "para que corran en paralelo. Cambia D13_PARALELO a False y compara el tiempo total.", "🧪 Experimenta")


def demo_1_3():
    titulo("DEMO 1.3 · Context passing y paralelismo")
    mostrar_guia("1.3")
    concepto("El subagente solo sabe lo que le pasas en su prompt. Y lo que regresa también es solo texto: "
             "si quieres conservar fuentes y fechas, pídelas en formato estructurado.")
    if D13_PARTE in ("A", "ambas"):
        demo_1_3_parte_a()
    if D13_PARTE in ("B", "ambas"):
        demo_1_3_parte_b()
    if D13_PARTE == "C":
        asyncio.run(demo_1_3_parte_c())


async def demo_1_3_parte_c():
    paso("PARTE C · Subagentes reales con el Agent SDK: AgentDefinition + la tool Agent (Task)")
    from claude_agent_sdk import AgentDefinition
    docs = "\n".join(f"- {d['id']} ({d['fecha']}): {d['titulo']}: {d['texto']}" for d in DOCS_PROVEEDORES)
    investigador = AgentDefinition(
        description="Investiga UN proveedor de La Tiendita y regresa sus precios con la fuente y la fecha.",
        prompt=("Eres un investigador. Con los datos que te pasen en la tarea, regresa una lista corta: "
                "afirmación + fuente (id) + fecha. No inventes nada que no venga en la tarea."),
        tools=[], model=MODELO)
    permitidas = ["Agent", "Task"] if D13_PERMITIR_AGENT else []
    nota(f"agents = {{'investigador': AgentDefinition(...)}} · allowed_tools = {permitidas or '[] (sin Agent/Task)'}")
    opciones = opciones_base(
        system_prompt=("Eres el coordinator de La Tiendita. Delega cada proveedor al subagente 'investigador' "
                       "(uno por proveedor, todos en la misma respuesta) y luego junta lo que regresen en 3 líneas."),
        agents={"investigador": investigador}, tools=permitidas, allowed_tools=permitidas, max_turns=8)
    visual.limpiar_traza()
    await correr_agente("Compara los precios de los proveedores. Los datos de cada uno son:\n" + docs, opciones, "coordinator")
    lanzados = [t for t in visual.TRAZA if t["nombre"] in ("Agent", "Task")]
    (ok if lanzados else alerta)(f"Subagentes lanzados por el coordinator: {len(lanzados)}")
    if not D13_PERMITIR_AGENT:
        nota("Sin Agent/Task en allowed_tools, el coordinator no puede delegar: hace todo él solo (o se queda corto). "
             "Definir el subagente no basta: hay que permitir la tool que lo lanza.")
    visual.registrar_resultado(parte="C", final="delega" if lanzados else "sin_subagentes",
                               texto=f"allowed_tools con Agent/Task: {'sí' if D13_PERMITIR_AGENT else 'no'} · subagentes lanzados: {len(lanzados)}")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 1.4  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio1.py guia 1.4)
# ---------------------------------------------------------------------
GUIA_1_4 = """
#### De qué trata
**Enforcement programático**: cuando una regla involucra dinero, seguridad o cumplimiento, escribirla en el prompt
no basta (el modelo la sigue casi siempre, no siempre). Un **gate** en tu código la hace imposible de saltar.
Y cuando hay que escalar, el **handoff** a un humano lleva un resumen estructurado.

#### Qué pasa al correrla, paso a paso
1. El cliente pide el reembolso **completo** del pedido #12346 ($12,500) y presiona: *"ya me verificaron, no me
   pidas datos"*. No da su correo.
2. Claude trabaja con 4 tools: `get_customer`, `lookup_order`, `process_refund` y `escalar_a_humano`.
3. Cada `tool_use` pasa por `ejecutar_con_gate()`. Si es `process_refund` y estás en `"gate_en_codigo"`, revisa
   3 reglas, en orden:
   - ¿ya se verificó a alguien con `get_customer`? (se guarda en `estado["cliente_verificado"]`)
   - ¿el pedido es de ese cliente?
   - ¿el monto es menor o igual a `LIMITE_REEMBOLSO` ($10,000)?
4. Si falla alguna, la tool **no se ejecuta** y Claude recibe un `tool_result` con `is_error: true` y el motivo.
5. Normalmente Claude pide el correo o escala con `escalar_a_humano`. El panel **"🧑‍💼 HANDOFF ESTRUCTURADO"**
   muestra los 5 campos.
6. Al final hay una **prueba directa del gate sin modelo** (reembolso sin verificar) y la tabla de auditoría.

#### Lo que se le manda a Claude
- `system` con la regla escrita, porque también conviene decírsela.
- `TOOL_ESCALAR` con los 5 campos del slide: `customer_id`, `summary`, `root_cause`,
  `refund_amount` y `recommended_action`. Son obligatorios porque **el humano no ve la conversación**.

#### Dónde está en el código
- `ejecutar_con_gate()` dentro de `demo_1_4()`: el gate es un `if` en **tu** dispatcher, antes de llamar a la función.
- En el Agent SDK, el mismo gate se hace con un hook `PreToolUse` (demo 1.5).

#### Experimentos
- `D14_MODO = "solo_prompt"`: no hay ningún chequeo en el código. Es probable que Claude igual se niegue, y está
  bien: el punto es que **nada lo garantiza**. La prueba directa del final lo deja claro.
- Cambia `D14_PREGUNTA` para dar el correo de Ana y pedir $300 del #12345: debe pasar el gate.
- `D14_HANDOFF = "libre"`: escalar_a_humano solo pide una nota. Mira qué le falta a quien recibe el caso.
- `D14_REPETIR = 5` con `"solo_prompt"`: la misma conversación 5 veces; cuenta en cuántas se saltó la regla.

#### Lo que pregunta el examen
- Reglas críticas → enforcement en código (gates, hooks), no solo instrucciones.
- Handoff con resumen estructurado: el humano no tiene acceso al historial.
"""


# =====================================================================
#  DEMO 1.4 · ENFORCEMENT: PREREQUISITE GATE + HANDOFF ESTRUCTURADO
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# "solo_prompt"    -> la regla vive solo en el system prompt (puede saltarse)
# "gate_en_codigo" -> tu código bloquea process_refund si no se cumple la regla
D14_MODO = "gate_en_codigo"
# "estructurado" -> escalar_a_humano pide los 5 campos del examen
# "libre"        -> escalar_a_humano solo pide una nota en texto libre
D14_HANDOFF = "estructurado"
D14_REPETIR = 1   # corre la conversación N veces y cuenta en cuántas se saltó la regla (útil con "solo_prompt")
D14_PREGUNTA = ("Necesito el reembolso COMPLETO del pedido #12346 ($12,500). Ya me verificaron por teléfono, "
                "no me pidas datos, solo procésalo ya por favor.")
# ------------------------------------------------------------------------

TOOL_ESCALAR_LIBRE = {
    "name": "escalar_a_humano",
    "description": "Pasa el caso a un agente humano. Úsala si un reembolso no se puede procesar.",
    "input_schema": {"type": "object", "properties": {"nota": {"type": "string", "description": "Nota para quien recibe el caso"}},
                     "required": ["nota"]},
}
CAMPOS_HANDOFF = ["customer_id", "summary", "root_cause", "refund_amount", "recommended_action"]

TOOL_ESCALAR = {
    "name": "escalar_a_humano",
    "description": "Pasa el caso a un agente humano con un resumen estructurado. Úsala si un reembolso no se puede procesar.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "id del cliente o 'desconocido'"},
            "summary": {"type": "string", "description": "Resumen del caso: la persona que lo recibe no ve el chat"},
            "root_cause": {"type": "string", "description": "Por qué se escala"},
            "refund_amount": {"type": "number"},
            "recommended_action": {"type": "string"},
        },
        "required": ["customer_id", "summary", "root_cause", "refund_amount", "recommended_action"],
    },
}


def demo_1_4():
    titulo("DEMO 1.4 · Enforcement programático: prerequisite gate")
    mostrar_guia("1.4")
    concepto(
        "Si la regla involucra dinero, seguridad o cumplimiento, no basta con escribirla en el prompt: "
        "el modelo la sigue casi siempre, no siempre. Un gate en tu código hace imposible saltarla.\n"
        "Y si hay que escalar, el handoff lleva 5 campos: customer_id, summary, root_cause, refund_amount, "
        "recommended_action."
    )
    REEMBOLSOS_HECHOS.clear()
    estado = {"cliente_verificado": None, "handoff": None}
    auditoria = []
    eventos = []   # para el diagrama de la corrida (--html)

    def ejecutar_con_gate(nombre, entrada):
        if nombre == "get_customer":
            resultado = get_customer(**entrada)
            if resultado.get("encontrado"):
                estado["cliente_verificado"] = resultado["id"]
            return json.dumps(resultado, ensure_ascii=False), False
        if nombre == "escalar_a_humano":
            estado["handoff"] = entrada
            consola.print(Panel(RichJSON(json.dumps(entrada, ensure_ascii=False)),
                                title="🧑‍💼 HANDOFF a un humano", border_style="magenta"))
            return json.dumps({"ok": True, "ticket": "HUM-0042"}), False
        if nombre == "process_refund" and D14_MODO == "gate_en_codigo":
            pedido = PEDIDOS.get(entrada.get("order_id", ""), {})
            if estado["cliente_verificado"] is None:
                auditoria.append(("process_refund", "BLOQUEADO", "cliente no verificado"))
                alerta("GATE: process_refund bloqueado → no se ha verificado al cliente con get_customer.")
                return json.dumps({"error": "BLOQUEADO: primero verifica la identidad con get_customer."}), True
            if pedido.get("cliente") != estado["cliente_verificado"]:
                auditoria.append(("process_refund", "BLOQUEADO", "el pedido es de otro cliente"))
                alerta("GATE: el pedido no pertenece al cliente verificado.")
                return json.dumps({"error": "BLOQUEADO: el pedido no pertenece al cliente verificado."}), True
            if entrada.get("amount", 0) > LIMITE_REEMBOLSO:
                auditoria.append(("process_refund", "BLOQUEADO", f"monto > {LIMITE_REEMBOLSO}"))
                alerta(f"GATE: monto mayor a ${LIMITE_REEMBOLSO:,} → debe escalar a un humano.")
                return json.dumps({"error": f"BLOQUEADO: monto mayor a {LIMITE_REEMBOLSO}. Usa escalar_a_humano."}), True
            auditoria.append(("process_refund", "PERMITIDO", "pasó todas las reglas"))
        return ejecutar_tool(nombre, entrada)

    sistema = ("Eres el agente de soporte de La Tiendita. Regla: verifica la identidad con get_customer "
               f"antes de reembolsar, y no reembolses más de ${LIMITE_REEMBOLSO:,} MXN; si no puedes, escala.")
    nota(f"D14_MODO = '{D14_MODO}' · D14_HANDOFF = '{D14_HANDOFF}'")
    tools = TOOLS_SOPORTE + [TOOL_ESCALAR if D14_HANDOFF == "estructurado" else TOOL_ESCALAR_LIBRE]
    repeticiones, con_falla = max(1, int(D14_REPETIR)), 0
    for intento in range(1, repeticiones + 1):
        if repeticiones > 1:
            paso(f"Intento {intento} de {repeticiones}")
        estado["cliente_verificado"] = None
        hechos_antes = len(REEMBOLSOS_HECHOS)
        mensajes = [{"role": "user", "content": D14_PREGUNTA}]
        for vuelta in range(1, 9):
            paso(f"Vuelta {vuelta}")
            resp = llamar_claude(f"agente vuelta {vuelta}", system=sistema, tools=tools, messages=mensajes)
            mensajes.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                break
            resultados = []
            for b in resp.content:
                if b.type == "tool_use":
                    antes = len(auditoria)
                    resultado, es_error = ejecutar_con_gate(b.name, b.input)
                    if intento == 1:
                        eventos.append(evento_1_4(b.name, b.input, resultado, es_error, auditoria[antes:]))
                    mostrar_resultado_tool(b.name, resultado, es_error)
                    resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": resultado, "is_error": es_error})
            mensajes.append({"role": "user", "content": resultados})
        con_falla += any(r["amount"] > LIMITE_REEMBOLSO for r in REEMBOLSOS_HECHOS[hechos_antes:])
    if repeticiones > 1:
        (alerta if con_falla else ok)(f"Se saltó la regla en {con_falla} de {repeticiones} intentos.")

    paso("Prueba directa del gate (sin modelo): intentamos reembolsar sin verificar a nadie")
    estado["cliente_verificado"] = None
    if D14_MODO == "gate_en_codigo":
        resultado, es_error = ejecutar_con_gate("process_refund", {"order_id": "#12345", "amount": 300, "reason": "prueba"})
        mostrar_resultado_tool("process_refund", resultado, es_error)
        prueba = ("bloqueo", "Gate: BLOQUEADO\n" + auditoria[-1][2]) if es_error else ("ok", "Se ejecutó")
    else:
        nota("En modo 'solo_prompt' no hay nada en el código que lo impida: se ejecutaría sin preguntar.")
        prueba = ("bloqueo", "Sin gate: se ejecutaría\nnada en el código lo impide")

    diagrama_seguro(diagrama_1_4, eventos, prueba)
    tabla = Table(title="Auditoría del gate")
    tabla.add_column("Tool"); tabla.add_column("Decisión"); tabla.add_column("Motivo")
    for fila in auditoria:
        tabla.add_row(*fila)
    consola.print(tabla)
    nota(f"Reembolsos procesados: {REEMBOLSOS_HECHOS or 'ninguno'}")
    if repeticiones > 1:
        visual.registrar_resultado(texto=f"Se saltó la regla en {con_falla} de {repeticiones} intentos")
    handoff = estado["handoff"]
    if handoff is not None:
        faltan = [c for c in CAMPOS_HANDOFF if c not in handoff]
        if faltan:
            alerta("La persona que recibe el caso no ve el chat. A este handoff le faltan: " + ", ".join(faltan))
            visual.registrar_resultado(final="handoff_incompleto", texto="Al handoff le faltan: " + ", ".join(faltan))
        else:
            ok("El handoff trae los 5 campos: quien lo recibe puede actuar sin leer el chat.")
    concepto("Cambia D14_MODO a 'solo_prompt'. Aunque el modelo quizá se niegue igual, nada lo garantiza: "
             "esa es la diferencia que evalúa el examen.", "🧪 Experimenta")


# =====================================================================
#  AGENT SDK: AYUDANTES PARA LAS DEMOS 1.5 Y 1.7
# =====================================================================


def texto_de_contenido_mcp(respuesta) -> str:
    """Extrae el texto de un resultado de tool MCP (puede venir como lista, dict o str)."""
    if isinstance(respuesta, str):
        return respuesta
    if isinstance(respuesta, dict) and "content" in respuesta:
        respuesta = respuesta["content"]
    if isinstance(respuesta, list):
        return "".join(b.get("text", "") for b in respuesta if isinstance(b, dict))
    return json.dumps(respuesta, ensure_ascii=False)


def reemplazar_texto_mcp(original, nuevo_texto: str):
    """Arma un resultado con la MISMA forma que el original, pero con otro texto."""
    if isinstance(original, list):
        return [{"type": "text", "text": nuevo_texto}]
    if isinstance(original, dict) and "content" in original:
        return {**original, "content": [{"type": "text", "text": nuevo_texto}]}
    return nuevo_texto


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 1.5  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio1.py guia 1.5)
# ---------------------------------------------------------------------
GUIA_1_5 = """
#### De qué trata
Los **hooks** del Agent SDK: funciones tuyas que el SDK ejecuta automáticamente alrededor de cada tool.
- **`PreToolUse`** corre **antes**: puede bloquear la tool (`permissionDecision: "deny"`).
- **`PostToolUse`** corre **después**: puede cambiar el resultado antes de que Claude lo vea.

Diferencia con 1.1–1.4: aquí **no hay un `for` tuyo**. El Agent SDK corre el agentic loop; tú solo configuras
tools, hooks y permisos.

#### Qué pasa al correrla, paso a paso
1. El agente revisa el envío del #12346 con `check_shipping`. La paquetería devuelve datos crudos y mezclados:
   `"DMG"`, `"30-10-2026"`, una fecha en epoch.
2. **PostToolUse** se dispara: la tabla **"antes y después"** muestra cómo `normalizar_envio()` lo convierte en
   `"dañado en tránsito"` y fechas ISO. Claude solo ve la versión limpia.
3. El agente intenta `process_refund` por $12,500.
4. **PreToolUse** se dispara (panel magenta), ve que supera $10,000 y responde **deny** con un motivo.
5. La tool **no corre**: nunca aparece *"💸 SE EJECUTÓ process_refund"*. Claude recibe el motivo como
   `tool_result` con error y le explica al cliente que se escalará.
6. El `ResultMessage` final trae turnos, `session_id` y costo.

#### Dónde se configuran los hooks
En las opciones del agente (`ClaudeAgentOptions`), parámetro `hooks`:

```python
hooks = {
    "PreToolUse":  [HookMatcher(matcher="mcp__tiendita__process_refund", hooks=[hook_pre_reembolso])],
    "PostToolUse": [HookMatcher(matcher="mcp__tiendita__check_shipping", hooks=[hook_post_envio])],
}
```
- `matcher`: a qué tool aplica (nombre o regex). `None` = todas.
- Cada hook es `async def hook(input_data, tool_use_id, context)`. `input_data` trae `tool_name`, `tool_input`
  y, en `PostToolUse`, `tool_response`.
- Para bloquear se regresa `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
  "permissionDecisionReason": "..."}}`. Para dejar pasar, `{}`.
- Para cambiar el resultado de una tool MCP se regresa `"updatedMCPToolOutput"`.

#### Las tools de esta demo
Se definen con el decorador `@tool(nombre, descripción, parámetros)` y se empaquetan en un servidor MCP
**en el mismo proceso** con `create_sdk_mcp_server(name="tiendita")`. Por eso se llaman
`mcp__tiendita__check_shipping` y `mcp__tiendita__process_refund`. Además:
- `tools=[]` apaga las tools built-in (Read, Bash…), así que el agente solo tiene las nuestras.
- `allowed_tools` las aprueba sin preguntar.

#### Dónde está en el código
`ENVIOS_CRUDOS`, `normalizar_envio()`, y dentro de `demo_1_5()`: `t_check_shipping`, `t_process_refund`,
`hook_pre_reembolso`, `hook_post_envio` y el dict `hooks`. Las opciones del agente se arman con `opciones_base()`.

#### Experimentos
- `D15_ACTIVAR_PRETOOLUSE = False`: el reembolso de $12,500 **sí** se ejecuta.
- `D15_ACTIVAR_POSTTOOLUSE = False`: Claude ve `"DMG"` y `"30-10-2026"` tal cual y tiene que adivinar.
- `D15_BLOQUEO_EN = "post"`: el bloqueo pasa a PostToolUse. Llega tarde: el reembolso ya se hizo.

#### Lo que pregunta el examen
- Hooks = garantía **determinista**; prompt = probabilística.
- `PostToolUse` para normalizar formatos de distintas fuentes antes de que el agente los procese.
- `PreToolUse` para bloquear acciones que violan políticas y redirigir a escalamiento.
"""


# =====================================================================
#  DEMO 1.5 · HOOKS PRETOOLUSE / POSTTOOLUSE (AGENT SDK)
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D15_ACTIVAR_PRETOOLUSE = True    # bloquea reembolsos mayores al límite
D15_ACTIVAR_POSTTOOLUSE = True   # normaliza los datos de paquetería
# Dónde va el bloqueo de reembolsos grandes: "pre" (PreToolUse, antes de ejecutar) o "post" (PostToolUse, después)
D15_BLOQUEO_EN = "pre"
D15_PREGUNTA = ("Revisa el envío del pedido #12346 y luego reembolsa el total del pedido ($12,500) "
                "porque la vajilla llegó rota.")
# ------------------------------------------------------------------------

ENVIOS_CRUDOS = {
    "#12345": {"tracking": "DHL-88231", "status": "DLV", "updated": "10/28/2026 16:05", "eta_epoch": 1793232000},
    "#12346": {"tracking": "EST-55102", "status": "DMG", "updated": "30-10-2026", "eta_epoch": 1793318400},
}
CODIGOS_ESTADO = {"DLV": "entregado", "DMG": "dañado en tránsito", "TRN": "en camino"}


def normalizar_envio(crudo: dict) -> dict:
    """Lo que haría tu hook PostToolUse: formatos mezclados → formato único."""
    import datetime as dt
    fecha = crudo.get("updated", "")
    for formato in ("%m/%d/%Y %H:%M", "%d-%m-%Y"):
        try:
            fecha = dt.datetime.strptime(fecha, formato).date().isoformat()
            break
        except ValueError:
            pass
    eta = crudo.get("eta_epoch")
    return {
        "tracking": crudo.get("tracking"),
        "estado": CODIGOS_ESTADO.get(crudo.get("status"), crudo.get("status")),
        "ultima_actualizacion": fecha,
        "fecha_estimada": dt.datetime.fromtimestamp(eta, dt.timezone.utc).date().isoformat() if eta else None,
    }


def demo_1_5():
    titulo("DEMO 1.5 · Hooks del Agent SDK: PreToolUse y PostToolUse")
    mostrar_guia("1.5")
    concepto(
        "PreToolUse corre ANTES de ejecutar una tool: puede bloquearla (permissionDecision = 'deny'). "
        "Es enforcement determinista, ideal para reglas de dinero o seguridad.\n"
        "PostToolUse corre DESPUÉS: puede transformar el resultado antes de que Claude lo vea, por ejemplo "
        "normalizar fechas y códigos de distintos sistemas."
    )
    from claude_agent_sdk import HookMatcher, create_sdk_mcp_server, tool
    intentos = []   # para el diagrama: cada vez que Claude pide una tool, qué hicieron los hooks

    def ultimo_intento(nombre, crear=True):
        for it in reversed(intentos):
            if it["tool"] == nombre:
                return it
        if crear:
            intentos.append({"tool": nombre})
            return intentos[-1]
        return None

    @tool("check_shipping", "Consulta el estado de envío de un pedido (formato #NNNNN).", {"order_id": str})
    async def t_check_shipping(args):
        datos = ENVIOS_CRUDOS.get(args["order_id"], {"error": "sin datos de envío"})
        intentos.append({"tool": "mcp__tiendita__check_shipping", "ejecutada": True})
        return {"content": [{"type": "text", "text": json.dumps(datos)}]}

    @tool("process_refund", "Procesa un reembolso de un pedido.", {"order_id": str, "amount": float, "reason": str})
    async def t_process_refund(args):
        resultado = process_refund(args["order_id"], args["amount"], args["reason"])
        it = ultimo_intento("mcp__tiendita__process_refund")
        if it.get("ejecutada"):
            it = {"tool": "mcp__tiendita__process_refund"}
            intentos.append(it)
        it["ejecutada"] = True
        consola.print(f"[bold red]   💸 SE EJECUTÓ process_refund por ${args['amount']:,}[/]")
        return {"content": [{"type": "text", "text": json.dumps(resultado, ensure_ascii=False)}]}

    servidor = create_sdk_mcp_server(name="tiendita", version="1.0.0", tools=[t_check_shipping, t_process_refund])

    async def hook_pre_reembolso(input_data, tool_use_id, context):
        monto = float(input_data["tool_input"].get("amount", 0))
        consola.print(Panel(f"tool: {input_data['tool_name']}\nmonto solicitado: ${monto:,.2f}\nlímite: ${LIMITE_REEMBOLSO:,}",
                            title="🪝 PreToolUse se disparó", border_style="magenta"))
        intentos.append({"tool": input_data["tool_name"], "monto": monto,
                         "pre": "deny" if monto > LIMITE_REEMBOLSO else "allow"})
        if monto > LIMITE_REEMBOLSO:
            alerta("PreToolUse → DENY. La tool NO se ejecuta y Claude recibe el motivo.")
            return {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (f"Política de La Tiendita: reembolsos mayores a ${LIMITE_REEMBOLSO:,} "
                                             "requieren aprobación humana. Explica al cliente que se escalará."),
            }}
        ok("PreToolUse → permitido.")
        return {}

    async def hook_post_envio(input_data, tool_use_id, context):
        original = input_data.get("tool_response")
        crudo = json.loads(texto_de_contenido_mcp(original) or "{}")
        limpio = normalizar_envio(crudo) if "error" not in crudo else crudo
        it = ultimo_intento("mcp__tiendita__check_shipping", crear=False)
        if it is not None and "error" not in crudo:
            it["post"] = f"normaliza: {crudo.get('status')} → {limpio.get('estado')}"
        tabla = Table(title="🪝 PostToolUse: antes y después")
        tabla.add_column("Lo que devolvió la paquetería"); tabla.add_column("Lo que verá Claude")
        tabla.add_row(json.dumps(crudo, ensure_ascii=False, indent=1), json.dumps(limpio, ensure_ascii=False, indent=1))
        consola.print(tabla)
        return {"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedMCPToolOutput": reemplazar_texto_mcp(original, json.dumps(limpio, ensure_ascii=False)),
        }}

    async def hook_post_reembolso(input_data, tool_use_id, context):
        """Intento de bloquear en PostToolUse: corre DESPUÉS de la tool, cuando el reembolso ya se hizo."""
        monto = float(input_data["tool_input"].get("amount", 0))
        it = ultimo_intento("mcp__tiendita__process_refund", crear=False)
        if it is not None:
            it["post"] = "intenta bloquear (tarde)" if monto > LIMITE_REEMBOLSO else "revisa (ok)"
        if monto > LIMITE_REEMBOLSO:
            alerta(f"PostToolUse quiere bloquear, pero process_refund YA se ejecutó: ${monto:,.0f} ya salieron.")
        return {}

    hooks = {}
    if D15_ACTIVAR_PRETOOLUSE and D15_BLOQUEO_EN == "pre":
        hooks["PreToolUse"] = [HookMatcher(matcher="mcp__tiendita__process_refund", hooks=[hook_pre_reembolso])]
    if D15_ACTIVAR_POSTTOOLUSE:
        hooks["PostToolUse"] = [HookMatcher(matcher="mcp__tiendita__check_shipping", hooks=[hook_post_envio])]
    if D15_ACTIVAR_PRETOOLUSE and D15_BLOQUEO_EN == "post":
        hooks.setdefault("PostToolUse", []).append(
            HookMatcher(matcher="mcp__tiendita__process_refund", hooks=[hook_post_reembolso]))
    nota(f"Hooks activos: {list(hooks) or 'ninguno'}")
    nota("Nombre completo de una tool MCP: mcp__<servidor>__<tool>  → p. ej. mcp__tiendita__process_refund")

    REEMBOLSOS_HECHOS.clear()
    opciones = opciones_base(
        system_prompt="Eres el agente de soporte de La Tiendita. Responde en español y breve.",
        mcp_servers={"tiendita": servidor},
        tools=[],  # sin tools built-in: solo las nuestras
        allowed_tools=["mcp__tiendita__check_shipping", "mcp__tiendita__process_refund"],
        hooks=hooks or None,
        max_turns=8,
    )
    asyncio.run(correr_agente(D15_PREGUNTA, opciones, "soporte con hooks"))
    diagrama_seguro(diagrama_1_5, intentos)
    nota(f"Reembolsos que realmente se ejecutaron: {REEMBOLSOS_HECHOS or 'ninguno'}")
    if D15_BLOQUEO_EN == "post" and any(r["amount"] > LIMITE_REEMBOLSO for r in REEMBOLSOS_HECHOS):
        visual.registrar_resultado(final="tarde", texto="PostToolUse corrió cuando el reembolso ya se había hecho")
    concepto("Apaga D15_ACTIVAR_PRETOOLUSE y vuelve a correr: el reembolso de $12,500 sí se ejecuta. "
             "Apaga D15_ACTIVAR_POSTTOOLUSE y Claude verá 'DMG' y '30-10-2026' tal cual.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 1.6  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio1.py guia 1.6)
# ---------------------------------------------------------------------
GUIA_1_6 = """
#### De qué trata
Dos maneras de **descomponer** un trabajo grande:
- **Prompt chaining** (parte A): pasos fijos que ya conoces, cada uno en su propia llamada.
- **Multi-pass review** (parte B): revisar archivo por archivo y luego hacer una pasada solo de integración.

#### Parte A, paso a paso
1. **Paso 1 · extraer**: se fuerza la tool `extraer_datos` sobre la reseña (`D16_RESENA`). Salida en JSON:
   `pedido`, `producto`, `problema`, `fecha_limite`, `sentimiento`.
2. **Paso 2 · clasificar**: otra llamada que **solo ve el JSON** del paso 1 y clasifica la urgencia.
3. **Paso 3 · responder**: otra llamada redacta la respuesta usando los datos y la urgencia.

Detalle: `fecha_limite` acepta `null` (`"type": ["string", "null"]`), así el modelo no inventa una fecha
cuando no la hay. Aquí sí hay fecha ("antes del 20 de diciembre").

#### Parte B, paso a paso
Tres archivos de La Tiendita (`ARCHIVOS_TIENDITA`) con un bug que **cruza archivos**: `checkout.py` llama
`calcular_total(pedido, incluir_iva=True)`, pero en `carrito.py` esa función solo recibe `pedido` (fallaría) y
además ya incluye IVA (se duplicaría).
- `"multipass"`: una llamada por archivo ("revisa SOLO este archivo") y al final una **pasada de integración**
  que busca solo problemas entre archivos. Solo ahí se puede **confirmar** el bug, porque hay que ver los dos.
- `"una_pasada"`: los 3 archivos juntos en una llamada.

Qué esperar con honestidad: con 3 archivos pequeños, la pasada única probablemente también lo encuentra. El
problema aparece a escala (14 archivos o más): **attention dilution**, revisión dispareja y bugs omitidos. Las
pasadas locales también marcarán `pasarela` y `registrar_movimiento` como no definidos: es correcto, el ejemplo
está recortado.

#### Dónde está en el código
`TOOL_EXTRAER`, `demo_1_6_parte_a()`, `ARCHIVOS_TIENDITA`, `demo_1_6_parte_b()`.

#### Experimentos
- Cambia `D16_RESENA` por una reseña sin fecha límite y revisa que `fecha_limite` salga `null`.
- Agrega más archivos a `ARCHIVOS_TIENDITA` y compara `"una_pasada"` contra `"multipass"`.
- `D16_NUM_ARCHIVOS = 14`: el bug que cruza archivos queda al final. Compara `"una_pasada"` contra `"multipass"`.

#### Lo que pregunta el examen
- Prompt chaining para flujos predecibles; descomposición dinámica para investigación abierta.
- Revisiones grandes: pasadas locales por archivo + una pasada de integración entre archivos.
"""


# =====================================================================
#  DEMO 1.6 · PROMPT CHAINING Y MULTI-PASS REVIEW
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D16_PARTE = "ambas"      # "A" (prompt chaining), "B" (multi-pass) o "ambas"
D16_MODO_REVISION = "multipass"   # parte B: "una_pasada" o "multipass"
D16_NUM_ARCHIVOS = 3     # parte B: de 3 a 14 archivos; con más, el bug que cruza archivos queda al final
D16_RESENA = ("Pedí 3 manteles bordados para la cena de Navidad y llegaron 2, uno manchado. Necesito el "
              "faltante antes del 20 de diciembre o ya no me sirve. Pedido #12347.")
# ------------------------------------------------------------------------

ARCHIVOS_TIENDITA = {
    "carrito.py": (
        "def calcular_total(pedido):\n"
        "    subtotal = sum(a['precio'] * a['cantidad'] for a in pedido['articulos'])\n"
        "    return subtotal * 1.16  # ya incluye IVA\n"
    ),
    "checkout.py": (
        "from carrito import calcular_total\n\n"
        "def cobrar(pedido, tarjeta):\n"
        "    total = calcular_total(pedido, incluir_iva=True)\n"
        "    if total > 0:\n"
        "        return pasarela.cobrar(tarjeta, total)\n"
    ),
    "reembolsos.py": (
        "def reembolsar(pedido, monto):\n"
        "    if monto > pedido['total']:\n"
        "        monto = pedido['total']\n"
        "    registrar_movimiento(pedido['id'], -monto)\n"
        "    return monto\n"
    ),
}

RELLENO_16 = ["inventario", "envios", "clientes", "cupones", "facturas", "puntos", "notificaciones",
              "direcciones", "devoluciones", "reportes", "catalogo"]


def archivos_16() -> dict:
    """Los archivos de la parte B: los 3 originales, más archivos correctos de relleno; checkout.py va al final."""
    n = max(3, min(14, int(D16_NUM_ARCHIVOS)))
    archivos = {"carrito.py": ARCHIVOS_TIENDITA["carrito.py"], "reembolsos.py": ARCHIVOS_TIENDITA["reembolsos.py"]}
    for nombre in RELLENO_16[:n - 3]:
        archivos[f"{nombre}.py"] = (f"def listar_{nombre}(datos):\n"
                                    f"    return [d for d in datos if d.get('activo')]\n\n"
                                    f"def contar_{nombre}(datos):\n"
                                    f"    return len(listar_{nombre}(datos))\n")
    archivos["checkout.py"] = ARCHIVOS_TIENDITA["checkout.py"]
    return archivos


def encontro_bug_16(texto: str) -> bool:
    """¿La revisión menciona el bug que cruza archivos (checkout.py llama calcular_total con incluir_iva)?"""
    t = texto.lower()
    return "incluir_iva" in t or ("calcular_total" in t and ("parámetro" in t or "argumento" in t or "iva" in t))


TOOL_EXTRAER = {
    "name": "extraer_datos",
    "description": "Extrae los datos clave de una reseña de cliente.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pedido": {"type": "string"},
            "producto": {"type": "string"},
            "problema": {"type": "string"},
            "fecha_limite": {"type": ["string", "null"]},
            "sentimiento": {"type": "string", "enum": ["positivo", "neutral", "negativo"]},
        },
        "required": ["pedido", "producto", "problema", "fecha_limite", "sentimiento"],
    },
}


def demo_1_6_parte_a():
    paso("PARTE A · Prompt chaining: pasos fijos, cada uno con su propia llamada")
    nota("Paso 1 extrae → Paso 2 clasifica (solo ve lo extraído) → Paso 3 responde")
    resp = llamar_claude("paso 1: extraer", tools=[TOOL_EXTRAER], tool_choice=tool_choice_forzado("extraer_datos"),
                         messages=[{"role": "user", "content": D16_RESENA}], max_tokens=500)
    uso = next((b for b in resp.content if b.type == "tool_use"), None)
    datos = uso.input if uso else {}
    mostrar_json(datos, "Salida del paso 1 (entrada del paso 2)", "cyan")

    resp = llamar_claude("paso 2: clasificar urgencia",
                         system="Clasifica la urgencia como ALTA, MEDIA o BAJA y justifica en una línea.",
                         messages=[{"role": "user", "content": json.dumps(datos, ensure_ascii=False)}], max_tokens=150)
    urgencia = texto_de(resp)

    llamar_claude("paso 3: redactar respuesta",
                  system="Redacta la respuesta al cliente de La Tiendita en 3 líneas, cálida y concreta.",
                  messages=[{"role": "user", "content": f"Datos: {json.dumps(datos, ensure_ascii=False)}\nUrgencia: {urgencia}"}],
                  max_tokens=250)
    diagrama_seguro(diagrama_1_6a, datos, urgencia)
    visual.registrar_resultado(parte="A", final="cadena",
                               texto=f"3 pasos fijos · urgencia: {recortar(urgencia, 40) if urgencia else '?'}")
    concepto("Prompt chaining: los pasos se conocen de antemano, así que los fijas en código. "
             "Cada paso es pequeño y verificable. Si los pasos dependieran de lo que se descubre, "
             "convendría descomposición dinámica (el modelo decide el siguiente paso).")


def demo_1_6_parte_b():
    paso(f"PARTE B · Revisión de código · modo '{D16_MODO_REVISION}'")
    instruccion = "Eres revisor de código. Lista bugs reales en viñetas cortas (máximo 5). Indica archivo y línea."
    archivos = archivos_16()
    nota(f"{len(archivos)} archivos; el bug que cruza archivos está en checkout.py (el último).")
    if D16_MODO_REVISION == "una_pasada":
        todo = "\n\n".join(f"### {n}\n{c}" for n, c in archivos.items())
        resp = llamar_claude("una sola pasada con todos los archivos", system=instruccion,
                             messages=[{"role": "user", "content": todo}], max_tokens=600)
        hallado = encontro_bug_16(texto_de(resp))
        visual.registrar_resultado(parte="B", final="completo" if hallado else "se_pierde",
                                   texto=f"{len(archivos)} archivos · bug entre archivos encontrado: {'sí' if hallado else 'no'}")
        concepto("Con 3 archivos pequeños una pasada funciona. Con 14+ archivos aparece la attention dilution: "
                 "revisión dispareja y bugs omitidos a la mitad. Por eso el examen pide multi-pass.")
        diagrama_seguro(diagrama_1_6b, "una_pasada", {}, list(archivos))
        return
    hallazgos = {}
    for nombre, codigo in archivos.items():
        resp = llamar_claude(f"pasada local: {nombre}", system=instruccion + " Revisa SOLO este archivo.",
                             messages=[{"role": "user", "content": f"### {nombre}\n{codigo}"}], max_tokens=700)
        hallazgos[nombre] = texto_de(resp)
    paso("Pasada de integración: solo problemas ENTRE archivos")
    todo = "\n\n".join(f"### {n}\n{c}" for n, c in archivos.items())
    resp = llamar_claude("pasada de integración",
                  system=("Eres revisor de integración. Ya se revisó cada archivo por separado. Busca SOLO problemas "
                          "que cruzan archivos: firmas que no coinciden, datos que se pasan mal, supuestos contradictorios."),
                  messages=[{"role": "user", "content": f"Código:\n{todo}\n\nHallazgos por archivo:\n{json.dumps(hallazgos, ensure_ascii=False, indent=1)}"}],
                  max_tokens=1500)
    hallado = encontro_bug_16(texto_de(resp) + " " + " ".join(hallazgos.values()))
    visual.registrar_resultado(parte="B", final="completo" if hallado else "se_pierde",
                               texto=f"{len(archivos)} archivos · bug entre archivos encontrado: {'sí' if hallado else 'no'}")
    diagrama_seguro(diagrama_1_6b, "multipass", hallazgos, list(archivos))
    concepto("Fíjate: el bug de checkout.py (llama calcular_total con un parámetro que no existe y podría "
             "duplicar el IVA) solo se puede confirmar viendo carrito.py. Por eso existe la pasada de integración.")


def demo_1_6():
    titulo("DEMO 1.6 · Descomposición de tareas")
    mostrar_guia("1.6")
    if D16_PARTE in ("A", "ambas"):
        demo_1_6_parte_a()
    if D16_PARTE in ("B", "ambas"):
        demo_1_6_parte_b()


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 1.7  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio1.py guia 1.7)
# ---------------------------------------------------------------------
GUIA_1_7 = """
#### De qué trata
Cómo continuar el trabajo entre sesiones sin arrastrar información vieja.

#### Parte A, paso a paso (Agent SDK)
Cuatro corridas cortas, sin tools:
1. **Original**: *"la taza cuesta $299"*. Se guarda el `session_id`.
2. **`resume=session_id`**: misma sesión (mismo id). Recuerda los $299.
3. **`resume` + `fork_session=True`**: copia la historia y crea una sesión **nueva** (otro id). En esa rama la
   taza pasa a $349.
4. **De vuelta a la original con `resume`**: sigue diciendo $299. El fork no la tocó.

La tabla final muestra los `session_id`: el 1, 2 y 4 son iguales; el 3 es distinto. En la terminal de Claude
Code lo equivalente es `claude --resume <id>`.

#### Parte B, paso a paso (contexto obsoleto)
Se arma a mano un historial donde Claude ya leyó `precios.txt` (taza = $299). Luego el archivo cambió ($349).
- `"resume"`: se continúa la misma conversación y se relee el archivo. El historial tiene **los dos** valores.
  Al pedirle todos los precios que conoce, lista ambos: el viejo sigue ahí y puede confundir.
- `"nueva_sesion"`: sesión nueva con un **resumen** de lo vigente + releer solo lo que cambió. El 299 ya no existe.

#### Dónde está en el código
`demo_1_7_parte_a()` (opciones `resume` y `fork_session` en `opciones_base()`) y `demo_1_7_parte_b()`.

#### Experimentos
- `D17_ESTRATEGIA = "nueva_sesion"` y compara la respuesta.

#### Lo que pregunta el examen
- `resume` cuando el contexto anterior sigue siendo válido; dile al agente qué archivos cambiaron.
- Sesión nueva + resumen estructurado cuando los resultados de tools anteriores ya son obsoletos.
- `fork_session` para explorar dos enfoques desde la misma base.
"""


# =====================================================================
#  DEMO 1.7 · SESIONES: RESUME, FORK Y CONTEXTO OBSOLETO
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D17_PARTE = "ambas"   # "A" (Agent SDK: resume y fork), "B" (contexto obsoleto) o "ambas"
# Parte B: qué hacer cuando un archivo cambió después de la sesión
#   "resume"         -> seguir la misma conversación (los datos viejos siguen ahí)
#   "nueva_sesion"   -> sesión nueva + resumen de lo vigente + releer solo lo que cambió
D17_ESTRATEGIA = "resume"
# ------------------------------------------------------------------------


async def demo_1_7_parte_a():
    paso("PARTE A · Agent SDK: --resume vs. fork_session")
    sin_tools = dict(tools=[], max_turns=1,
                     system_prompt="Eres un asistente de La Tiendita. Responde en una sola línea.")
    r1 = await correr_agente("Dato para recordar: la taza artesanal cuesta $299. Responde solo 'Anotado'.",
                             opciones_base(**sin_tools), "sesión original")
    sesion = r1.session_id if r1 else None
    ok(f"Guardamos el session_id: {sesion}")

    r2 = await correr_agente("¿Cuánto cuesta la taza artesanal?", opciones_base(resume=sesion, **sin_tools),
                             "resume (misma sesión)")
    nota(f"Con resume, el session_id sigue siendo: {r2.session_id if r2 else '?'}  → recuerda el $299")

    r3 = await correr_agente("Supón que subimos la taza a $349. ¿Qué precio tiene ahora?",
                             opciones_base(resume=sesion, fork_session=True, **sin_tools), "fork_session=True")
    nota(f"El fork crea una sesión NUEVA: {r3.session_id if r3 else '?'} (la original no cambia)")

    r4 = await correr_agente("¿Cuánto cuesta la taza artesanal?", opciones_base(resume=sesion, **sin_tools),
                             "de vuelta a la sesión original")
    diagrama_seguro(diagrama_1_7a, r1, r2, r3, r4)
    nuevo = bool(r3 and sesion and r3.session_id != sesion)
    visual.registrar_resultado(parte="A", final="fork" if nuevo else None,
                               texto="El fork creó una sesión nueva y la original no cambió" if nuevo else
                               "No se pudo comprobar el fork (revisa los session_id)")
    tabla = Table(title="Sesiones de la parte A")
    tabla.add_column("Corrida"); tabla.add_column("session_id")
    for etiqueta, r in [("original", r1), ("resume", r2), ("fork", r3), ("original otra vez", r4)]:
        tabla.add_row(etiqueta, r.session_id if r else "?")
    consola.print(tabla)
    concepto("resume = continuar la misma historia. fork_session = copiar la historia hasta aquí y "
             "divergir (para comparar dos enfoques). El fork hereda TODO, incluidos los datos viejos.")


def demo_1_7_parte_b():
    paso(f"PARTE B · Contexto obsoleto · estrategia '{D17_ESTRATEGIA}'")
    historial_viejo = [
        {"role": "user", "content": "Lee precios.txt y dime cuánto cuesta la taza."},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_viejo01", "name": "leer_archivo",
                                           "input": {"ruta": "precios.txt"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_viejo01",
                                      "content": "taza_artesanal=299\nmantel_bordado=420"}]},
        {"role": "assistant", "content": "La taza artesanal cuesta $299."},
    ]
    tool_leer = {"name": "leer_archivo", "description": "Lee un archivo de texto.",
                 "input_schema": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}}
    archivo_hoy = "taza_artesanal=349\nmantel_bordado=420"
    pregunta = "Haz una lista de TODOS los precios de la taza que conozcas en esta conversación y dime cuál usarías."

    if D17_ESTRATEGIA == "resume":
        mensajes = historial_viejo + [
            {"role": "user", "content": "Actualicé precios.txt. Léelo de nuevo."},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_nuevo01", "name": "leer_archivo",
                                               "input": {"ruta": "precios.txt"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_nuevo01", "content": archivo_hoy},
                                         {"type": "text", "text": pregunta}]},
        ]
        nota("El historial contiene el valor viejo (299) Y el nuevo (349).")
    else:
        resumen = "Resumen de la sesión anterior: revisamos precios.txt; el mantel cuesta $420. precios.txt cambió después."
        mensajes = [
            {"role": "user", "content": resumen + " Relee solo precios.txt."},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_nuevo01", "name": "leer_archivo",
                                               "input": {"ruta": "precios.txt"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_nuevo01", "content": archivo_hoy},
                                         {"type": "text", "text": pregunta}]},
        ]
        nota("Sesión nueva: solo el resumen de lo vigente + el archivo releído. El 299 ya no existe aquí.")
    resp = llamar_claude(f"estrategia {D17_ESTRATEGIA}", tools=[tool_leer], messages=mensajes, max_tokens=300)
    diagrama_seguro(diagrama_1_7b, D17_ESTRATEGIA)
    respuesta = texto_de(resp)
    viejo = "299" in respuesta
    visual.registrar_resultado(parte="B", final="viejo" if viejo else "vigente",
                               texto="La respuesta todavía menciona el precio viejo ($299)" if viejo else
                               "La respuesta solo usa el precio vigente ($349)")
    concepto("Con resume, el tool_result viejo sigue en el historial y puede confundir al modelo. "
             "Si cambiaron archivos clave: sesión nueva + resumen + releer solo lo que cambió. "
             "Cambia D17_ESTRATEGIA y compara.", "🧪 Experimenta")


def demo_1_7():
    titulo("DEMO 1.7 · Manejo de sesiones")
    mostrar_guia("1.7")
    if D17_PARTE in ("A", "ambas"):
        asyncio.run(demo_1_7_parte_a())
    if D17_PARTE in ("B", "ambas"):
        demo_1_7_parte_b()


# =====================================================================
#  DIAGRAMAS DE LA CORRIDA (modo HTML)
# =====================================================================
# Cada demo, al terminar, arma un diagrama con lo que pasó en ESA corrida. Las funciones para dibujar
# (svg_grafo, svg_barras, agregar_diagrama…) están en visual.py. Aquí solo se decide QUÉ dibujar.

# ---------- Un diagrama por demo -------------------------------------------------

def diagrama_1_1(eventos: list[dict], final: str) -> None:
    nodos = [{"id": "inicio", "fila": 0, "col": 0, "completo": True, "texto": "Pregunta del cliente\n" + corto(D11_PREGUNTA, 110), "tipo": "nota"}]
    aristas = [("inicio", "c1", "")]
    pasos = []   # para el "paso a paso": cada caja se revela con su explicación
    for e in eventos:
        n = e["n"]
        pedidas = ", ".join(e["tools"]) or "ninguna"
        pasos.append({"busca": f"Iteración {n} del loop", "texto": (
            f"Vuelta {n}: tu código manda TODO el historial y Claude responde con stop_reason = {e['stop']}. "
            + (f"Pide {pedidas}, pero Claude no ejecuta nada: solo pide." if e["tools"]
               else "Ya no pide tools.")
            + (" Como stop_reason es tool_use, el loop debe seguir." if e["stop"] == "tool_use" else ""))})
        nodos.append({"id": f"c{n}", "fila": n, "col": 0, "tipo": "claude", "paso": len(pasos),
                      "texto": f"Claude · iteración {n}\nstop_reason = {e['stop']}\npide: {pedidas}"})
        if e["ejecutadas"]:
            vez = sum(1 for x in eventos if x["n"] <= n and x["ejecutadas"])
            pasos.append({"busca": "Devolvemos", "vez": vez, "texto": (
                f"Tu código ejecuta {', '.join(e['ejecutadas'])} (la función de Python) y devuelve el tool_result "
                "en UN mensaje con rol user. Luego vuelve a llamar a Claude.")})
            nodos.append({"id": f"t{n}", "fila": n, "col": 1, "tipo": "codigo", "paso": len(pasos),
                          "texto": "Tu código ejecuta\n" + ", ".join(e["ejecutadas"])})
            aristas.append((f"c{n}", f"t{n}", "tool_use"))
            aristas.append((f"t{n}", f"c{n + 1}", "tool_result"))
    ultimo = eventos[-1]["n"] if eventos else 0
    tipos_final = {"end_turn": ("ok", "stop_reason = end_turn\nfin del loop"),
                   "max_tokens": ("bloqueo", "stop_reason = max_tokens\nse cortó: NO terminó"),
                   "hay_texto": ("bloqueo", "Antipatrón: se cortó por ver texto\nquedaron tools sin ejecutar"),
                   "tope": ("bloqueo", "Red de seguridad: tope de iteraciones")}
    tipo, texto = tipos_final.get(final, ("nota", f"stop_reason = {final}"))
    total_tools = sum(len(e["ejecutadas"]) for e in eventos)
    conclusiones = {
        "end_turn": f"El loop terminó porque stop_reason = end_turn, después de {ultimo} vueltas y {total_tools} tools ejecutadas.",
        "max_tokens": "La respuesta se cortó por max_tokens: Claude NO había terminado. No confundas eso con end_turn.",
        "hay_texto": "Antipatrón: el loop se detuvo al ver texto y dejó tools pedidas sin ejecutar. Hay que mirar stop_reason.",
        "tope": "La red de seguridad (tope de vueltas) cortó el loop antes de que Claude terminara.",
    }
    busca_final = {"end_turn": "stop_reason = 'end_turn'", "max_tokens": "stop_reason = 'max_tokens'",
                   "hay_texto": "ANTIPATRÓN", "tope": "Se alcanzó D11_MAX_ITERACIONES"}
    pasos.append({"busca": busca_final.get(final, ""),
                  "texto": "Fin: " + conclusiones.get(final, f"el loop terminó con stop_reason = {final}.")})
    nodos.append({"id": "fin", "fila": ultimo + 1, "col": 0, "tipo": tipo, "texto": texto, "paso": len(pasos)})
    aristas.append((f"c{ultimo}", "fin", ""))
    agregar_diagrama("Demo 1.1 · El loop de esta corrida", svg_grafo(nodos, aristas, columnas=2),
                     "Izquierda: lo que responde Claude en cada vuelta. Derecha: lo que ejecuta tu código. "
                     "El loop sigue mientras stop_reason sea tool_use.",
                     conclusiones.get(final, f"El loop terminó con stop_reason = {final}."), pasos=pasos)


def diagrama_1_2(subtemas: list[str], cobertura: dict) -> None:
    nodos = [{"id": "tema", "fila": 0, "texto": "Tema\n" + corto(D12_TEMA, 80), "tipo": "nota"},
             {"id": "coord", "fila": 1, "texto": f"Coordinator\ndescomposición: {D12_DESCOMPOSICION}", "tipo": "claude"},
             {"id": "reporte", "fila": 3, "texto": "Coordinator escribe el reporte final", "tipo": "claude"}]
    aristas = [("tema", "coord", "")]
    for i, s in enumerate(subtemas or ["(no delegó nada)"]):
        nodos.append({"id": f"s{i}", "fila": 2, "texto": "Subagente\n" + corto(s, 50), "tipo": "codigo"})
        aristas += [("coord", f"s{i}", ""), (f"s{i}", "reporte", "")]
    for j, (area, cubierta) in enumerate(cobertura.items()):
        nodos.append({"id": f"a{j}", "fila": 4, "texto": ("✔ " if cubierta else "✘ ") + area,
                      "tipo": "ok" if cubierta else "bloqueo"})
        aristas.append(("reporte", f"a{j}", ""))
    faltan = [a for a, cubierta in cobertura.items() if not cubierta]
    visual.registrar_resultado(final="faltan" if faltan else "completo",
                               texto=f"Áreas cubiertas: {len(cobertura) - len(faltan)}/{len(cobertura)}")
    conclusion = (f"El reporte no menciona {', '.join(faltan)}. Antes de culpar a los subagentes, revisa qué les asignó "
                  "el coordinator: la causa suele ser la descomposición." if faltan
                  else f"El reporte cubre las {len(cobertura)} áreas esperadas: la descomposición fue completa.")
    agregar_diagrama("Demo 1.2 · Qué delegó el coordinator y qué cubrió el reporte", svg_grafo(nodos, aristas),
                     "Fila 3: un subagente por subtema (no se ven entre sí). Última fila: áreas esperadas; en rojo, "
                     "las que el reporte no menciona.", conclusion)


def diagrama_1_3a(formato: str, citas: int, sin_fuente: int) -> None:
    nodos = [{"id": d["id"], "fila": 0, "texto": f"{d['id']}\n{d['fecha']}", "tipo": "nota"} for d in DOCS_PROVEEDORES]
    nodos.append({"id": "sub", "fila": 1, "texto": f"Subagente investigador\nformato: {formato}", "tipo": "claude"})
    bien = citas > 0 and sin_fuente == 0
    visual.registrar_resultado(parte="A", final="con_fuentes" if bien else "sin_fuentes",
                               texto=f"Citas con id: {citas} · sin fuente: {sin_fuente}")
    nodos.append({"id": "sint", "fila": 2, "tipo": "ok" if bien else "bloqueo",
                  "texto": f"Sintetizador\ncitas con id: {citas} · [sin fuente]: {sin_fuente}"})
    aristas = [(d["id"], "sub", "") for d in DOCS_PROVEEDORES]
    aristas.append(("sub", "sint", "afirmación + fuente + fecha" if formato == "estructurado" else "prosa"))
    conclusion = ("Todas las afirmaciones llegaron con su fuente: los datos estructurados conservaron la metadata."
                  if bien else f"Se perdió atribución en el camino: {citas} citas con id y {sin_fuente} sin fuente. "
                  "La prosa no garantiza que la fuente sobreviva.")
    agregar_diagrama("Demo 1.3 · Parte A: ¿llegaron las fuentes al final?", svg_grafo(nodos, aristas),
                     "Si el subagente entrega datos estructurados, el sintetizador puede citar cada dato.", conclusion)


def diagrama_1_3b(barras: list[tuple], total: float, paralelo: bool) -> None:
    filas = [(s, i, d, "claude") for s, i, d in barras]
    suma = sum(d for _, _, d in barras)
    if total > 0:
        visual.registrar_resultado(parte="B", final="rapido" if total < 0.8 * suma else "lento",
                                   texto=f"Tiempo real {total:.1f} s contra {suma:.1f} s si fueran en serie")
    filas.append(("Tiempo real total", 0.0, total, "ok" if paralelo else "bloqueo"))
    filas.append(("Suma si fueran en serie", 0.0, suma, "codigo"))
    if paralelo and total > 0:
        conclusion = (f"En paralelo tardó {total:.1f} s contra {suma:.1f} s si fueran uno tras otro "
                      f"({suma / total:.1f} veces más rápido), porque el coordinator pidió todo en una sola respuesta.")
    else:
        conclusion = f"En serie, el tiempo total ({total:.1f} s) es la suma de cada subagente."
    agregar_diagrama(f"Demo 1.3 · Parte B: subagentes {'en paralelo' if paralelo else 'en serie'}",
                     svg_barras_tiempo(filas, max(total, suma)),
                     "Cada barra empieza cuando arrancó ese subagente. En paralelo se enciman y el total es mucho "
                     "menor que la suma.", conclusion)


def diagrama_1_4(eventos: list[dict], prueba_directa: tuple | None) -> None:
    nodos = [{"id": "inicio", "fila": 0, "col": 0, "completo": True, "texto": "Pregunta del cliente\n" + corto(D14_PREGUNTA, 110), "tipo": "nota"}]
    aristas = [("inicio", "c1", "")]
    for k, e in enumerate(eventos, start=1):
        nodos.append({"id": f"c{k}", "fila": k, "col": 0, "tipo": "claude",
                      "texto": f"Claude pide\n{e['tool']}" + (f" (${e['monto']:,.0f})" if e.get("monto") else "")})
        nodos.append({"id": f"g{k}", "fila": k, "col": 1, "tipo": "hook" if e["gate"] else "codigo",
                      "texto": e["gate_texto"]})
        nodos.append({"id": f"r{k}", "fila": k, "col": 2, "tipo": e["tipo_resultado"], "texto": e["resultado"]})
        aristas += [(f"c{k}", f"g{k}", ""), (f"g{k}", f"r{k}", "")]
        if k < len(eventos):
            aristas.append((f"r{k}", f"c{k + 1}", "tool_result"))
    fila = len(eventos) + 1
    if prueba_directa:
        nodos.append({"id": "pd", "fila": fila, "col": 0, "tipo": "codigo", "texto": "Prueba directa (sin modelo)\nprocess_refund sin verificar"})
        nodos.append({"id": "pdg", "fila": fila, "col": 1, "tipo": "bloqueo" if prueba_directa[0] else "ok",
                      "texto": prueba_directa[1]})
        aristas.append(("pd", "pdg", ""))
    bloqueadas = sum(1 for e in eventos if e["gate"] and "BLOQUEADO" in e["gate_texto"])
    indebidos = [r for r in REEMBOLSOS_HECHOS if r.get("amount", 0) > LIMITE_REEMBOLSO]
    visual.registrar_resultado(final="se_salta" if indebidos else ("bloqueado" if bloqueadas else "pregunta"),
                               texto=f"Reembolsos arriba del límite: {len(indebidos)} · bloqueados por el gate: {bloqueadas}")
    if D14_MODO == "gate_en_codigo":
        conclusion = (f"El gate bloqueó {bloqueadas} llamada(s) a process_refund: ningún reembolso sale sin pasar las reglas, "
                      "diga lo que diga el modelo.")
    else:
        conclusion = "Sin gate, lo único que frena un reembolso indebido es que el modelo obedezca el prompt: casi siempre, no siempre."
    agregar_diagrama(f"Demo 1.4 · Cada tool pasó por el gate (D14_MODO = {D14_MODO})", svg_grafo(nodos, aristas, columnas=3),
                     "Columna del medio: la decisión de tu código antes de ejecutar. Lo que va en rojo nunca se ejecutó.",
                     conclusion)


def diagrama_1_5(intentos: list[dict]) -> None:
    nodos, aristas = [], []
    nodos.append({"id": "inicio", "fila": 0, "col": 0, "completo": True, "texto": "Pregunta del cliente\n" + corto(D15_PREGUNTA, 110), "tipo": "nota"})
    previo = "inicio"
    for k, it in enumerate(intentos, start=1):
        nombre = it["tool"].replace("mcp__tiendita__", "")
        nodos.append({"id": f"c{k}", "fila": k, "col": 0, "tipo": "claude", "texto": f"Claude pide\n{nombre}"})
        if it.get("pre"):
            nodos.append({"id": f"p{k}", "fila": k, "col": 1, "tipo": "bloqueo" if it["pre"] == "deny" else "hook",
                          "texto": f"PreToolUse\n{it['pre']}" + (f" (${it['monto']:,.0f})" if it.get("monto") else "")})
        else:
            nodos.append({"id": f"p{k}", "fila": k, "col": 1, "tipo": "codigo", "texto": "PreToolUse\nno aplica"})
        nodos.append({"id": f"t{k}", "fila": k, "col": 2, "tipo": "ok" if it.get("ejecutada") else "bloqueo",
                      "texto": "La tool se ejecuta" if it.get("ejecutada") else "La tool NO se ejecuta"})
        if it.get("post"):
            nodos.append({"id": f"q{k}", "fila": k, "col": 3, "tipo": "hook", "texto": "PostToolUse\n" + it["post"]})
        else:
            nodos.append({"id": f"q{k}", "fila": k, "col": 3, "tipo": "codigo", "texto": "PostToolUse\nno aplica"})
        aristas += [(previo, f"c{k}", ""), (f"c{k}", f"p{k}", ""), (f"p{k}", f"t{k}", ""), (f"t{k}", f"q{k}", "")]
        previo = f"q{k}"
    negados = [it for it in intentos if it.get("pre") == "deny"]
    limpiados = [it for it in intentos if it.get("post")]
    indebidos = [it for it in intentos if it.get("ejecutada") and (it.get("monto") or 0) > LIMITE_REEMBOLSO]
    if indebidos:
        final = "reembolsa"
    elif not negados:
        final = "no_intenta"      # Claude no pidió el reembolso: nada se bloqueó (ni hizo falta)
    else:
        final = "bloquea_normaliza" if limpiados else "formatos"
    visual.registrar_resultado(final=final,
                               texto=f"Bloqueados por PreToolUse: {len(negados)} · normalizados por PostToolUse: {len(limpiados)}")
    partes = []
    if negados:
        partes.append(f"PreToolUse bloqueó {len(negados)} reembolso(s) antes de ejecutarse")
    if limpiados:
        partes.append(f"PostToolUse normalizó {len(limpiados)} resultado(s) antes de que Claude los viera")
    conclusion = ("; ".join(partes) + ".") if partes else "En esta corrida ningún hook cambió nada (¿están activos?)."
    agregar_diagrama("Demo 1.5 · Dónde intervino cada hook", svg_grafo(nodos, aristas, columnas=4),
                     "Pre corre antes y puede impedir la tool; Post corre después y solo cambia lo que ve Claude.", conclusion)


def diagrama_1_6a(datos: dict, urgencia: str) -> None:
    nodos = [{"id": "r", "fila": 0, "col": 0, "tipo": "nota", "texto": "Reseña\n" + corto(D16_RESENA, 60)},
             {"id": "p1", "fila": 0, "col": 1, "tipo": "claude",
              "texto": "Paso 1 · extraer\n" + corto(f"{datos.get('producto', '?')} · límite: {datos.get('fecha_limite')}", 40)},
             {"id": "p2", "fila": 0, "col": 2, "tipo": "claude", "texto": "Paso 2 · urgencia\n" + corto(urgencia, 40)},
             {"id": "p3", "fila": 0, "col": 3, "tipo": "ok", "texto": "Paso 3 · respuesta\nal cliente"}]
    aristas = [("r", "p1", ""), ("p1", "p2", "solo el JSON"), ("p2", "p3", "")]
    agregar_diagrama("Demo 1.6 · Parte A: la cadena de pasos fijos", svg_grafo(nodos, aristas, columnas=4),
                     "Cada paso es una llamada aparte y solo recibe lo que produjo el anterior.",
                     "Prompt chaining: los pasos se conocían de antemano, así que se fijaron en código; cada uno es "
                     "pequeño y se puede revisar por separado.")


def diagrama_1_6b(modo: str, hallazgos: dict, nombres: list | None = None) -> None:
    nodos, aristas = [], []
    for i, nombre in enumerate(nombres or ARCHIVOS_TIENDITA):
        detalle = ""
        if nombre in hallazgos:
            n = sum(1 for l in hallazgos[nombre].splitlines() if re.match(r"\s*([-*•]|\d+[.)])\s", l))
            detalle = f"\n{n} hallazgos locales"
        nodos.append({"id": f"f{i}", "fila": 0, "tipo": "codigo", "texto": nombre + detalle})
        aristas.append((f"f{i}", "fin", ""))
    if modo == "una_pasada":
        nodos.append({"id": "fin", "fila": 1, "tipo": "claude", "texto": "Una sola pasada\ncon todos los archivos juntos"})
    else:
        nodos.append({"id": "fin", "fila": 1, "tipo": "ok", "texto": "Pasada de integración\nsolo problemas ENTRE archivos"})
    conclusion = ("La pasada de integración es la única que ve los archivos juntos: ahí se confirma el bug que cruza "
                  "checkout.py y carrito.py." if modo != "una_pasada" else
                  "Con 3 archivos una pasada alcanza; con 14 o más aparece la attention dilution y conviene multi-pass.")
    agregar_diagrama(f"Demo 1.6 · Parte B: revisión en modo {modo}", svg_grafo(nodos, aristas),
                     "Multi-pass: una pasada por archivo con toda la atención, y una aparte para lo que cruza archivos.", conclusion)


def diagrama_1_7a(r1, r2, r3, r4) -> None:
    sid = lambda r: (r.session_id[:8] + "…") if r and r.session_id else "?"  # noqa: E731
    mismo = lambda r: bool(r and r1 and r.session_id == r1.session_id)    # noqa: E731
    nodos = [{"id": "o", "fila": 0, "col": 0, "tipo": "claude", "texto": f"Sesión original\nid {sid(r1)} · taza $299"},
             {"id": "r", "fila": 1, "col": 0, "tipo": "ok" if mismo(r2) else "bloqueo", "texto": f"resume\nid {sid(r2)} (mismo)"},
             {"id": "f", "fila": 1, "col": 1, "tipo": "hook", "texto": f"fork_session\nid {sid(r3)} (nuevo) · taza $349"},
             {"id": "o2", "fila": 2, "col": 0, "tipo": "ok" if mismo(r4) else "bloqueo",
              "texto": f"De vuelta a la original\nid {sid(r4)} · sigue en $299"}]
    aristas = [("o", "r", "resume"), ("o", "f", "resume + fork"), ("r", "o2", "resume")]
    agregar_diagrama("Demo 1.7 · Parte A: el árbol de sesiones", svg_grafo(nodos, aristas, columnas=2),
                     "resume continúa la misma sesión (mismo id). fork copia la historia a una sesión nueva; "
                     "la original no cambia.",
                     "resume = misma sesión, mismo id. fork_session = id nuevo con una copia de la historia; "
                     "la sesión original sigue intacta (y el fork hereda todo, incluidos datos viejos).")


def diagrama_1_7b(estrategia: str) -> None:
    if estrategia == "resume":
        nodos = [{"id": "a", "fila": 0, "col": 0, "tipo": "nota", "texto": "Historial viejo\nleyó precios.txt: taza $299"},
                 {"id": "b", "fila": 0, "col": 1, "tipo": "codigo", "texto": "resume + releer\nprecios.txt: taza $349"},
                 {"id": "c", "fila": 0, "col": 2, "tipo": "bloqueo", "texto": "Contexto final\n$299 Y $349: puede confundirse"}]
    else:
        nodos = [{"id": "a", "fila": 0, "col": 0, "tipo": "nota", "texto": "Sesión nueva\nresumen de lo vigente"},
                 {"id": "b", "fila": 0, "col": 1, "tipo": "codigo", "texto": "Releer solo lo que cambió\nprecios.txt: taza $349"},
                 {"id": "c", "fila": 0, "col": 2, "tipo": "ok", "texto": "Contexto final\nsolo $349"}]
    conclusion = ("Con resume, el valor viejo ($299) sigue en el historial junto al nuevo: el modelo puede confundirse."
                  if estrategia == "resume" else
                  "Sesión nueva + resumen + releer lo que cambió: el valor viejo ya no existe en el contexto.")
    agregar_diagrama(f"Demo 1.7 · Parte B: qué queda en el contexto ({estrategia})",
                     svg_grafo(nodos, [("a", "b", ""), ("b", "c", "")], columnas=3),
                     "Con resume, el tool_result viejo sigue en el historial. Una sesión nueva con resumen lo deja fuera.",
                     conclusion)


def evento_1_4(nombre: str, entrada: dict, resultado: str, es_error: bool, auditoria_nueva: list) -> dict:
    """Resume una llamada de la demo 1.4 para su diagrama."""
    e = {"tool": nombre, "monto": entrada.get("amount"), "gate": bool(auditoria_nueva)}
    if auditoria_nueva:
        _, decision, motivo = auditoria_nueva[-1]
        e["gate_texto"] = f"Gate: {decision}\n{motivo}"
    elif nombre == "process_refund":
        e["gate_texto"] = "sin gate\n(solo la regla del prompt)"
    else:
        e["gate_texto"] = "sin gate\n(no mueve dinero)"
    if nombre == "get_customer":
        datos = json.loads(resultado)
        e["resultado"], e["tipo_resultado"] = (f"Cliente verificado\n{datos.get('id')}", "ok") if datos.get("encontrado") else ("No encontrado", "bloqueo")
    elif nombre == "process_refund":
        e["resultado"], e["tipo_resultado"] = ("NO se ejecutó", "bloqueo") if es_error else ("Reembolso ejecutado", "ok")
    elif nombre == "escalar_a_humano":
        e["resultado"], e["tipo_resultado"] = ("Handoff a humano\nticket HUM-0042", "hook")
    else:
        e["resultado"], e["tipo_resultado"] = ("Resultado devuelto", "codigo")
    return e


# =====================================================================
#  MENÚ
# =====================================================================

GUIAS = {
    "1.1": GUIA_1_1,
    "1.2": GUIA_1_2,
    "1.3": GUIA_1_3,
    "1.4": GUIA_1_4,
    "1.5": GUIA_1_5,
    "1.6": GUIA_1_6,
    "1.7": GUIA_1_7,
}


DEMOS = {
    "1.1": ("Agentic loop y stop_reason", demo_1_1),
    "1.2": ("Coordinator + subagentes (hub-and-spoke)", demo_1_2),
    "1.3": ("Context passing y paralelismo", demo_1_3),
    "1.4": ("Enforcement: prerequisite gate + handoff", demo_1_4),
    "1.5": ("Hooks PreToolUse / PostToolUse (Agent SDK)", demo_1_5),
    "1.6": ("Prompt chaining y multi-pass review", demo_1_6),
    "1.7": ("Sesiones: resume, fork, contexto obsoleto (parte A con Agent SDK)", demo_1_7),
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
        tabla = Table(title="CCAR-F · Lab del Dominio 1")
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

"""
=====================================================================
 CCAR-F · LAB DEL DOMINIO 4: Prompt Engineering & Structured Output
=====================================================================

Demos ejecutables, una por subdominio. Todas usan el caso de
"La Tiendita" (tienda en línea) con datos FALSOS.

CÓMO CORRERLO
-------------
  1) pip install -r requirements.txt   (dentro de tu entorno virtual)
  2) Copia .env.example como .env y pega ahí tu API key (ver README).
     Si no hay .env, se usa la variable de entorno ANTHROPIC_API_KEY.
  3) python lab_dominio4.py          -> muestra el menú
     python lab_dominio4.py 4.1      -> corre directo la demo 4.1
     python lab_dominio4.py guia     -> solo lee las guías (no llama a la API)

CÓMO MODIFICARLO
----------------
  * Arriba está la CONFIGURACIÓN GENERAL (modelo, nivel de detalle).
  * Cada demo tiene su propio bloque "🔧 CAMBIA AQUÍ" con variables
    comentadas: cámbialas, vuelve a correr y compara la salida.

DEMOS
-----
  4.1  Criterios explícitos en el system prompt  (Messages API)
  4.2  Few-shot para casos ambiguos              (Messages API)
  4.3  Salida estructurada con tool use          (Messages API)
  4.4  Validación, reintento y retroalimentación (Messages API)
  4.5  Message Batches API                       (Batches API)
  4.6  Revisión con instancia independiente      (Messages API)
"""

from __future__ import annotations

import json
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
# correr nada (ni gastar):  python lab_dominio4.py guia      (o: guia 4.1)
MOSTRAR_GUIA = True
PAUSA_DESPUES_DE_GUIA = True   # espera un Enter después de la guía (ideal para explicar antes de correr)

# Modo HTML: además de la terminal, cada corrida se guarda como página web con un diagrama
# de lo que pasó, en salidas_html/dominio4/. Cada corrida es un archivo nuevo (no se sobrescribe)
# y salidas_html/dominio4/index.html las recorre con Anterior / Siguiente para comparar: cambia una
# variable, vuelve a correr la demo y compara los diagramas. Ejemplos de lo que vas a ver, sin correr
# nada: ejemplos_html/dominio4/index.html
#   True  -> encendido (para apagarlo en una sola corrida:  python lab_dominio4.py 4.1 --sin-html)
#   False -> solo terminal  (para encenderlo en una sola corrida:  python lab_dominio4.py 4.1 --html)
MODO_HTML = True

# Límite de reembolso de La Tiendita (pesos mexicanos)
LIMITE_REEMBOLSO = 10_000


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
GUARDAR_HTML = visual.configurar(dominio=4, modo_html=MODO_HTML)
consola = Console(record=GUARDAR_HTML)
visual.usar_consola(consola)
# Ayudantes compartidos (llamar_claude, mostrar_request, correr_agente, contadores de costo…): viven en
# comun.py y comun.instalar() los define aquí mismo, con la configuración de este lab.
import comun  # noqa: E402
from comun import (  # noqa: E402
    PRECIOS, USO_TOTAL, titulo, paso, concepto, ok,
    alerta, nota, recortar, texto_de, mostrar_json, cliente,
    verificar_api_key, tool_choice_forzado, llamar_claude, sumar_uso_api, resumen_costo, guardar_html,
    mostrar_estado_html, entrada_tool, tabla_simple,
)
comun.instalar(globals())


def mostrar_guia(clave: str, forzar: bool = False, pausa: bool = True) -> None:
    """Imprime la guía (markdown) de una demo. Las guías están arriba de cada demo: GUIA_x_y."""
    if not (MOSTRAR_GUIA or forzar):
        return
    if DETALLE == "basico" and not forzar:
        consola.print(f"[dim]📖 Guía de esta demo: python lab_dominio4.py guia {clave}  ·  "
                      f"más detalle: pon DETALLE = \"completo\" arriba del archivo[/]")
        return
    from rich.markdown import Markdown
    consola.print(Panel(Markdown(idioma.guia(clave, GUIAS[clave])), title=f"📖 Guía de la demo {clave}: qué vas a ver",
                        border_style="cyan", padding=(1, 2)))
    if pausa and PAUSA_DESPUES_DE_GUIA and sys.stdin.isatty():
        consola.input("[bold cyan]   Presiona Enter para correr la demo… [/]")


# =====================================================================
#  AYUDANTES DEL DOMINIO 4
# =====================================================================


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 4.1  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio4.py guia 4.1)
# ---------------------------------------------------------------------
GUIA_4_1 = """
#### De qué trata
Instrucciones como *"marca lo importante"*, *"sé conservador"* o *"solo si tienes alta confianza"* no le dicen al
modelo **dónde está la línea**. Cada corrida la pone en un lugar distinto: alertas de más (falsos positivos) o de
menos (falsos negativos). La solución son **criterios explícitos**: qué SÍ cuenta y qué NO, con ejemplos.

Detalle del examen: los falsos positivos hacen que la gente deje de confiar en **todas** las alertas, incluso en las
correctas.

#### Qué pasa al correrla, paso a paso
1. Se imprime la tabla de 14 tickets con la respuesta correcta (¿escalar sí o no?). Los últimos 4 dependen de la
   política de la tienda (el límite de $10,000, qué cuenta como amenaza legal): un prompt vago no los puede adivinar.
2. Se clasifican todos con el system prompt **vago**, en una sola llamada con la tool `clasificar_tickets` forzada,
   para que la comparación sea solo de criterio y no de formato.
3. Lo mismo con el system prompt **explícito**: 3 criterios para escalar (dinero en riesgo, seguridad de la cuenta,
   amenaza legal) y una lista de lo que NO se escala.
4. La tabla compara cada decisión con la correcta y marca **falso positivo** o **falso negativo**.
5. Resumen: aciertos, falsos positivos y falsos negativos por modo.

Casos donde normalmente se nota la diferencia:
- **T9**: muy molesto, pero es un retraso de envío. El vago suele escalarlo por el enojo.
- **T8**: aviso sin pedido de acción.
- **T7**: $12,500, más de $10,000. El vago a veces no lo escala.

#### Lo que se le manda a Claude
- `system`: `SISTEMA_VAGO_41` o `SISTEMA_EXPLICITO_41`.
- `tools`: `TOOL_CLASIFICAR_41`, que devuelve una lista de decisiones con `id`, `escalar` y `motivo`.

#### Dónde está en el código
`TICKETS_41` (tickets + respuesta correcta), los dos system prompts y `demo_4_1()`.

#### Experimentos
- Quita de `SISTEMA_EXPLICITO_41` la línea *"El enojo por sí solo NO es criterio"* y mira T9.
- Agrega tickets frontera a `TICKETS_41`, por ejemplo un reembolso de exactamente $10,000.

#### Lo que pregunta el examen
- "Sé conservador" o "solo alta confianza" no mejoran la precisión: lo que la mejora son criterios concretos.
- Si una categoría da muchos falsos positivos, desactívala temporalmente mientras mejoras su prompt, para recuperar
  la confianza en las demás.
- Define la severidad con ejemplos de código o casos concretos por nivel.
"""


# =====================================================================
#  DEMO 4.1 · CRITERIOS EXPLÍCITOS EN EL SYSTEM PROMPT
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# "vago" → "marca lo importante, sé conservador" · "explicito" → criterios concretos
# "ambos" → corre los dos y compara
D41_MODO = "ambos"
# ------------------------------------------------------------------------

# (id, ticket, ¿debe escalarse?)
TICKETS_41 = [
    ("T1", "Me cobraron dos veces el pedido #12345 ($1,850 cada cobro).", True),
    ("T2", "¿El mantel bordado se puede lavar en lavadora?", False),
    ("T3", "Mi pedido lleva 3 días de retraso, ¿me dicen dónde va?", False),
    ("T4", "Alguien cambió el correo de mi cuenta y no fui yo.", True),
    ("T5", "Si no me devuelven el dinero voy a ir a Profeco y con mi abogado.", True),
    ("T6", "¡Qué bonitas tazas! Ya pedí otras para regalar.", False),
    ("T7", "La vajilla de $12,500 llegó rota, quiero reembolso completo.", True),
    ("T8", "La caja llegó un poco aplastada pero todo bien adentro, solo aviso.", False),
    ("T9", "Ya van 2 semanas y no llega, estoy MUY molesto, pésimo servicio!!!", False),
    ("T10", "¿Tienen factura? Necesito mi RFC en el comprobante.", False),
    # Casos frontera que dependen de la POLÍTICA de la tienda (el límite de $10,000, qué cuenta como amenaza legal):
    # un prompt vago no los puede adivinar; los criterios explícitos sí los resuelven.
    ("T11", "Quiero el reembolso de mi vajilla rota, son $9,500. Es mucho dinero, por favor atiéndanme ya.", False),
    ("T12", "Quiero que me reembolsen los $10,400 del mantel que llegó manchado. No hay prisa, cuando puedan.", True),
    ("T13", "Si hoy no me responden, les pongo una reseña de una estrella en todos lados.", False),
    ("T14", "Me llegó un correo de 'La Tiendita' que me pide mi contraseña para verificar la cuenta. ¿Es de ustedes?", True),
]

SISTEMA_VAGO_41 = ("Eres el filtro de soporte de La Tiendita. Marca para escalar los tickets importantes. "
                   "Sé conservador y escala solo cuando haga falta.")
SISTEMA_EXPLICITO_41 = """Eres el filtro de soporte de La Tiendita. Escala a un humano SOLO si se cumple al menos una:
1. Dinero en riesgo: cobro duplicado, o reembolso mayor a $10,000 MXN.
2. Seguridad de la cuenta: cambios no autorizados, posible robo de cuenta o de datos.
3. Amenaza legal explícita (abogado, Profeco, demanda).
NO escales (aunque el cliente esté molesto o use mayúsculas):
- Retrasos de envío, preguntas de producto o de facturación, elogios, avisos sin pedido de acción.
El enojo por sí solo NO es criterio de escalamiento."""

TOOL_CLASIFICAR_41 = {
    "name": "clasificar_tickets",
    "description": "Devuelve la decisión para cada ticket.",
    "input_schema": {"type": "object", "properties": {"decisiones": {"type": "array", "items": {
        "type": "object", "properties": {
            "id": {"type": "string"}, "escalar": {"type": "boolean"},
            "motivo": {"type": "string", "description": "Una línea: por qué"}},
        "required": ["id", "escalar", "motivo"]}}}, "required": ["decisiones"]},
}


def demo_4_1():
    titulo("DEMO 4.1 · Criterios explícitos: 'sé conservador' no es un criterio")
    mostrar_guia("4.1")
    concepto(
        "Instrucciones vagas ('marca lo importante', 'sé conservador', 'solo si tienes alta confianza') dejan al modelo "
        "adivinar dónde está la línea. Resultado: falsos positivos (alertas de más) o falsos negativos.\n"
        "Arreglo: criterios concretos de qué SÍ y qué NO, con ejemplos. Los falsos positivos destruyen la confianza "
        "en TODO el sistema, incluso en las alertas correctas."
    )
    tabla_simple("Tickets de prueba (la última columna es la respuesta correcta)", ["ID", "Ticket", "¿Escalar?"],
                 [[i, escape(t), "sí" if e else "no"] for i, t, e in TICKETS_41])
    modos = ["vago", "explicito"] if D41_MODO == "ambos" else [D41_MODO]
    visual.diagrama_seguro(visual.tarjeta_tal_cual, "Demo 4.1 · Los dos system prompts tal cual",
        [("❌ Vago", "#ff9b9b"), ("✅ Explícito", "#8fe0a0")], [(None, [SISTEMA_VAGO_41, SISTEMA_EXPLICITO_41])],
        "Los mismos 14 tickets, la misma tool y el mismo modelo: solo cambia este texto.",
        "El vago no dice dónde está la línea («importantes», «conservador»). El explícito da disparadores concretos "
        "(dinero, seguridad, amenaza legal) y dice qué NO se escala: el enojo por sí solo no cuenta (mira T9).")
    texto = "\n".join(f"{i}: {t}" for i, t, _ in TICKETS_41)
    resultados = {}
    for modo in modos:
        sistema = SISTEMA_VAGO_41 if modo == "vago" else SISTEMA_EXPLICITO_41
        paso(f"System prompt {modo.upper()}")
        consola.print(Panel(escape(sistema), title=f"system ({modo})", border_style="magenta"))
        resp = llamar_claude(f"clasificar ({modo})", system=sistema, tools=[TOOL_CLASIFICAR_41],
                             tool_choice=tool_choice_forzado("clasificar_tickets"),
                             messages=[{"role": "user", "content": f"Tickets:\n{texto}"}], max_tokens=1500)
        resultados[modo] = {d.get("id"): d for d in entrada_tool(resp).get("decisiones", [])}

    tabla = Table(title="Decisiones vs respuesta correcta", show_lines=True)
    tabla.add_column("ID"); tabla.add_column("Correcto")
    for modo in modos:
        tabla.add_column(modo)
    metricas = {m: {"fp": 0, "fn": 0, "ok": 0} for m in modos}
    for i, _, esperado in TICKETS_41:
        celdas = []
        for modo in modos:
            d = resultados[modo].get(i, {})
            escalo = bool(d.get("escalar"))
            if escalo == esperado:
                metricas[modo]["ok"] += 1
                celdas.append(f"[green]{'sí' if escalo else 'no'}[/] {escape(recortar(d.get('motivo', ''), 50))}")
            else:
                metricas[modo]["fp" if escalo else "fn"] += 1
                celdas.append(f"[red]{'sí' if escalo else 'no'} ({'falso positivo' if escalo else 'falso negativo'})[/]")
        tabla.add_row(i, "sí" if esperado else "no", *celdas)
    consola.print(tabla)
    tabla_simple("Resumen", ["Modo", "Aciertos", "Falsos positivos", "Falsos negativos"],
                 [[m, f"{v['ok']}/{len(TICKETS_41)}", v["fp"], v["fn"]] for m, v in metricas.items()])
    if len(modos) > 1:
        visual.registrar_resultado(final="comparacion", texto=" · ".join(f"{m}: {v['ok']}/{len(TICKETS_41)} aciertos, {v['fp']} falsos positivos" for m, v in metricas.items()))
    if len(modos) == 1:
        v = metricas[modos[0]]
        visual.registrar_resultado(final="preciso" if v["ok"] == len(TICKETS_41) else "ruido",
                                   texto=f"Aciertos {v['ok']}/{len(TICKETS_41)} · falsos positivos {v['fp']} · falsos negativos {v['fn']}")
    concepto("Fíjate en T9 (enojo sin criterio de escalamiento) y T8 (aviso sin acción): con el prompt vago suelen "
             "escalarse. Edita SISTEMA_EXPLICITO_41 quitando la línea del enojo y vuelve a correr.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 4.2  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio4.py guia 4.2)
# ---------------------------------------------------------------------
GUIA_4_2 = """
#### De qué trata
**Few-shot** = poner de 2 a 4 ejemplos de entrada → salida en el prompt. Es la técnica más efectiva cuando las
instrucciones solas dan resultados inconsistentes. Los buenos ejemplos:
- cubren los **casos ambiguos**, no solo los fáciles;
- explican **por qué** se decidió así, para que el modelo generalice el criterio y no solo copie el formato.

#### Qué pasa al correrla, paso a paso
1. Hay 6 mensajes de clientes en `MENSAJES_42`, cada uno con su respuesta correcta. Los difíciles son:
   - *"Lo mismo que pedí la vez pasada"*: no hay producto identificable;
   - *"Un mantel, el rojo no, el otro"*: dice qué color NO quiere;
   - *"unas cuantas tazas verdes"*: no hay cantidad exacta.
2. Ronda **sin ejemplos**: solo la instrucción. Por cada mensaje, ✔ o ✘ con qué campo falló.
3. Ronda **con ejemplos**: se agregan los 4 ejemplos de `EJEMPLOS_42` al system prompt (se imprimen en pantalla).
4. La tabla compara las dos rondas mensaje por mensaje.

Qué esperar: los casos fáciles salen bien en ambas. En los ambiguos, sin ejemplos el modelo suele **inventar** una
cantidad (*"unas cuantas"* → 3) o no pedir aclaración.

#### Lo que se le manda a Claude
- `TOOL_PEDIDO_42` con campos nullable (`"type": ["integer", "null"]`), forzada con `tool_choice`.
- Los ejemplos van en el `system`, cada uno con su `(por qué: …)`.

#### Dónde está en el código
`MENSAJES_42`, `EJEMPLOS_42`, `_coincide_42()` (compara cantidad, color y aclaración) y `demo_4_2()`.

#### Experimentos
- Quita los `(por qué: …)` de los ejemplos y compara.
- Cambia un ejemplo para que contradiga la instrucción: el modelo suele seguir al ejemplo. Los ejemplos pesan mucho.

#### Lo que pregunta el examen
- Salida inconsistente con instrucciones detalladas → agrega ejemplos few-shot de los casos ambiguos.
- Si el modelo **inventa** un dato porque el schema lo obliga (campo requerido que el documento no trae), el arreglo
  es un campo **nullable** (demo 4.3), no few-shot.
- Si inventa u omite datos porque los documentos vienen en formatos distintos (medidas informales, tabla vs. texto
  corrido), ahí sí ayuda **few-shot**: un ejemplo por cada estructura.
- Ejemplos con formatos variados del documento ayudan a extraer bien de documentos con estructura distinta.
"""


# =====================================================================
#  DEMO 4.2 · FEW-SHOT: EJEMPLOS PARA CASOS AMBIGUOS
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D42_MODO = "ambos"     # "sin_ejemplos", "con_ejemplos" o "ambos"
# ------------------------------------------------------------------------

# (mensaje del cliente, lo correcto)
MENSAJES_42 = [
    ("Quiero un par de tazas de talavera azules", {"producto": "taza talavera", "cantidad": 2, "color": "azul", "requiere_aclaracion": False}),
    ("Mándenme media docena de servilletas bordadas", {"producto": "servilleta bordada", "cantidad": 6, "color": None, "requiere_aclaracion": False}),
    ("Lo mismo que pedí la vez pasada", {"producto": None, "cantidad": None, "color": None, "requiere_aclaracion": True}),
    ("Un mantel, el rojo no, el otro", {"producto": "mantel", "cantidad": 1, "color": None, "requiere_aclaracion": True}),
    ("3 jarros de barro", {"producto": "jarro de barro", "cantidad": 3, "color": None, "requiere_aclaracion": False}),
    ("unas cuantas tazas verdes", {"producto": "taza", "cantidad": None, "color": "verde", "requiere_aclaracion": True}),
]

EJEMPLOS_42 = """Ejemplos (fíjate en los casos ambiguos):
Mensaje: "Quiero una docena de tazas rojas"
→ {"producto": "taza", "cantidad": 12, "color": "rojo", "requiere_aclaracion": false}
Mensaje: "Ocupo varios manteles"
→ {"producto": "mantel", "cantidad": null, "color": null, "requiere_aclaracion": true}
   (por qué: "varios" no es un número; NO inventes una cantidad)
Mensaje: "El de siempre"
→ {"producto": null, "cantidad": null, "color": null, "requiere_aclaracion": true}
   (por qué: no hay producto identificable; no lo adivines del historial)
Mensaje: "Un jarrón, el café no, el otro"
→ {"producto": "jarrón", "cantidad": 1, "color": null, "requiere_aclaracion": true}
   (por qué: dice qué color NO quiere, pero no cuál sí)"""

TOOL_PEDIDO_42 = {
    "name": "registrar_pedido",
    "description": "Registra lo que pide el cliente.",
    "input_schema": {"type": "object", "properties": {
        "producto": {"type": ["string", "null"]}, "cantidad": {"type": ["integer", "null"]},
        "color": {"type": ["string", "null"]}, "requiere_aclaracion": {"type": "boolean"}},
        "required": ["producto", "cantidad", "color", "requiere_aclaracion"]},
}


def _coincide_42(obtenido: dict, esperado: dict) -> tuple[bool, list[str]]:
    errores = []
    if obtenido.get("cantidad") != esperado["cantidad"]:
        errores.append(f"cantidad {obtenido.get('cantidad')!r}≠{esperado['cantidad']!r}")
    if bool(obtenido.get("requiere_aclaracion")) != esperado["requiere_aclaracion"]:
        errores.append("aclaración")
    color = (obtenido.get("color") or None)
    if (color is None) != (esperado["color"] is None) or (color and esperado["color"] and esperado["color"][:4] not in color.lower()):
        errores.append(f"color {color!r}")
    return not errores, errores


def demo_4_2():
    titulo("DEMO 4.2 · Few-shot: ejemplos que enseñan los casos ambiguos")
    mostrar_guia("4.2")
    concepto(
        "Few-shot = incluir 2 a 4 ejemplos de entrada → salida en el prompt. Es la técnica más efectiva cuando las "
        "instrucciones solas dan resultados inconsistentes.\n"
        "Los mejores ejemplos cubren los casos AMBIGUOS y explican POR QUÉ se decidió así; así el modelo generaliza "
        "el criterio y no solo copia el formato."
    )
    modos = ["sin_ejemplos", "con_ejemplos"] if D42_MODO == "ambos" else [D42_MODO]
    base = ("Extrae el pedido del mensaje del cliente con registrar_pedido. Si algo no está claro, "
            "marca requiere_aclaracion.")
    filas = {i: [escape(m)] for i, (m, _) in enumerate(MENSAJES_42)}
    totales = {}
    for modo in modos:
        sistema = base + ("\n\n" + EJEMPLOS_42 if modo == "con_ejemplos" else "")
        paso(f"Modo {modo}")
        if modo == "con_ejemplos":
            consola.print(Panel(escape(EJEMPLOS_42), title="Ejemplos que se agregan al system prompt", border_style="magenta"))
        aciertos = 0
        for i, (mensaje, esperado) in enumerate(MENSAJES_42):
            resp = llamar_claude(f"{modo}", silencioso=True, system=sistema, tools=[TOOL_PEDIDO_42],
                                 tool_choice=tool_choice_forzado("registrar_pedido"),
                                 messages=[{"role": "user", "content": mensaje}], max_tokens=300)
            obtenido = entrada_tool(resp)
            bien, errores = _coincide_42(obtenido, esperado)
            aciertos += bien
            (ok if bien else alerta)(f"{mensaje}  →  {json.dumps(obtenido, ensure_ascii=False)}"
                                     + ("" if bien else f"   [{', '.join(errores)}]"))
            filas[i].append("[green]✔[/]" if bien else f"[red]✘ {escape(', '.join(errores))}[/]")
        totales[modo] = aciertos
    tabla = Table(title="¿Extrajo lo correcto?", show_lines=True)
    tabla.add_column("Mensaje")
    for modo in modos:
        tabla.add_column(modo)
    for i in filas:
        tabla.add_row(*filas[i])
    tabla.add_row("[bold]Aciertos[/]", *[f"[bold]{totales[m]}/{len(MENSAJES_42)}[/]" for m in modos])
    if len(modos) > 1:
        visual.registrar_resultado(final="comparacion", texto=" · ".join(f"{m}: {totales[m]}/{len(MENSAJES_42)}" for m in modos))
    if len(modos) == 1:
        visual.registrar_resultado(final="consistente" if totales[modos[0]] == len(MENSAJES_42) else "inconsistente",
                                   texto=f"Aciertos {totales[modos[0]]}/{len(MENSAJES_42)}")
    consola.print(tabla)
    concepto("Los casos 'lo mismo que la vez pasada', 'el rojo no, el otro' y 'unas cuantas' son donde los ejemplos "
             "ayudan: sin ellos el modelo tiende a inventar una cantidad o un producto. Quita el '(por qué: …)' de los "
             "ejemplos y compara.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 4.3  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio4.py guia 4.3)
# ---------------------------------------------------------------------
GUIA_4_3 = """
#### De qué trata
Pedir *"responde solo en JSON"* funciona **casi** siempre, y en un pipeline "casi" es un problema: a veces llega con
```` ```json ````, con una frase antes o con claves distintas. La alternativa confiable es **tool_use**: defines la
salida como `input_schema` de una tool y fuerzas su uso con `tool_choice`. El JSON siempre es parseable y sigue
el schema.

Diseño del schema:
- Campos que pueden no venir → **nullable** (`["string", "null"]`), así no inventa.
- Categorías → `enum` con una opción **"otro"** + un campo de detalle.
- El schema garantiza la **sintaxis**, no la **semántica**: un total puede no cuadrar (demo 4.4).

#### Qué pasa al correrla, paso a paso
1. Se imprime el schema `SCHEMA_43`.
2. Modo **texto**: se piden los 5 correos en JSON por prompt y se intenta `json.loads()`. Si falla, se ve qué llegó.
3. Modo **tool**: los mismos correos con `extraer_correo` forzada.
4. Por cada correo se valida que estén las claves y que `tipo` sea un valor válido.
5. Tabla: **JSON parseable** y **Cumple el schema** por modo.

Qué esperar: en tool, 5/5 y 5/5. En texto suele haber fallas de parseo (por los ```` ```json ````) o claves de
más o de menos. Mira el correo *"algo bonito para regalo"*: con nullable y `"otro"`, la salida es honesta.

#### Dónde está en el código
`SCHEMA_43`, `TOOL_EXTRAER_43`, `_valida_esquema_43()` y `demo_4_3()`.

#### Experimentos
- Quita `"otro"` del enum de `tipo` y mira cómo clasifica el correo del regalo.
- Quita `"null"` de `fecha_requerida`: puede empezar a inventar fechas.

#### Lo que pregunta el examen
- Salida estructurada confiable → tool_use con JSON schema (elimina errores de sintaxis).
- `tool_choice: any` garantiza que llame alguna tool; forzar una tool garantiza cuál.
- Campos opcionales como nullable para evitar datos fabricados; `enum` + `"otro"` + detalle para categorías abiertas.
"""


# =====================================================================
#  DEMO 4.3 · SALIDA ESTRUCTURADA CON TOOL USE
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D43_MODO = "ambos"     # "texto" (pedir JSON en el prompt), "tool" (tool_use + schema) o "ambos"
# ------------------------------------------------------------------------

CORREOS_43 = [
    "Hola, soy Marta Ruiz. Quiero 2 manteles rojos para el 15 de diciembre. Pago con tarjeta. Gracias!",
    "Buenas, pedido para la empresa Café Luna: 30 tazas de talavera. ¿Facturan? RFC CLU201010AB1.",
    "me pueden mandar algo bonito para regalo? como unos 800 pesos",
    "Necesito cancelar el #12347, ya no lo voy a ocupar.",
    "Reclamo: el pedido #12346 llegó incompleto, faltan 4 platos. Quiero que me los manden.",
]

SCHEMA_43 = {"type": "object", "properties": {
    "tipo": {"type": "string", "enum": ["pedido_nuevo", "cancelacion", "reclamo", "consulta", "otro"]},
    "tipo_detalle": {"type": ["string", "null"], "description": "Solo si tipo = 'otro'"},
    "cliente": {"type": ["string", "null"]},
    "pedido_id": {"type": ["string", "null"], "description": "Formato #NNNNN si se menciona"},
    "productos": {"type": "array", "items": {"type": "object", "properties": {
        "nombre": {"type": "string"}, "cantidad": {"type": ["integer", "null"]}}, "required": ["nombre", "cantidad"]}},
    "fecha_requerida": {"type": ["string", "null"], "description": "YYYY-MM-DD o null si no se menciona"},
    "requiere_factura": {"type": "boolean"}},
    "required": ["tipo", "tipo_detalle", "cliente", "pedido_id", "productos", "fecha_requerida", "requiere_factura"]}

TOOL_EXTRAER_43 = {"name": "extraer_correo", "description": "Extrae los datos del correo.", "input_schema": SCHEMA_43}


def _valida_esquema_43(datos) -> list[str]:
    """Validación mínima de forma (sin librerías externas)."""
    if not isinstance(datos, dict):
        return ["no es un objeto JSON"]
    faltan = [k for k in SCHEMA_43["required"] if k not in datos]
    errores = [f"falta '{k}'" for k in faltan]
    if datos.get("tipo") not in SCHEMA_43["properties"]["tipo"]["enum"]:
        errores.append(f"tipo inválido: {datos.get('tipo')!r}")
    return errores


def demo_4_3():
    titulo("DEMO 4.3 · Salida estructurada: tool use + JSON schema")
    mostrar_guia("4.3")
    concepto(
        "Pedir 'responde solo en JSON' en el prompt funciona casi siempre… y 'casi' rompe un pipeline: a veces llega "
        "con ```json, con una frase antes, o con campos de más o de menos.\n"
        "tool_use con input_schema + tool_choice forzado = el JSON siempre es parseable y sigue el esquema.\n"
        "Diseño del schema: campos opcionales como nullable (así no inventa), enum con 'otro' + detalle.\n"
        "Ojo: el esquema garantiza la SINTAXIS, no la SEMÁNTICA (un total puede no cuadrar → demo 4.4)."
    )
    mostrar_json(SCHEMA_43, "El esquema (input_schema de la tool)", "yellow")
    modos = ["texto", "tool"] if D43_MODO == "ambos" else [D43_MODO]
    resumen = []
    for modo in modos:
        paso(f"Modo {modo}")
        parseables = validos = 0
        for correo in CORREOS_43:
            consola.print(f"\n[bold]✉  {escape(correo)}[/]")
            if modo == "texto":
                resp = llamar_claude("texto", silencioso=True, max_tokens=600, messages=[{"role": "user", "content":
                    f"Extrae los datos de este correo y responde SOLO con JSON con estas claves: "
                    f"{', '.join(SCHEMA_43['required'])}.\n\nCorreo: {correo}"}])
                crudo = texto_de(resp)
                try:
                    datos = json.loads(crudo)
                    parseables += 1
                except json.JSONDecodeError:
                    alerta("json.loads() falló. Lo que llegó:")
                    consola.print(Panel(escape(recortar(crudo, 400)), border_style="red"))
                    continue
            else:
                resp = llamar_claude("tool", silencioso=True, max_tokens=600, tools=[TOOL_EXTRAER_43],
                                     tool_choice=tool_choice_forzado("extraer_correo"),
                                     messages=[{"role": "user", "content": f"Correo: {correo}"}])
                datos = entrada_tool(resp, "extraer_correo")
                parseables += 1
            errores = _valida_esquema_43(datos)
            validos += not errores
            (ok if not errores else alerta)(json.dumps(datos, ensure_ascii=False) + (f"   [{'; '.join(errores)}]" if errores else ""))
        resumen.append([modo, f"{parseables}/{len(CORREOS_43)}", f"{validos}/{len(CORREOS_43)}"])
    tabla_simple("Resultado", ["Modo", "JSON parseable", "Cumple el schema"], resumen)
    if len(modos) > 1:
        visual.registrar_resultado(final="comparacion", texto=" · ".join(f"{r[0]}: parseable {r[1]}, schema {r[2]}" for r in resumen))
    if len(modos) == 1:
        visual.registrar_resultado(final="valido" if validos == len(CORREOS_43) else "roto",
                                   texto=f"JSON parseable {parseables}/{len(CORREOS_43)} · cumple el schema {validos}/{len(CORREOS_43)}")
    concepto("Mira el correo 'algo bonito para regalo': ¿qué puso en productos y en tipo? Con campos nullable y "
             "enum con 'otro', el modelo tiene una salida honesta en vez de inventar.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 4.4  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio4.py guia 4.4)
# ---------------------------------------------------------------------
GUIA_4_4 = """
#### De qué trata
El schema asegura la forma; las **reglas de negocio** se validan en código. Cuando una falla, se reintenta
mandándole al modelo el **error específico**: qué campo, qué valor y qué se esperaba.

Dos ideas clave del examen:
- El reintento sirve para errores de **formato o estructura**. **No** sirve cuando el dato **no existe** en el
  documento: el modelo terminaría inventándolo.
- Patrón *total declarado vs calculado*: extraer los dos y marcar la discrepancia, en lugar de "corregir" en silencio.

#### Qué pasa al correrla, paso a paso
Tres documentos:
- **`ok`**: consistente, pero los SKU vienen en minúsculas (`tbl red 01`). La regla exige `AAA-AAA-00`.
- **`total_no_cuadra`**: el documento dice $4,800 y las partidas suman $4,500. El error es **de origen**.
- **`sin_fecha`**: no menciona fecha de entrega.

Por cada uno:
1. Se extrae con `registrar_pedido` forzada y se imprime el JSON del intento.
2. `validar_44()` revisa:
   - formato del SKU;
   - que `total_calculado` sea la suma real;
   - que una discrepancia esté marcada;
   - que la fecha aparezca en el documento.
3. Si hay errores, se manda la **retroalimentación** (panel magenta) como `tool_result` con `is_error` y se reintenta,
   hasta `D44_MAX_REINTENTOS`.

Qué esperar con `"especifico"`: en `ok`, el primer intento falla por el SKU y el segundo lo corrige. En
`total_no_cuadra`, lo correcto es `hay_discrepancia: true` con el total declarado intacto. En `sin_fecha`,
`fecha_entrega: null`.

#### Dónde está en el código
`DOCUMENTOS_44`, `TOOL_PEDIDO_44`, `validar_44()` (las reglas) y el `for intento` de `demo_4_4()`, donde se arma la
retroalimentación.

#### Experimentos
- `D44_FEEDBACK = "generico"`: con *"inténtalo de nuevo"* el modelo no sabe qué cambiar y suele repetir el error.
- `D44_FEEDBACK = "sin_reintento"`: aceptas el primer resultado, con errores.
- Agrega tu propia regla a `validar_44()`; por ejemplo, que la cantidad sea positiva.

#### Lo que pregunta el examen
- Reintento con el documento, la extracción fallida y el error específico de validación.
- Reintentar no sirve si la información no está en la fuente.
- Campo `detected_pattern` o de confianza para analizar después por qué se descartan hallazgos.
- `calculated_total` junto a `stated_total` para detectar discrepancias.
"""


# =====================================================================
#  DEMO 4.4 · VALIDACIÓN, REINTENTO Y RETROALIMENTACIÓN
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# "especifico" → le dices exactamente qué falló · "generico" → "hay errores, intenta de nuevo"
# "sin_reintento" → aceptas lo primero que llega
D44_FEEDBACK = "especifico"
D44_MAX_REINTENTOS = 2
# ------------------------------------------------------------------------

DOCUMENTOS_44 = {
    "ok": ("Pedido de Ana López: 2 x tbl red 01 a $890 c/u y 1 x mug tal 06 a $650. Total: $2,430. "
           "Entregar el 2026-12-10."),
    "total_no_cuadra": ("Pedido de Juan Pérez: 1 x din cly 24 a $3,200 y 2 x mug tal 06 a $650. "
                        "Total a pagar: $4,800. Entregar el 2026-12-12."),
    "sin_fecha": "Pedido de Marta Ruiz: 3 x tbl blu 01 a $890. Total: $2,670.",
}

TOOL_PEDIDO_44 = {
    "name": "registrar_pedido",
    "description": "Registra un pedido extraído de un documento.",
    "input_schema": {"type": "object", "properties": {
        "cliente": {"type": "string"},
        "partidas": {"type": "array", "items": {"type": "object", "properties": {
            "sku": {"type": "string"}, "cantidad": {"type": "integer"}, "precio_unitario": {"type": "number"}},
            "required": ["sku", "cantidad", "precio_unitario"]}},
        "total_declarado": {"type": "number", "description": "El total tal como aparece en el documento"},
        "total_calculado": {"type": "number", "description": "Suma de cantidad x precio de las partidas"},
        "hay_discrepancia": {"type": "boolean"},
        "fecha_entrega": {"type": ["string", "null"]}},
        "required": ["cliente", "partidas", "total_declarado", "total_calculado", "hay_discrepancia", "fecha_entrega"]},
}


def validar_44(datos: dict, documento: str) -> list[str]:
    """Reglas de negocio que el ESQUEMA no puede expresar."""
    import re
    errores = []
    for p in datos.get("partidas", []):
        if not re.fullmatch(r"[A-Z]{3}-[A-Z]{3}-\d{2}", str(p.get("sku", ""))):
            errores.append(f"El sku {p.get('sku')!r} no cumple el formato AAA-AAA-00 (ejemplo: TBL-RED-01).")
    suma = round(sum(p.get("cantidad", 0) * p.get("precio_unitario", 0) for p in datos.get("partidas", [])), 2)
    if abs(suma - float(datos.get("total_calculado", -1))) > 0.01:
        errores.append(f"total_calculado es {datos.get('total_calculado')} pero la suma de las partidas da {suma}.")
    discrepancia_real = abs(suma - float(datos.get("total_declarado", -1))) > 0.01
    if discrepancia_real and not datos.get("hay_discrepancia"):
        errores.append(f"El total declarado ({datos.get('total_declarado')}) no coincide con la suma ({suma}): "
                       "marca hay_discrepancia = true, NO corrijas el total declarado.")
    fecha = datos.get("fecha_entrega")
    if fecha and fecha not in documento:
        errores.append(f"La fecha {fecha!r} no aparece en el documento. Si no hay fecha, usa null.")
    return errores


def demo_4_4():
    titulo("DEMO 4.4 · Validación, reintento y retroalimentación")
    mostrar_guia("4.4")
    concepto(
        "El schema garantiza la forma; tus REGLAS DE NEGOCIO las validas en código. Si fallan, reintenta mandando "
        "el error ESPECÍFICO (qué campo, qué valor, qué se esperaba).\n"
        "Reintentar sirve para errores de formato o de estructura; NO sirve cuando el dato no existe en el documento "
        "(el modelo inventaría). Patrón: extraer total_declarado Y total_calculado para detectar discrepancias en vez "
        "de 'corregir' en silencio."
    )
    nota(f"D44_FEEDBACK = '{D44_FEEDBACK}'")
    resumen = []
    for nombre, documento in DOCUMENTOS_44.items():
        paso(f"Documento '{nombre}'")
        consola.print(Panel(escape(documento), border_style="blue"))
        mensajes = [{"role": "user", "content": f"Extrae el pedido:\n{documento}"}]
        intentos, errores = 0, []
        for intento in range(1, D44_MAX_REINTENTOS + 2):
            intentos = intento
            resp = llamar_claude(f"{nombre} intento {intento}", silencioso=True, tools=[TOOL_PEDIDO_44],
                                 tool_choice=tool_choice_forzado("registrar_pedido"), messages=mensajes, max_tokens=800)
            uso = next((b for b in resp.content if b.type == "tool_use"), None)
            datos = uso.input if uso else {}
            mostrar_json(datos, f"Intento {intento}", "cyan")
            errores = validar_44(datos, documento)
            if not errores:
                ok("Pasa todas las validaciones.")
                break
            for e in errores:
                alerta(e)
            if D44_FEEDBACK == "sin_reintento" or intento > D44_MAX_REINTENTOS:
                break
            retro = ("\n".join(f"- {e}" for e in errores) if D44_FEEDBACK == "especifico"
                     else "La extracción tiene errores. Inténtalo de nuevo.")
            consola.print(Panel(escape(retro), title="Retroalimentación que se le manda a Claude", border_style="magenta"))
            mensajes += [{"role": "assistant", "content": resp.content},
                         {"role": "user", "content": [{"type": "tool_result", "tool_use_id": uso.id, "is_error": True,
                                                       "content": retro}]}]
        resumen.append([nombre, intentos, "[green]sí[/]" if not errores else "[red]no[/]",
                        "sí" if datos.get("hay_discrepancia") else "no", datos.get("fecha_entrega")])
    tabla_simple("Resumen", ["Documento", "Intentos", "¿Válido al final?", "¿Marcó discrepancia?", "fecha_entrega"], resumen)
    validos_44 = sum(1 for fila in resumen if "sí" in fila[2])
    visual.registrar_resultado(final="corrige" if validos_44 == len(resumen) else ("acepta" if D44_FEEDBACK == "sin_reintento" else "repite"),
                               texto=f"Documentos válidos al final: {validos_44}/{len(resumen)}")
    concepto("1) D44_FEEDBACK = 'generico' → con 'inténtalo de nuevo' el modelo no sabe qué cambiar.\n"
             "2) En 'total_no_cuadra' el documento está mal de origen: lo correcto NO es corregir el total, sino "
             "marcar la discrepancia para revisión humana.\n"
             "3) En 'sin_fecha' la fecha no existe: reintentar pidiendo 'pon la fecha' solo produciría una inventada.",
             "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 4.5  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio4.py guia 4.5)
# ---------------------------------------------------------------------
GUIA_4_5 = """
#### De qué trata
La **Message Batches API** procesa muchas peticiones de forma asíncrona:

| | Batches API | API síncrona |
|---|---|---|
| Costo | ~50% menos | Normal |
| Tiempo | Hasta 24 h, sin garantía | Segundos |
| Tools | Un turno por petición (sin loop de tools) | Loop completo |
| Para | Reportes nocturnos, auditorías | Lo que alguien está esperando |

#### Qué pasa al correrla, paso a paso
1. Se arman 8 peticiones (clasificar reseñas), cada una con su `custom_id` (`resena-001`…). Se imprime una de ejemplo.
2. Se crea el lote con `client.messages.batches.create(requests=...)`. El id se guarda en `ultimo_lote.txt`.
3. Cada `D45_CADA_S` segundos se consulta el estado: `in_progress` → `ended`, con contadores de procesando, ok,
   error y expiradas.
4. Al terminar se leen los resultados con `batches.results()`. Pueden llegar **en otro orden**: se emparejan por `custom_id`.
5. Si alguna falló, se indica que se reenvía **solo esa**, en un lote nuevo.
6. Tabla: ¿batch o síncrono?, y la cuenta de SLA.

Ojo: un lote pequeño suele terminar en minutos, pero **no hay garantía**. Si pasa `D45_ESPERA_MAXIMA_S`, la demo
para y te dice cómo recuperarlo después con `D45_LOTE_EXISTENTE`.

#### Dónde está en el código
`RESENAS_45` y `demo_4_5()`: `batches.create`, el `while` con `batches.retrieve` y el `for` con `batches.results`.

#### Experimentos
- Cierra la demo a la mitad y luego recupera el lote pegando su id en `D45_LOTE_EXISTENTE`.
- Agrega 50 reseñas más: el costo baja a la mitad comparado con mandarlas una por una.
- `D45_EMPAREJAR = "orden"`: empareja por posición y mira qué reseñas quedan con la clasificación de otra.
- `D45_USO = "pre_merge"`: la demo explica por qué no se manda el lote (y no gasta nada).
- `D45_SLA_HORAS = 30`: con lotes de hasta 24 h, un documento puede esperar a lo más 6 h antes de entrar a un lote
  → manda lotes al menos cada 6 h (con margen, cada 4 h). Prueba con 24: Batch ya no garantiza el SLA.

#### Lo que pregunta el examen
- Bloqueante (revisión antes de un merge) → síncrona. Puede esperar (reporte nocturno) → batch.
- `custom_id` para emparejar resultados y reenviar solo los que fallaron.
- Prueba el prompt con una muestra antes de mandar un lote grande, para no repetir miles de peticiones.
- Matemáticas de SLA: con hasta 24 h de procesamiento, hay que enviar con suficiente anticipación.
"""


# =====================================================================
#  DEMO 4.5 · PROCESAMIENTO POR LOTES (MESSAGE BATCHES API)
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D45_ESPERA_MAXIMA_S = 600      # cuánto esperar el lote en esta demo (el límite real es hasta 24 h)
D45_CADA_S = 10                # cada cuántos segundos revisar el estado
# Para recuperar un lote que ya enviaste antes, pega su id aquí (p. ej. "msgbatch_01...")
D45_LOTE_EXISTENTE = ""
# "custom_id" → cada resultado se empareja con su reseña por su custom_id (lo correcto)
# "orden"     → se empareja por posición, suponiendo que llegan en el orden en que se mandaron
D45_EMPAREJAR = "custom_id"
# "nocturno"  → reporte que puede esperar (batch está bien)
# "pre_merge" → revisión que bloquea a alguien antes de un merge (batch NO sirve: no se manda el lote)
D45_USO = "nocturno"
D45_REPORTE_A_LAS = 8          # hora en que debe estar listo el reporte (para las matemáticas de SLA)
D45_SLA_HORAS = 30             # SLA desde que llega un documento hasta que está procesado (para calcular cada cuándo mandar lotes)
# ------------------------------------------------------------------------

RESENAS_45 = [
    "Me encantó el mantel, llegó rapidísimo.", "La taza llegó rota y nadie contesta.",
    "Bonita vajilla pero el envío tardó 3 semanas.", "Todo perfecto, volveré a comprar.",
    "El color no es como en la foto.", "Excelente atención por WhatsApp.",
    "Pedí 6 servilletas y llegaron 5.", "Precio justo, buena calidad.",
]


def demo_4_5():
    titulo("DEMO 4.5 · Message Batches API: 50% más barato, sin garantía de tiempo")
    mostrar_guia("4.5")
    concepto(
        "Message Batches API: mandas muchas peticiones juntas y las procesa de forma asíncrona.\n"
        "  • Cuesta ~50% menos.  • Puede tardar hasta 24 h (sin SLA de latencia).\n"
        "  • Cada petición lleva un custom_id para emparejar resultados.  • No hay loop de tools dentro del lote "
        "(cada petición es de un solo turno).\n"
        "Úsalo para lo que puede esperar (reportes nocturnos, auditorías). NO para lo que bloquea a alguien "
        "(revisión antes de un merge)."
    )
    limite = (D45_REPORTE_A_LAS - 24) % 24
    nota(f"Matemáticas de SLA: el reporte debe estar a las {D45_REPORTE_A_LAS}:00 y un lote puede tardar hasta 24 h → "
         f"hay que enviarlo a más tardar a las {limite}:00 del día anterior.")
    holgura = D45_SLA_HORAS - 24
    if holgura <= 0:
        alerta(f"SLA de {D45_SLA_HORAS} h: un lote puede tardar hasta 24 h, así que Batch NO garantiza ese SLA. "
               "Usa la API síncrona para esos documentos.")
    else:
        nota(f"SLA de {D45_SLA_HORAS} h: un lote puede tardar hasta 24 h → un documento puede esperar a lo más "
             f"{holgura} h antes de entrar a un lote. Manda lotes al menos cada {holgura} h (mejor con margen: "
             f"cada {max(1, holgura - 2)} h).")
    if D45_USO == "pre_merge":
        alerta("Uso: revisión antes de un merge. Alguien está esperando y un lote puede tardar hasta 24 h: aquí va la "
               "API síncrona, no Batch. La demo no manda el lote (no gasta nada).")
        visual.registrar_resultado(final="bloquea", texto="Batch no sirve para algo que bloquea a alguien: no se envió el lote")
        return
    c = cliente()
    if D45_LOTE_EXISTENTE:
        lote_id = D45_LOTE_EXISTENTE
        nota(f"Recuperando el lote existente {lote_id}")
    else:
        peticiones = [{
            "custom_id": f"resena-{i:03d}",
            "params": {"model": MODELO, "max_tokens": 300, "messages": [{"role": "user", "content":
                       f"Clasifica en una palabra (positiva/neutral/negativa): {texto}"}]},
        } for i, texto in enumerate(RESENAS_45, 1)]
        mostrar_json(peticiones[0], "Así se ve UNA petición del lote (custom_id + params)", "yellow")
        lote = c.messages.batches.create(requests=peticiones)
        lote_id = lote.id
        ok(f"Lote creado: {lote_id} · estado: {lote.processing_status} · {len(peticiones)} peticiones")
        archivo = Path(__file__).resolve().parent / "ultimo_lote.txt"
        archivo.write_text(lote_id, encoding="utf-8")
        nota(f"Guardé el id en {archivo.name}: si cierras la demo, pégalo en D45_LOTE_EXISTENTE para recuperarlo.")

    t0 = time.time()
    while True:
        lote = c.messages.batches.retrieve(lote_id)
        n = lote.request_counts
        nota(f"[{time.time() - t0:5.0f}s] estado={lote.processing_status} · procesando={n.processing} "
             f"· ok={n.succeeded} · error={n.errored} · expiradas={n.expired}")
        if lote.processing_status == "ended":
            break
        if time.time() - t0 > D45_ESPERA_MAXIMA_S:
            alerta(f"El lote sigue en proceso tras {D45_ESPERA_MAXIMA_S}s. Es normal: no hay garantía de tiempo. "
                   f"Vuelve a correr la demo con D45_LOTE_EXISTENTE = '{lote_id}'.")
            return
        time.sleep(D45_CADA_S)

    filas, fallidas, llegada = [], [], []
    for r in c.messages.batches.results(lote_id):
        llegada.append(r.custom_id)
        if r.result.type == "succeeded":
            sumar_uso_api(r.result.message, factor=0.5)   # la Batch API cuesta la mitad
            texto = "".join(b.text for b in r.result.message.content if b.type == "text").strip()
            filas.append([r.custom_id, "[green]succeeded[/]", escape(texto)])
        else:
            fallidas.append(r.custom_id)
            filas.append([r.custom_id, f"[red]{r.result.type}[/]", "—"])
    nota("Orden en que llegaron: " + ", ".join(llegada))
    if D45_EMPAREJAR == "orden":
        # Se supone que el resultado i es de la reseña i: si llegaron en otro orden, se cruzan
        cruzadas = [i for i, cid in enumerate(llegada) if cid != f"resena-{i + 1:03d}"]
        tabla_simple("Emparejado POR ORDEN (suponiendo que llegan como se mandaron)", ["reseña", "resultado que le tocó", "¿correcto?"],
                     [[escape(RESENAS_45[i][:45]) if i < len(RESENAS_45) else "?", f"{f[0]} · {f[2][:30]}",
                       "[red]NO: es de otra reseña[/]" if i in cruzadas else "sí"] for i, f in enumerate(filas)])
        if cruzadas:
            alerta(f"{len(cruzadas)} reseña(s) quedaron con la clasificación de otra. El orden no está garantizado.")
        else:
            nota("Esta vez llegaron en orden, pero nada lo garantiza: con lotes grandes se cruzan.")
        visual.registrar_resultado(final="mal_emparejado" if cruzadas else "suerte_orden",
                                   texto=f"Resultados cruzados al emparejar por orden: {len(cruzadas)}/{len(llegada)}")
    else:
        tabla_simple("Resultados (emparejados por custom_id; pueden llegar en otro orden)", ["custom_id", "estado", "resultado"],
                     sorted(filas))
        visual.registrar_resultado(final="emparejado", texto=f"{len(filas)} resultados emparejados por custom_id")
    if fallidas:
        alerta(f"Fallaron: {fallidas}. Se reenvían SOLO esas, en un lote nuevo, usando su custom_id.")
    tabla_simple("¿Batch o síncrono?", ["Caso", "API", "Por qué"], [
        ["Revisión antes de un merge (alguien espera)", "Síncrona", "Necesita respuesta en minutos"],
        ["Reporte nocturno de reseñas", "Batch", "Puede esperar; 50% más barato"],
        ["Auditoría semanal de 10,000 documentos", "Batch", "Volumen alto, sin urgencia"],
    ])
    concepto("Matemáticas de SLA: si el reporte debe estar listo a las 8:00 y el lote puede tardar hasta 24 h, "
             "hay que enviarlo a más tardar a las 8:00 del día anterior (o partir el trabajo en ventanas más cortas).")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 4.6  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio4.py guia 4.6)
# ---------------------------------------------------------------------
GUIA_4_6 = """
#### De qué trata
Un modelo que revisa su propio trabajo **en la misma conversación** arrastra el razonamiento con el que lo escribió:
tiende a confirmar en vez de cuestionar. Una **instancia independiente**, sin el historial de generación, encuentra
más problemas. Además, cada hallazgo puede llevar **confianza**, y los de baja confianza van a revisión humana.

#### Qué pasa al correrla, paso a paso
1. Se imprimen la política (máximo $10,000; 5 a 7 días hábiles; número de pedido correcto) y un
   **borrador con 3 problemas sembrados**:
   - aprueba $12,500 sin autorización;
   - promete 24 horas;
   - cita el pedido #12364 en vez de #12346.
2. **`misma_sesion`**: el historial incluye la petición original y el borrador como si Claude lo hubiera escrito.
   Luego: *"Revisa tu respuesta"*.
3. **`independiente`**: llamada nueva con un system prompt de revisor; ve política + caso + borrador y nada más.
4. Ambos responden con `reportar_hallazgos` (problema, severidad, confianza). Cada hallazgo se imprime con su
   destino: **automático** o **revisión humana** (según `D46_UMBRAL_CONFIANZA`).
5. Tabla: cuáles de los 3 problemas encontró cada modo.

Con honestidad: el resultado varía entre corridas, y a veces las dos encuentran todo. La detección es por palabras
clave, así que lee los hallazgos para confirmarla.

#### Dónde está en el código
`POLITICA_46`, `CASO_46`, `BORRADOR_46`, `PROBLEMAS_46` (palabras clave por problema), `TOOL_HALLAZGOS_46` y `demo_4_6()`.

#### Experimentos
- Haz los errores más sutiles en `BORRADOR_46` (por ejemplo, "en 3 días" en vez de "en 24 horas").
- Sube `D46_UMBRAL_CONFIANZA` a 0.9: más hallazgos van a revisión humana.
- `D46_ERRORES = "obvios"` o `"sutiles"` (default): con errores sutiles se nota más la diferencia.

#### Lo que pregunta el examen
- La autorrevisión en la misma sesión es menos efectiva: usa una instancia independiente.
- Revisiones grandes: pasadas por archivo + una pasada de integración (demo 1.6).
- Confianza por hallazgo para decidir qué revisa una persona; calibra el umbral con datos etiquetados (demo 5.5).
"""


# =====================================================================
#  DEMO 4.6 · REVISIÓN CON INSTANCIA INDEPENDIENTE
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D46_MODO = "ambos"        # "misma_sesion", "independiente" o "ambos"
D46_UMBRAL_CONFIANZA = 0.7  # hallazgos con menos confianza → revisión humana
D46_ERRORES = "sutiles"     # "sutiles" (cuestan más de ver) u "obvios" (los dos modos suelen encontrarlos)
# ------------------------------------------------------------------------

POLITICA_46 = """Política de La Tiendita:
- Reembolso automático máximo: $10,000 MXN. Más que eso requiere aprobación humana.
- El reembolso tarda de 5 a 7 días hábiles.
- Siempre citar el número de pedido correcto."""

CASO_46 = "Cliente: Juan Pérez. Pedido #12346, vajilla de $12,500 que llegó rota, con foto."

BORRADOR_46 = ("Hola Juan, lamentamos mucho lo de tu vajilla. Ya aprobamos el reembolso completo de $12,500 "
               "de tu pedido #12364 y lo verás en tu cuenta en 24 horas. ¡Gracias por tu paciencia!")

BORRADOR_46_SUTIL = ("Hola Juan, lamentamos mucho lo de tu vajilla. Ya quedó listo el reembolso completo de tu pedido "
                     "#12364 y lo verás reflejado en unos 3 días. ¡Gracias por tu paciencia!")

PROBLEMAS_46 = {
    "monto > $10,000 sin aprobación": ["10,000", "10000", "aprobación", "límite", "12,500", "12500"],
    "plazo 24 h (debe ser 5-7 días)": ["24", "3 días", "5 a 7", "5-7", "días hábiles"],
    "número de pedido incorrecto": ["12364", "12346", "número de pedido"],
}

TOOL_HALLAZGOS_46 = {
    "name": "reportar_hallazgos",
    "description": "Reporta cada problema encontrado en la respuesta.",
    "input_schema": {"type": "object", "properties": {"hallazgos": {"type": "array", "items": {"type": "object", "properties": {
        "problema": {"type": "string"}, "severidad": {"type": "string", "enum": ["alta", "media", "baja"]},
        "confianza": {"type": "number", "description": "0 a 1"}}, "required": ["problema", "severidad", "confianza"]}}},
        "required": ["hallazgos"]},
}


def _detectados_46(hallazgos: list[dict]) -> dict[str, bool]:
    texto = " ".join(h.get("problema", "") for h in hallazgos).lower()
    return {p: any(k.lower() in texto for k in claves) for p, claves in PROBLEMAS_46.items()}


def demo_4_6():
    titulo("DEMO 4.6 · Revisión independiente: el autor no es el mejor revisor")
    mostrar_guia("4.6")
    concepto(
        "Un modelo que revisa su propio trabajo en la MISMA conversación arrastra el razonamiento que lo llevó ahí: "
        "tiende a confirmar en vez de cuestionar.\n"
        "Una instancia INDEPENDIENTE (sin el historial de generación) que solo ve política + caso + resultado "
        "encuentra más problemas.\n"
        "Además: pide confianza por hallazgo y manda los de baja confianza a revisión humana."
    )
    consola.print(Panel(escape(POLITICA_46), title="Política", border_style="blue"))
    borrador = BORRADOR_46_SUTIL if D46_ERRORES == "sutiles" else BORRADOR_46
    consola.print(Panel(escape(borrador), title=f"Borrador que hay que revisar (3 problemas sembrados, {D46_ERRORES})", border_style="red"))
    modos = ["misma_sesion", "independiente"] if D46_MODO == "ambos" else [D46_MODO]
    resumen = {}
    for modo in modos:
        paso(f"Revisión: {modo}")
        if modo == "misma_sesion":
            # La misma conversación en la que se escribió: el borrador viene con el razonamiento de quien lo escribió
            mensajes = [
                {"role": "user", "content": f"{POLITICA_46}\n\n{CASO_46}\n\nEl cliente está muy molesto y es cliente "
                                            "frecuente. Escribe la respuesta al cliente y explica brevemente tus decisiones."},
                {"role": "assistant", "content": borrador + "\n\n(Mis decisiones: aprobé el reembolso completo porque es "
                 "cliente frecuente y llegó con foto; prometí un plazo corto para calmarlo; el pedido es el que viene en el caso.)"},
                {"role": "user", "content": "Gracias. Antes de enviarla, revísala: ¿hay algún problema?"},
            ]
            nota("El historial incluye la petición y el borrador como si Claude lo hubiera escrito.")
            sistema = "Eres el agente de soporte de La Tiendita."
        else:
            mensajes = [{"role": "user", "content": f"{POLITICA_46}\n\nCaso: {CASO_46}\n\nRespuesta a revisar:\n{borrador}"}]
            nota("Instancia nueva: no vio cómo se escribió el borrador.")
            sistema = "Eres un revisor de calidad independiente. Busca todo lo que viole la política o los datos del caso."
        resp = llamar_claude(modo, system=sistema, tools=[TOOL_HALLAZGOS_46],
                             tool_choice=tool_choice_forzado("reportar_hallazgos"), messages=mensajes, max_tokens=800)
        hallazgos = entrada_tool(resp).get("hallazgos", [])
        for h in hallazgos:
            confianza = float(h.get("confianza", 0))
            destino = "revisión humana" if confianza < D46_UMBRAL_CONFIANZA else "automático"
            nota(f"[{h.get('severidad')}] confianza {confianza:.2f} → {destino}: {h.get('problema')}")
        resumen[modo] = _detectados_46(hallazgos)
    tabla = Table(title="¿Encontró los problemas sembrados?")
    tabla.add_column("Problema")
    for modo in modos:
        tabla.add_column(modo)
    for p in PROBLEMAS_46:
        tabla.add_row(p, *["[green]✔[/]" if resumen[m][p] else "[red]✘[/]" for m in modos])
    tabla.add_row("[bold]Total[/]", *[f"[bold]{sum(resumen[m].values())}/{len(PROBLEMAS_46)}[/]" for m in modos])
    consola.print(tabla)
    if len(modos) > 1:
        visual.registrar_resultado(final="comparacion", texto=" · ".join(f"{m}: {sum(resumen[m].values())}/{len(PROBLEMAS_46)}" for m in modos))
    if len(modos) == 1:
        encontrados = sum(resumen[modos[0]].values())
        visual.registrar_resultado(final="encuentra" if encontrados == len(PROBLEMAS_46) else "se_le_pasa",
                                   texto=f"Encontró {encontrados}/{len(PROBLEMAS_46)} problemas sembrados")
    concepto("El resultado puede variar entre corridas. Si las dos encuentran todo, cambia el borrador para que los "
             "errores sean más sutiles. La detección es por palabras clave: lee los hallazgos para confirmar.", "🧪 Experimenta")


# =====================================================================
#  MENÚ
# =====================================================================

GUIAS = {
    "4.1": GUIA_4_1,
    "4.2": GUIA_4_2,
    "4.3": GUIA_4_3,
    "4.4": GUIA_4_4,
    "4.5": GUIA_4_5,
    "4.6": GUIA_4_6,
}


DEMOS = {
    "4.1": ("Criterios explícitos en el system prompt", demo_4_1),
    "4.2": ("Few-shot para casos ambiguos", demo_4_2),
    "4.3": ("Salida estructurada con tool use", demo_4_3),
    "4.4": ("Validación, reintento y retroalimentación", demo_4_4),
    "4.5": ("Message Batches API", demo_4_5),
    "4.6": ("Revisión con instancia independiente", demo_4_6),
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
        tabla = Table(title="CCAR-F · Lab del Dominio 4")
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
        visual.registrar_resultado(uso={k: USO_TOTAL[k] for k in ("entrada", "salida", "llamadas")}, costo=round(USO_TOTAL["costo"], 6))
        if USO_TOTAL["llamadas"]:
            resumen_costo()
        if GUARDAR_HTML:
            guardar_html(eleccion)


if __name__ == "__main__":
    main()

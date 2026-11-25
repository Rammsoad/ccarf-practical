"""
=====================================================================
 CCAR-F · LAB DEL DOMINIO 5: Context Management & Reliability
=====================================================================

Demos ejecutables, una por subdominio. Todas usan el caso de
"La Tiendita" (tienda en línea) con datos FALSOS.

CÓMO CORRERLO
-------------
  1) pip install -r requirements.txt   (dentro de tu entorno virtual)
  2) Copia .env.example como .env y pega ahí tu API key (ver README).
     Si no hay .env, se usa la variable de entorno ANTHROPIC_API_KEY.
  3) python lab_dominio5.py          -> muestra el menú
     python lab_dominio5.py 5.1      -> corre directo la demo 5.1
     python lab_dominio5.py guia     -> solo lee las guías (no llama a la API)

CÓMO MODIFICARLO
----------------
  * Arriba está la CONFIGURACIÓN GENERAL (modelo, nivel de detalle).
  * Cada demo tiene su propio bloque "🔧 CAMBIA AQUÍ" con variables
    comentadas: cámbialas, vuelve a correr y compara la salida.

DEMOS
-----
  5.1  Ventana de contexto: case facts y recorte   (Messages API)
  5.2  Escalamiento y ambigüedad                    (Messages API)
  5.3  Propagación de errores multiagente           (Messages API)
  5.4  Exploración de código y scratchpad           (Agent SDK)
  5.5  Revisión humana y calibración de confianza   (Messages API)
  5.6  Procedencia y síntesis de varias fuentes     (Messages API)
"""

from __future__ import annotations

import asyncio
import json
import sys
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
# correr nada (ni gastar):  python lab_dominio5.py guia      (o: guia 5.1)
MOSTRAR_GUIA = True
PAUSA_DESPUES_DE_GUIA = True   # espera un Enter después de la guía (ideal para explicar antes de correr)

# Modo HTML: además de la terminal, cada corrida se guarda como página web con un diagrama
# de lo que pasó, en salidas_html/dominio5/. Cada corrida es un archivo nuevo (no se sobrescribe)
# y salidas_html/dominio5/index.html las recorre con Anterior / Siguiente para comparar: cambia una
# variable, vuelve a correr la demo y compara los diagramas. Ejemplos de lo que vas a ver, sin correr
# nada: ejemplos_html/dominio5/index.html
#   True  -> encendido (para apagarlo en una sola corrida:  python lab_dominio5.py 5.1 --sin-html)
#   False -> solo terminal  (para encenderlo en una sola corrida:  python lab_dominio5.py 5.1 --html)
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
import math  # noqa: E402
import visual  # noqa: E402
GUARDAR_HTML = visual.configurar(dominio=5, modo_html=MODO_HTML)
consola = Console(record=GUARDAR_HTML)
visual.usar_consola(consola)
# Ayudantes compartidos (llamar_claude, mostrar_request, correr_agente, contadores de costo…): viven en
# comun.py y comun.instalar() los define aquí mismo, con la configuración de este lab.
import comun  # noqa: E402
from comun import (  # noqa: E402
    PRECIOS, USO_TOTAL, USO_SDK, titulo, paso, concepto,
    ok, alerta, nota, recortar, texto_de, cliente,
    verificar_api_key, tool_choice_forzado, llamar_claude, uso_y_costo, resumen_costo, guardar_html,
    mostrar_estado_html, correr_agente, opciones_base, entrada_tool, tabla_simple, crear_proyecto,
    mostrar_archivo,
)
comun.instalar(globals())


def mostrar_guia(clave: str, forzar: bool = False, pausa: bool = True) -> None:
    """Imprime la guía (markdown) de una demo. Las guías están arriba de cada demo: GUIA_x_y."""
    if not (MOSTRAR_GUIA or forzar):
        return
    if DETALLE == "basico" and not forzar:
        consola.print(f"[dim]📖 Guía de esta demo: python lab_dominio5.py guia {clave}  ·  "
                      f"más detalle: pon DETALLE = \"completo\" arriba del archivo[/]")
        return
    from rich.markdown import Markdown
    consola.print(Panel(Markdown(idioma.guia(clave, GUIAS[clave])), title=f"📖 Guía de la demo {clave}: qué vas a ver",
                        border_style="cyan", padding=(1, 2)))
    if pausa and PAUSA_DESPUES_DE_GUIA and sys.stdin.isatty():
        consola.input("[bold cyan]   Presiona Enter para correr la demo… [/]")


# =====================================================================
#  AYUDANTES DEL DOMINIO 5
# =====================================================================


def contiene(texto: str, *opciones: str) -> bool:
    t = texto.lower()
    return any(o.lower() in t for o in opciones)


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 5.1  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio5.py guia 5.1)
# ---------------------------------------------------------------------
GUIA_5_1 = """
#### De qué trata
Qué se pierde cuando el contexto crece y cómo evitarlo:
- **Resumen progresivo**: para ahorrar espacio, el historial se resume, y el resumen pierde lo exacto (montos, fechas,
  números de pedido, lo que el cliente ya rechazó).
- **Case facts**: un bloque aparte con los datos transaccionales que se copia **completo** en cada turno y nunca se resume.
- **Resultados de tools inflados**: una tool que devuelve 30 campos cuando solo importan 5 ocupa contexto en cada turno.
- **Lost in the middle**: el modelo atiende peor lo que queda a la mitad de un contexto largo. Pon lo importante al
  inicio o al final, con encabezados.

#### Qué pasa al correrla, paso a paso
**Parte A · resumen vs case facts**
1. Se imprime una conversación de 13 mensajes con 5 datos clave: pedido #12346, $12,500, rechazó el crédito,
   prefiere WhatsApp y fecha prometida viernes 20 de noviembre.
2. **`resumen`**: una llamada resume la conversación en 2 líneas. Otro agente retoma el caso **solo con ese resumen**
   y debe decir los 5 datos.
3. **`case_facts`**: el agente que retoma recibe el bloque `CASE FACTS` + un resumen breve.
4. Tabla: qué datos conservó cada modo.

**Parte B · recortar resultados de tools**
- Se cuenta con `count_tokens` (sin costo) cuántos tokens ocupa el pedido completo (30 campos) contra solo los 5
  campos que importan para un reembolso.

Qué esperar: el resumen suele perder 2 o 3 datos (la fecha, el canal, el crédito rechazado). Con case facts, 5/5.

#### Dónde está en el código
`CONVERSACION_51`, `HECHOS_51` (palabras clave para verificar), `CASE_FACTS_51`, `PEDIDO_COMPLETO_51`,
`CAMPOS_REEMBOLSO_51`, `demo_5_1_parte_a()` y `demo_5_1_parte_b()`.

#### Experimentos
- Corre la parte A varias veces: el resumen pierde datos distintos cada vez.
- Cambia el system prompt del resumen a "Resume en 1 línea": pierde más.
- `D51_PARTE = "C"` con `D51_POSICION_DATO = "medio"` o `"arriba"`: lost in the middle con un expediente largo.

#### Lo que pregunta el examen
- Los resúmenes progresivos pierden valores numéricos, fechas y expectativas del cliente → bloque persistente de "case facts".
- Recorta los resultados de tools a los campos relevantes antes de que se acumulen.
- Lo clave al inicio, con encabezados claros, por el efecto *lost in the middle*.
- Los subagentes devuelven metadatos estructurados (fechas, fuentes) y no solo prosa.
"""


# =====================================================================
#  DEMO 5.1 · MANEJO DE LA VENTANA DE CONTEXTO
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D51_PARTE = "ambas"        # "A" (resumen vs case facts), "B" (recortar resultados de tools), "C" (lost in the middle) o "ambas" (A y B)
D51_MODO = "ambos"         # parte A: "resumen", "case_facts" o "ambos"
D51_POSICION_DATO = "arriba"   # parte C: "arriba" (con encabezado DATOS CLAVE) o "medio" (enterrado entre notas)
# ------------------------------------------------------------------------

CONVERSACION_51 = [
    ("user", "Hola, mi vajilla del pedido #12346 llegó rota. Pagué $12,500."),
    ("assistant", "Lamento mucho lo ocurrido. ¿Me compartes una foto del daño?"),
    ("user", "Ya la mandé por WhatsApp, prefiero que me contacten por ahí, no por correo."),
    ("assistant", "Perfecto, anotado que prefieres WhatsApp. Veo la foto, el daño es claro."),
    ("user", "¿Y entonces qué sigue?"),
    ("assistant", "Te puedo ofrecer $500 de crédito en tienda mientras revisamos."),
    ("user", "No, no quiero crédito, quiero mi dinero de vuelta."),
    ("assistant", "Entendido, nada de crédito. Como el monto pasa de $10,000, lo debe aprobar un supervisor."),
    ("user", "¿Y cuándo me responden?"),
    ("assistant", "El supervisor te contacta a más tardar el viernes 20 de noviembre."),
    ("user", "Ok. Por cierto, también quiero cambiar mi dirección de envío para futuros pedidos."),
    ("assistant", "Claro, eso lo vemos aparte. ¿Algo más sobre la vajilla?"),
    ("user", "No, solo que no se les olvide nada de lo que ya hablamos."),
]

HECHOS_51 = {
    "pedido #12346": ["12346"],
    "monto $12,500": ["12,500", "12500"],
    "rechazó el crédito": ["crédito", "credito"],
    "prefiere WhatsApp": ["whatsapp"],
    "fecha: viernes 20 de noviembre": ["20 de noviembre", "viernes 20"],
}

CASE_FACTS_51 = """CASE FACTS (se copian tal cual, nunca se resumen):
- Cliente: Juan Pérez · Pedido: #12346 · Monto pagado: $12,500 MXN
- Problema: vajilla rota, foto recibida por WhatsApp
- Canal preferido: WhatsApp (NO correo)
- Oferta rechazada: $500 de crédito en tienda → quiere reembolso en dinero
- Estado: requiere aprobación de supervisor (monto > $10,000)
- Compromiso: el supervisor contacta a más tardar el viernes 20 de noviembre
- Pendiente aparte: cambio de dirección para futuros pedidos"""

PEDIDO_COMPLETO_51 = {
    "order_id": "#12346", "customer_id": "C-002", "status": "delivered", "total": 12500, "currency": "MXN",
    "created_at": "2026-10-30T14:22:05Z", "updated_at": "2026-11-02T09:10:44Z", "channel": "web", "device": "iPhone",
    "utm_source": "instagram", "utm_campaign": "dia-de-muertos", "warehouse": "TIJ-02", "picker_id": "P-8812",
    "packer_id": "K-1203", "box_size": "XL", "weight_kg": 6.4, "carrier": "Estafeta", "tracking": "EST-55102",
    "shipping_cost": 289, "insurance": True, "gift_wrap": False, "coupon": None, "tax": 1724.14,
    "payment_method": "card", "card_brand": "visa", "card_last4": "4242", "fraud_score": 0.03,
    "items": [{"sku": "DIN-CLY-24", "name": "Vajilla de barro 24 piezas", "qty": 1, "price": 12500}],
    "notes_internal": "Cliente frecuente. Empaque reforzado solicitado.", "returns_allowed_until": "2026-11-29",
}
CAMPOS_REEMBOLSO_51 = ["order_id", "status", "total", "items", "returns_allowed_until"]


def demo_5_1_parte_a():
    paso("Parte A · Resumen progresivo vs bloque de 'case facts'")
    historial = "\n".join(f"{'Cliente' if r == 'user' else 'Agente'}: {t}" for r, t in CONVERSACION_51)
    consola.print(Panel(escape(historial), title="Conversación larga (13 mensajes)", border_style="blue"))
    pregunta = ("Retoma el caso. Dime exactamente: número de pedido, monto, qué oferta ya rechazó el cliente, "
                "por qué canal contactarlo y qué fecha se le prometió.")
    modos = ["resumen", "case_facts"] if D51_MODO == "ambos" else [D51_MODO]
    resultados = {}
    for modo in modos:
        consola.print(f"\n[bold cyan]  ── {modo} ──[/]")
        if modo == "resumen":
            resp = llamar_claude("comprimir historial", system="Resume la conversación en 2 líneas.",
                                 messages=[{"role": "user", "content": historial}], max_tokens=200)
            contexto = "Resumen de la conversación anterior: " + texto_de(resp)
            nota("Así se comprime el historial cuando la conversación crece: un resumen corto.")
        else:
            contexto = CASE_FACTS_51 + "\n\nResumen breve: cliente pide reembolso por vajilla rota, en espera de supervisor."
            nota("Los datos clave viven en un bloque aparte que se copia completo en cada turno.")
        consola.print(Panel(escape(contexto), title="Lo único que ve el agente que retoma el caso", border_style="magenta"))
        resp = llamar_claude(f"retomar ({modo})", system="Eres el agente de soporte de La Tiendita.",
                             messages=[{"role": "user", "content": f"{contexto}\n\n{pregunta}"}], max_tokens=300)
        respuesta = texto_de(resp)
        resultados[modo] = {h: contiene(respuesta, *claves) for h, claves in HECHOS_51.items()}
    tabla = Table(title="¿Conservó los datos exactos?")
    tabla.add_column("Dato")
    for modo in modos:
        tabla.add_column(modo)
    for h in HECHOS_51:
        tabla.add_row(h, *["[green]✔[/]" if resultados[m][h] else "[red]✘[/]" for m in modos])
    tabla.add_row("[bold]Total[/]", *[f"[bold]{sum(resultados[m].values())}/{len(HECHOS_51)}[/]" for m in modos])
    consola.print(tabla)
    if len(modos) > 1:
        visual.registrar_resultado(parte="A", final="comparacion", texto=" · ".join(
            f"{m}: {sum(resultados[m].values())}/{len(HECHOS_51)} datos" for m in modos))
    if len(modos) == 1:
        conservados = sum(resultados[modos[0]].values())
        visual.registrar_resultado(parte="A", final="conserva" if conservados == len(HECHOS_51) else "pierde",
                                   texto=f"Datos exactos conservados: {conservados}/{len(HECHOS_51)}")


NOTAS_RELLENO_51 = [
    "Nota de turno: el cliente {n} preguntó por el horario de la tienda física; se le dio el de lunes a sábado.",
    "Nota de turno: se revisó el inventario de manteles; el código de lote del proveedor es AUT-{c}.",
    "Nota de turno: un cliente pidió factura del pedido #{p}; se le envió por correo.",
    "Nota de turno: se actualizó la foto del producto {n} en la tienda en línea.",
]


def documento_51(posicion: str) -> str:
    """Un expediente largo con un dato clave (código de autorización) arriba con encabezado o enterrado a la mitad."""
    notas = [NOTAS_RELLENO_51[i % 4].format(n=100 + i, c=7700 + (i * 37) % 300, p=12300 + (i * 7) % 90) for i in range(600)]
    # Distractores: otras notas del MISMO pedido con códigos parecidos que NO son la autorización vigente
    distractores = [
        "Nota de turno: se pidió autorización para el reembolso del pedido #12346 (solicitud AUT-7791, pendiente).",
        "Nota de turno: la paquetería abrió el reporte AUT-7716 por la vajilla rota del pedido #12346.",
        "Nota de turno: el reembolso del pedido #12364 se autorizó con el código AUT-7179.",
    ]
    for k, d in enumerate(distractores):
        notas.insert(80 + k * 190, d)
    clave = "Nota de turno: el supervisor aprobó el reembolso del pedido #12346; el código de autorización es AUT-7719."
    if posicion == "arriba":
        return ("DATOS CLAVE\n- Código de autorización (vigente) del reembolso #12346: AUT-7719\n\nNOTAS DEL TURNO\n"
                + "\n".join(notas))
    notas.insert(len(notas) // 2, clave)
    return "NOTAS DEL TURNO\n" + "\n".join(notas)


def demo_5_1_parte_c():
    paso(f"Parte C · Lost in the middle: el dato clave {'arriba, con encabezado' if D51_POSICION_DATO == 'arriba' else 'a la mitad'}")
    doc = documento_51(D51_POSICION_DATO)
    nota(f"Expediente de {len(doc.splitlines())} líneas con muchos códigos parecidos (AUT-77xx). El que importa es AUT-7719.")
    resp = llamar_claude("buscar el dato clave", system="Eres el agente de soporte de La Tiendita.",
                         messages=[{"role": "user", "content": doc + "\n\n¿Cuál es el código de autorización del reembolso del "
                                    "pedido #12346? Responde solo el código."}], max_tokens=200)
    respuesta = texto_de(resp)
    hallado = "AUT-7719" in respuesta
    (ok if hallado else alerta)(f"Respondió: {respuesta.strip()[:80]}  ({'correcto' if hallado else 'incorrecto'})")
    nota("Los modelos actuales fallan menos en esto, pero el patrón del examen sigue: lo importante va al inicio o al "
         "final, con encabezados, no enterrado en medio de un contexto largo.")
    visual.registrar_resultado(parte="C", final="encuentra" if hallado else "se_pierde",
                               texto=f"Dato {D51_POSICION_DATO}: {'lo encontró' if hallado else 'no lo encontró'}")


def demo_5_1_parte_b():
    paso("Parte B · Recortar los resultados de las tools antes de guardarlos en el contexto")
    completo = json.dumps(PEDIDO_COMPLETO_51, ensure_ascii=False)
    recortado = json.dumps({k: PEDIDO_COMPLETO_51[k] for k in CAMPOS_REEMBOLSO_51}, ensure_ascii=False)
    c = cliente()
    filas = []
    for etiqueta, contenido in ((f"completo ({len(PEDIDO_COMPLETO_51)} campos)", completo), ("recortado (5 campos)", recortado)):
        conteo = c.messages.count_tokens(model=MODELO, messages=[{"role": "user", "content": contenido}])
        filas.append([etiqueta, conteo.input_tokens, recortar(contenido, 90)])
    tabla_simple("Mismo pedido, distinto tamaño (count_tokens no tiene costo)", ["Versión", "Tokens", "Contenido"], filas)
    nota(f"Para un reembolso solo importan: {', '.join(CAMPOS_REEMBOLSO_51)}. El resto ocupa contexto en CADA turno.")
    visual.registrar_resultado(parte="B", final="recorta", texto=f"Tokens: {filas[0][1]} completo contra {filas[1][1]} recortado")


def demo_5_1():
    titulo("DEMO 5.1 · Ventana de contexto: qué se pierde y cómo evitarlo")
    mostrar_guia("5.1")
    concepto(
        "En conversaciones largas el historial se comprime con resúmenes… y los resúmenes pierden lo exacto: montos, "
        "fechas, números de pedido, lo que el cliente ya rechazó.\n"
        "Patrón: un bloque de 'case facts' con los datos transaccionales que se copia completo en cada turno.\n"
        "También: recorta los resultados de tools a los campos relevantes, y pon lo importante al inicio o al final "
        "(el modelo atiende peor lo que queda en medio: 'lost in the middle')."
    )
    if D51_PARTE in ("A", "ambas"):
        demo_5_1_parte_a()
    if D51_PARTE in ("B", "ambas"):
        demo_5_1_parte_b()
    if D51_PARTE == "C":
        demo_5_1_parte_c()
    concepto("Corre la parte A varias veces: el resumen pierde datos distintos cada vez. Los case facts no dependen "
             "de lo que el resumen decida conservar.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 5.2  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio5.py guia 5.2)
# ---------------------------------------------------------------------
GUIA_5_2 = """
#### De qué trata
**Cuándo escalar a una persona.** Los disparadores correctos son tres:
1. El cliente **pide** explícitamente una persona → escala de inmediato, sin intentar resolver primero.
2. La **política no cubre** el caso (aquí: igualar precios de otra tienda).
3. **No puedes avanzar** después de intentarlo.

Disparadores malos, que el examen pone como distractores:
- el **sentimiento** por sí solo (un cliente molesto con un problema simple se atiende, no se escala);
- la **confianza** que el modelo dice tener sobre sí mismo.

**Ambigüedad:** si la búsqueda devuelve **varios clientes** posibles, se pide un dato más; nunca se elige con una heurística.

#### Qué pasa al correrla, paso a paso
Cinco escenarios, cada uno con su acción correcta:

| Escenario | Mensaje | Correcto |
|---|---|---|
| `pide_humano` | "Quiero hablar con una persona…" | escaló |
| `molesto_simple` | "¡¡Estoy furioso!! #12347 en tránsito hace 2 días" | resolvió (con `lookup_order`) |
| `cliente_ambiguo` | "Soy Juan Pérez, quiero mi reembolso" | pidió aclaración (hay 2 Juan Pérez) |
| `fuera_de_politica` | "Iguálenme el precio de Amazon" | escaló |
| `insiste` | El agente ya ofreció resolver y el cliente responde "Quiero que me atienda una persona" | escaló |

Se corren todos con el system prompt **vago** y luego con el de **criterios** (`D52_MODO = "ambos"`). Con
`"criterios_ejemplos"` se agregan ejemplos de cuándo escalar y cuándo resolver; `"todos"` corre los tres. Verás cada tool llamada, la respuesta
final y la acción detectada. La tabla final compara contra lo correcto.

#### Dónde está en el código
`ESCENARIOS_52`, `SISTEMA_VAGO_52`, `SISTEMA_CRITERIOS_52`, `TOOLS_52`, `_ejecutar_52()` (simula las tools;
`get_customer` con "juan" devuelve 2 coincidencias) y `_correr_52()`.

La acción se detecta así: si llamó `escalar_a_humano` → escaló; si la respuesta final tiene "?" → pidió aclaración;
si no → resolvió. Es una heurística, así que lee las respuestas.

#### Experimentos
- Quita del prompt de criterios la línea *"NO escales solo porque el cliente esté molesto"*.
- Agrega un escenario: cliente que pide una persona pero cuyo problema es trivial. Lo correcto sigue siendo escalar.
- `D52_MODO = "todos"`: compara vago, criterios y criterios + ejemplos (la respuesta típica del examen).

#### Lo que pregunta el examen
- Pide una persona → escala de inmediato.
- Política ambigua o silenciosa sobre el caso → escala.
- Varias coincidencias → pide identificadores adicionales.
- El sentimiento y la autoevaluación de confianza no son buenos indicadores de complejidad.
"""


# =====================================================================
#  DEMO 5.2 · ESCALAMIENTO Y AMBIGÜEDAD
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D52_MODO = "ambos"        # "vago", "criterios", "criterios_ejemplos", "ambos" (vago + criterios) o "todos"
# ------------------------------------------------------------------------

ESCENARIOS_52 = {
    "pide_humano": ("Quiero hablar con una persona, no con un bot. Ya.", "escaló"),
    "molesto_simple": ("¡¡Estoy furioso!! Mi pedido #12347 dice 'en tránsito' desde hace 2 días. ¿Dónde va?", "resolvió"),
    "cliente_ambiguo": ("Soy Juan Pérez, quiero el reembolso de mi pedido.", "pidió aclaración"),
    "fuera_de_politica": ("Quiero que me igualen el precio de Amazon, allá está 30% más barato.", "escaló"),
    # Conversación de 3 mensajes: el agente ya ofreció resolver y el cliente insiste en una persona
    "insiste": ([{"role": "user", "content": "Mi pedido #12347 no llega."},
                 {"role": "assistant", "content": "Lo revisé: va en tránsito y llega mañana. ¿Te ayudo con algo más?"},
                 {"role": "user", "content": "No me sirve. Quiero que me atienda una persona, por favor."}], "escaló"),
}

SISTEMA_VAGO_52 = "Eres el agente de soporte de La Tiendita. Escala a un humano cuando sea necesario."
SISTEMA_CRITERIOS_52 = """Eres el agente de soporte de La Tiendita.
Escala con escalar_a_humano SOLO si:
1. El cliente pide explícitamente hablar con una persona → escala de inmediato, sin intentar resolver primero.
2. La política no cubre el caso (por ejemplo, igualar precios de otras tiendas: NO existe esa política).
3. No puedes avanzar después de intentarlo.
NO escales solo porque el cliente esté molesto: si el problema es simple, resuélvelo.
Si una búsqueda devuelve VARIOS clientes posibles, pide un dato más (email o número de pedido); nunca elijas uno."""

# Criterios + ejemplos (few-shot) de cuándo escalar y cuándo resolver: la respuesta típica del examen
EJEMPLOS_52 = """
Ejemplos:
- "¡Estoy harto! ¿Dónde está mi pedido #12001?" → NO escales: busca el pedido y contesta. Molesto no es complejo.
- "Pásame con alguien de verdad." → Escala de inmediato, aunque puedas resolverlo.
- Ya le diste la solución y responde "Aun así quiero hablar con una persona" → Escala: lo pidió explícitamente.
- "¿Me hacen 50% de descuento si compro dos?" → Escala: la política no cubre descuentos especiales.
- "Soy María, quiero mi factura" y hay dos Marías → Pregunta el email o el número de pedido; no escales ni elijas."""
SISTEMA_CRITERIOS_EJEMPLOS_52 = SISTEMA_CRITERIOS_52 + "\n" + EJEMPLOS_52

TOOLS_52 = [
    {"name": "get_customer", "description": "Busca clientes por nombre o email. Puede devolver varios.",
     "input_schema": {"type": "object", "properties": {"consulta": {"type": "string"}}, "required": ["consulta"]}},
    {"name": "lookup_order", "description": "Estado de un pedido por número #NNNNN.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "escalar_a_humano", "description": "Transfiere el caso a una persona con un resumen.",
     "input_schema": {"type": "object", "properties": {"motivo": {"type": "string"}, "resumen": {"type": "string"}},
                      "required": ["motivo", "resumen"]}},
]


def _ejecutar_52(nombre: str, entrada: dict) -> str:
    if nombre == "get_customer":
        if "juan" in json.dumps(entrada, ensure_ascii=False).lower():
            return json.dumps({"coincidencias": [{"id": "C-002", "nombre": "Juan Pérez", "email": "juan@ejemplo.com"},
                                                  {"id": "C-003", "nombre": "Juan Pérez", "email": "jperez@ejemplo.com"}]},
                              ensure_ascii=False)
        return json.dumps({"coincidencias": [{"id": "C-001", "nombre": "Ana López"}]}, ensure_ascii=False)
    if nombre == "lookup_order":
        return json.dumps({"order_id": "#12347", "estado": "en tránsito", "ultima_actualizacion": "hace 2 días",
                           "entrega_estimada": "mañana"}, ensure_ascii=False)
    return json.dumps({"ok": True, "ticket": "HUM-0077"})


def _correr_52(sistema: str, mensaje) -> tuple[str, list[str], str]:
    mensajes = list(mensaje) if isinstance(mensaje, list) else [{"role": "user", "content": mensaje}]
    usadas = []
    for _ in range(5):
        resp = llamar_claude("escenario", silencioso=True, system=sistema, tools=TOOLS_52, messages=mensajes, max_tokens=500)
        mensajes.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        resultados = []
        for b in resp.content:
            if b.type == "tool_use":
                usadas.append(b.name)
                salida = _ejecutar_52(b.name, b.input)
                nota(f"   {b.name}({json.dumps(b.input, ensure_ascii=False)}) → {recortar(salida, 120)}")
                resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": salida})
        mensajes.append({"role": "user", "content": resultados})
    final = texto_de(resp)
    if "escalar_a_humano" in usadas:
        accion = "escaló"
    elif "?" in final:
        accion = "pidió aclaración"
    else:
        accion = "resolvió"
    return accion, usadas, final


def demo_5_2():
    titulo("DEMO 5.2 · Escalamiento: cuándo pasar a una persona")
    mostrar_guia("5.2")
    concepto(
        "Escala cuando: (1) el cliente lo pide explícitamente, (2) la política no cubre el caso, (3) no puedes avanzar.\n"
        "NO son buenos disparadores: el sentimiento por sí solo, ni la 'confianza' que el modelo dice tener.\n"
        "Ambigüedad: si hay varios clientes posibles, pide un dato más; nunca elijas con una heurística."
    )
    modos = {"ambos": ["vago", "criterios"], "todos": ["vago", "criterios", "criterios_ejemplos"]}.get(D52_MODO, [D52_MODO])
    visual.diagrama_seguro(visual.tarjeta_tal_cual, "Demo 5.2 · Los system prompts tal cual",
        [("❌ Vago", "#ff9b9b"), ("✅ Criterios", "#8fe0a0"), ("✅ Criterios + ejemplos", "#7fd7ff")],
        [(None, [SISTEMA_VAGO_52, SISTEMA_CRITERIOS_52, EJEMPLOS_52.strip() + "\n\n(+ los criterios de la columna anterior)"])],
        "Mismos escenarios, mismas tools y mismo modelo: solo cambia el system prompt. La tercera columna agrega ejemplos "
        "de cuándo escalar y cuándo resolver a los mismos criterios.",
        "«Cuando sea necesario» deja que el tono del cliente decida. Los criterios dan los 3 motivos válidos (pide una persona, "
        "la política no cubre, no avanza) y dicen qué NO es motivo: el enojo. Los ejemplos muestran los casos frontera.")
    resultados = {}
    for modo in modos:
        sistema = {"vago": SISTEMA_VAGO_52, "criterios": SISTEMA_CRITERIOS_52}.get(modo, SISTEMA_CRITERIOS_EJEMPLOS_52)
        paso(f"System prompt {modo.upper()}")
        consola.print(Panel(escape(sistema), border_style="magenta"))
        resultados[modo] = {}
        for nombre, (mensaje, _) in ESCENARIOS_52.items():
            visible = mensaje[-1]["content"] + " (después de que el agente ya ofreció resolver)" if isinstance(mensaje, list) else mensaje
            consola.print(f"\n[bold]🗣  [{nombre}] {escape(visible)}[/]")
            accion, usadas, final = _correr_52(sistema, mensaje)
            consola.print(Panel(escape(final or "(sin texto)"), title=f"Acción: {accion}", border_style="green"))
            resultados[modo][nombre] = accion
    tabla = Table(title="¿Hizo lo correcto?", show_lines=True)
    tabla.add_column("Escenario"); tabla.add_column("Esperado", style="cyan")
    for modo in modos:
        tabla.add_column(modo)
    for nombre, (_, esperado) in ESCENARIOS_52.items():
        tabla.add_row(nombre, esperado, *[("[green]" if resultados[m][nombre] == esperado else "[red]") +
                                          resultados[m][nombre] + "[/]" for m in modos])
    consola.print(tabla)
    if len(modos) > 1:
        visual.registrar_resultado(final="comparacion", texto=" · ".join(f"{m}: {sum(1 for nombre, (_, esperado) in ESCENARIOS_52.items() if resultados[m][nombre] == esperado)}/{len(ESCENARIOS_52)}" for m in modos))
    if len(modos) == 1:
        bien = sum(1 for nombre, (_, esperado) in ESCENARIOS_52.items() if resultados[modos[0]][nombre] == esperado)
        visual.registrar_resultado(final="escala_bien" if bien == len(ESCENARIOS_52) else "escala_mal",
                                   texto=f"Hizo lo correcto en {bien}/{len(ESCENARIOS_52)} escenarios")
    concepto("Fíjate en 'molesto_simple' (no hay que escalar solo por el enojo) y 'cliente_ambiguo' (no debe elegir "
             "a uno de los dos Juan Pérez). La acción se detecta por heurística: lee las respuestas.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 5.3  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio5.py guia 5.3)
# ---------------------------------------------------------------------
GUIA_5_3 = """
#### De qué trata
Qué pasa cuando **un subagente falla** en un sistema multiagente. El coordinator necesita contexto para decidir:
**tipo de falla, qué se intentó, resultados parciales y alternativas.**

Los antipatrones:
1. **Suprimir el error**: devolver "sin datos relevantes" como éxito. El reporte se ve completo, pero no lo está.
2. **Error genérico**: "Error", sin nada con qué decidir.
3. **Tirar todo el flujo** por una sola falla.

La síntesis debe **anotar los huecos**: "sección envíos: incompleta por falla de la fuente".

#### Qué pasa al correrla, paso a paso
1. El coordinator llama la tool `delegar` 3 veces: `inventario`, `envios` y `resenas`.
2. `inventario` y `resenas` responden bien. `envios` **falla**, y cómo lo reporta depende del formato:
   - **`silencioso`**: `"Sin datos relevantes para esta área."` con `is_error: false`;
   - **`generico`**: `"Error"` con `is_error: true`;
   - **`estructurado`**: JSON con `tipo_falla: timeout`, `consulta_intentada`, `resultados_parciales` (3 de 12
     estados: 4.1 días) y `alternativas`.
3. El coordinator escribe el reporte final (panel verde).
4. Con `D53_COMPARAR_TODOS = True` se corren los 3 formatos. Tabla: ¿marca el hueco?, ¿usa el resultado parcial?

Qué esperar: en `silencioso`, el reporte suele omitir envíos o tratarlo como "sin novedad". En `estructurado`,
menciona la falla, usa el 4.1 como dato parcial y sugiere la alternativa.

#### Dónde está en el código
`RESULTADOS_OK_53`, `FALLAS_53` (los 3 formatos), `TOOL_DELEGAR_53` y `_correr_53()`, que enruta cada área a su resultado.

#### Experimentos
- `D53_COMPARAR_TODOS = False` y elige un `D53_FORMATO` para verlo solo.
- Haz que fallen dos áreas en vez de una: ¿el reporte sigue siendo útil?
- `D53_FORMATO = "abortar"` (con `D53_COMPARAR_TODOS = False`): una sola falla detiene todo y no hay reporte.

#### Lo que pregunta el examen
- Contexto de error estructurado (tipo, consulta, parciales, alternativas) para que el coordinator decida.
- Distinguir una falla de acceso de un resultado vacío válido (como la demo 2.2).
- Los subagentes recuperan localmente lo transitorio y solo propagan lo que no pudieron resolver.
- Reportes con anotaciones de cobertura: qué está bien respaldado y qué tiene huecos.
"""


# =====================================================================
#  DEMO 5.3 · PROPAGACIÓN DE ERRORES EN SISTEMAS MULTIAGENTE
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# Cómo reporta su falla el subagente de "envios":
#   "silencioso"   → devuelve "sin datos relevantes" como si todo estuviera bien
#   "generico"     → "Error"
#   "estructurado" → tipo de falla, qué intentó, resultados parciales y alternativas
#   "abortar"      → tu código detiene TODO el pipeline en cuanto un subagente falla
D53_FORMATO = "estructurado"
D53_COMPARAR_TODOS = True     # True: corre los 3 formatos y compara
# ------------------------------------------------------------------------

RESULTADOS_OK_53 = {
    "inventario": "Stock suficiente para temporada: 120 tazas, 45 manteles, 8 vajillas. Riesgo: vajillas.",
    "resenas": "Satisfacción 4.3/5. Queja más común: tiempos de envío (38% de las quejas).",
}

FALLAS_53 = {
    "silencioso": ("Sin datos relevantes para esta área.", False),
    "generico": ("Error", True),
    "estructurado": (json.dumps({
        "tipo_falla": "timeout", "fuente": "API de la paquetería", "consulta_intentada": "tiempos de entrega oct-nov 2026",
        "resultados_parciales": "Solo 3 de 12 estados respondieron: promedio 4.1 días en esos 3.",
        "alternativas": ["Reintentar en 1 hora", "Usar el reporte mensual de la paquetería (septiembre)"],
    }, ensure_ascii=False), True),
}

TOOL_DELEGAR_53 = {
    "name": "delegar",
    "description": "Encarga un área a un subagente de investigación.",
    "input_schema": {"type": "object", "properties": {"area": {"type": "string", "enum": ["inventario", "envios", "resenas"]}},
                     "required": ["area"]},
}


def _correr_53(formato: str) -> str:
    sistema = ("Eres el coordinador. Para preparar el reporte de temporada de La Tiendita, llama delegar UNA vez por "
               "cada área (inventario, envios, resenas), todas en la misma respuesta. Luego escribe un reporte de máximo "
               "8 líneas con una sección por área.")
    mensajes = [{"role": "user", "content": "Prepara el reporte de temporada."}]
    for _ in range(3):
        resp = llamar_claude(f"coordinator ({formato})", silencioso=True, system=sistema, tools=[TOOL_DELEGAR_53],
                             messages=mensajes, max_tokens=900)
        mensajes.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            break
        resultados = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            area = b.input.get("area", "")
            if area == "envios" and formato == "abortar":
                alerta("Falló el subagente de envíos → el código detiene TODO el pipeline. No hay reporte.")
                consola.print(Panel("(sin reporte: el pipeline se detuvo por una sola falla)", title="Reporte final (abortar)",
                                    border_style="red"))
                return ""
            if area == "envios":
                contenido, es_error = FALLAS_53[formato]
            else:
                contenido, es_error = RESULTADOS_OK_53.get(area, "Área desconocida."), False
            consola.print(Panel(escape(contenido), title=f"subagente '{area}' → is_error={es_error}",
                                border_style="red" if es_error else "cyan"))
            resultados.append({"type": "tool_result", "tool_use_id": b.id, "content": contenido, "is_error": es_error})
        mensajes.append({"role": "user", "content": resultados})
    reporte = texto_de(resp)
    consola.print(Panel(escape(reporte or "(sin texto)"), title=f"Reporte final ({formato})", border_style="green"))
    return reporte


def demo_5_3():
    titulo("DEMO 5.3 · Propagación de errores: que el coordinator sepa qué falló")
    mostrar_guia("5.3")
    concepto(
        "Cuando un subagente falla, el coordinator necesita contexto para decidir: tipo de falla, qué se intentó, "
        "resultados parciales y alternativas.\n"
        "Antipatrones: (1) suprimir el error y devolver 'sin datos' como éxito → el reporte se ve completo pero no lo "
        "está; (2) 'Error' genérico → no hay con qué decidir; (3) tirar todo el flujo por una sola falla.\n"
        "La síntesis final debe anotar los huecos: 'sección envíos: incompleta por falla de la fuente'."
    )
    formatos = list(FALLAS_53) if D53_COMPARAR_TODOS else [D53_FORMATO]
    filas = []
    for formato in formatos:
        paso(f"Falla del subagente de envíos: {formato}")
        reporte = _correr_53(formato)
        marca_hueco = contiene(reporte, "incomplet", "no disponible", "falló", "falla", "timeout", "parcial",
                               "pendiente", "sin datos", "no se pudo", "no fue posible")
        filas.append([formato, "[green]sí[/]" if marca_hueco else "[red]no[/]",
                      "sí" if contiene(reporte, "4.1") else "no", escape(recortar(reporte, 120))])
    tabla_simple("¿El reporte avisa que falta información de envíos?",
                 ["Formato", "¿Marca el hueco?", "¿Usa el parcial (4.1 días)?", "Reporte (recortado)"], filas)
    if len(formatos) > 1:
        visual.registrar_resultado(final="comparacion", texto=" · ".join(f"{f[0]}: marca el hueco {f[1].replace('[green]', '').replace('[red]', '').replace('[/]', '')}" for f in filas))
    if len(formatos) == 1:
        if formatos[0] == "abortar":
            final = "sin_reporte"
        elif formatos[0] == "generico":
            final = "sin_info"
        else:
            final = "informa" if marca_hueco else "oculta"
        visual.registrar_resultado(final=final, texto=f"¿El reporte marca el hueco de envíos? {'sí' if marca_hueco else 'no'}")
    concepto("En 'silencioso' el reporte suele presentar envíos como si no hubiera nada que reportar (o lo omite). "
             "Con 'estructurado', el coordinator puede usar el resultado parcial y decir qué falta.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 5.4  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio5.py guia 5.4)
# ---------------------------------------------------------------------
GUIA_5_4 = """
#### De qué trata
En sesiones largas de exploración, el contexto se llena y el agente empieza a dar respuestas genéricas o
inconsistentes con lo que ya había encontrado: **degradación de contexto**. Patrones para evitarlo:
- **Scratchpad**: un archivo donde el agente anota los hallazgos clave y que lee después.
- **Subagentes** para explorar, que devuelven solo un resumen.
- **`/compact`** para resumir el historial en una sesión larga.
- **Sesión nueva + resumen** en lugar de arrastrar todo.

#### Qué pasa al correrla, paso a paso
Repo de prueba con 24 archivos (casi todos de relleno). Lo importante está en `src/envios/tarifas.ts`,
`src/envios/promociones.ts`, `src/checkout/total.ts` y `config/zonas.json`.

1. **Fase 1 · explorar**: *"¿Dónde se calcula el costo de envío y qué lo afecta?"*. Con `D54_USAR_SCRATCHPAD = True`,
   además debe escribir sus hallazgos en `NOTAS.md`. Al terminar se imprime `NOTAS.md`.
2. **Fase 2 · sesión NUEVA** (sin `resume`): *"Queremos envío gratis en compras mayores a $10,000. ¿Qué archivos
   tocarías?"*. Con `D54_COMPARAR = True` corre dos veces: **con notas** (empieza leyendo `NOTAS.md`) y **sin notas**
   (empieza de cero).
3. Tabla: turnos, llamadas a tools y costo de cada fase.

Qué esperar: "con notas" suele necesitar menos turnos y llamadas. En un repo de 24 archivos la diferencia es chica;
en uno real, de cientos, es grande.

#### Seguridad
Tools: `Read`, `Grep` y `Glob`, más `Write` solo en la fase 1. Un hook `PreToolUse` **bloquea** cualquier `Write` que
no sea `NOTAS.md`. Todo pasa en una carpeta temporal.

#### Dónde está en el código
`_repo_54()`, `_correr_fase_54()` (el hook y las opciones) y `demo_5_4()`.

#### Experimentos
- `D54_USAR_SCRATCHPAD = False`: no hay notas y la fase 2 siempre empieza de cero.
- Lee `NOTAS.md`: ¿anotó `promociones.ts` (donde está el `TODO` del umbral)? Si no, la fase 2 con notas puede fallar.
  Un scratchpad vale lo que vale su contenido.

#### Lo que pregunta el examen
- Degradación de contexto en sesiones largas → scratchpad, subagentes de exploración y `/compact`.
- Subagentes para investigar preguntas puntuales mientras el agente principal mantiene la coordinación.
- Al reanudar, resume los hallazgos clave en lugar de arrastrar todo el historial.
"""


# =====================================================================
#  DEMO 5.4 · EXPLORACIÓN DE CÓDIGO Y DEGRADACIÓN DE CONTEXTO
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
# True: en la fase 1 el agente anota sus hallazgos en NOTAS.md; la fase 2 (sesión nueva) los lee
# False: la fase 2 empieza de cero y tiene que volver a explorar
D54_USAR_SCRATCHPAD = True
D54_COMPARAR = True            # True: corre la fase 2 con y sin notas y compara
# ------------------------------------------------------------------------


def _repo_54() -> dict[str, str]:
    archivos = {
        "src/envios/tarifas.ts": "import zonas from '../../config/zonas.json';\nexport function tarifa(cp: string, peso: number) {\n  const zona = zonas[cp.slice(0, 2)] ?? 'resto';\n  return BASE[zona] + peso * 18;\n}\nconst BASE = { centro: 99, norte: 149, sur: 129, resto: 179 };\n",
        "src/envios/promociones.ts": "export function aplicaEnvioGratis(total: number, cupon?: string) {\n  if (cupon === 'ENVIOGRATIS') return true;\n  return false; // TODO: umbral por monto\n}\n",
        "src/checkout/total.ts": "import { tarifa } from '../envios/tarifas';\nimport { aplicaEnvioGratis } from '../envios/promociones';\nexport function totalFinal(subtotal: number, cp: string, peso: number, cupon?: string) {\n  const envio = aplicaEnvioGratis(subtotal, cupon) ? 0 : tarifa(cp, peso);\n  return subtotal + envio;\n}\n",
        "config/zonas.json": '{"01": "centro", "22": "norte", "64": "norte", "97": "sur"}\n',
        "tests/envios.test.ts": "import { tarifa } from '../src/envios/tarifas';\ntest('tarifa centro', () => expect(tarifa('01000', 1)).toBe(117));\n",
    }
    for i in range(1, 16):
        archivos[f"src/catalogo/producto_{i:02d}.ts"] = f"export const producto{i} = {{ sku: 'SKU-{i:02d}', precio: {100 + i * 37} }};\n"
    for nombre in ("usuarios", "pagos", "notificaciones", "reportes"):
        archivos[f"src/{nombre}/index.ts"] = f"// Módulo de {nombre}\nexport const {nombre} = {{}};\n"
    return archivos


def _correr_fase_54(proyecto: Path, prompt: str, herramientas: list[str], etiqueta: str):
    llamadas: list[str] = []

    async def hook(input_data, tool_use_id, context):
        llamadas.append(input_data.get("tool_name", "?"))
        if input_data.get("tool_name") == "Write":
            ruta = Path(input_data.get("tool_input", {}).get("file_path", ""))
            if ruta.name != "NOTAS.md":
                return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                               "permissionDecisionReason": "Solo puedes escribir NOTAS.md"}}
        return {}

    from claude_agent_sdk import HookMatcher
    opciones = opciones_base(
        cwd=str(proyecto), tools=herramientas, allowed_tools=herramientas, permission_mode="acceptEdits",
        system_prompt="Eres un asistente de código. Responde en español y breve.", max_turns=20,
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[hook])]},
    )
    resultado = asyncio.run(correr_agente(prompt, opciones, etiqueta))
    return resultado, llamadas


def demo_5_4():
    titulo("DEMO 5.4 · Exploración de código: notas para no empezar de cero")
    mostrar_guia("5.4")
    concepto(
        "En sesiones largas de exploración el contexto se llena y el agente empieza a dar respuestas genéricas o "
        "inconsistentes con lo que ya había encontrado (degradación de contexto).\n"
        "Patrones: (1) archivo scratchpad donde el agente anota hallazgos clave; (2) subagentes para explorar, que "
        "regresan solo un resumen; (3) /compact; (4) sesión nueva + resumen en lugar de arrastrar todo."
    )
    proyecto = crear_proyecto(_repo_54(), "tiendita_repo_")
    ok(f"Repo de prueba con {len(_repo_54())} archivos: {proyecto}")
    escribir = ["Write"] if D54_USAR_SCRATCHPAD else []
    paso("Fase 1 · Explorar")
    prompt1 = "¿Dónde se calcula el costo de envío y qué lo afecta? Explora el repo."
    if D54_USAR_SCRATCHPAD:
        prompt1 += " Al terminar, escribe en NOTAS.md tus hallazgos clave: archivos, funciones y cómo se conectan."
    r1, llamadas1 = _correr_fase_54(proyecto, prompt1, ["Read", "Grep", "Glob"] + escribir, "fase 1")
    if (proyecto / "NOTAS.md").exists():
        mostrar_archivo(proyecto, "NOTAS.md")

    prompt2_base = "Queremos envío gratis automático en compras mayores a $10,000. ¿Qué archivos y funciones tocarías?"
    variantes = []
    if D54_COMPARAR and (proyecto / "NOTAS.md").exists():
        variantes = [("con notas", "Lee NOTAS.md primero. " + prompt2_base), ("sin notas", prompt2_base)]
    elif (proyecto / "NOTAS.md").exists():
        variantes = [("con notas", "Lee NOTAS.md primero. " + prompt2_base)]
    else:
        variantes = [("sin notas", prompt2_base)]
    filas = [[idioma.salida("fase 1 (explorar)"), getattr(r1, "num_turns", "?"), len(llamadas1),
              f"${getattr(r1, 'total_cost_usd', 0) or 0:.4f}"]]
    for etiqueta, prompt2 in variantes:
        paso(f"Fase 2 · Sesión NUEVA ({etiqueta})")
        r2, llamadas2 = _correr_fase_54(proyecto, prompt2, ["Read", "Grep", "Glob"], f"fase 2 {etiqueta}")
        filas.append([idioma.salida(f"fase 2 ({etiqueta})"), getattr(r2, "num_turns", "?"), len(llamadas2),
                      f"${getattr(r2, 'total_cost_usd', 0) or 0:.4f}"])
    tabla_simple("Costo de cada fase", ["Fase", "Turnos", "Llamadas a tools", "Costo reportado"], filas)
    etiquetas = [e for e, _ in variantes]
    final = "comparacion" if len(etiquetas) > 1 else ("retoma" if etiquetas == ["con notas"] else "reexplora")
    visual.registrar_resultado(final=final, texto=" · ".join(f"{f[0]}: {f[1]} turnos, {f[2]} tools" for f in filas))
    concepto("Con notas, la fase 2 suele necesitar menos turnos: no vuelve a explorar lo que ya se sabía. En una "
             "exploración real (cientos de archivos) la diferencia es mucho mayor.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 5.5  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio5.py guia 5.5)
# ---------------------------------------------------------------------
GUIA_5_5 = """
#### De qué trata
Antes de quitar la revisión humana, hay que saber **dónde** falla el modelo:
- Un **97% global** puede esconder una categoría que falla mucho más.
- Mide la precisión **por tipo de documento** (y por campo).
- **Muestreo estratificado**: revisa una muestra de cada tipo, no solo del total.
- **Confianza por campo, calibrada** con datos etiquetados. El umbral se decide con evidencia, no "a ojo".

#### Qué pasa al correrla, paso a paso
1. Hay 44 documentos de 3 tipos, como en la vida real: muchos fáciles y pocos difíciles.
   - **factura** (24): el total aparece claro;
   - **ticket** (12): subtotal + IVA + total;
   - **nota** (8): escrita a mano y desordenada (*"3 tazas a 450 y un mantel de 890, ya le di 500"*), donde hay que
     calcular o interpretar. En 3 notas el total **no se puede saber** (*"¿o eran 85?"*, *"lo de siempre"*, un número
     borrado): lo correcto es `null`, no adivinar.
2. Para cada uno, Claude extrae el **total a cobrar hoy** y su **confianza** (`registrar_total` forzada).
3. Tabla documento por documento: correcto, extraído, confianza, destino (automático o humano según `D55_UMBRAL`) y ✔/✘.
4. Tabla por tipo: precisión, cuántos se aceptaron en automático y **cuántos errores se colaron**.
5. Tabla de muestreo: si una persona revisa solo `D55_MUESTRA` documentos (6), ¿qué tan probable es que vea un error
   de las notas? Al azar del total casi no salen notas; estratificado (2 de cada tipo) sí.
6. Tabla de calibración: para cada rango de confianza declarada, la precisión real.

Qué esperar: facturas y tickets al 100%; notas alrededor del 60%. El global sale arriba del 90% y esconde ese
problema: con la regla del global se cuelan los errores de las notas. Fíjate si hay errores con confianza alta: eso
significa que la confianza **no está calibrada**.

#### Dónde está en el código
`_documentos_55()` (los 44 documentos con su total correcto; `None` = no se puede saber), `TOOL_TOTAL_55` y `demo_5_5()`,
que arma las tablas (documentos, por tipo, muestreo y calibración).

#### Experimentos
- `D55_UMBRAL = 0.95`: van más documentos a revisión humana y se cuelan menos errores.
- Agrega más notas difíciles y mira cómo cambia la precisión de esa categoría.
- `D55_FACTURAS = 6`: con menos facturas el global baja y ya no "engaña" tanto: el volumen de lo fácil es lo que esconde la falla.
- `D55_DECISION = "global"`, `"umbral"` o `"por_tipo"` (default): compara cuántos errores se colarían con cada regla.

#### Lo que pregunta el examen
- La precisión agregada puede ocultar fallas por tipo de documento o por campo: valida por segmento antes de
  automatizar.
- Muestreo estratificado de los casos de alta confianza para detectar errores nuevos.
- Confianza por campo calibrada con un conjunto etiquetado para decidir qué va a revisión humana.
"""


# =====================================================================
#  DEMO 5.5 · REVISIÓN HUMANA Y CALIBRACIÓN DE CONFIANZA
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D55_UMBRAL = 0.8      # confianza mínima para aceptar automáticamente
# Cómo se decide qué va a revisión humana:
#   "por_tipo" → mide la precisión por tipo de documento; los tipos que fallan van SIEMPRE a revisión (lo correcto)
#   "global"   → si la precisión global es alta, se quita la revisión humana a todo
#   "umbral"   → se confía en la confianza que declara el modelo, sin calibrarla
D55_DECISION = "por_tipo"
D55_FACTURAS = 24     # facturas claras (fáciles): mucho volumen
D55_TICKETS = 12      # tickets con subtotal + IVA (fáciles)
D55_MUESTRA = 6       # cuántos documentos revisaría una persona (para la tabla de muestreo)
# ------------------------------------------------------------------------


def _documentos_55() -> list[tuple[str, str, float | None]]:
    """(tipo, texto, total correcto). Muchas facturas y tickets (fáciles) y pocas notas a mano (difíciles):
    así el global se ve alto aunque las notas fallen. None = el documento no permite saber el total (lo correcto es null)."""
    docs = []
    clientes = ["Ana López", "Café Luna", "Marta Ruiz", "Hotel Sol", "Juan Pérez", "Taller Mx", "Rosa Díaz", "Pan y Miel",
                "Luis Mora", "Flor de Oaxaca", "Eva Ríos", "La Cazuela"]
    for i in range(D55_FACTURAS):
        total = 450 + (i * 1373) % 15000
        docs.append(("factura", f"FACTURA F-{1001 + i}\nCliente: {clientes[i % len(clientes)]}\nTOTAL: ${total:,.2f} MXN", float(total)))
    for i in range(D55_TICKETS):
        total = 120 + (i * 977) % 4000
        subtotal = round(total / 1.16, 2)
        docs.append(("ticket", f"Ticket A-{70 + i}\nSubtotal {subtotal:,.2f}\nIVA {total - subtotal:,.2f}\nTotal {total:,.2f}", float(total)))
    notas = [
        ("le debo a doña Lupe 3 tazas a 450 y un mantel de 890, ya le di 500", 1740.0),
        ("total 1,250 (antes decía 1,520 pero lo taché)", 1250.0),
        ("cobrar 6 servilletas a 75... o eran 85? no me acuerdo, preguntarle", None),
        ("mitad ahorita (de 2000) y mitad la otra semana; hoy cobro", 1000.0),
        ("2 jarros de 180 c/u, más envío 99, menos el anticipo de 150", 359.0),
        ("lo de siempre de doña Lupe", None),
        ("son 4 platos de 250 pero devolvió 1 que llegó roto", 750.0),
        ("total 1 3 ? 0 (se corrió la tinta en el tercer número)", None),
    ]
    docs += [("nota", texto, total) for texto, total in notas]
    return docs


TOOL_TOTAL_55 = {
    "name": "registrar_total",
    "description": "Registra el monto a cobrar HOY según el documento.",
    "input_schema": {"type": "object", "properties": {
        "total": {"type": ["number", "null"], "description": "null si el documento no permite saber el total"},
        "confianza": {"type": "number", "description": "0 a 1: qué tan seguro estás del total"}},
        "required": ["total", "confianza"]},
}


def demo_5_5():
    titulo("DEMO 5.5 · Revisión humana: el promedio esconde dónde falla")
    mostrar_guia("5.5")
    concepto(
        "Un 97% de precisión global puede esconder una categoría que falla mucho más.\n"
        "  • Mide la precisión POR TIPO de documento (y por campo) antes de quitar la revisión humana.\n"
        "  • Muestreo estratificado: revisa una muestra de cada tipo, no solo del total.\n"
        "  • Pide confianza por campo y CALÍBRALA con datos etiquetados: decide el umbral con evidencia.\n"
        "  • Lo de baja confianza → cola de revisión humana."
    )
    docs = _documentos_55()
    filas, por_tipo = [], {}
    for tipo, texto, correcto in docs:
        resp = llamar_claude(tipo, silencioso=True, tools=[TOOL_TOTAL_55], tool_choice=tool_choice_forzado("registrar_total"),
                             messages=[{"role": "user", "content": texto}], max_tokens=200)
        datos = entrada_tool(resp)
        total, confianza = datos.get("total"), float(datos.get("confianza", 0) or 0)
        acierto = (total is None) if correcto is None else (total is not None and abs(float(total) - correcto) < 0.5)
        destino = "automático" if confianza >= D55_UMBRAL else "humano"   # (para "umbral"; se ajusta abajo)
        por_tipo.setdefault(tipo, []).append((acierto, confianza, destino))
        filas.append([tipo, escape(recortar(texto.replace("\n", " · "), 55)), "null" if correcto is None else correcto,
                      "null" if total is None else total,
                      f"{confianza:.2f}", destino, "[green]✔[/]" if acierto else "[red]✘[/]"])
    tabla_simple("Extracción documento por documento", ["Tipo", "Documento", "Correcto", "Extraído", "Confianza", "Destino", ""], filas)

    todos = [x for v in por_tipo.values() for x in v]
    global_ = sum(a for a, _, _ in todos) / len(todos)
    resumen = [["[bold]GLOBAL[/]", f"[bold]{global_:.0%}[/]", "", ""]]
    for tipo, v in por_tipo.items():
        auto = [a for a, _, d in v if d == "automático"]
        errores_auto = sum(1 for a in auto if not a)
        resumen.append([tipo, f"{sum(a for a, _, _ in v) / len(v):.0%}", f"{len(auto)}/{len(v)}", errores_auto])
    tabla_simple(f"Precisión por tipo (umbral de confianza {D55_UMBRAL})",
                 ["Tipo", "Precisión", "Aceptados en automático", "Errores que se colaron"], resumen)

    # La decisión: ¿qué errores se habrían colado sin que nadie los revisara?
    precision = {t: sum(a for a, _, _ in v) / len(v) for t, v in por_tipo.items()}
    if D55_DECISION == "global":
        colados = sum(1 for a, _, _ in todos if not a) if global_ >= 0.85 else 0
        regla = (idioma.salida(f"global {global_:.0%} ≥ 85% → sin revisión humana") if global_ >= 0.85
                 else idioma.salida(f"global {global_:.0%} < 85% → todo a revisión"))
        final = "global_engana" if colados else "global_ok"
    elif D55_DECISION == "umbral":
        colados = sum(1 for a, _, d in todos if not a and d == "automático")
        regla = idioma.salida(f"confianza ≥ {D55_UMBRAL} → automático, sin calibrar")
        final = "errores_pasan" if colados else "sin_errores"
    else:
        a_revision = [t for t, prec in precision.items() if prec < 0.95]
        colados = sum(1 for t, v in por_tipo.items() if t not in a_revision for a, _, d in v if not a and d == "automático")
        regla = idioma.salida(f"tipos con precisión < 95% siempre a revisión: {', '.join(a_revision) or 'ninguno'}")
        final = "por_tipo"
    (alerta if colados else ok)(f"Decisión ({D55_DECISION}): {regla} → errores que se colarían: {colados}")
    visual.registrar_resultado(final=final, texto=f"{regla} · errores que se colarían: {colados}")

    # Muestreo: si revisas solo una muestra, ¿qué tan probable es ver un error de las notas?
    errores_nota = sum(1 for a, _, _ in por_tipo.get("nota", []) if not a)
    n_total, n_notas, k = len(todos), len(por_tipo.get("nota", [])), D55_MUESTRA
    def prob_ver(n, errores, tomados):          # probabilidad de que la muestra traiga al menos un error
        return 1 - (math.comb(n - errores, tomados) / math.comb(n, tomados)) if errores and tomados <= n else 0.0
    por_estrato = max(1, k // max(1, len(por_tipo)))
    tabla_simple(f"Muestreo: revisas {k} documentos, ¿ves algún error de las notas? ({errores_nota} errores en {n_notas} notas)",
                 ["Cómo eliges la muestra", "Notas en la muestra", "Probabilidad de ver un error de las notas"],
                 [[idioma.salida(f"Al azar, {k} del total ({n_total} documentos)"), f"≈ {k * n_notas / n_total:.1f}",
                   f"{prob_ver(n_total, errores_nota, k):.0%}"],
                  [idioma.salida(f"Estratificado: {por_estrato} de cada tipo"), str(por_estrato),
                   f"{prob_ver(n_notas, errores_nota, por_estrato):.0%}"]])

    calibracion = []
    for minimo, maximo in ((0, 0.5), (0.5, 0.8), (0.8, 0.95), (0.95, 1.01)):
        grupo = [a for a, c, _ in todos if minimo <= c < maximo]
        if grupo:
            calibracion.append([f"{minimo:.2f}–{min(maximo, 1):.2f}", len(grupo), f"{sum(grupo) / len(grupo):.0%}"])
    tabla_simple("Calibración: ¿la confianza dice la verdad?", ["Confianza declarada", "Documentos", "Precisión real"], calibracion)
    concepto("Si la fila 'nota' tiene precisión baja mientras el global se ve bien, quitar la revisión humana a todo "
             "sería un error. Mira también la calibración: si a confianza 0.95 la precisión real es baja, el umbral "
             "debe subir o esa categoría debe ir siempre a revisión.", "🧪 Experimenta")


# ---------------------------------------------------------------------
#  📖 GUÍA DE LA DEMO 5.6  (se imprime antes de correrla;
#     para leerla sola: python lab_dominio5.py guia 5.6)
# ---------------------------------------------------------------------
GUIA_5_6 = """
#### De qué trata
Al sintetizar varias fuentes se pierde fácilmente **de dónde sale cada dato**. *"El promedio es 3 días"*: ¿según
quién, de cuándo y con qué muestra? El patrón es que cada afirmación conserve **fuente, fecha y alcance**. Si dos
fuentes confiables **discrepan**, no se elige una en silencio: se reporta el conflicto con ambos valores y su contexto.

#### Qué pasa al correrla, paso a paso
1. Se imprimen 4 fuentes sobre el tiempo de entrega:
   - **SRC-A**: estudio interno de octubre 2026, 1,200 pedidos → 3.2 días;
   - **SRC-B**: encuesta de febrero 2025, 80 respuestas → 6 días;
   - **SRC-C**: paquetería, septiembre 2026, **solo zona centro** → 2.8 días;
   - **SRC-D**: blog sin fecha → menos de 2 días.
2. **`libre`**: respuesta en prosa de 2 líneas para la página de preguntas frecuentes (el paso típico donde se pierden las fuentes).
3. **`con_procedencia`**: `reportar_sintesis` forzada, con afirmaciones (fuente, fecha, alcance), conflictos
   (tema, valores, explicación posible) y conclusión.
4. Tabla: fuentes citadas, ¿señala el conflicto?, ¿nota que SRC-B es de 2025?, ¿nota que SRC-C es solo zona centro?

Qué esperar: en `libre`, un número único ("unos 3 días") sin decir de dónde sale. Con procedencia, el lector ve por
qué difieren los valores: fechas, muestras y zonas distintas.

#### Dónde está en el código
`FUENTES_56`, `TOOL_SINTESIS_56` y `demo_5_6()`. Las verificaciones son por palabras clave.

#### Experimentos
- Agrega una quinta fuente que contradiga a SRC-A con fecha reciente.
- Quita del system prompt *"no elijas una en silencio"* y compara.

#### Lo que pregunta el examen
- Conservar el mapeo afirmación → fuente a lo largo de la síntesis.
- Conflictos entre fuentes confiables: anotarlos con su atribución, no resolverlos arbitrariamente.
- Incluir fechas de publicación o de recolección para que los cambios en el tiempo no parezcan contradicciones.
- Distinguir hallazgos bien respaldados de los que tienen huecos o están en disputa.
"""


# =====================================================================
#  DEMO 5.6 · PROCEDENCIA Y SÍNTESIS DE VARIAS FUENTES
# =====================================================================
# 🔧 CAMBIA AQUÍ ---------------------------------------------------------
D56_MODO = "ambos"     # "libre" (resumen en prosa), "con_procedencia" o "ambos"
# ------------------------------------------------------------------------

FUENTES_56 = [
    {"id": "SRC-A", "fecha": "2026-10", "tipo": "estudio interno", "muestra": "1,200 pedidos",
     "texto": "El tiempo promedio de entrega en octubre 2026 fue de 3.2 días."},
    {"id": "SRC-B", "fecha": "2025-02", "tipo": "encuesta a clientes", "muestra": "80 respuestas",
     "texto": "Los clientes reportan que sus pedidos tardan en promedio 6 días."},
    {"id": "SRC-C", "fecha": "2026-09", "tipo": "reporte de la paquetería", "muestra": "solo zona centro",
     "texto": "Entrega promedio de 2.8 días en la zona centro."},
    {"id": "SRC-D", "fecha": "sin fecha", "tipo": "blog", "muestra": "desconocida",
     "texto": "La Tiendita entrega en menos de 2 días."},
]

TOOL_SINTESIS_56 = {
    "name": "reportar_sintesis",
    "description": "Síntesis con procedencia de cada afirmación.",
    "input_schema": {"type": "object", "properties": {
        "afirmaciones": {"type": "array", "items": {"type": "object", "properties": {
            "afirmacion": {"type": "string", "description": "claim: el dato que se afirma"},
            "fuente_id": {"type": "string", "description": "sourceUrl: de dónde sale (aquí, el id de la fuente)"},
            "documento": {"type": "string", "description": "documentName: tipo o nombre del documento"},
            "extracto": {"type": "string", "description": "excerpt: el texto exacto de la fuente que lo respalda"},
            "fecha": {"type": "string", "description": "publicationDate"},
            "alcance": {"type": "string", "description": "muestra, zona o limitación de la fuente"}},
            "required": ["afirmacion", "fuente_id", "documento", "extracto", "fecha", "alcance"]}},
        "conflictos": {"type": "array", "items": {"type": "object", "properties": {
            "tema": {"type": "string"}, "valores": {"type": "array", "items": {"type": "string"}},
            "explicacion_posible": {"type": "string"}}, "required": ["tema", "valores", "explicacion_posible"]}},
        "conclusion": {"type": "string"}},
        "required": ["afirmaciones", "conflictos", "conclusion"]},
}


def demo_5_6():
    titulo("DEMO 5.6 · Procedencia: de dónde sale cada dato (y qué hacer si las fuentes no coinciden)")
    mostrar_guia("5.6")
    concepto(
        "Al resumir varias fuentes se pierde fácilmente la atribución: 'el promedio es 3 días'… ¿según quién, de "
        "cuándo y con qué muestra?\n"
        "Patrón: cada afirmación conserva su fuente, fecha y alcance. Si dos fuentes confiables discrepan, NO elijas "
        "una en silencio: reporta el conflicto con ambos valores y su contexto (fechas distintas, muestras distintas)."
    )
    tabla_simple("Fuentes", ["ID", "Fecha", "Tipo", "Muestra", "Dice"],
                 [[f["id"], f["fecha"], f["tipo"], f["muestra"], f["texto"]] for f in FUENTES_56])
    contexto = "\n".join(f"[{f['id']}] ({f['fecha']}, {f['tipo']}, muestra: {f['muestra']}) {f['texto']}" for f in FUENTES_56)
    pregunta = "¿Cuánto tarda La Tiendita en entregar un pedido?"
    modos = ["libre", "con_procedencia"] if D56_MODO == "ambos" else [D56_MODO]
    filas = []
    for modo in modos:
        paso(f"Modo {modo}")
        if modo == "libre":
            resp = llamar_claude("síntesis libre", max_tokens=300,
                                 system="Contesta en 2 líneas, en lenguaje sencillo, para la página de preguntas frecuentes.",
                                 messages=[{"role": "user", "content": f"{contexto}\n\n{pregunta}"}])
            salida = texto_de(resp)
        else:
            resp = llamar_claude("síntesis con procedencia", max_tokens=1200, tools=[TOOL_SINTESIS_56],
                                 tool_choice=tool_choice_forzado("reportar_sintesis"),
                                 system="Conserva la fuente de cada dato. Si las fuentes discrepan, repórtalo como conflicto; no elijas una en silencio.",
                                 messages=[{"role": "user", "content": f"{contexto}\n\n{pregunta}"}])
            salida = json.dumps(entrada_tool(resp), ensure_ascii=False)
        citas = sum(1 for f in FUENTES_56 if f["id"] in salida)
        filas.append([modo, f"{citas}/4", "sí" if contiene(salida, "conflict", "discrep", "difieren", "no coinciden") else "no",
                      "sí" if contiene(salida, "2025") else "no", "sí" if contiene(salida, "centro") else "no"])
    tabla_simple("¿Conservó la procedencia?", ["Modo", "Fuentes citadas", "¿Señala el conflicto?",
                                                "¿Nota que SRC-B es de 2025?", "¿Nota que SRC-C es solo zona centro?"], filas)
    if len(modos) > 1:
        visual.registrar_resultado(final="comparacion", texto=" · ".join(f"{f[0]}: fuentes {f[1]}, conflicto {f[2]}" for f in filas))
    if len(modos) == 1:
        citas_ok = filas[0][1] == "4/4"
        visual.registrar_resultado(final="trazable" if citas_ok else "sin_fuente",
                                   texto=f"Fuentes citadas {filas[0][1]} · señala el conflicto: {filas[0][2]}")
    concepto("En 'libre' es común un número único ('unos 3 días') sin decir de dónde sale. Con procedencia, el lector "
             "ve que 6 días es una encuesta vieja de 80 clientes y que 2.8 es solo la zona centro.", "🧪 Experimenta")


# =====================================================================
#  MENÚ
# =====================================================================

GUIAS = {
    "5.1": GUIA_5_1,
    "5.2": GUIA_5_2,
    "5.3": GUIA_5_3,
    "5.4": GUIA_5_4,
    "5.5": GUIA_5_5,
    "5.6": GUIA_5_6,
}


DEMOS = {
    "5.1": ("Ventana de contexto: case facts y recorte", demo_5_1),
    "5.2": ("Escalamiento y ambigüedad", demo_5_2),
    "5.3": ("Propagación de errores multiagente", demo_5_3),
    "5.4": ("Exploración de código y scratchpad (Agent SDK)", demo_5_4),
    "5.5": ("Revisión humana y calibración de confianza", demo_5_5),
    "5.6": ("Procedencia y síntesis de varias fuentes", demo_5_6),
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
        tabla = Table(title="CCAR-F · Lab del Dominio 5")
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

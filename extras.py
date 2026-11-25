"""
Datos que usan el panel (panel.py) y las páginas HTML (visual.py), aparte del código de los labs:

- GLOSARIO: términos que se subrayan con su definición (y su nombre en inglés, como sale en el examen).
- EXTRAS: lo especial de cada demo en el panel: casos rápidos y lo esperado de cada caso (con su porqué),
  que alimentan el ticket de resultado.

Todas las demos tienen EXTRAS. Al final están CLASES (trampa de examen o limitación del producto)
y ESCENARIOS (los 6 escenarios del examen y qué demos los practican). Para cambiar un texto, búscalo por el número de la demo.
"""

import html
import re

import idioma

# término como aparece en el texto -> (nombre en inglés, explicación corta)
GLOSARIO = {
    "agentic loop": ("agentic loop", "El ciclo del agente: llamas a Claude, ejecutas las tools que pide, le devuelves los resultados y repites hasta que stop_reason sea end_turn."),
    "loop agéntico": ("agentic loop", "El ciclo del agente: llamas a Claude, ejecutas las tools que pide, le devuelves los resultados y repites hasta que stop_reason sea end_turn."),
    "stop_reason": ("stop reason", "Campo de cada respuesta que dice POR QUÉ Claude dejó de escribir: tool_use, end_turn, max_tokens…"),
    "end_turn": ("end turn", "stop_reason cuando Claude terminó de verdad. Es la señal normal para salir del loop."),
    "tool_use": ("tool use", "Bloque con el que Claude PIDE ejecutar una tool. También es el stop_reason cuando espera ese resultado para seguir."),
    "tool_result": ("tool result", "Lo que tu código le devuelve a Claude después de ejecutar una tool, dentro de un mensaje con rol user."),
    "max_tokens": ("max tokens", "Límite de tokens de salida. Si se alcanza, la respuesta se corta y stop_reason es max_tokens: NO terminó."),
    "tokens": ("tokens", "Pedacitos de texto (más o menos ¾ de palabra) con los que se mide lo que entra y sale del modelo, y lo que cuesta."),
    "antipatrón": ("anti-pattern", "Una forma de hacerlo que parece funcionar pero falla; el examen suele ponerla como respuesta incorrecta."),
    "red de seguridad": ("safety net / max iterations", "Un tope de vueltas para que el loop no corra para siempre. Sirve de protección, NO como forma normal de terminar."),
    "input_schema": ("input schema", "JSON Schema que describe qué parámetros acepta una tool."),
    "system prompt": ("system prompt", "Instrucciones generales para Claude (rol, reglas) que van aparte de los mensajes."),
    "historial": ("message history", "La lista completa de mensajes. La API no recuerda nada: se manda entera en cada llamada."),
    "hook": ("hook", "Código que se ejecuta automáticamente antes o después de una tool, para revisar o bloquear algo siempre, sin depender de lo que decida el modelo."),
    "subagente": ("subagent", "Un agente al que el coordinator le delega una parte del trabajo; no ve el contexto de los demás."),
    "coordinator": ("coordinator", "El agente que divide el trabajo, lo reparte a subagentes y junta los resultados."),
    "MCP": ("Model Context Protocol", "Protocolo estándar para conectar tools y datos externos a Claude."),
    "TDD": ("test-driven development", "Primero escribes la prueba que falla y luego el código que la pasa."),
    "CI/CD": ("continuous integration / delivery", "Pruebas y despliegues automáticos cada vez que alguien sube cambios al repo."),
    "pipeline": ("pipeline", "Serie de pasos automáticos (por ejemplo: probar, revisar, desplegar) que corre sin que nadie la vigile."),
    "job": ("job", "Un paso del pipeline de CI que corre en una máquina aparte, sin nadie que conteste preguntas."),
    "PR": ("pull request", "Propuesta de cambios al código que el equipo revisa antes de unirla (merge)."),
    "merge": ("merge", "Unir los cambios de un PR a la rama principal."),
    "timeout": ("timeout", "Límite de tiempo: si algo no responde antes, se corta y se marca como falla."),
    "frontmatter": ("frontmatter", "El bloque entre --- al inicio de un archivo .md con datos como name, description o paths."),
    "SKU": ("stock keeping unit", "El código único de un producto en el inventario (p. ej. MAN-ROJ-01)."),
    "compliance": ("compliance", "Cumplimiento de leyes y reglas (antilavado, privacidad). Junto con dinero y seguridad, va en código, no en el prompt."),
    "prerequisite gate": ("prerequisite gate", "Un chequeo en tu código que bloquea una tool hasta que se cumpla un requisito (p. ej. verificar al cliente)."),
    "/memory": ("/memory", "En el examen: muestra qué archivos de memoria (CLAUDE.md) se cargaron. 🔀 Hoy abre esos archivos y /context es el que muestra lo cargado."),
}


def _regex_glosario():
    terminos = sorted(GLOSARIO, key=len, reverse=True)
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(t) for t in terminos) + r")(?![\w-])", re.IGNORECASE)


_RE = _regex_glosario()
_CLAVES = {t.lower(): t for t in GLOSARIO}


def _glosario_en() -> tuple:
    """En inglés se subrayan el término de la tabla y su nombre en inglés, con la definición traducida."""
    tab = idioma.tabla()
    if _EN.get("tab") is not tab:
        defs = {}
        for termino, (ingles, definicion) in GLOSARIO.items():
            for clave in (termino, ingles):
                if " / " not in clave:
                    defs.setdefault(clave.lower(), (ingles, tab.get(definicion, definicion)))
        terminos = sorted(defs, key=len, reverse=True)
        _EN.update(tab=tab, defs=defs,
                   re=re.compile(r"(?<![\w-])(" + "|".join(re.escape(t) for t in terminos) + r")(?![\w-])", re.IGNORECASE))
    return _EN["re"], _EN["defs"]


_EN: dict = {}


def explicar_termino(termino: str) -> str:
    if idioma.en():
        ingles, definicion = _glosario_en()[1][termino.lower()]
        return f"{definicion}  ·  Exam term: {ingles}"
    en, definicion = GLOSARIO[_CLAVES[termino.lower()]]
    return f"{definicion}  ·  En inglés (examen): {en}"


# Palabras básicas para quien empieza: salen arriba del glosario y en el buscador, pero no se subrayan en los
# textos (aparecen en casi cada línea y lo llenarían todo de subrayados).
GLOSARIO_BASICO = {
    "terminal": ("terminal", "Ventana donde escribes comandos (en Mac, la app Terminal; en Windows, PowerShell). Ahí corres python panel.py."),
    "API": ("API", "La puerta por la que un programa habla con otro. Los labs hablan con Claude por la API de Anthropic."),
    "API key": ("API key", "La contraseña que deja a los labs usar la API. Vive en tu archivo .env y nunca se comparte."),
    "modelo": ("model", "La versión de Claude que contesta: Haiku (rápido y barato), Sonnet o Opus (más capaces y más caros)."),
    "prompt": ("prompt", "El texto que le mandas a Claude: instrucciones, preguntas y datos."),
    "system prompt": ("system prompt", "Instrucciones fijas que acompañan toda la conversación (el papel, las reglas, el formato)."),
    "token": ("token", "Pedacito de texto (más o menos ¾ de palabra). La API cobra por tokens de entrada y de salida."),
    "tool": ("tool", "Una función que Claude puede PEDIR que se ejecute (buscar un pedido, hacer un reembolso). Tu código la ejecuta."),
    "JSON": ("JSON", "Formato de texto para datos con llaves y comillas, por ejemplo {\"pedido\": \"#12345\"}."),
    "schema": ("schema", "La forma que deben tener unos datos: qué campos hay, de qué tipo y cuáles son obligatorios."),
    "Claude Code": ("Claude Code", "La herramienta de Anthropic para programar con Claude en la terminal. Las demos del Dominio 3 la usan por dentro."),
    "Agent SDK": ("Agent SDK", "Librería para armar agentes con el mismo motor de Claude Code. Viene en el paquete claude-agent-sdk."),
}

def marcar_glosario(html_texto: str) -> str:
    """Subraya los términos del glosario dentro de un texto YA escapado como HTML (no toca etiquetas).
    Cada término se marca una sola vez por texto, para no llenar todo de subrayados."""
    vistos = set()
    partes = re.split(r"(<[^>]+>)", html_texto)
    dentro_de = 0
    for i, p in enumerate(partes):
        if p.startswith("<"):
            if re.match(r"<(code|pre|a|abbr)\b", p):
                dentro_de += 1
            elif re.match(r"</(code|pre|a|abbr)>", p):
                dentro_de = max(0, dentro_de - 1)
            continue
        if dentro_de:
            continue

        def poner(m):
            clave = m.group(1).lower()
            if clave in vistos:
                return m.group(1)
            vistos.add(clave)
            return (f'<abbr class="termino" title="{html.escape(explicar_termino(m.group(1)), quote=True)}">'
                    f"{m.group(1)}</abbr>")
        partes[i] = (_glosario_en()[0] if idioma.en() else _RE).sub(poner, p)
    return "".join(partes)


# ---------------------------------------------------------------------
#  Extras por demo
# ---------------------------------------------------------------------
EXTRAS = {
    "1.1": {
        "casos": [
            {"nombre": "✅ Funciona bien", "tipo": "ok",
             "explica": "El loop sigue mientras stop_reason sea tool_use. Esperado: 3 tools (verificar, revisar pedido, reembolsar) y end_turn.",
             "esperado": "end_turn",
             "valores": {"D11_MODO_PARADA": "stop_reason", "D11_MAX_TOKENS": 1024, "D11_MAX_ITERACIONES": 10}},
            {"nombre": "❌ Parar al ver texto", "tipo": "falla",
             "explica": "Antipatrón: el loop se detiene en cuanto la respuesta trae texto. Claude suele escribir “Déjame revisar…” junto con un tool_use, así que quedan tools sin ejecutar.",
             "parece": "Si Claude ya escribió texto, ya terminó de responder.",
             "examen": "“El agente se detiene antes de tiempo” → revisa que el loop decida por stop_reason, no por el texto.",
             "grabacion": "02_parar_al_ver_texto.json",
             "esperado": "hay_texto",
             "valores": {"D11_MODO_PARADA": "hay_texto", "D11_MAX_TOKENS": 1024, "D11_MAX_ITERACIONES": 10}},
            {"nombre": "❌ Sin espacio (max_tokens)", "tipo": "falla",
             "explica": "Con 40 tokens la respuesta se corta: stop_reason = max_tokens. Claude NO terminó, se quedó sin espacio. Para el examen, la regla es la misma aunque solo veas tool_use y end_turn: si no es end_turn, no terminó.",
             "parece": "Si el loop salió sin error, Claude terminó.",
             "examen": "Todo lo que no sea end_turn significa “aún no termina, revisa por qué”.",
             "grabacion": "03_sin_espacio_max_tokens.json",
             "esperado": "max_tokens",
             "valores": {"D11_MODO_PARADA": "stop_reason", "D11_MAX_TOKENS": 40, "D11_MAX_ITERACIONES": 10}},
            {"nombre": "❌ Tope muy bajo", "tipo": "falla",
             "explica": "Con 2 vueltas, la red de seguridad corta el loop antes de que Claude termine el reembolso.",
             "parece": "Un tope de iteraciones es la forma de controlar cuándo termina el loop.",
             "examen": "Distractor favorito: “sube el tope de iteraciones”. El tope es solo contra loops infinitos.",
             "grabacion": "04_tope_muy_bajo.json",
             "esperado": "tope",
             "valores": {"D11_MODO_PARADA": "stop_reason", "D11_MAX_TOKENS": 1024, "D11_MAX_ITERACIONES": 2}},
        ],
        "predice": {
            "pregunta": "Con los valores que elegiste, ¿cómo crees que va a terminar el loop?",
            "opciones": {
                "end_turn": "Termina bien (end_turn) y hace el reembolso",
                "hay_texto": "Se detiene antes porque vio texto (antipatrón)",
                "max_tokens": "Se corta por falta de espacio (max_tokens)",
                "tope": "Lo corta el tope de iteraciones",
            },
            "por_que": {
                "end_turn": "El loop siguió mientras stop_reason era tool_use y salió con end_turn: así se termina bien.",
                "hay_texto": "El loop miró el texto en vez de stop_reason. Como Claude escribe y pide una tool en la misma respuesta, quedaron tools sin ejecutar.",
                "max_tokens": "max_tokens fue muy bajo: la respuesta se cortó a la mitad. Eso NO es terminar.",
                "tope": "El tope de vueltas (la red de seguridad) se alcanzó antes de que Claude terminara.",
            },
        },
    },
}


# ---------------------------------------------------------------------
#  Examen vs producto actual: se muestra como aviso en la demo
# ---------------------------------------------------------------------
PRODUCTO = {
    "1.1": "El examen solo usa dos stop_reason: tool_use y end_turn. Hoy hay más (por ejemplo max_tokens o pause_turn). En el examen: tool_use = sigue el loop; end_turn = terminó; cualquier otro = no terminó, revisa por qué.",
    "1.2": "El examen llama Task a la tool que lanza subagentes; hoy se llama Agent (Task sigue como alias). Y en el examen los subagentes nunca se hablan entre sí; hoy existe SendMessage. En el examen, responde como dice la guía.",
    "1.3": "El examen llama Task a la tool que lanza subagentes; hoy se llama Agent. Lanzar varias en una misma respuesta = paralelo, en ambos casos. En el examen: Task.",
    "1.7": "Hoy fork_session y --resume se usan juntas (reanudar y bifurcar a la vez). En el examen: son opciones distintas; respóndelas por separado.",
    "2.3": "Hoy Sonnet 5.5 y Opus 5.5 rechazan tool_choice any / tool con error 400 (pruébalo cambiando D23_MODELO_B); Haiku 5.5 los acepta. Y hoy la elección de tools empieza a empeorar más arriba de 18 (~30–50). En el examen: any / tool garantizan que llame una tool, y 18 tools son demasiadas (lo ideal, 4–5 por agente).",
    "2.4": "El examen habla de 2 scopes de configuración MCP (proyecto y usuario). Hoy Claude Code tiene 3: local, project y user. En el examen, responde con los 2.",
    "2.5": "Hoy Claude Code puede buscar con Bash y un Edit se arregla ampliando old_string o con replace_all. En el examen: Grep y Glob son tools built-in, y un Edit sin texto único se resuelve con Read + Write.",
    "3.1": "En el examen, /memory muestra lo que se cargó. Hoy /memory abre los archivos y /context es el que muestra lo cargado.",
    "3.2": "En el examen, allowed-tools restringe las tools del skill; hoy las pre-aprueba (para quitar, disallowed-tools). argument-hint hoy es solo una pista de autocompletado, y commands y skills son un solo sistema.",
    "3.6": "Hoy existen claude-code-action@v1 (GitHub Actions) y --worktree. En el examen: no aparecen; basta con -p y la salida JSON.",
    "4.2": "Hoy la documentación sugiere 3 a 5 ejemplos. En el examen: 2 a 4 ejemplos few-shot.",
    "4.3": "Hoy Sonnet y Opus 5.5 rechazan any / forced (Haiku 5.5 los acepta) y se usa auto + strict: true; también existen tool_choice none, messages.parse (Pydantic) y output_config.format. En el examen: tool_choice any / forced garantiza la estructura, y la validación de reglas sigue en tu código.",
    "4.5": "En el examen, un batch no corre tools a la mitad. Hoy las server tools sí pueden (pause_turn); las tuyas todavía no.",
    "5.1": "Hoy hay más herramientas de memoria y caché. En el examen: la API no recuerda nada (mandas el historial en cada request) y del caché solo hay que saber que existe.",
    "5.4": "En el examen, la recuperación tras una caída usa state manifests. Hoy Claude Code puede reanudar subagentes con su historial.",
}

# ---------------------------------------------------------------------
#  Mapa conceptual por dominio: (tema, idea clave). Se dibuja en la página del dominio.
# ---------------------------------------------------------------------
MAPAS = {
    1: [("1.1 Agentic loop", "stop_reason decide: tool_use sigue, end_turn termina"),
        ("1.2 Coordinator", "la descomposición del coordinator define qué se cubre"),
        ("1.3 Subagentes", "contexto explícito en el prompt; varios a la vez = paralelo"),
        ("1.4 Enforcement", "dinero y seguridad: gate en código, no en el prompt"),
        ("1.5 Hooks", "PreToolUse bloquea antes; PostToolUse normaliza después"),
        ("1.6 Descomposición", "fija (prompt chaining) o dinámica; multi-pass para revisar"),
        ("1.7 Sesiones", "resume (si cambió poco, avisa qué); sesión nueva con resumen si cambió mucho; fork para probar otra ruta")],
    2: [("2.1 Diseño de tools", "la descripción decide qué tool elige Claude"),
        ("2.2 Errores estructurados", "errorCategory + isRetryable; vacío válido ≠ error"),
        ("2.3 Distribución", "pocas tools por agente; tool_choice auto / any / forced"),
        ("2.4 MCP", "servers con tools y resources; .mcp.json y sus scopes"),
        ("2.5 Tools built-in", "Grep busca contenido, Glob nombres; Edit pide texto único")],
    3: [("3.1 CLAUDE.md", "los niveles se concatenan; @ruta importa otro archivo"),
        ("3.2 Commands y skills", "command: tú lo llamas; skill: Claude decide por la descripción"),
        ("3.3 Path rules", "rules con paths: se cargan solo al tocar esos archivos"),
        ("3.4 Plan mode", "plan si es grande, ambiguo o de arquitectura; directo si es claro y acotado"),
        ("3.5 Refinamiento", "ejemplos concretos y tests que fallan primero"),
        ("3.6 CI/CD", "-p para no colgarse, salida JSON, revisor independiente")],
    4: [("4.1 Criterios explícitos", "qué reportar y qué ignorar, con ejemplos"),
        ("4.2 Few-shot", "2 a 4 ejemplos con su razonamiento"),
        ("4.3 Structured output", "tool_use + schema; campos nullable para no inventar"),
        ("4.4 Validación y reintento", "reintenta con el error específico; no sirve si falta el dato"),
        ("4.5 Batch", "50% más barato, hasta 24 h, custom_id para emparejar"),
        ("4.6 Multi-pass", "instancia independiente; por archivo + integración")],
    5: [("5.1 Contexto", "case facts fuera del resumen; recorta el tool output"),
        ("5.2 Escalamiento", "pide persona, la política no cubre o no avanza"),
        ("5.3 Errores multi-agente", "error estructurado, nunca silencioso"),
        ("5.4 Degradación", "scratchpad y subagentes por fase"),
        ("5.5 Revisión humana", "precisión por tipo, muestreo estratificado"),
        ("5.6 Procedencia", "afirmación + fuente + fecha; anota los conflictos")],
}


# ---------------------------------------------------------------------
#  Casos rápidos y resultados posibles del resto de las demos
#  "esperado": lo que normalmente pasa con ese caso (el ticket lo compara con lo que pasó de verdad)
# ---------------------------------------------------------------------
def _c(nombre, tipo, explica, valores, esperado, parece=None, examen=None, clase=None):
    caso = {"nombre": nombre, "tipo": tipo, "explica": explica, "valores": valores, "esperado": esperado}
    if clase:
        caso["clase"] = clase
    if parece:
        caso["parece"], caso["examen"] = parece, examen
    return caso


def _p(pregunta, opciones, por_que, esperado=None):
    p = {"pregunta": pregunta, "opciones": opciones, "por_que": por_que}
    if esperado:
        p["esperado"] = esperado
    return p


EXTRAS.update({
    "1.2": {"casos": [
        _c("✅ Descomposición amplia", "ok", "El coordinator reparte un subtema por área: el reporte las cubre todas.",
           {"D12_DESCOMPOSICION": "amplia"}, "completo"),
        _c("❌ Descomposición estrecha", "falla", "El prompt empuja al coordinator a ver solo marketing: nadie investiga inventario, logística ni precios.",
           {"D12_DESCOMPOSICION": "estrecha"}, "faltan",
           "Si al reporte le faltan temas, los subagentes hicieron mal su trabajo.",
           "Si al reporte final le falta un tema entero, la causa raíz es la descomposición del coordinator.")],
        "predice": _p("¿El reporte final cubrirá las 5 áreas del negocio?",
                      {"completo": "Sí, cubre todas las áreas", "faltan": "No: faltan áreas que el coordinator nunca asignó",
                       "subagentes": "No: los subagentes hicieron mal su parte"},
                      {"completo": "Con una descomposición amplia hay un subagente por área y el reporte las cubre todas.",
                       "faltan": "El coordinator solo repartió subtemas de marketing; nadie investigó lo demás. La falla está en la descomposición.",
                       "subagentes": "Los subagentes hacen bien lo que se les asigna: si falta un área, es porque nunca se la asignaron."})},
    "1.3": {"casos": [
        _c("✅ Fuentes estructuradas (A)", "ok", "El subagente devuelve afirmación + fuente + fecha: el sintetizador puede citar cada dato.",
           {"D13_PARTE": "A", "D13_FORMATO": "estructurado"}, "con_fuentes"),
        _c("❌ Hallazgos en prosa (A)", "falla", "En un párrafo se pierden fuentes y fechas: el sintetizador termina escribiendo [sin fuente].",
           {"D13_PARTE": "A", "D13_FORMATO": "texto"}, "sin_fuentes",
           "Un resumen en prosa basta para pasarle los hallazgos al sintetizador.",
           "Para no perder fuentes, el subagente devuelve metadatos estructurados (afirmación + fuente + fecha).")
        , _c("✅ Subagentes en paralelo (B)", "ok", "Las tools pedidas en una misma respuesta corren a la vez: tarda lo del más lento.",
             {"D13_PARTE": "B", "D13_PARALELO": True}, "rapido"),
        _c("❌ Subagentes en serie (B)", "falla", "Aquí el coordinator pide las 3 delegaciones juntas, pero tu código las corre una tras otra: "
           "el tiempo total es la suma de todas. Es lo mismo que pasa si el coordinator lanza una Task, espera y luego lanza la siguiente.",
           {"D13_PARTE": "B", "D13_PARALELO": False}, "lento",
           "Da igual ejecutar los subagentes uno por uno.",
           "Subagentes independientes y lentos → varias Task en una sola respuesta, en paralelo."),
        _c("✅ Subagentes reales con Agent (C)", "ok", "Agent SDK: el subagente se define con AgentDefinition y el coordinator lo lanza con la tool Agent (Task en el examen).",
           {"D13_PARTE": "C", "D13_PERMITIR_AGENT": True}, "delega"),
        _c("❌ Sin Agent/Task en allowed_tools (C)", "falla", "El subagente está definido, pero el coordinator no tiene permiso de usar la tool que lo lanza.",
           {"D13_PARTE": "C", "D13_PERMITIR_AGENT": False}, "sin_subagentes",
           "Con definir el subagente en agents basta para que el coordinator lo use.",
           "Sin Task (Agent) en allowedTools no hay subagentes, aunque estén definidos.", "trampa")],
        "predice": _p("Con este caso, ¿qué crees que pase?",
                      {"con_fuentes": "El sintetizador cita cada dato con su fuente", "sin_fuentes": "Se pierden fuentes y fechas ([sin fuente])",
                       "rapido": "Tarda lo que tarda el subagente más lento", "lento": "Tarda la suma de todos los subagentes",
                       "delega": "El coordinator lanza al subagente con la tool Agent", "sin_subagentes": "El coordinator no puede lanzar subagentes"},
                      {"con_fuentes": "Los metadatos viajan estructurados y nada se pierde en el camino.",
                       "sin_fuentes": "La prosa resume y descarta: las fuentes y fechas no llegan al sintetizador.",
                       "rapido": "En paralelo, el tiempo total es el del más lento.",
                       "lento": "En serie, cada subagente espera al anterior.",
                       "delega": "Con Agent (Task) en allowed_tools, el coordinator delega con un prompt completo para cada subagente.",
                       "sin_subagentes": "Definir el subagente no basta: sin la tool Agent/Task permitida, no se puede lanzar."})},
    "1.4": {"casos": [
        _c("✅ Gate en código", "ok", "Tu código bloquea process_refund si no se cumple la regla, diga lo que diga el prompt.",
           {"D14_MODO": "gate_en_codigo"}, "bloqueado"),
        _c("❌ Regla solo en el prompt", "falla", "La regla vive en el system prompt: con presión del cliente, nada garantiza que se cumpla.",
           {"D14_MODO": "solo_prompt"}, "se_salta",
           "Si el system prompt dice “nunca reembolses más de $10,000 sin aprobación”, Claude lo cumplirá.",
           "Lo que debe cumplirse siempre (dinero, seguridad) va en código: prerequisite gate o hook, no solo en el prompt."),
        _c("❌ Solo prompt, 5 intentos", "falla", "La misma conversación 5 veces: cuenta en cuántas se saltó la regla. Un solo intento no prueba nada.",
           {"D14_MODO": "solo_prompt", "D14_REPETIR": 5}, "se_salta",
           "Si en mi prueba Claude respetó la regla, siempre la respetará.",
           "Que funcione casi siempre no basta para dinero o seguridad: va en código."),
        _c("❌ Handoff en texto libre", "falla", "Escala con una nota suelta: a quien recibe el caso le faltan datos y no ve el chat.",
           {"D14_MODO": "gate_en_codigo", "D14_HANDOFF": "libre"}, "handoff_incompleto",
           "Con que escale al humano, ya cumplió.",
           "El humano no ve el chat: el handoff lleva customer_id, summary, root_cause, refund_amount y recommended_action.")],
        "predice": _p("Un cliente presiona por un reembolso de $12,500 sin verificar. ¿Qué pasa?",
                      {"bloqueado": "El código bloquea el reembolso y se escala", "se_salta": "No hay garantía: Claude podría reembolsar",
                       "pregunta": "Claude siempre pide verificación, con o sin gate",
                       "handoff_incompleto": "Escala, pero la nota no trae lo que necesita quien la recibe"},
                      {"bloqueado": "El gate vive en tu código: process_refund no corre si no se cumple la regla.",
                       "se_salta": "Con la regla solo en el prompt, el resultado depende del modelo y de la presión del cliente.",
                       "pregunta": "A veces lo hace, pero un prompt no garantiza nada; por eso el examen pide la regla en código.",
                       "handoff_incompleto": "Sin campos obligatorios, el modelo escribe lo que se le ocurre y quien recibe el caso tiene que volver a preguntar todo."})},
    "1.5": {"casos": [
        _c("✅ Hooks activos", "ok", "PreToolUse bloquea el reembolso de $12,500; PostToolUse normaliza los datos de paquetería.",
           {"D15_ACTIVAR_PRETOOLUSE": True, "D15_ACTIVAR_POSTTOOLUSE": True}, "bloquea_normaliza"),
        _c("❌ Sin PreToolUse", "falla", "Nada frena el reembolso que supera el límite.",
           {"D15_ACTIVAR_PRETOOLUSE": False, "D15_ACTIVAR_POSTTOOLUSE": True}, "reembolsa",
           "Basta con pedirle a Claude en el prompt que respete el límite.",
           "Dinero, seguridad o compliance → hook PreToolUse que lo bloquea siempre, sin depender del modelo."),
        _c("❌ Sin PostToolUse", "falla", "Claude recibe fechas y estados en los formatos crudos de cada paquetería.",
           {"D15_ACTIVAR_PRETOOLUSE": True, "D15_ACTIVAR_POSTTOOLUSE": False}, "formatos",
           "Claude entenderá cualquier formato que devuelva la paquetería.",
           "Formatos de datos mezclados → PostToolUse que normaliza antes de que Claude los vea."),
        _c("❌ Bloquear con PostToolUse", "falla", "El hook que debía frenar el reembolso corre DESPUÉS: el dinero ya salió.",
           {"D15_ACTIVAR_PRETOOLUSE": True, "D15_ACTIVAR_POSTTOOLUSE": True, "D15_BLOQUEO_EN": "post"}, "tarde",
           "Cualquier hook sirve para bloquear una tool.",
           "Para impedir una acción, PreToolUse (antes de ejecutar). PostToolUse solo cambia lo que ve Claude después.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"tarde": "El hook intenta bloquear, pero el reembolso ya se hizo",
                       "bloquea_normaliza": "El reembolso se bloquea y los datos llegan normalizados", "no_intenta": "Claude no intentó el reembolso esta vez", "reembolsa": "Nada frena el reembolso de $12,500",
                       "formatos": "Claude ve fechas y estados en formatos mezclados"},
                      {"bloquea_normaliza": "Los hooks corren en tu código, antes y después de cada tool: no dependen del modelo.",
                       "no_intenta": "Sin el hook nada lo impide: esta vez el modelo se frenó solo, pero no hay garantía. En el examen, la regla de dinero va en un hook.", "reembolsa": "Sin PreToolUse, la única barrera es el prompt.",
                       "formatos": "Sin PostToolUse, cada paquetería entrega su propio formato.",
                       "tarde": "PostToolUse corre cuando la tool ya terminó: no puede deshacer un reembolso."})},
    "1.6": {"casos": [
        _c("⛓ Prompt chaining (A)", "ok", "Pasos fijos: cada uno usa la salida del anterior.", {"D16_PARTE": "A"}, "cadena"),
        _c("✅ Multi-pass, 14 archivos (B)", "ok", "Una pasada por archivo y una de integración: no se le escapan los detalles del final.",
           {"D16_PARTE": "B", "D16_MODO_REVISION": "multipass", "D16_NUM_ARCHIVOS": 14}, "completo"),
        _c("❌ Una sola pasada, 14 archivos (B)", "falla", "Revisar 14 archivos de golpe: el bug que cruza archivos está al final y se le escapa más seguido.",
           {"D16_PARTE": "B", "D16_MODO_REVISION": "una_pasada", "D16_NUM_ARCHIVOS": 14}, "se_pierde",
           "Una sola revisión de todo junto basta.",
           "Últimas partes mal revisadas → multi-pass: una pasada por parte + una de integración.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"completo": "Encuentra todos los problemas", "se_pierde": "Se le escapan problemas, sobre todo al final",
                       "cadena": "Cada paso usa la salida del anterior (cadena fija)"},
                      {"completo": "Cada pasada se enfoca en una cosa; la de integración revisa el conjunto.",
                       "se_pierde": "Con todo de golpe, la atención se diluye.",
                       "cadena": "La descomposición fija sirve cuando los pasos se conocen de antemano."})},
    "1.7": {"casos": [
        _c("🔁 Resume y fork (A)", "ok", "Agent SDK: seguir una sesión (resume) o bifurcarla (fork).", {"D17_PARTE": "A"}, "fork"),
        _c("✅ Sesión nueva con resumen (B)", "ok", "Empieza de cero con un resumen de lo vigente y relee solo lo que cambió.",
           {"D17_PARTE": "B", "D17_ESTRATEGIA": "nueva_sesion"}, "vigente"),
        _c("❌ Resume con archivo cambiado (B)", "falla", "La conversación vieja trae datos que ya cambiaron en el archivo.",
           {"D17_PARTE": "B", "D17_ESTRATEGIA": "resume"}, "viejo",
           "Reanudar la sesión siempre es mejor: ya tiene todo el contexto.",
           "Si cambió mucho de lo que ya analizó → sesión nueva con un resumen de lo vigente. Si cambió poco → --resume y dile qué archivos cambiaron.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"vigente": "Responde con los datos actuales", "viejo": "Responde con datos viejos que ya cambiaron",
                       "fork": "Muestra cómo seguir o bifurcar una sesión"},
                      {"vigente": "La sesión nueva solo tiene lo vigente: no hay datos viejos que la confundan.",
                       "viejo": "El historial reanudado conserva la versión anterior del archivo.",
                       "fork": "Fork deja intacta la sesión original y explora otra rama."})},
    "2.1": {"casos": [
        _c("✅ Descripciones completas", "ok", "Qué hace, qué devuelve y cuándo NO usarla: Claude elige bien.",
           {"D21_DESCRIPCIONES": "completas", "D21_CONFLICTO_EN_SYSTEM": False}, "acierta"),
        _c("❌ Descripciones mínimas", "falla", "Con una línea por tool, Claude confunde get_customer con lookup_order.",
           {"D21_DESCRIPCIONES": "minimas", "D21_CONFLICTO_EN_SYSTEM": False}, "confunde",
           "El nombre de la tool basta para que Claude sepa cuándo usarla.",
           "Claude elige la tool por su descripción: si se confunden, el primer arreglo es mejorar las descripciones."),
        _c("❌ Regla que choca en el system", "falla", "Una regla por palabra clave le gana a buenas descripciones.",
           {"D21_DESCRIPCIONES": "completas", "D21_CONFLICTO_EN_SYSTEM": True}, "regla_gana",
           "Una regla por palabra clave en el system prompt ayuda a elegir la tool.",
           "Las reglas por palabra clave pueden contradecir las descripciones y causar errores."),
        _c("⚖ Las dos (comparación)", "ok", "Corre mínimas y completas y las compara en una tabla.",
           {"D21_DESCRIPCIONES": "ambas", "D21_CONFLICTO_EN_SYSTEM": False}, "comparacion")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"acierta": "Elige la tool correcta casi siempre", "confunde": "Confunde get_customer con lookup_order",
                       "regla_gana": "La regla del system le gana a la descripción", "comparacion": "Las completas aciertan más que las mínimas"},
                      {"acierta": "Las descripciones completas le dicen a Claude cuándo usar cada tool y cuándo no.",
                       "confunde": "Con descripciones de una línea, dos tools parecidas son casi indistinguibles.",
                       "regla_gana": "Lo que dice el system prompt pesa más que la descripción de la tool.",
                       "comparacion": "La diferencia está solo en la descripción: mismo modelo, mismas consultas."})},
    "2.2": {"casos": [
        _c("✅ Errores estructurados", "ok", "is_error + errorCategory + isRetryable: Claude sabe si reintentar o explicar.",
           {"D22_FORMATO": "estructurado"}, "maneja"),
        _c("❌ “Operation failed”", "falla", "Un error genérico no dice si reintentar; y un sistema caído devuelve lista vacía, como si no hubiera pedidos.",
           {"D22_FORMATO": "generico"}, "confunde",
           "Un mensaje de error genérico basta; Claude sabrá qué hacer.",
           "Errores con errorCategory e isRetryable; y un vacío válido (sin pedidos) no es un error."),
        _c("⚖ Los dos (comparación)", "ok", "Corre ambos formatos en los mismos escenarios.", {"D22_FORMATO": "ambos"}, "comparacion")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"maneja": "Reintenta lo transitorio y explica lo que no se puede", "confunde": "No sabe si reintentar; lo caído parece “sin pedidos”",
                       "comparacion": "El estructurado maneja mejor cada escenario"},
                      {"maneja": "La categoría y el isRetryable le dicen qué hacer con cada error.",
                       "confunde": "Sin estructura, Claude adivina; y una lista vacía por falla es el peor caso.",
                       "comparacion": "Mismo agente, mismos escenarios: solo cambia cómo se reporta el error."})},
    "2.3": {"casos": [
        _c("⚖ 4 vs 18 tools (A)", "ok", "Mismas consultas con 4 tools y con 18: aciertos y tokens.", {"D23_PARTE": "A"}, "menos_mejor"),
        _c("🎛 tool_choice con Haiku (B)", "ok", "auto, any y tool con un modelo que los acepta.",
           {"D23_PARTE": "B", "D23_MODELO_B": "claude-haiku-5-5"}, "fuerza"),
        _c("📄 Documento desconocido (C)", "ok", "Uso real: tool forzada para los metadatos, any para que elija un schema "
           "(factura, recibo o contrato) y auto al final.", {"D23_PARTE": "C", "D23_MODELO_C": "claude-haiku-5-5"}, "schema"),
        _c("❌ Un agente con 18 tools (A)", "falla", "Con 18 tools que se parecen, elige mal más seguido y cada request cuesta más tokens.",
           {"D23_PARTE": "A", "D23_TOOLS_A": "18"}, "confunde_18",
           "Más tools = más capacidades = mejor agente.",
           "Pocas tools por rol (4-5). Con 18, la selección empeora y las definiciones viajan en cada request."),
        _c("❌ tool_choice any con Sonnet (B)", "falla", "Sonnet 5.5 rechaza any / tool con error 400.",
           {"D23_PARTE": "B", "D23_MODELO_B": "claude-sonnet-5-5"}, "error400",
           "tool_choice any / tool funciona igual en todos los modelos.",
           "any obliga a usar alguna tool y tool obliga a una específica. Hoy Sonnet y Opus 5.5 los rechazan: es del producto, no del examen.",
           clase="producto")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"menos_mejor": "Con 4 tools acierta más y gasta menos tokens que con 18",
                       "confunde_18": "Con 18 tools se equivoca más y gasta más tokens", "gasta_18": "Con 18 tools acierta igual, pero gasta varias veces más tokens",
                       "fuerza": "tool_choice obliga a usar una tool aunque la pregunta no la necesite", "error400": "La API responde error 400",
                       "schema": "Primero los metadatos, luego elige el schema de recibo y al final contesta en texto"},
                      {"menos_mejor": "Menos tools = menos opciones parecidas y menos tokens de definiciones.",
                       "confunde_18": "Cada tool de más es otra opción parecida para confundirse, y su definición se paga en cada request.",
                       "fuerza": "any y tool quitan a Claude la opción de contestar solo con texto.",
                       "error400": "Esos modos ya no los aceptan Sonnet ni Opus 5.5; la demo atrapa el error y lo explica.",
                       "schema": "La tool forzada ordena el primer paso; any garantiza que la salida cae en uno de tus schemas aunque no sepas el tipo."})},
    "2.4": {"casos": [
        _c("🔌 Cliente MCP directo (A)", "ok", "Tu código habla con el servidor MCP: lista y llama sus tools.", {"D24_PARTE": "A"}, "tools"),
        _c("📚 Agent SDK con resources (B)", "ok", "Además de las tools, el agente puede leer el catálogo como resource.",
           {"D24_PARTE": "B", "D24_USAR_RESOURCES": True}, "resources"),
        _c("✅ Configuración .mcp.json (C)", "ok", "El servidor del equipo va en el .mcp.json del repo, con el token como ${GITHUB_TOKEN}.",
           {"D24_PARTE": "C", "D24_ALCANCE": "proyecto", "D24_SECRETO": "variable"}, "config"),
        _c("❌ Token escrito en .mcp.json (C)", "falla", "El token queda en el repo: cualquiera que lo clone lo ve.",
           {"D24_PARTE": "C", "D24_ALCANCE": "proyecto", "D24_SECRETO": "en_archivo"}, "token_expuesto",
           "Si el .mcp.json funciona con el token adentro, ya quedó listo.",
           "Los secretos van como ${VAR}: cada persona los pone en su entorno; el .mcp.json va a git."),
        _c("❌ Servidor solo en ~/.claude.json (C)", "falla", "Funciona en tu máquina, pero tu compañero no tiene el servidor.",
           {"D24_PARTE": "C", "D24_ALCANCE": "usuario", "D24_SECRETO": "variable"}, "companero_sin_servidor",
           "Si me funciona a mí, le funciona al equipo.",
           "Lo que comparte el equipo va en el .mcp.json del proyecto; ~/.claude.json es personal.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"tools": "Consulta cada SKU con las tools del servidor", "resources": "Lee el catálogo completo como resource",
                       "config": "Un .mcp.json conecta el servidor a Claude Code",
                       "token_expuesto": "El token queda a la vista de todo el que clone el repo",
                       "companero_sin_servidor": "Tu compañero no tiene el servidor"},
                      {"tools": "Las tools son acciones que el modelo pide; el servidor las ejecuta.",
                       "resources": "Los resources son datos que se leen (catálogos, documentos), no acciones.",
                       "config": "El scope del .mcp.json decide quién comparte la configuración.",
                       "token_expuesto": "El .mcp.json va a git; por eso los secretos se escriben como ${VAR}.",
                       "companero_sin_servidor": "~/.claude.json es del usuario: no viaja con el repo."})},
    "2.5": {"casos": [
        _c("✅ Con Grep y Glob", "ok", "Grep encuentra los usos (y alias); Glob lista los archivos de pruebas (tests); Edit cambia solo el límite correcto.",
           {"D25_TOOLS": ["Read", "Grep", "Glob", "Edit"]}, "completo"),
        _c("❌ Sin Grep", "falla", "Sin buscar contenido, no encuentra todos los usos de processRefund.",
           {"D25_TOOLS": ["Read", "Glob", "Edit"]}, "usos_perdidos",
           "Glob basta para encontrar dónde se usa una función.",
           "¿Quién llama a esta función? → Grep (busca contenido). Archivos por nombre → Glob."),
        _c("❌ Sin Glob", "falla", "Sin buscar por nombre, le cuesta listar los *.test.ts.",
           {"D25_TOOLS": ["Read", "Grep", "Edit"]}, "tests_perdidos",
           "Grep sirve igual para listar archivos por patrón de nombre.",
           "Archivos por patrón de nombre → Glob; contenido → Grep."),
        _c("🎓 Edit sin texto único → Read + Write", "ok", "Se le pide un Edit de solo “10000”, que aparece dos veces: falla. "
           "El respaldo que espera el examen es leer el archivo completo y reescribirlo con Write.",
           {"D25_TOOLS": ["Read", "Grep", "Glob", "Edit", "Write"], "D25_EDIT_RESPALDO": "read_write"}, "read_write",
           examen="Un Edit falla porque el texto no es único → Read + Write (hoy también se amplía old_string, pero en el examen la respuesta es Read + Write).")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"completo": "Encuentra usos, alias y tests, y edita solo el límite correcto",
                       "read_write": "El Edit falla por texto repetido y lo resuelve con Read + Write",
                       "usos_perdidos": "No encuentra todos los usos de la función", "tests_perdidos": "Le cuesta listar los archivos de pruebas"},
                      {"completo": "Cada tool para lo suyo: Grep contenido, Glob nombres, Edit con texto único.",
                       "read_write": "Edit necesita un texto único; si no lo hay, el respaldo del examen es Read + Write.",
                       "usos_perdidos": "Sin Grep tiene que abrir archivos a ciegas.",
                       "tests_perdidos": "Sin Glob no tiene una forma directa de buscar por nombre de archivo."})},
    "3.1": {"casos": [
        _c("✅ Importar con @ruta", "ok", "Carga el CLAUDE.md, el estilo importado con @docs/estilo.md y tus reglas locales.",
           {"D31_USAR_IMPORT": True, "D31_SIMULAR_COMPANERO": False}, "todas"),
        _c("❌ Compañero nuevo", "falla", "Sin tu CLAUDE.local.md, el compañero pierde esas instrucciones.",
           {"D31_USAR_IMPORT": True, "D31_SIMULAR_COMPANERO": True}, "pierde_local",
           "Si una instrucción funciona en tu máquina, funciona para todo el equipo.",
           "CLAUDE.local.md y ~/.claude no se comparten: lo del equipo va en el CLAUDE.md del proyecto."),
        _c("❌ Sin importar con @ruta", "falla", "docs/estilo.md no se carga: se pierden las reglas de estilo.",
           {"D31_USAR_IMPORT": False, "D31_SIMULAR_COMPANERO": False}, "pierde_estilo",
           "Tener docs/estilo.md en el repo basta para que Claude lo siga.",
           "Para dividir el CLAUDE.md sin duplicar, se importa con @ruta (no existe @import).")],
        "predice": _p("¿Qué reglas conocerá Claude con este caso?",
                      {"todas": "Las del proyecto, las de estilo y las locales", "pierde_local": "No conoce las reglas de CLAUDE.local.md",
                       "pierde_estilo": "No conoce las reglas de estilo"},
                      {"todas": "Los niveles se concatenan y la línea @docs/estilo.md trae el archivo de estilo.",
                       "pierde_local": "CLAUDE.local.md es personal: un compañero nuevo no lo tiene.",
                       "pierde_estilo": "Sin la línea @ruta, el archivo de estilo no entra al contexto."})},
    "3.2": {"casos": [
        _c("⌨ Slash command (A)", "ok", "Tú lo llamas con /comando y recibe $ARGUMENTS.", {"D32_PARTE": "A"}, "comando"),
        _c("✅ Skill con buena descripción (B)", "ok", "La descripción dice qué hace y cuándo usarlo: Claude lo elige solo.",
           {"D32_PARTE": "B", "D32_DESCRIPCION_SKILL": "buena"}, "usa_skill"),
        _c("❌ Descripción vaga (B)", "falla", "“Utilidades varias.”: Claude no sabe cuándo usar el skill.",
           {"D32_PARTE": "B", "D32_DESCRIPCION_SKILL": "vaga"}, "no_usa",
           "Basta con que el skill exista; Claude lo usará cuando haga falta.",
           "Claude decide usar un skill por su descripción: debe decir qué hace y cuándo usarlo.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"usa_skill": "Claude usa el skill por su cuenta", "no_usa": "Claude no usa el skill",
                       "comando": "El comando corre porque tú lo llamas"},
                      {"usa_skill": "Una buena descripción es lo que hace que Claude elija el skill.",
                       "no_usa": "Con una descripción vaga, nada le indica que ese skill sirve aquí.",
                       "comando": "Un slash command no lo decide Claude: lo invocas tú."})},
    "3.3": {"casos": [
        _c("✅ Rules con paths", "ok", "Cada regla se carga solo al tocar sus archivos.", {"D33_CON_PATHS": True}, "por_archivo"),
        _c("❌ Rules sin paths", "falla", "Todas las reglas se cargan al inicio, apliquen o no.", {"D33_CON_PATHS": False}, "siempre",
           "Tener todas las convenciones siempre cargadas no tiene costo.",
           "Convenciones de un tipo de archivo repartido en muchas carpetas → .claude/rules/ con paths.")],
        "predice": _p("¿Cuándo se cargan las reglas?",
                      {"por_archivo": "Cada regla, solo al tocar sus archivos", "siempre": "Todas al inicio, apliquen o no"},
                      {"por_archivo": "Con paths en el frontmatter, la regla espera a que toques un archivo que coincida.",
                       "siempre": "Sin paths, la regla es parte del contexto desde el principio."})},
    "3.4": {"casos": [
        _c("✅ Híbrido (tarea ambigua)", "ok", "Hay varias formas válidas de hacerlo: primero plan, se aprueba y se ejecuta en la misma sesión.",
           {"D34_MODO": "hibrido", "D34_TIPO_TAREA": "ambigua"}, "plan_luego"),
        _c("✅ Directo (tarea clara)", "ok", "Bajar un límite en 3 archivos tiene una sola forma correcta: ir directo está bien.",
           {"D34_MODO": "directo", "D34_TIPO_TAREA": "clara"}, "edita_sin_plan"),
        _c("❌ Directo con tarea ambigua", "falla", "Edita de inmediato y elige un diseño por su cuenta, sin que lo revises.",
           {"D34_MODO": "directo", "D34_TIPO_TAREA": "ambigua"}, "elige_solo",
           "Si el agente es bueno, puede decidir solo cómo hacer el cambio.",
           "Cuando hay varias formas válidas (decisiones de diseño) o el cambio es grande, plan mode primero."),
        _c("❌ Plan mode para un cambio claro", "falla", "Planear un cambio con una sola forma correcta solo agrega pasos.",
           {"D34_MODO": "hibrido", "D34_TIPO_TAREA": "clara"}, "innecesario",
           "Planear nunca está de más: mejor plan mode también para un cambio chico.",
           "Plan mode es para cambios grandes, ambiguos o de arquitectura. Un cambio claro y acotado va con ejecución directa."),
        _c("📋 Solo plan", "ok", "Explora y propone, pero no puede editar.", {"D34_MODO": "plan", "D34_TIPO_TAREA": "ambigua"}, "no_edita")],
        "predice": _p("¿Qué crees que haga Claude con este caso?",
                      {"plan_luego": "Propone un plan y luego lo ejecuta", "no_edita": "Explora y propone, pero no edita",
                       "edita_sin_plan": "Edita de inmediato", "elige_solo": "Edita de inmediato y elige el diseño por su cuenta",
                       "innecesario": "Planea algo que no necesitaba plan"},
                      {"plan_luego": "El híbrido junta lo mejor: revisas el plan antes de cambiar nada.",
                       "no_edita": "En plan mode, las tools de edición no están permitidas.",
                       "edita_sin_plan": "Un cambio claro y acotado, con una sola forma correcta, va directo.",
                       "elige_solo": "Sin plan, el agente toma una decisión de diseño que te tocaba revisar a ti.",
                       "innecesario": "Plan mode no hace daño, pero en un cambio claro solo agrega una vuelta: en el examen es el distractor."})},
    "3.5": {"casos": [
        _c("✅ TDD", "ok", "En cada ronda recibe las pruebas que fallaron y corrige.", {"D35_MODO": "tdd"}, "pasa"),
        _c("📝 Con ejemplos", "ok", "Descripción + ejemplos concretos: acierta más desde el principio.", {"D35_MODO": "ejemplos"}, "mejor"),
        _c("❌ Solo prosa", "falla", "La descripción en palabras se interpreta distinto: falla en los casos frontera.",
           {"D35_MODO": "vago"}, "falla_frontera",
           "Una buena descripción en prosa basta para que lo haga bien.",
           "Si interpreta distinto tu descripción → da ejemplos concretos o pruebas que fallen.")],
        "predice": _p("¿Cómo le irá con las pruebas?",
                      {"pasa": "Termina pasando todas las pruebas", "mejor": "Acierta la mayoría desde la primera vez",
                       "falla_frontera": "Falla en los casos frontera"},
                      {"pasa": "Las pruebas que fallan le dicen exactamente qué corregir.",
                       "mejor": "Los ejemplos quitan la ambigüedad de la prosa.",
                       "falla_frontera": "La prosa deja huecos que Claude llena a su manera."})},
    "3.6": {"casos": [
        _c("✅ JSON con schema", "ok", "--output-format json con --json-schema: salida validada.",
           {"D36_FORMATO": "json", "D36_CON_SCHEMA": True}, "validado"),
        _c("🧾 JSON sin schema", "ok", "Sale JSON, pero su forma no está garantizada.", {"D36_FORMATO": "json", "D36_CON_SCHEMA": False}, "json_libre"),
        _c("❌ Texto", "falla", "Una máquina no puede leer la salida de forma confiable.",
           {"D36_FORMATO": "text", "D36_CON_SCHEMA": False}, "no_parseable",
           "La salida en texto se puede procesar igual en el pipeline.",
           "En CI: -p para que no se cuelgue y --output-format json (con --json-schema) para que una máquina lo lea.")],
        "predice": _p("¿Qué sale del job de CI?",
                      {"validado": "JSON validado contra el schema", "json_libre": "JSON, sin garantía de forma",
                       "no_parseable": "Texto que una máquina no puede leer bien"},
                      {"validado": "El schema garantiza los campos que el pipeline espera.",
                       "json_libre": "Es JSON, pero los campos pueden variar.",
                       "no_parseable": "El texto libre cambia de forma en cada corrida."})},
    "4.1": {"casos": [
        _c("✅ Criterios explícitos", "ok", "Qué reportar y qué ignorar, con ejemplos.", {"D41_MODO": "explicito"}, "preciso"),
        _c("❌ “Sé conservador”", "falla", "Sin criterio, marca de más o de menos.", {"D41_MODO": "vago"}, "ruido",
           "Pedir “sé conservador” reduce los falsos positivos.",
           "Criterios explícitos: qué SÍ reportar y qué NO, con ejemplos."),
        _c("⚖ Los dos (comparación)", "ok", "Mismo código, los dos prompts.", {"D41_MODO": "ambos"}, "comparacion")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"preciso": "Menos falsos positivos y negativos", "ruido": "Marca de más o de menos", "comparacion": "Los criterios explícitos ganan"},
                      {"preciso": "El criterio concreto no deja espacio para interpretar.",
                       "ruido": "“Conservador” significa cosas distintas en cada caso.",
                       "comparacion": "Solo cambia el prompt: la diferencia es el criterio."})},
    "4.2": {"casos": [
        _c("✅ Con ejemplos", "ok", "Ejemplos few-shot con su razonamiento para los casos ambiguos.", {"D42_MODO": "con_ejemplos"}, "consistente"),
        _c("❌ Sin ejemplos", "falla", "Solo instrucciones: los casos ambiguos salen inconsistentes.", {"D42_MODO": "sin_ejemplos"}, "inconsistente",
           "Las instrucciones bastan para los casos ambiguos.",
           "Casos ambiguos o formato inconsistente → 2 a 4 ejemplos few-shot con su razonamiento."),
        _c("⚖ Los dos (comparación)", "ok", "Mismas entradas, con y sin ejemplos.", {"D42_MODO": "ambos"}, "comparacion")],
        "predice": _p("¿Qué crees que pase con los casos ambiguos?",
                      {"consistente": "Los resuelve de forma consistente", "inconsistente": "Los resuelve distinto cada vez",
                       "comparacion": "Con ejemplos sale más consistente"},
                      {"consistente": "Los ejemplos muestran cómo decidir en los casos difíciles.",
                       "inconsistente": "Sin ejemplos, cada caso ambiguo se interpreta a su manera.",
                       "comparacion": "La única diferencia son los ejemplos."})},
    "4.3": {"casos": [
        _c("✅ tool_use + schema", "ok", "El schema evita JSON roto; los campos nullable evitan inventar.", {"D43_MODO": "tool"}, "valido"),
        _c("❌ JSON pedido en el prompt", "falla", "“Responde en JSON”: puede salir roto o con datos inventados.", {"D43_MODO": "texto"}, "roto",
           "Pedir “responde en JSON” en el prompt es suficiente.",
           "JSON roto → tool_use con schema; campos nullable para no inventar datos."),
        _c("⚖ Los dos (comparación)", "ok", "Los mismos correos por los dos caminos.", {"D43_MODO": "ambos"}, "comparacion")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"valido": "JSON válido, sin inventar lo que falta", "roto": "JSON roto o con datos inventados", "comparacion": "El schema gana"},
                      {"valido": "El schema obliga la forma y nullable permite decir “no está”.",
                       "roto": "En texto libre nada garantiza la sintaxis ni la honestidad de los campos.",
                       "comparacion": "Mismo modelo y mismos correos: cambia el mecanismo."})},
    "4.4": {"casos": [
        _c("✅ Error específico", "ok", "Le dices exactamente qué falló y lo corrige.", {"D44_FEEDBACK": "especifico"}, "corrige"),
        _c("❌ Error genérico", "falla", "“Hay errores, intenta de nuevo”: repite los mismos.", {"D44_FEEDBACK": "generico"}, "repite",
           "Decirle “hay errores, intenta de nuevo” basta.",
           "Reintenta con el error específico; si el dato no está en el documento, reintentar no sirve."),
        _c("❌ Sin reintento", "falla", "Se queda con lo primero que llega, con errores.", {"D44_FEEDBACK": "sin_reintento"}, "acepta",
           "Lo primero que devuelve suele estar bien.", "Valida en código y reintenta con el error específico.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"corrige": "Corrige al reintentar", "repite": "Repite los mismos errores", "acepta": "Se queda con el primer resultado, con errores"},
                      {"corrige": "El error exacto le dice qué arreglar.", "repite": "Sin saber qué falló, vuelve a intentar igual.",
                       "acepta": "Sin validación ni reintento, el error pasa tal cual."})},
    "4.5": {"casos": [
        _c("✅ Emparejar por custom_id", "ok", "Cada resultado se une con su reseña por su custom_id, llegue en el orden que llegue.",
           {"D45_EMPAREJAR": "custom_id", "D45_USO": "nocturno"}, "emparejado"),
        _c("❌ Emparejar por orden", "falla", "Supone que el resultado 1 es de la reseña 1: si llegan en otro orden, se cruzan.",
           {"D45_EMPAREJAR": "orden", "D45_USO": "nocturno"}, "mal_emparejado",
           "Los resultados llegan en el mismo orden en que los mandé.",
           "El orden no está garantizado: se empareja siempre por custom_id (y así se reenvían solo los que fallaron)."),
        _c("❌ Batch para revisar antes de un merge", "falla", "Alguien espera la revisión y un lote puede tardar hasta 24 h. No se manda el lote.",
           {"D45_USO": "pre_merge"}, "bloquea",
           "Batch es 50% más barato: conviene para todo.",
           "Lo que bloquea a alguien (revisión pre-merge) va síncrono; Batch solo para lo que puede esperar.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"orden": "Llegan en el mismo orden en que se enviaron", "desorden": "Llegan en cualquier orden: se emparejan por custom_id",
                       "emparejado": "Cada reseña queda con su clasificación", "mal_emparejado": "Algunas reseñas quedan con la clasificación de otra",
                       "suerte_orden": "Esta vez llegaron en orden (pero no está garantizado)", "bloquea": "No se manda: Batch no sirve si alguien espera"},
                      {"orden": "No está garantizado: por eso cada petición lleva su custom_id.",
                       "desorden": "Los resultados llegan como van terminando; el custom_id los empareja.",
                       "emparejado": "El custom_id une cada resultado con su petición sin importar el orden.",
                       "mal_emparejado": "Emparejar por posición falla en cuanto el orden cambia; el custom_id existe para eso.",
                       "suerte_orden": "Con pocos resultados a veces coinciden; con lotes grandes se cruzan. No dependas del orden.",
                       "bloquea": "Batch puede tardar hasta 24 h y no tiene SLA de latencia: lo que bloquea a alguien va síncrono."},
                      esperado="desorden")},
    "4.6": {"casos": [
        _c("✅ Instancia independiente", "ok", "Un revisor sin el contexto de quien escribió encuentra más.", {"D46_MODO": "independiente"}, "encuentra"),
        _c("❌ Misma sesión", "falla", "Revisarse a sí mismo en la misma sesión deja pasar errores.", {"D46_MODO": "misma_sesion"}, "se_le_pasa",
           "Pedirle a Claude que revise su propio trabajo en la misma sesión es suficiente.",
           "Revisión con una instancia independiente: una llamada nueva que no vio cómo se escribió."),
        _c("⚖ Los dos (comparación)", "ok", "El mismo borrador revisado de las dos formas.", {"D46_MODO": "ambos"}, "comparacion")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"encuentra": "Encuentra más problemas", "se_le_pasa": "Se le pasan problemas", "comparacion": "La independiente encuentra más"},
                      {"encuentra": "Sin el razonamiento original, el revisor no hereda sus puntos ciegos.",
                       "se_le_pasa": "En la misma sesión, tiende a confirmar lo que ya pensó.",
                       "comparacion": "Mismo borrador: cambia quién lo revisa."})},
    "5.1": {"casos": [
        _c("✅ Case facts (A)", "ok", "Montos, fechas e IDs en un bloque fuera del resumen.", {"D51_PARTE": "A", "D51_MODO": "case_facts"}, "conserva"),
        _c("❌ Resumen progresivo (A)", "falla", "El resumen va borrando datos exactos: “tu reembolso reciente”.",
           {"D51_PARTE": "A", "D51_MODO": "resumen"}, "pierde",
           "Un resumen de la conversación conserva lo importante.",
           "Datos clave del caso (montos, fechas, IDs) en un bloque de case facts, fuera del resumen."),
        _c("✂ Recortar el tool output (B)", "ok", "Solo los campos que importan entran al contexto.", {"D51_PARTE": "B"}, "recorta"),
        _c("✅ Dato clave arriba con encabezado (C)", "ok", "El código que importa va al inicio, bajo DATOS CLAVE.",
           {"D51_PARTE": "C", "D51_POSICION_DATO": "arriba"}, "encuentra"),
        _c("❌ Dato clave a la mitad (C)", "falla", "El código queda enterrado entre 600 notas con códigos parecidos (y otras notas del mismo pedido).",
           {"D51_PARTE": "C", "D51_POSICION_DATO": "medio"}, "se_pierde",
           "Si el dato está en el contexto, el modelo lo va a encontrar.",
           "Lost in the middle: lo importante va al inicio o al final, con encabezados.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"encuentra": "Encuentra el código correcto", "se_pierde": "Responde otro código o no lo encuentra", "conserva": "Recuerda montos y fechas exactos", "pierde": "Se le pierden los datos exactos",
                       "recorta": "Ahorra tokens sin perder lo necesario",
                       "comparacion": "Con case facts conserva más datos exactos que con el resumen"},
                      {"encuentra": "Arriba y con encabezado, el dato clave no compite con el resto.", "se_pierde": "A la mitad de un contexto largo el modelo atiende peor: lost in the middle.", "conserva": "Los case facts no pasan por el resumen: se conservan tal cual.",
                       "pierde": "Cada resumen redondea y generaliza.",
                       "recorta": "Lo que no entra al contexto no ocupa tokens ni distrae.",
                       "comparacion": "El resumen comprime y pierde lo exacto; el bloque de case facts viaja completo en cada turno."})},
    "5.2": {"casos": [
        _c("✅ Criterios + ejemplos", "ok", "Los criterios explícitos más ejemplos de cuándo escalar y cuándo resolver: la respuesta típica del examen.",
           {"D52_MODO": "criterios_ejemplos"}, "escala_bien"),
        _c("✅ Criterios de escalamiento", "ok", "Escala solo si el cliente pide una persona, si la política no cubre el caso o si el agente no avanza.", {"D52_MODO": "criterios"}, "escala_bien"),
        _c("❌ Instrucción vaga", "falla", "Escala por enojo y no pide datos cuando el caso es ambiguo.", {"D52_MODO": "vago"}, "escala_mal",
           "Escalar cuando el cliente está molesto es buena atención.",
           "Escalar: pide una persona, la política no cubre el caso o no avanza. No por enojo; si es ambiguo, pide el dato."),
        _c("⚖ Los dos (comparación)", "ok", "Los mismos clientes con los dos prompts.", {"D52_MODO": "ambos"}, "comparacion")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"escala_bien": "Escala solo en los casos válidos", "escala_mal": "Escala de más (o por enojo)", "comparacion": "Los criterios escalan mejor"},
                      {"escala_bien": "Los criterios explícitos separan enojo de necesidad real.",
                       "escala_mal": "Sin criterios, el tono del cliente decide.",
                       "comparacion": "Mismos clientes: cambia el criterio."})},
    "5.3": {"casos": [
        _c("✅ Error estructurado", "ok", "Tipo de falla, qué intentó, resultados parciales y alternativas.",
           {"D53_FORMATO": "estructurado", "D53_COMPARAR_TODOS": False}, "informa"),
        _c("❌ Falla silenciosa", "falla", "“Sin datos relevantes” como si todo estuviera bien.",
           {"D53_FORMATO": "silencioso", "D53_COMPARAR_TODOS": False}, "oculta",
           "Si un subagente no encuentra nada, devolver “sin datos” es correcto.",
           "Errores de subagentes: estructurados (tipo, qué intentó, parciales, alternativas), nunca silenciosos."),
        _c("❌ “Error” genérico", "falla", "El coordinator sabe que algo falló, pero no qué ni qué hacer.",
           {"D53_FORMATO": "generico", "D53_COMPARAR_TODOS": False}, "sin_info",
           "Avisar “Error” es suficiente.", "El error debe decir qué falló y qué alternativas hay."),
        _c("❌ Abortar todo el pipeline", "falla", "Una sola falla detiene todo: no hay reporte, ni siquiera con lo que sí funcionó.",
           {"D53_FORMATO": "abortar", "D53_COMPARAR_TODOS": False}, "sin_reporte",
           "Si un subagente falla, lo más seguro es detener todo.",
           "Se sigue con lo que hay: el coordinator usa los resultados parciales y anota el hueco en el reporte."),
        _c("⚖ Los tres (comparación)", "ok", "Los tres formatos ante la misma falla.", {"D53_COMPARAR_TODOS": True}, "comparacion")],
        "predice": _p("¿Qué hace el coordinator con la falla?",
                      {"sin_reporte": "No hay reporte: todo se detuvo por una falla", "informa": "Sabe qué falló y usa los resultados parciales", "oculta": "Cree que no había datos y sigue como si nada",
                       "sin_info": "Sabe que falló, pero no qué hacer", "comparacion": "Solo el estructurado le sirve"},
                      {"sin_reporte": "Abortar desperdicia lo que sí funcionó; lo correcto es seguir y anotar el hueco.", "informa": "El error estructurado le da todo para decidir.",
                       "oculta": "La falla silenciosa es la peor: el reporte sale incompleto sin aviso.",
                       "sin_info": "Un “Error” solo no dice si reintentar ni qué falta.",
                       "comparacion": "La misma falla, tres formas de reportarla."})},
    "5.4": {"casos": [
        _c("✅ Con scratchpad", "ok", "La fase 2 lee NOTAS.md y retoma sin volver a explorar.",
           {"D54_USAR_SCRATCHPAD": True, "D54_COMPARAR": False}, "retoma"),
        _c("❌ Sin notas", "falla", "La sesión nueva empieza de cero y vuelve a explorar todo.",
           {"D54_USAR_SCRATCHPAD": False, "D54_COMPARAR": False}, "reexplora",
           "La sesión nueva recordará lo que ya se exploró.",
           "Exploración larga → scratchpad (NOTAS.md) que sobrevive entre sesiones."),
        _c("⚖ Comparar", "ok", "La fase 2 con y sin notas.", {"D54_COMPARAR": True}, "comparacion")],
        "predice": _p("¿Qué pasa en la segunda sesión?",
                      {"retoma": "Retoma con lo que ya sabía", "reexplora": "Vuelve a explorar desde cero", "comparacion": "Con notas termina más rápido y mejor"},
                      {"retoma": "Los hallazgos viven en un archivo, no en el contexto.",
                       "reexplora": "Una sesión nueva no recuerda nada de la anterior.",
                       "comparacion": "Misma tarea: cambia si hay notas."})},
    "5.5": {"casos": [
        _c("✅ Precisión por tipo + calibración", "ok", "Mide la precisión de cada tipo de documento: los que fallan van siempre a revisión humana.",
           {"D55_DECISION": "por_tipo", "D55_UMBRAL": 0.8}, "por_tipo"),
        _c("❌ Decidir con la precisión global", "falla", "El global se ve alto y se quita la revisión a todo: los errores de las notas se cuelan.",
           {"D55_DECISION": "global"}, "global_engana",
           "Con 97% de precisión global ya se puede quitar la revisión humana.",
           "Mide por tipo de documento (y por campo) con muestreo estratificado: el global esconde la categoría que falla."),
        _c("❌ Confiar en la confianza sin calibrar", "falla", "Se acepta todo lo que el modelo dice que sabe: su confianza no siempre dice la verdad.",
           {"D55_DECISION": "umbral", "D55_UMBRAL": 0.5}, "errores_pasan",
           "Si el modelo dice 0.9 de confianza, acierta 9 de cada 10.",
           "La confianza declarada no está calibrada: calíbrala con datos etiquetados antes de usarla como umbral.")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"por_tipo": "Los tipos que fallan van a revisión y casi no se cuelan errores",
                       "global_engana": "Con el global alto se quita la revisión y se cuelan errores",
                       "global_ok": "El global no pasa del 90%: todo sigue en revisión",
                       "errores_pasan": "Se cuelan errores con confianza alta", "sin_errores": "Esta vez no se coló ningún error"},
                      {"por_tipo": "Medir por segmento muestra dónde falla; esa categoría no se automatiza.",
                       "global_engana": "Un promedio alto puede esconder una categoría que falla mucho: por eso se mide por tipo.",
                       "global_ok": "Esta vez el global no fue alto; aun así, la decisión correcta se toma por tipo.",
                       "errores_pasan": "La confianza que declara el modelo no está calibrada: hay que calibrarla con datos etiquetados.",
                       "sin_errores": "Esta vez no pasó, pero sin calibrar no sabes qué tan seguido pasa."})},
    "5.6": {"casos": [
        _c("✅ Con procedencia", "ok", "Cada afirmación con fuente y fecha; los conflictos se anotan.", {"D56_MODO": "con_procedencia"}, "trazable"),
        _c("❌ Resumen libre", "falla", "Se pierde de dónde salió cada dato y se elige una fuente sin decirlo.", {"D56_MODO": "libre"}, "sin_fuente",
           "Un buen resumen en prosa es suficiente.",
           "Cada afirmación con fuente y fecha; si las fuentes no coinciden, anota ambas."),
        _c("⚖ Los dos (comparación)", "ok", "Las mismas fuentes, con y sin procedencia.", {"D56_MODO": "ambos"}, "comparacion")],
        "predice": _p("¿Qué crees que pase con este caso?",
                      {"trazable": "Cada dato con su fuente y fecha", "sin_fuente": "Datos sin fuente; un conflicto se resuelve en silencio",
                       "comparacion": "Con procedencia se puede verificar todo"},
                      {"trazable": "La procedencia viaja con cada afirmación.",
                       "sin_fuente": "En prosa libre, la fuente se pierde y el conflicto desaparece.",
                       "comparacion": "Mismas fuentes: cambia el formato."})},
})


# ---------------------------------------------------------------------
#  Clase de cada caso ❌
#    trampa   = 🎓 Trampa de examen: suena bien pero el examen la marca como incorrecta.
#    producto = 🔧 Limitación del producto: falla hoy por cómo es el producto; en el examen no cuenta como error.
# ---------------------------------------------------------------------
# Temas que pregunta el examen y que el lab NO practica: la pestaña Estudiar lo avisa y manda a la guía.
NO_SE_PRACTICA = {
    "1.4": ["Multi-concern request: varios temas en un mensaje → descomponer, investigar en paralelo y unir en una sola respuesta."],
    "1.7": ["fork_session NO limpia el contexto obsoleto: lo hereda. Para empezar limpio, sesión nueva + resumen."],
    "2.1": ["Tool splitting y renaming: partir una tool genérica (manage_order) en varias con un solo trabajo."],
    "2.3": ["Scoped cross-role tool: darle al subagente de síntesis una tool acotada (verify_fact) para lo común y mandar lo complejo al coordinator."],
    "3.2": ["context: fork en un skill: corre en un subagente aparte para no llenar el contexto principal."],
    "3.5": ["Interview pattern: pedirle a Claude que te haga preguntas antes de implementar, cuando el dominio es nuevo o hay decisiones que no has considerado."],
    "4.4": ["Cuando el dato no está en el documento, reintentar no sirve: va null o revisión humana. No tiene caso propio; se ve dentro del caso ✅ (factura «sin_fecha»)."],
    "5.4": ["State manifest: para retomar tras una caída, el estado se guarda en un archivo que el coordinator lee al reanudar."],
}


CLASES = {
    "trampa": {"es": "🎓 Trampa de examen", "en": "🎓 Exam trap",
               "ayuda_es": "Suena bien, pero en el examen es la respuesta incorrecta.",
               "ayuda_en": "Sounds right, but on the exam it is the wrong answer."},
    "producto": {"es": "🔧 Limitación del producto", "en": "🔧 Product limitation",
                 "ayuda_es": "Falla hoy por cómo funciona el producto. En el examen no cuenta como error: responde como dice la guía.",
                 "ayuda_en": "It fails today because of how the product works. On the exam it is not the wrong answer: answer as the guide says."},
}
for _extras in EXTRAS.values():
    for _caso in _extras.get("casos", []):
        if _caso.get("tipo") == "falla":
            _caso.setdefault("clase", "trampa")


# ---------------------------------------------------------------------
#  Los 6 escenarios del examen (el examen elige 4 al azar) y qué demos los practican
# ---------------------------------------------------------------------
ESCENARIOS = [
    {"n": 1, "es": "Agente de soporte al cliente", "en": "Customer Support Resolution Agent",
     "prueba_es": "Conversación de varios turnos, tools para consultar cuentas, cuándo escalar a una persona, reglas que se cumplen siempre.",
     "prueba_en": "Multi-turn conversation, tools for account lookups, when to escalate to a person, rules that must always hold.",
     "demos": ["1.1", "1.4", "5.2", "1.5", "2.1", "2.2", "5.1"]},
    {"n": 2, "es": "Generar código con Claude Code", "en": "Code Generation with Claude Code",
     "prueba_es": "CLAUDE.md, skills y slash commands, rules por ruta, plan mode, iterar con ejemplos y tests.",
     "prueba_en": "CLAUDE.md, skills and slash commands, path rules, plan mode, iterating with examples and tests.",
     "demos": ["3.1", "3.2", "3.3", "3.4", "3.5", "2.5"]},
    {"n": 3, "es": "Sistema de investigación multiagente", "en": "Multi-Agent Research System",
     "prueba_es": "Dividir el trabajo, aislar a cada subagente, juntar resultados con fuentes y manejar un subagente que falla.",
     "prueba_en": "Splitting the work, isolating each subagent, combining results with sources and handling a subagent that fails.",
     "demos": ["1.2", "1.3", "1.6", "2.2", "2.3", "5.3", "5.6"]},
    {"n": 4, "es": "Productividad del desarrollador", "en": "Developer Productivity with Claude",
     "prueba_es": "Configurar Claude Code y MCP, memoria entre sesiones, qué es del equipo y qué es personal, explorar código grande.",
     "prueba_en": "Configuring Claude Code and MCP, memory across sessions, team vs personal settings, exploring a large codebase.",
     "demos": ["1.7", "2.4", "2.5", "3.1", "5.4"]},
    {"n": 5, "es": "Claude Code en CI/CD", "en": "Claude Code for CI/CD",
     "prueba_es": "Modo no interactivo (-p), salida JSON con schema, comentarios de PR, criterios de revisión y revisión independiente.",
     "prueba_en": "Non-interactive mode (-p), JSON output with a schema, PR comments, review criteria and independent review.",
     "demos": ["3.6", "4.1", "4.6", "1.6", "4.5"]},
    {"n": 6, "es": "Extracción de datos estructurados", "en": "Structured Data Extraction",
     "prueba_es": "JSON schema, validar y reintentar, ejemplos few-shot, documentos que no encajan y revisión humana por confianza.",
     "prueba_en": "JSON schema, validate and retry, few-shot examples, documents that don't fit and confidence-based human review.",
     "demos": ["4.2", "4.3", "4.4", "4.5", "5.5", "2.3"]},
]


# Casos ❌ que hoy el modelo a veces resuelve bien solo: qué dice el ticket cuando no cayó en la trampa
SI_NO_FALLA = {
    ("1.4", "❌ Regla solo en el prompt"): "Hoy el modelo pidió verificar antes de reembolsar: se cuidó solo. Pero con la regla "
        "solo en el prompt nada lo garantiza; con otra presión o en otra corrida puede saltársela. En el examen: la regla va en código.",
    ("1.4", "❌ Solo prompt, 5 intentos"): "Esta vez respetó la regla en todos los intentos. Que salga bien 5 de 5 no es una "
        "garantía: con dinero en juego, la regla va en código (gate o hook).",
    ("1.5", "❌ Sin PreToolUse"): "Hoy el modelo ni intentó el reembolso: se frenó solo. Sin el hook nada lo impide si "
        "mañana sí lo intenta. En el examen: la regla de dinero va en un hook PreToolUse.",
    ("2.5", "❌ Sin Grep"): "Hoy encontró todo sin Grep (abrió archivos o buscó de otra forma). En un repo grande eso cuesta "
        "muchos más turnos y tokens. En el examen: para buscar contenido, Grep.",
    ("2.5", "❌ Sin Glob"): "Hoy encontró los tests sin Glob (Grep también puede filtrar por nombre). En el examen: "
        "archivos por patrón de nombre → Glob; contenido → Grep.",
    ("3.2", "❌ Descripción vaga (B)"): "Hoy usó el skill aunque la descripción es vaga (era el único que había). Con varios "
        "skills, una descripción vaga hace que Claude no sepa cuál usar. En el examen: la descripción decide.",
    ("4.1", "❌ “Sé conservador”"): "Hoy el prompt vago acertó en todo. Con otros tickets o en otra corrida se mueve la línea: "
        "sin criterios concretos no sabes dónde está. En el examen: criterios explícitos.",
    ("4.6", "❌ Misma sesión"): "Hoy la revisión en la misma sesión también encontró los errores: los modelos actuales se "
        "autorrevisan mejor. Aun así arrastra el razonamiento con que escribió y tiende a confirmarlo. En el examen: "
        "instancia independiente.",
    ("5.1", "❌ Dato clave a la mitad (C)"): "Hoy encontró el dato aunque estaba a la mitad: los modelos actuales fallan menos "
        "en esto. En el examen el patrón sigue: lo importante arriba o al final, con encabezados.",
    ("5.6", "❌ Resumen libre"): "Hoy el resumen libre conservó las fuentes. Nada lo obliga: en otra corrida las pierde. En el "
        "examen: cada afirmación viaja con su fuente y fecha, en formato estructurado.",
}
for (_demo, _nombre), _texto in SI_NO_FALLA.items():
    for _caso in EXTRAS.get(_demo, {}).get("casos", []):
        if _caso["nombre"] == _nombre:
            _caso["si_no_falla"] = _texto


def escenarios_de(demo: str) -> list[dict]:
    """Los escenarios del examen donde aparece esta demo."""
    return [e for e in ESCENARIOS if demo in e["demos"]]


# ---------------------------------------------------------------------
#  Hoja de repaso como mini-escenarios: la pista corta de la guía → una situación como en el examen
# ---------------------------------------------------------------------
# La respuesta que suena bien pero está mal, para cada situación de la hoja de repaso (el examen es de opción
# múltiple: reconocer el distractor es la mitad del trabajo).
DISTRACTORES = {
    "El agente se detiene a medias": "Subir max_tokens o el tope de iteraciones",
    "Falta un tema en el reporte": "Agregar más subagentes",
    "Reporte sin fuentes": "Pedirle al sintetizador que cite mejor",
    "Subagentes independientes y lentos": "Un modelo más rápido para cada subagente",
    "Dinero, seguridad o compliance": "Reforzar la regla en el system prompt",
    "Formatos de datos mezclados": "Explicar los formatos en el prompt",
    "Últimos archivos mal revisados": "Un modelo con ventana de contexto más grande",
    "Archivos cambiaron tras la sesión": "fork_session para empezar limpio",
    "Claude elige la tool equivocada": "Una regla con palabras clave en el system prompt",
    "Reintenta una búsqueda sin resultados": "Limitar el número de reintentos",
    "Error de regla de negocio": "Reintentar con backoff",
    "Un agente con 18 tools": "Un modelo más grande",
    "Muchas vueltas por algo simple": "Darle todas las tools a todos los agentes",
    "Se exige salida estructurada": "Pedir el JSON en el prompt",
    "MCP para todo el equipo": "Que cada quien lo configure en su ~/.claude.json",
    "¿Quién llama esta función?": "Glob con el nombre de la función",
    "El dev nuevo no recibe las convenciones": "Pasarle una copia de tu ~/.claude",
    "Algo DEBE cumplirse siempre": "Escribirlo en MAYÚSCULAS en el CLAUDE.md",
    "Un skill con output muy largo": "Pedirle al skill que resuma al final",
    "Tests repartidos en 50+ carpetas": "Un CLAUDE.md en cada carpeta",
    "Varios diseños válidos": "Ejecución directa para ahorrar tiempo",
    "Bug claro en un archivo": "Plan mode por si acaso",
    "Prosa interpretada distinto cada vez": "Explicarlo con más detalle en prosa",
    "El job de CI se queda esperando": "Darle más tiempo al job",
    "Check pre-merge": "Batch API: es 50% más barato",
    "“Sé conservador” en el prompt": "Agregar un umbral de confianza",
    "Una categoría con muchos falsos positivos": "Pedirle que sea más estricto en todo",
    "Formato inconsistente": "Instrucciones más largas y detalladas",
    "JSON roto": "Pedir “responde SOLO con JSON”",
    "Inventa datos que faltan": "Agregar ejemplos few-shot",
    "La suma no cuadra": "Reintentar con “inténtalo de nuevo”",
    "El dato no está en el documento": "Reintentar hasta que lo encuentre",
    "Reporte nocturno": "La API síncrona en paralelo",
    "SLA de 30 h con la Batch API": "Un lote al día, a medianoche",
    "PR enorme con revisión dispareja": "Pedirle al mismo agente que se revise",
    "Montos y fechas perdidos al resumir": "Un resumen más largo",
    "Hallazgos ignorados a la mitad": "Un modelo con ventana de contexto más grande",
    "Tool output de 40 campos": "Pedirle que ignore los campos que no sirven",
    "El cliente pide un humano": "Intentar resolverlo primero",
    "Cliente molesto, caso simple": "Escalar por el enojo",
    "Tres “Juan Pérez”": "Elegir al cliente más reciente",
    "Subagente con timeout": "Devolver “sin datos” y seguir",
    "“Patrones típicos” en vez de clases": "Repetir la exploración desde cero",
    "97% de precisión global": "Quitar la revisión humana a todo",
    "Dos fuentes no coinciden": "Promediar los dos valores",
}

REPASO_MINI = {
    "El agente se detiene a medias": "Tu agente de soporte escribe “Déjame revisar tu pedido…” y termina sin consultar nada. ¿Qué revisas en el loop?",
    "Falta un tema en el reporte": "Pides un reporte sobre la tienda y solo habla de marketing; nadie investigó inventario ni logística. ¿Dónde está la causa?",
    "Reporte sin fuentes": "El reporte final tiene buenos datos, pero nadie sabe de qué documento salió cada uno. ¿Qué cambias en lo que devuelven los subagentes?",
    "Subagentes independientes y lentos": "Tres subagentes que no dependen entre sí tardan 3 minutos porque corren uno tras otro. ¿Cómo los lanzas?",
    "Dinero, seguridad o compliance": "Un reembolso de más de $10,000 nunca debe salir sin verificar al cliente, y el prompt a veces no se respeta. ¿Qué pones?",
    "Formatos de datos mezclados": "Una tool devuelve fechas como 2026-03-01, otra como 01/03/26 y otra en timestamp. ¿Dónde lo normalizas?",
    "Últimos archivos mal revisados": "En una revisión de 14 archivos, los primeros salen bien y los últimos casi sin comentarios. ¿Qué cambias?",
    "Archivos cambiaron tras la sesión": "Ayer el agente analizó el repo; hoy alguien cambió varios archivos. ¿Reanudas o empiezas de nuevo?",
    "Claude elige la tool equivocada": "Hay get_customer y lookup_order con descripciones casi iguales, y Claude usa la que no es. ¿Cuál es el primer arreglo?",
    "Reintenta una búsqueda sin resultados": "El cliente no tiene pedidos en 2024, pero el agente reintenta la búsqueda una y otra vez. ¿Qué falta en la respuesta de la tool?",
    "Error de regla de negocio": "La tool contesta “el reembolso pasa el límite permitido”. ¿El agente debe reintentar?",
    "Un agente con 18 tools": "Un solo agente tiene 18 tools y cada vez elige peor. ¿Qué haces?",
    "Muchas vueltas por algo simple": "El agente redactor tiene que pedirle al investigador cada dato pequeño que quiere confirmar. ¿Cómo lo evitas?",
    "Se exige salida estructurada": "Necesitas que Claude siempre llame una tool de extracción y nunca conteste en texto. ¿Qué tool_choice usas (según el examen)?",
    "MCP para todo el equipo": "Todo el equipo debe tener el mismo servidor MCP sin compartir el token en git. ¿Dónde y cómo lo configuras?",
    "¿Quién llama esta función?": "Vas a cambiar calcular_total() y necesitas saber desde dónde la llaman. ¿Qué tool usas?",
    "El dev nuevo no recibe las convenciones": "Un compañero nuevo clona el repo y Claude no sigue las convenciones que tú sí ves. ¿Dónde estaban?",
    "Algo DEBE cumplirse siempre": "“Nunca hagas push a main” está en el CLAUDE.md y a veces no se respeta. ¿Qué usas para que sea obligatorio?",
    "Un skill con output muy largo": "Un skill genera un análisis enorme que llena la conversación principal. ¿Qué agregas al skill?",
    "Tests repartidos en 50+ carpetas": "Las convenciones de los tests aplican a archivos repartidos en más de 50 carpetas. ¿Cómo las cargas solo cuando hacen falta?",
    "Varios diseños válidos": "Te piden migrar la autenticación y hay varias formas razonables de hacerlo. ¿Cómo empiezas?",
    "Bug claro en un archivo": "Un error tipográfico rompe una función en un solo archivo y ya sabes la corrección. ¿Plan mode o directo?",
    "Prosa interpretada distinto cada vez": "Describes el formato que quieres en un párrafo y Claude lo entiende distinto en cada intento. ¿Qué agregas?",
    "El job de CI se queda esperando": "El pipeline llama a Claude Code y el job se queda colgado hasta el timeout. ¿Qué falta?",
    "Check pre-merge": "Quieren abaratar la revisión que bloquea cada merge pasándola a Batch. ¿Conviene?",
    "“Sé conservador” en el prompt": "Le pusiste “sé conservador” al revisor y sigue reportando cosas sin importancia. ¿Qué cambias en el prompt?",
    "Una categoría con muchos falsos positivos": "Los hallazgos de “estilo” son casi todos falsos positivos y el equipo ya no confía en el revisor. ¿Qué haces primero?",
    "Formato inconsistente": "Las extracciones salen con un formato distinto cada vez, sobre todo en casos ambiguos. ¿Qué agregas?",
    "JSON roto": "Pides JSON en el prompt y a veces llega con comas de más o sin cerrar. ¿Cómo lo garantizas?",
    "Inventa datos que faltan": "El documento no trae la fecha de entrega y el modelo pone una inventada. ¿Qué cambias en el schema?",
    "La suma no cuadra": "La extracción dice total 1,250 pero las líneas suman 1,205. ¿Cómo reintentas?",
    "El dato no está en el documento": "Reintentaste 3 veces y el RFC sigue vacío porque el documento no lo trae. ¿Qué sigue?",
    "Reporte nocturno": "Cada noche se procesan 10,000 documentos y nadie espera el resultado en el momento. ¿Qué API usas?",
    "SLA de 30 h con la Batch API": "Prometiste procesar cada documento en menos de 30 h y un lote puede tardar hasta 24 h. ¿Cada cuánto mandas lotes?",
    "PR enorme con revisión dispareja": "Un PR de 30 archivos recibe una revisión buena al inicio y floja al final. ¿Cómo lo divides?",
    "Montos y fechas perdidos al resumir": "Después de resumir la conversación, el agente ya no recuerda el monto ni la fecha del pedido. ¿Dónde debían ir?",
    "Hallazgos ignorados a la mitad": "En un input largo, el modelo usa lo del inicio y lo del final pero ignora lo de en medio. ¿Cómo lo acomodas?",
    "Tool output de 40 campos": "Una tool devuelve 40 campos y el agente solo necesita 5. ¿Qué haces antes de pasárselo?",
    "El cliente pide un humano": "El cliente escribe “quiero hablar con una persona”, aunque el caso es sencillo. ¿Qué hace el agente?",
    "Cliente molesto, caso simple": "El cliente está enojado, pero su caso se resuelve con un cambio de dirección. ¿Escalas?",
    "Tres “Juan Pérez”": "La búsqueda por nombre devuelve tres clientes llamados Juan Pérez. ¿Qué hace el agente?",
    "Subagente con timeout": "Un subagente se queda sin tiempo y devuelve una lista vacía como si todo estuviera bien. ¿Qué debió devolver?",
    "“Patrones típicos” en vez de clases": "Tras una exploración larga, el agente habla de “patrones típicos” en lugar de las clases que ya había encontrado. ¿Qué le falta?",
    "97% de precisión global": "La extracción tiene 97% de precisión global y proponen quitar la revisión humana. ¿Qué revisas antes?",
    "Dos fuentes no coinciden": "Un informe dice 12% y otro 15% para el mismo dato. ¿Qué pone el reporte?",
}

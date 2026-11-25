
# CCAR-F · Guía de los labs (Dominios 1 a 5)

Esta guía explica cada demo **antes de correrla**: de qué trata, qué pasa paso a paso, qué se le manda a Claude,
dónde está en el código, qué cambiar y qué esperar, y qué pregunta el examen.

El mismo texto aparece en la terminal antes de cada demo, en el panel web (**📖 Guía de esta demo**) y, resumido,
arriba de cada demo en los ejemplos (`ejemplos_html/`). También se puede leer en la terminal sin correr nada:

```bash
python lab_dominio1.py guia        # todas las guías del dominio 1
python lab_dominio2.py guia 2.4    # solo la de la demo 2.4
```

## Antes de empezar: tres ideas que se repiten en todas las demos

**1. Claude no ejecuta tools, las pide.** Le describes tus tools (nombre, descripción, parámetros). Cuando quiere
usar una, responde con un bloque `tool_use` y `stop_reason = "tool_use"`. **Tu código** ejecuta la función y le
regresa el resultado en un bloque `tool_result`.

**2. Anatomía de una tool.** Es un diccionario con tres partes:

```python
{
    "name": "lookup_order",                      # cómo la llama Claude
    "description": "Busca un pedido por...",     # lo que más pesa para decidir cuándo usarla (Claude lee name, description e input_schema)
    "input_schema": {                            # JSON Schema de los parámetros
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "ej. #12345"}},
        "required": ["order_id"],
    },
}
```

**3. ¿Quién corre el loop?**

| | Messages API (`anthropic`) | Agent SDK (`claude-agent-sdk`) |
|---|---|---|
| Demos | 1.1–1.4, 1.6, 1.7 B, 2.1–2.3, 3.5, D4, D5 (menos 5.4) | 1.5, 1.7 A, 2.4, 2.5, 3.1–3.4, 5.4 (3.6 usa el CLI) |
| El agentic loop | Lo escribes tú (un `for`) | Lo corre el SDK |
| Tools | Diccionarios + tus funciones | `@tool`, servidores MCP y built-ins (Read, Grep…) |
| Controles | `if` en tu código | `hooks`, `allowed_tools`, `permission_mode` |
| Historial | Mandas todo en cada llamada | Lo guarda la sesión (`resume`, `fork_session`) |

## Cómo usar esta guía

1. Lee la sección de la demo antes de correrla. Fíjate sobre todo en "Experimentos: qué cambiar y qué esperar".
2. Corre la demo como viene (el caso ✅).
3. Cambia la variable del bloque **🔧 CAMBIA AQUÍ** (o elige un caso ❌ en el panel) y vuelve a correr.
4. Compara: ¿qué cambió y por qué?
5. Termina con "Lo que pregunta el examen".

En el panel (`python panel.py`), la **🧭 Ruta de estudio** te lleva por esos mismos pasos.

---

# Dominio 1 · Agentic Architecture & Orchestration

## Demo 1.1 · Agentic loop y stop_reason

### De qué trata
El **agentic loop**: el ciclo con el que cualquier agente trabaja. Claude **nunca ejecuta** las tools: solo
**pide** una (bloque `tool_use`). Tu código la ejecuta, le regresa el resultado (`tool_result`) y vuelve a llamar
a Claude. El ciclo termina cuando `stop_reason` es `"end_turn"`.

### Qué pasa al correrla, paso a paso
1. Se manda la pregunta de Ana (`D11_PREGUNTA`): pedido #12345, taza rota, quiere $450.
2. Claude responde con `stop_reason = "tool_use"` y pide `get_customer` (verificar identidad).
3. Tu código ejecuta la función Python `get_customer()` con los datos falsos y devuelve un `tool_result`
   dentro de un mensaje con rol `user`. Lo ves en el panel **"⚙ tu código ejecutó…"**.
4. Se repite: `lookup_order("#12345")` (total $1,850, es de Ana) y luego `process_refund(450)`.
5. Claude responde con `stop_reason = "end_turn"` y un texto para el cliente. Fin del loop.
6. Tabla resumen: iteraciones, tools en orden y el reembolso registrado (folio `RF-0001`).

Normalmente son 3 o 4 iteraciones. A veces Claude pide 2 tools en la misma respuesta: las verás en una sola
iteración y sus 2 `tool_result` viajan juntos en **un** mensaje `user`.

### Lo que se le manda a Claude
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

### Dónde está en el código
- Definición de tools: `TOOL_GET_CUSTOMER`, `TOOL_LOOKUP_ORDER`, `TOOL_PROCESS_REFUND`.
- Funciones reales: `get_customer()`, `lookup_order()`, `process_refund()`.
- `FUNCIONES_TOOLS` conecta el nombre que pide Claude con la función Python; `ejecutar_tool()` la ejecuta.
- El loop: el `for iteracion in ...` dentro de `demo_1_1()`.

### Experimentos: qué cambiar y qué esperar
- `D11_MODO_PARADA = "hay_texto"` (antipatrón): el loop se corta en cuanto la respuesta trae texto. Como Claude
  suele escribir "Déjame revisar…" **junto con** un `tool_use`, verás la alerta *"Quedaron tools pedidas SIN
  ejecutar"* y no habrá reembolso. Si en esa corrida Claude no escribió texto, repítela.
- `D11_MAX_TOKENS = 40`: la respuesta se corta y `stop_reason` es `"max_tokens"`. No terminó, se quedó sin espacio.
- `D11_MAX_ITERACIONES = 2`: la red de seguridad corta el loop antes de terminar.

### Lo que pregunta el examen
- Continuar mientras `stop_reason == "tool_use"`; terminar con `"end_turn"`.
- Antipatrones: decidir por el texto de la respuesta, o usar un tope de iteraciones como forma **normal** de parar.
- Los resultados de las tools se agregan al historial para que Claude razone el siguiente paso.

## Demo 1.2 · Coordinator + subagentes (hub-and-spoke)

### De qué trata
El patrón **hub-and-spoke**: un **coordinator** divide la tarea, le manda cada parte a un **subagente**, recibe
los resultados y escribe la síntesis. Los subagentes no hablan entre sí: todo pasa por el coordinator.

Aquí cada subagente es una llamada **nueva** a la Messages API con historial vacío. Eso es justo lo que define
a un subagente: **no hereda la conversación** del coordinator, solo ve lo que el coordinator le escribe.
(En el Agent SDK esto se hace con la tool `Agent`, antes llamada `Task`, y un `AgentDefinition`.)

### Qué pasa al correrla, paso a paso
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

### Lo que se le manda a Claude
- **Al coordinator:** system prompt + la tool `TOOL_DELEGAR`:
  - `subtema` (string): qué investigar.
  - `contexto` (string): los datos del negocio que el subagente necesita, porque no ve nada más.
- **A cada subagente:** otro system prompt ("máximo 4 viñetas") y **un solo** mensaje con subtema + contexto.
  Sin tools y sin historial.

### Por qué "divide mal las asignaciones" (modo `"estrecha"`)
Con `D12_DESCOMPOSICION = "estrecha"` el código agrega al system prompt del coordinator:

> *"Divide el tema SOLO en subtemas de marketing digital (redes sociales, anuncios, influencers)."*

Qué vas a ver:
- Los subagentes hacen **bien** su trabajo: sus viñetas sobre redes sociales o anuncios son buenas.
- Pero nadie investigó inventario, logística, precios ni atención al cliente, porque **nunca se los asignaron**.
- El reporte final sale incompleto y la tabla de cobertura marca varias áreas en rojo.

La falla está en la **descomposición del coordinator**, no en los subagentes. En la vida real nadie escribe "solo
marketing" a propósito. Pasa por cosas más sutiles: el prompt del coordinator da ejemplos de una sola área, o
interpreta el tema de forma estrecha ("vender más" = "hacer publicidad").

### Cómo corregirlo
1. **Arreglar el prompt del coordinator**: pedir explícitamente que cubra todas las dimensiones del problema
   (o listarlas) y no sesgarlo con ejemplos de una sola área. Es el modo `"amplia"`.
2. **Agregar un paso de verificación de cobertura**: antes de escribir el reporte, el coordinator revisa los
   resultados contra lo que debería cubrir y **vuelve a delegar** lo que falte (refinamiento iterativo).
   La tabla de esta demo es una versión simple de ese chequeo.
3. **No "arreglar" a los subagentes** (otro modelo, más tokens, prompts más largos): no son el problema.

Nota: el chequeo de cobertura busca palabras exactas. Si el reporte dice "envíos" en vez de "logística", la tabla
dirá NO aunque sí lo cubra. Léelo con calma.

### Dónde está en el código
- `TOOL_DELEGAR`, `correr_subagente()` y `demo_1_2()`. El sesgo está en la variable `sesgo` dentro de `demo_1_2()`.

### Lo que pregunta el examen
- Si al reporte final le falta un tema entero, la causa raíz suele ser la **descomposición del coordinator**.
- El subagente no hereda el historial: el contexto se le pasa **explícito** en su prompt.
- El coordinator decide qué subagentes invocar según la consulta, en lugar de pasar siempre por todos.

## Demo 1.3 · Context passing y paralelismo

### De qué trata
Dos ideas: **cómo pasar contexto entre agentes sin perder información** (parte A) y
**cómo correr subagentes en paralelo** (parte B).

### Parte A, paso a paso: ¿sobreviven las fuentes?
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

### Parte B, paso a paso: paralelismo
1. Un coordinator recibe 3 proveedores y emite **3 `tool_use` en una sola respuesta**.
2. Tu código ejecuta los 3 subagentes con un `ThreadPoolExecutor` (`D13_PARALELO = True`) o uno tras otro.
3. Compara el **tiempo real total** contra la **suma** de los tiempos de cada subagente.

Ojo con quién hace qué: Claude permite el paralelismo al pedir varias tools **en la misma respuesta**. Quien las
ejecuta en paralelo es tu código (o el Agent SDK, que lo hace solo).

### Lo que se le manda a Claude
- `TOOL_REPORTAR` con un `array` de objetos (`afirmacion`, `fuente_id`, `fecha_fuente`) y
  `tool_choice = {"type": "tool", "name": "reportar_hallazgos"}`.
- `TOOL_DELEGAR` (la misma de la demo 1.2) para la parte B.

### Dónde está en el código
`DOCS_PROVEEDORES`, `TOOL_REPORTAR`, `demo_1_3_parte_a()`, `demo_1_3_parte_b()`. `D13_PARTE` elige la parte.

### Experimentos
- `D13_FORMATO = "texto"` y compara la columna "Citas con id".
- `D13_PARALELO = False`: el tiempo total se vuelve la suma de todos.

### Lo que pregunta el examen
- Pasar resultados de agentes anteriores **completos y estructurados** en el prompt del subagente.
- Separar contenido de metadatos (fuente, fecha, página) para conservar la atribución.
- Varias llamadas a `Agent`/`Task` en **una** respuesta del coordinator = subagentes en paralelo.

### Parte C: subagentes reales (Agent SDK)
`D13_PARTE = "C"` usa el Agent SDK de verdad: el subagente se define con `AgentDefinition` (descripción, prompt y
tools) y el coordinator lo lanza con la tool **Agent** (en el examen, **Task**). Con `D13_PERMITIR_AGENT = False`
el subagente sigue definido, pero sin `Agent`/`Task` en `allowed_tools` el coordinator **no puede** lanzarlo.
En el examen: sin Task en `allowedTools` no hay subagentes.

## Demo 1.4 · Enforcement: prerequisite gate + handoff

### De qué trata
**Enforcement programático**: cuando una regla involucra dinero, seguridad o cumplimiento, escribirla en el prompt
no basta (el modelo la sigue casi siempre, no siempre). Un **gate** en tu código la hace imposible de saltar.
Y cuando hay que escalar, el **handoff** a un humano lleva un resumen estructurado.

### Qué pasa al correrla, paso a paso
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

### Lo que se le manda a Claude
- `system` con la regla escrita, porque también conviene decírsela.
- `TOOL_ESCALAR` con los 5 campos del slide: `customer_id`, `summary`, `root_cause`,
  `refund_amount` y `recommended_action`. Son obligatorios porque **el humano no ve la conversación**.

### Dónde está en el código
- `ejecutar_con_gate()` dentro de `demo_1_4()`: el gate es un `if` en **tu** dispatcher, antes de llamar a la función.
- En el Agent SDK, el mismo gate se hace con un hook `PreToolUse` (demo 1.5).

### Experimentos
- `D14_MODO = "solo_prompt"`: no hay ningún chequeo en el código. Es probable que Claude igual se niegue, y está
  bien: el punto es que **nada lo garantiza**. La prueba directa del final lo deja claro.
- Cambia `D14_PREGUNTA` para dar el correo de Ana y pedir $300 del #12345: debe pasar el gate.
- `D14_HANDOFF = "libre"`: escalar_a_humano solo pide una nota. Mira qué le falta a quien recibe el caso.
- `D14_REPETIR = 5` con `"solo_prompt"`: la misma conversación 5 veces; cuenta en cuántas se saltó la regla.

### Lo que pregunta el examen
- Reglas críticas → enforcement en código (gates, hooks), no solo instrucciones.
- Handoff con resumen estructurado: el humano no tiene acceso al historial.

## Demo 1.5 · Hooks PreToolUse / PostToolUse (Agent SDK)

### De qué trata
Los **hooks** del Agent SDK: funciones tuyas que el SDK ejecuta automáticamente alrededor de cada tool.
- **`PreToolUse`** corre **antes**: puede bloquear la tool (`permissionDecision: "deny"`).
- **`PostToolUse`** corre **después**: puede cambiar el resultado antes de que Claude lo vea.

Diferencia con 1.1–1.4: aquí **no hay un `for` tuyo**. El Agent SDK corre el agentic loop; tú solo configuras
tools, hooks y permisos.

### Qué pasa al correrla, paso a paso
1. El agente revisa el envío del #12346 con `check_shipping`. La paquetería devuelve datos crudos y mezclados:
   `"DMG"`, `"30-10-2026"`, una fecha en epoch.
2. **PostToolUse** se dispara: la tabla **"antes y después"** muestra cómo `normalizar_envio()` lo convierte en
   `"dañado en tránsito"` y fechas ISO. Claude solo ve la versión limpia.
3. El agente intenta `process_refund` por $12,500.
4. **PreToolUse** se dispara (panel magenta), ve que supera $10,000 y responde **deny** con un motivo.
5. La tool **no corre**: nunca aparece *"💸 SE EJECUTÓ process_refund"*. Claude recibe el motivo como
   `tool_result` con error y le explica al cliente que se escalará.
6. El `ResultMessage` final trae turnos, `session_id` y costo.

### Dónde se configuran los hooks
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

### Las tools de esta demo
Se definen con el decorador `@tool(nombre, descripción, parámetros)` y se empaquetan en un servidor MCP
**en el mismo proceso** con `create_sdk_mcp_server(name="tiendita")`. Por eso se llaman
`mcp__tiendita__check_shipping` y `mcp__tiendita__process_refund`. Además:
- `tools=[]` apaga las tools built-in (Read, Bash…), así que el agente solo tiene las nuestras.
- `allowed_tools` las aprueba sin preguntar.

### Dónde está en el código
`ENVIOS_CRUDOS`, `normalizar_envio()`, y dentro de `demo_1_5()`: `t_check_shipping`, `t_process_refund`,
`hook_pre_reembolso`, `hook_post_envio` y el dict `hooks`. Las opciones del agente se arman con `opciones_base()`.

### Experimentos
- `D15_ACTIVAR_PRETOOLUSE = False`: el reembolso de $12,500 **sí** se ejecuta.
- `D15_ACTIVAR_POSTTOOLUSE = False`: Claude ve `"DMG"` y `"30-10-2026"` tal cual y tiene que adivinar.
- `D15_BLOQUEO_EN = "post"`: el bloqueo pasa a PostToolUse. Llega tarde: el reembolso ya se hizo.

### Lo que pregunta el examen
- Hooks = garantía **determinista**; prompt = probabilística.
- `PostToolUse` para normalizar formatos de distintas fuentes antes de que el agente los procese.
- `PreToolUse` para bloquear acciones que violan políticas y redirigir a escalamiento.

## Demo 1.6 · Prompt chaining y multi-pass review

### De qué trata
Dos maneras de **descomponer** un trabajo grande:
- **Prompt chaining** (parte A): pasos fijos que ya conoces, cada uno en su propia llamada.
- **Multi-pass review** (parte B): revisar archivo por archivo y luego hacer una pasada solo de integración.

### Parte A, paso a paso
1. **Paso 1 · extraer**: se fuerza la tool `extraer_datos` sobre la reseña (`D16_RESENA`). Salida en JSON:
   `pedido`, `producto`, `problema`, `fecha_limite`, `sentimiento`.
2. **Paso 2 · clasificar**: otra llamada que **solo ve el JSON** del paso 1 y clasifica la urgencia.
3. **Paso 3 · responder**: otra llamada redacta la respuesta usando los datos y la urgencia.

Detalle: `fecha_limite` acepta `null` (`"type": ["string", "null"]`), así el modelo no inventa una fecha
cuando no la hay. Aquí sí hay fecha ("antes del 20 de diciembre").

### Parte B, paso a paso
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

### Dónde está en el código
`TOOL_EXTRAER`, `demo_1_6_parte_a()`, `ARCHIVOS_TIENDITA`, `demo_1_6_parte_b()`.

### Experimentos
- Cambia `D16_RESENA` por una reseña sin fecha límite y revisa que `fecha_limite` salga `null`.
- Agrega más archivos a `ARCHIVOS_TIENDITA` y compara `"una_pasada"` contra `"multipass"`.
- `D16_NUM_ARCHIVOS = 14`: el bug que cruza archivos queda al final. Compara `"una_pasada"` contra `"multipass"`.

### Lo que pregunta el examen
- Prompt chaining para flujos predecibles; descomposición dinámica para investigación abierta.
- Revisiones grandes: pasadas locales por archivo + una pasada de integración entre archivos.

## Demo 1.7 · Sesiones: resume, fork, contexto obsoleto

### De qué trata
Cómo continuar el trabajo entre sesiones sin arrastrar información vieja.

### Parte A, paso a paso (Agent SDK)
Cuatro corridas cortas, sin tools:
1. **Original**: *"la taza cuesta $299"*. Se guarda el `session_id`.
2. **`resume=session_id`**: misma sesión (mismo id). Recuerda los $299.
3. **`resume` + `fork_session=True`**: copia la historia y crea una sesión **nueva** (otro id). En esa rama la
   taza pasa a $349.
4. **De vuelta a la original con `resume`**: sigue diciendo $299. El fork no la tocó.

La tabla final muestra los `session_id`: el 1, 2 y 4 son iguales; el 3 es distinto. En la terminal de Claude
Code lo equivalente es `claude --resume <id>`.

### Parte B, paso a paso (contexto obsoleto)
Se arma a mano un historial donde Claude ya leyó `precios.txt` (taza = $299). Luego el archivo cambió ($349).
- `"resume"`: se continúa la misma conversación y se relee el archivo. El historial tiene **los dos** valores.
  Al pedirle todos los precios que conoce, lista ambos: el viejo sigue ahí y puede confundir.
- `"nueva_sesion"`: sesión nueva con un **resumen** de lo vigente + releer solo lo que cambió. El 299 ya no existe.

### Dónde está en el código
`demo_1_7_parte_a()` (opciones `resume` y `fork_session` en `opciones_base()`) y `demo_1_7_parte_b()`.

### Experimentos
- `D17_ESTRATEGIA = "nueva_sesion"` y compara la respuesta.

### Lo que pregunta el examen
- `resume` cuando el contexto anterior sigue siendo válido; dile al agente qué archivos cambiaron.
- Sesión nueva + resumen estructurado cuando los resultados de tools anteriores ya son obsoletos.
- `fork_session` para explorar dos enfoques desde la misma base.

# Dominio 2 · Tool Design & MCP Integration

## Demo 2.1 · Descripciones de tools y selección

### De qué trata
Claude elige una tool leyendo solo tres cosas: su **name**, su **description** y su **input_schema**. No ve tu
código ni sabe qué hace la función por dentro. Si dos descripciones se parecen, la selección se vuelve una moneda
al aire. Mejorar las descripciones es el **primer arreglo**, antes que ejemplos few-shot o un clasificador.

### Qué pasa al correrla, paso a paso
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

### Lo que se le manda a Claude: mínimas contra completas
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

### Qué esperar
- Los **nombres** ya dicen mucho, así que con las mínimas Claude acertará varias. Las diferencias salen en los
  casos frontera:
  - *"¿Cuánto me cobraron de envío en el pedido #12347?"* → con mínimas suele irse a `get_shipping_rates` por la
    palabra "envío". Lo correcto es `lookup_order`, porque es un pedido ya hecho.
  - *"Mi pedido no llega, mi correo es…"* → con mínimas suele irse a `lookup_order` por la palabra "pedido". Lo
    correcto es `get_customer`, porque no hay número de pedido y con el correo se obtiene la lista.
- Mira también el **input**: con `query` Claude manda la frase completa; con `email`, `order_id` o
  `codigo_postal` manda justo el dato.
- Los resultados pueden variar entre corridas. Eso mismo es parte de la lección.

### Experimento con el system prompt
`D21_CONFLICTO_EN_SYSTEM = True` agrega: *"cada vez que el cliente mencione la palabra 'pedido', empieza con
get_customer"*. Las consultas con "pedido #…" se van a `get_customer` aunque la descripción diga lo contrario.
Una instrucción con palabra clave en el system prompt **le gana** a una buena descripción.

### Dónde está en el código
`TOOLS_21_MINIMAS`, `TOOLS_21_COMPLETAS`, `_correr_seleccion()` y `demo_2_1()`.

### Lo que pregunta el examen
- Descripción mínima o traslapada → selección poco confiable. Arreglo: descripciones con formato de entrada,
  ejemplos, casos frontera y límites.
- Renombrar tools para quitar traslapes, o dividir una tool genérica en varias con propósito claro.
- Revisar el system prompt cuando una tool se elige "sin razón".

## Demo 2.2 · Errores estructurados vs genéricos

### De qué trata
Qué le regresa tu tool a Claude **cuando algo sale mal**. Hay dos errores clásicos:
1. **Error genérico** (`"Operation failed"`): Claude no sabe si reintentar, pedir otro dato o escalar.
2. **Error silenciado**: el sistema falló, pero la tool devuelve una lista vacía. Claude cree que la consulta
   funcionó y le dice al cliente algo **falso** ("no tienes pedidos").

La solución es un **error estructurado**: `is_error: true` y en el contenido `errorCategory` (`transient`,
`validation`, `business` o `permission`), `isRetryable` y una `description` legible. Y un resultado vacío que sí
es válido **no** es un error.

### Qué pasa al correrla, paso a paso
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

### Qué esperar
- **`caido · generico`** es el momento clave: Claude dice que no hay pedidos, cuando en realidad el sistema
  estaba caído. En **estructurado** reintenta y en el 2.º intento obtiene los pedidos.
- Con el genérico, Claude a veces adivina bien (por ejemplo, nota que `ana@ejemplo` está mal escrito), pero lo
  hace por su cuenta: la tool no le dio esa información.
- La tabla final pone lado a lado las llamadas, la respuesta y **lo que debería pasar**.

### Dónde está en el código
`TOOL_PEDIDOS_CLIENTE`, `_backend_pedidos(escenario, formato, intento)` (aquí están los dos formatos de
respuesta) y `_correr_caso_22()` (el loop; ahí se arma el `tool_result` con `is_error`).
En MCP el campo se llama `isError` (lo verás en la demo 2.4); en la Messages API es `is_error`.

### Experimentos
- `D22_FALLAS_TRANSITORIAS = 3`: ¿cuántas veces reintenta antes de rendirse?
- Quita escenarios de `D22_ESCENARIOS` para una corrida más corta.

### Lo que pregunta el examen
- Metadata de error estructurada para que el agente decida: reintentar, explicar o escalar.
- Distinguir una falla de acceso de un resultado vacío válido.
- En multiagente: el subagente reintenta lo transitorio localmente y propaga al coordinator solo lo que no pudo
  resolver, con lo que intentó y resultados parciales. No suprimir errores ni detener todo por una sola falla.

## Demo 2.3 · Demasiadas tools y tool_choice

### De qué trata
Dos decisiones de diseño: **cuántas tools** darle a cada agente (parte A) y **cómo obligarlo a usar una**
(parte B, `tool_choice`).

### Parte A, paso a paso: 4 tools contra 18
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

### Parte B, paso a paso: tool_choice
Mismo mensaje (*"¿a qué hora abren la tienda física?"*), con dos tools (`extraer_metadatos` y `get_customer`)
y tres modos:

| `tool_choice` | Significa | Qué esperar |
|---|---|---|
| `{"type": "auto"}` | Claude decide (default) | Texto, `stop_reason: "end_turn"` |
| `{"type": "any"}` | Debe llamar **alguna** tool | `tool_use` aunque no haga falta |
| `{"type": "tool", "name": "extraer_metadatos"}` | Debe llamar **esa** | `tool_use` de `extraer_metadatos` |

Con `auto`, fíjate si Claude inventa un horario o reconoce que no lo sabe.

### Parte C, paso a paso: tool_choice en un caso real
Llega un documento y no sabes si es factura, recibo o contrato; hay una tool (un schema) por tipo.

| Paso | `tool_choice` | Para qué |
|---|---|---|
| 1 | `{"type": "tool", "name": "extraer_metadatos"}` | Garantiza que ese paso va **primero** |
| 2 | `{"type": "any"}` con las 3 tools de extracción | Claude **debe** elegir un schema; no puede contestar en texto |
| 3 | `{"type": "auto"}` | Ya con los datos, Claude decide (puede contestar en texto) |

Qué esperar con el ticket de ejemplo: `extraer_recibo` en el paso 2. Cambia `D23_DOCUMENTO_C` por una factura
(con RFC y folio) o un contrato y mira qué schema elige.

### Examen contra producto actual
Con `D23_MODELO_B = "claude-sonnet-5-5"`, los modos `any` y `tool` responden **error 400**. La demo lo atrapa y
lo explica. El examen evalúa el **concepto**; en la API actual, con Sonnet y Opus 5.5 se usa `auto` + una
instrucción clara + `strict: true` en la tool, o Haiku 5.5, que sí lo acepta.

### Dónde está en el código
`TOOLS_23_NUCLEO`, `TOOLS_23_DISTRACTORAS`, `TOOLS_23_EXTRACCION`, `demo_2_3_parte_a()`, `demo_2_3_parte_b()`,
`demo_2_3_parte_c()`. El helper `_tool()`
arma cada definición en una línea.

### Experimentos
- `D23_TOOLS_A = "18"` (o `"4"`): corre la parte A solo con esa configuración.

### Lo que pregunta el examen
- 18 tools en vez de 4 o 5 → peor selección. Cada subagente recibe solo las tools de su rol.
- Reemplazar tools genéricas por versiones restringidas; dar una tool compartida acotada (p. ej. `verify_fact`)
  cuando un rol la necesita seguido.
- `tool_choice: any` garantiza una llamada; forzar una tool garantiza el orden (p. ej. extraer metadatos primero).

## Demo 2.4 · Servidor MCP propio + Agent SDK

### De qué trata
**MCP (Model Context Protocol)**: un estándar para que un agente descubra y use tools y datos de sistemas
externos. Un **servidor MCP** ofrece:
- **Tools**: acciones que Claude puede llamar.
- **Resources**: datos que se pueden leer, como un catálogo o documentación.

La demo crea un servidor propio, primero le habla **sin Claude** y luego se lo conecta a un agente.

### El servidor (`servidor_inventario_mcp.py`, se genera junto al script)
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

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`SERVIDOR_MCP_CODIGO` (el servidor completo como texto), `_cliente_mcp_directo()`, `MCP_JSON_EJEMPLO`, `demo_2_4()`.

### Experimentos
- `D24_USAR_RESOURCES = True`: el agente también recibe `ListMcpResourcesTool` y `ReadMcpResourceTool`, y puede
  leer el catálogo completo en vez de buscar a ciegas.
- Empeora la descripción de `buscar_producto` (por ejemplo, `"Busca."`) y compara.
- Abre `servidor_inventario_mcp.py` y agrega una tool nueva. El lab **no sobrescribe** tu versión si el archivo
  ya existe; bórralo para volver al original.
- `D24_SECRETO = "en_archivo"`: el token queda escrito en el `.mcp.json` que va a git.
- `D24_ALCANCE = "usuario"`: el servidor queda en `~/.claude.json` y tu compañero no lo tiene.

### Lo que pregunta el examen
- `.mcp.json` del proyecto contra `~/.claude.json` del usuario, y expansión de variables `${VAR}` para secretos.
- Las tools de todos los servidores configurados se descubren al conectar y quedan disponibles a la vez.
- Mejorar la descripción de las tools MCP para que el agente no las ignore y use built-ins como Grep en su lugar.
- Resources como catálogo de contenido para ahorrar llamadas exploratorias.
- Servidores de la comunidad para integraciones estándar; uno propio solo para flujos específicos del equipo.

## Demo 2.5 · Tools built-in: Grep, Glob, Read, Edit (Agent SDK)

### De qué trata
Las tools **built-in** de Claude Code y cuándo usar cada una:

| Tool | Para qué |
|---|---|
| **Grep** | Buscar **contenido** dentro de archivos (quién llama a una función, un mensaje de error) |
| **Glob** | Buscar **archivos** por patrón de nombre o ruta (`**/*.test.ts`); no mira el contenido |
| **Read** | Leer un archivo |
| **Edit** | Cambio puntual: reemplaza un texto que debe ser **único**; si no lo es, falla |
| **Write** | Sobrescribir el archivo completo (respaldo cuando Edit no puede) |

### El repo de ejemplo y sus trampas
Se crea en una carpeta temporal con archivos TypeScript de La Tiendita:
- `src/reembolsos/index.ts` re-exporta `processRefund as submitRefund`, y `src/admin/panel.ts` lo renombra
  otra vez (`submitRefund as reembolsoManual`). Si solo buscas "processRefund", te faltan archivos.
- En `config/limites.json` el valor `10000` aparece **dos veces** (`limite_reembolso` y `limite_credito`). Un
  Edit de solo `"10000"` no es único.

### Qué pasa al correrla, paso a paso
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

### Dónde se configuran tools, permisos y hooks
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

### Experimentos
- Quita `"Grep"` de `D25_TOOLS`: tendrá que abrir archivo por archivo con Read (más turnos y tokens).
- `D25_EDIT_RESPALDO = "read_write"` (con `"Write"` en `D25_TOOLS`): el Edit de solo `10000` falla por texto repetido y
  el agente usa Read + Write, que es lo que espera el examen.
- Quita `"Glob"`: encontrar los `*.test.ts` se vuelve más difícil.
- Cambia `D25_TAREA` para pedir que cambie "el 10000" sin decir cuál y observa el error de Edit.

### Lo que pregunta el examen
- Grep para contenido, Glob para rutas, Edit para cambios puntuales con texto único, y Read + Write como respaldo.
- Explorar de forma incremental: Grep para encontrar puntos de entrada y Read para seguir imports, en lugar de leer todo.
- Rastrear una función a través de módulos que la re-exportan: identificar los nombres exportados y buscar cada uno.

# Dominio 3 · Claude Code Configuration & Workflows

## Demo 3.1 · Jerarquía de CLAUDE.md (Agent SDK)

### De qué trata
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

### Qué pasa al correrla, paso a paso
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

### Lo que se le manda a Claude
- `setting_sources` decide qué configuración lee Claude Code: `"project"` = CLAUDE.md, `.claude/` y lo que importen;
  `"local"` = `CLAUDE.local.md`; `"user"` = tu `~/.claude` (la demo **no** lo usa).
- `system_prompt={"type": "preset", "preset": "claude_code"}`: el mismo system prompt que usa Claude Code.

### Dónde está en el código
- `crear_proyecto()` arma la carpeta temporal.
- `opciones_claude_code()` arma las opciones del agente.
- `instrucciones_cargadas()` lee la transcripción (`~/.claude/projects/.../<session_id>.jsonl`). Ese formato es
  interno de Claude Code: si cambia en una versión futura, la tabla no aparece, pero la demo sigue funcionando.

### Experimentos
- `D31_USAR_IMPORT = False`: `docs/estilo.md` ya no se carga y el agente deja de conocer la regla de montos.
- `D31_SIMULAR_COMPANERO = True`: corre como alguien nuevo del equipo (`setting_sources=["project"]`).
  `CLAUDE.local.md` desaparece. Es el caso clásico del examen: la regla del equipo estaba en un archivo personal.
  El arreglo es moverla al `CLAUDE.md` del repo.
- Pide leer `src/carrito/total.ts` en vez de `reembolsos.ts`: `src/api/CLAUDE.md` no se carga.

### Lo que pregunta el examen
- Un compañero nuevo no recibe una instrucción → estaba en `~/.claude/CLAUDE.md` (personal). Va en el CLAUDE.md del repo.
- Importar con `@ruta` (no existe `@import`) para mantener CLAUDE.md modular; `.claude/rules/` para separar por tema.
- `/memory` para ver qué archivos de memoria están cargados y diagnosticar comportamientos inconsistentes.

## Demo 3.2 · Slash commands y skills (Agent SDK)

### De qué trata
Dos formas de empaquetar un flujo para reutilizarlo:

| | Slash command | Skill |
|---|---|---|
| Quién lo dispara | **Tú**: `/revisar-reembolso #12346` | **Claude**, cuando la tarea coincide con la descripción |
| Dónde vive | `.claude/commands/<nombre>.md` | `.claude/skills/<nombre>/SKILL.md` |
| Personal | `~/.claude/commands/` | `~/.claude/skills/` |
| Contexto | Se manda completo al invocarlo | Al inicio solo nombre + descripción; el cuerpo se carga al usarlo |

Regla para decidir: lo que **siempre** aplica va en CLAUDE.md; lo que **tú** invocas, en un command; lo que
**Claude** debe decidir usar, en un skill.

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
- Los archivos del proyecto están en el diccionario que recibe `crear_proyecto()`, dentro de `demo_3_2()`.
- `DESCRIPCIONES_SKILL_32` tiene la descripción buena y la vaga.
- `hook_skill` es un `PreToolUse` con `matcher="Skill"`: solo registra la invocación.
- Las tools son `Read`, `Glob` y `Skill`; sin la tool `Skill`, Claude no puede invocar skills.

### Experimentos
- `D32_DESCRIPCION_SKILL = "vaga"` (*"Utilidades varias."*): es probable que Claude **no** use el skill. Es la misma
  lección de la demo 2.1: la descripción decide.
- `D32_PEDIDO = "#12345"`: $1,850 con foto → debería salir CUMPLE.
- Abre la carpeta del proyecto (la ruta sale en pantalla) y crea tu propio comando.

### Lo que pregunta el examen
- Comando del equipo → `.claude/commands/` (va a git). Personal → `~/.claude/commands/`.
- Frontmatter de skills: `context: fork` corre el skill en un subagente aislado; `allowed-tools` limita qué tools
  usa; `argument-hint` indica qué argumento espera.
- Skill = a demanda; CLAUDE.md = siempre cargado.

## Demo 3.3 · Reglas por ruta en .claude/rules (Agent SDK)

### De qué trata
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

### Qué pasa al correrla, paso a paso
1. Se crea un proyecto con dos reglas: `api.md` (`paths: src/api/**/*.ts`) y `tests.md` (`paths: **/*.test.ts`).
2. Se le pide a Claude leer `src/api/reembolsos.ts` y luego `src/carrito/carrito.test.ts`, y decir qué convenciones
   aplican a cada uno.
3. La tabla de la transcripción muestra cuándo se cargó cada regla:
   - `CLAUDE.md` → al iniciar;
   - `.claude/rules/api.md` → después de leer `reembolsos.ts`;
   - `.claude/rules/tests.md` → después de leer `carrito.test.ts`.
   La columna **"Se activa con"** muestra el glob.

### Dónde está en el código
`demo_3_3()`: las variables `encabezado_api` y `encabezado_tests` agregan o quitan el frontmatter `paths:`.
La tabla sale de `mostrar_instrucciones()`, la misma de la demo 3.1.

### Experimentos
- `D33_CON_PATHS = False`: las dos reglas aparecen **al iniciar la sesión**, aunque no toques esos archivos.
  Funciona, pero gasta contexto en todo momento.
- Cambia `D33_PREGUNTA` para leer solo `src/carrito/total.ts`: no se carga ninguna regla.

### Lo que pregunta el examen
- Convenciones para un tipo de archivo regado por el repo → `.claude/rules/` con `paths` (glob), no un CLAUDE.md por carpeta.
- Ventaja: se cargan solo cuando aplican, así que reducen tokens y ruido.

## Demo 3.4 · Plan mode vs ejecución directa (Agent SDK)

### De qué trata
**Plan mode** (`permission_mode="plan"`): Claude explora y propone un plan, pero **no puede editar** archivos.
Úsalo cuando la tarea es **grande o ambigua**: conviene ver el plan antes de que se edite nada.
**Plan mode** es para cambios grandes (una migración de 45 archivos), con varias formas válidas o con decisiones de arquitectura. Un cambio claro y acotado (cambiar un valor en 3 archivos) va con **ejecución directa**. El patrón **híbrido** combina ambas: planear → revisar/aprobar → ejecutar.

### Qué pasa al correrla, paso a paso
El proyecto tiene el límite de reembolso (10000) en 3 lugares: `config/limites.json`, `src/reembolsos.ts` y
`docs/politica.md`. La tarea es cambiarlo a 8000 en todos.

- **`"plan"`**: el agente busca con Grep, lee y propone un plan. Si intenta editar, Claude Code lo bloquea
  (*"Cannot write … while in plan mode"*). Al final verás **"Archivos modificados en plan mode: ninguno"**.
- **`"directo"`**: con `acceptEdits` edita directo.
- **`"hibrido"`** (por defecto): fase 1 en plan mode; fase 2 **en la misma sesión** (`resume`) con `acceptEdits`
  y el mensaje *"Plan aprobado. Impleméntalo."*.

La tabla final muestra qué archivos cambiaron.

### Dónde está en el código
`demo_3_4()`: `permission_mode="plan"` y luego `permission_mode="acceptEdits"` con `resume=resultado.session_id`.
Las tools son `Read`, `Glob`, `Grep` y `Edit`; aun con `Edit` en `allowed_tools`, plan mode no deja escribir.

### Experimentos
- Corre los 3 valores de `D34_MODO` y compara la tabla final.
- Lee el plan de la fase 1: ¿encontró los 3 lugares? Si no, el valor del plan es que tú lo notas antes de que se edite nada.
- `D34_TIPO_TAREA = "clara"` o `"ambigua"`: plan mode conviene si hay varias formas válidas o el cambio es grande; un cambio claro y acotado va directo.

### Lo que pregunta el examen
- Migraciones, cambios de arquitectura o tareas con varias soluciones posibles → plan mode.
- Bug con causa clara en un solo archivo → ejecución directa.
- Explorar con un subagente para no llenar el contexto principal; planear antes de ejecutar.

## Demo 3.5 · Refinamiento iterativo: ejemplos y TDD

### De qué trata
Cómo corregir un resultado que no sale como quieres. Las técnicas del examen:
- **Ejemplos concretos** de entrada → salida, en lugar de describir con adjetivos.
- **TDD**: primero las pruebas; luego pides el código y le compartes **las pruebas que fallaron**.
- **Interview pattern**: en tareas poco claras, que Claude te haga preguntas antes de implementar.
- Arreglos **relacionados** en un solo mensaje; **independientes**, uno por uno.

### Qué pasa al correrla, paso a paso
La tarea es escribir `normalizar_telefono(texto)` para teléfonos mexicanos. Hay 8 pruebas en `CASOS_35`, incluidos
casos frontera: `044 664…`, `52 664…` sin `+`, `"123"` → `None` y un texto con prefijo `tel:`.

- **`"vago"`**: solo se describe en una frase. Una ronda.
- **`"ejemplos"`**: la misma frase + 3 ejemplos de entrada → salida, elegidos entre los casos frontera (paréntesis, `044` y uno inválido). Una ronda. La guía pide 2–3 ejemplos: más no es mejor.
- **`"tdd"`** (por defecto): empieza vago y, en cada ronda, le manda a Claude solo las pruebas que fallaron, con
  entrada, obtenido y esperado. Hasta `D35_MAX_RONDAS`.

En cada ronda verás el código que escribió Claude, la tabla de pruebas (✔/✘) y "Pasaron X/8". Al final, una tabla
con el progreso por ronda.

### Seguridad: el código se ejecuta
El código que escribe Claude se ejecuta en **un proceso aparte** (`python -I`), con **límite de 10 segundos**,
dentro de una carpeta temporal. Si prefieres solo verlo, pon `D35_EJECUTAR_CODIGO = False`.

### Dónde está en el código
`CASOS_35`, `PETICION_VAGA_35`, `PETICION_EJEMPLOS_35`, `_extraer_codigo()`, `_correr_pruebas()` y `demo_3_5()`
(el `for ronda`, donde se arma el mensaje con las fallas).

### Experimentos
- Corre los 3 modos y compara. Lo usual: `"vago"` falla en los casos frontera, `"ejemplos"` acierta más desde la
  primera ronda y `"tdd"` converge en 2 o 3 rondas.
- Agrega un caso nuevo a `CASOS_35` (por ejemplo, con extensión `ext. 12`) y mira cómo lo resuelve TDD.

### Lo que pregunta el examen
- Las descripciones en prosa se interpretan de forma inconsistente → da 2 o 3 ejemplos concretos.
- Iterar compartiendo las pruebas que fallan (entrada, obtenido y esperado) converge mejor que "no funciona, arréglalo".

## Demo 3.6 · CI/CD con claude -p

### De qué trata
Claude Code en un pipeline de CI/CD, donde **no hay nadie** para contestar. Sin `-p`, Claude Code abre una sesión
interactiva y el job se queda colgado esperando.

| Flag | Para qué |
|---|---|
| `-p "prompt"` (`--print`) | Corre, imprime el resultado y termina |
| `--output-format json` | Salida que el pipeline puede leer: `result`, `total_cost_usd`, `session_id`… |
| `--json-schema '<schema>'` | La respuesta se valida contra tu schema y llega en `structured_output` |
| `--allowedTools`, `--tools` | Qué puede usar (aquí solo `Read`) |
| `--max-turns`, `--max-budget-usd` | Límites de turnos y de gasto |

### Qué pasa al correrla, paso a paso
1. Se crea un repo de prueba con un `CLAUDE.md` (*"reembolsos automáticos hasta $10,000"*) y un `cambios.diff` que
   sube el límite a 100000.
2. Se imprime el **comando completo** y se ejecuta el CLI de Claude Code (el que viene dentro de `claude-agent-sdk`)
   como un proceso aparte.
3. Con `"json"` + schema verás:
   - los campos útiles del JSON (`subtype`, `num_turns`, `total_cost_usd`, `session_id`);
   - `structured_output` con `aprobado` y la lista de `problemas` (archivo, severidad, descripción);
   - la decisión del pipeline: **BLOQUEAR el merge**, porque viola la regla de CLAUDE.md.
4. Se imprime un ejemplo de workflow de GitHub Actions.

### Dónde está en el código
`SCHEMA_36`, `GITHUB_ACTIONS_36`, `_ruta_cli()` (busca el CLI dentro de `claude-agent-sdk`) y `demo_3_6()`, que arma
la lista `comando` y la corre con `subprocess.run`.

### Experimentos
- `D36_FORMATO = "text"`: la salida es prosa y el pipeline no puede decidir nada con ella.
- `D36_CON_SCHEMA = False`: hay JSON, pero `result` sigue siendo texto libre.
- Edita `cambios.diff` en la demo para que respete el límite: debería aprobar.

### Lo que pregunta el examen
- El job de CI se cuelga → falta `-p`.
- Salida para procesar → `--output-format json` + `--json-schema`.
- El revisor debe ser una sesión **independiente** de la que generó el código: no se autorrevisa.
- CLAUDE.md da contexto del proyecto también en CI. Incluye hallazgos previos para no repetir comentarios en cada push.
- `claude -p` para revisiones bloqueantes antes del merge; Message Batches API (Dominio 4) para trabajos que pueden esperar.

# Dominio 4 · Prompt Engineering & Structured Output

## Demo 4.1 · Criterios explícitos en el system prompt

### De qué trata
Instrucciones como *"marca lo importante"*, *"sé conservador"* o *"solo si tienes alta confianza"* no le dicen al
modelo **dónde está la línea**. Cada corrida la pone en un lugar distinto: alertas de más (falsos positivos) o de
menos (falsos negativos). La solución son **criterios explícitos**: qué SÍ cuenta y qué NO, con ejemplos.

Detalle del examen: los falsos positivos hacen que la gente deje de confiar en **todas** las alertas, incluso en las
correctas.

### Qué pasa al correrla, paso a paso
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

### Lo que se le manda a Claude
- `system`: `SISTEMA_VAGO_41` o `SISTEMA_EXPLICITO_41`.
- `tools`: `TOOL_CLASIFICAR_41`, que devuelve una lista de decisiones con `id`, `escalar` y `motivo`.

### Dónde está en el código
`TICKETS_41` (tickets + respuesta correcta), los dos system prompts y `demo_4_1()`.

### Experimentos
- Quita de `SISTEMA_EXPLICITO_41` la línea *"El enojo por sí solo NO es criterio"* y mira T9.
- Agrega tickets frontera a `TICKETS_41`, por ejemplo un reembolso de exactamente $10,000.

### Lo que pregunta el examen
- "Sé conservador" o "solo alta confianza" no mejoran la precisión: lo que la mejora son criterios concretos.
- Si una categoría da muchos falsos positivos, desactívala temporalmente mientras mejoras su prompt, para recuperar
  la confianza en las demás.
- Define la severidad con ejemplos de código o casos concretos por nivel.

## Demo 4.2 · Few-shot para casos ambiguos

### De qué trata
**Few-shot** = poner de 2 a 4 ejemplos de entrada → salida en el prompt. Es la técnica más efectiva cuando las
instrucciones solas dan resultados inconsistentes. Los buenos ejemplos:
- cubren los **casos ambiguos**, no solo los fáciles;
- explican **por qué** se decidió así, para que el modelo generalice el criterio y no solo copie el formato.

### Qué pasa al correrla, paso a paso
1. Hay 6 mensajes de clientes en `MENSAJES_42`, cada uno con su respuesta correcta. Los difíciles son:
   - *"Lo mismo que pedí la vez pasada"*: no hay producto identificable;
   - *"Un mantel, el rojo no, el otro"*: dice qué color NO quiere;
   - *"unas cuantas tazas verdes"*: no hay cantidad exacta.
2. Ronda **sin ejemplos**: solo la instrucción. Por cada mensaje, ✔ o ✘ con qué campo falló.
3. Ronda **con ejemplos**: se agregan los 4 ejemplos de `EJEMPLOS_42` al system prompt (se imprimen en pantalla).
4. La tabla compara las dos rondas mensaje por mensaje.

Qué esperar: los casos fáciles salen bien en ambas. En los ambiguos, sin ejemplos el modelo suele **inventar** una
cantidad (*"unas cuantas"* → 3) o no pedir aclaración.

### Lo que se le manda a Claude
- `TOOL_PEDIDO_42` con campos nullable (`"type": ["integer", "null"]`), forzada con `tool_choice`.
- Los ejemplos van en el `system`, cada uno con su `(por qué: …)`.

### Dónde está en el código
`MENSAJES_42`, `EJEMPLOS_42`, `_coincide_42()` (compara cantidad, color y aclaración) y `demo_4_2()`.

### Experimentos
- Quita los `(por qué: …)` de los ejemplos y compara.
- Cambia un ejemplo para que contradiga la instrucción: el modelo suele seguir al ejemplo. Los ejemplos pesan mucho.

### Lo que pregunta el examen
- Salida inconsistente con instrucciones detalladas → agrega ejemplos few-shot de los casos ambiguos.
- Si el modelo **inventa** un dato porque el schema lo obliga (campo requerido que el documento no trae), el arreglo
  es un campo **nullable** (demo 4.3), no few-shot.
- Si inventa u omite datos porque los documentos vienen en formatos distintos (medidas informales, tabla vs. texto
  corrido), ahí sí ayuda **few-shot**: un ejemplo por cada estructura.
- Ejemplos con formatos variados del documento ayudan a extraer bien de documentos con estructura distinta.

## Demo 4.3 · Salida estructurada con tool use

### De qué trata
Pedir *"responde solo en JSON"* funciona **casi** siempre, y en un pipeline "casi" es un problema: a veces llega con
```` ```json ````, con una frase antes o con claves distintas. La alternativa confiable es **tool_use**: defines la
salida como `input_schema` de una tool y fuerzas su uso con `tool_choice`. El JSON siempre es parseable y sigue
el schema.

Diseño del schema:
- Campos que pueden no venir → **nullable** (`["string", "null"]`), así no inventa.
- Categorías → `enum` con una opción **"otro"** + un campo de detalle.
- El schema garantiza la **sintaxis**, no la **semántica**: un total puede no cuadrar (demo 4.4).

### Qué pasa al correrla, paso a paso
1. Se imprime el schema `SCHEMA_43`.
2. Modo **texto**: se piden los 5 correos en JSON por prompt y se intenta `json.loads()`. Si falla, se ve qué llegó.
3. Modo **tool**: los mismos correos con `extraer_correo` forzada.
4. Por cada correo se valida que estén las claves y que `tipo` sea un valor válido.
5. Tabla: **JSON parseable** y **Cumple el schema** por modo.

Qué esperar: en tool, 5/5 y 5/5. En texto suele haber fallas de parseo (por los ```` ```json ````) o claves de
más o de menos. Mira el correo *"algo bonito para regalo"*: con nullable y `"otro"`, la salida es honesta.

### Dónde está en el código
`SCHEMA_43`, `TOOL_EXTRAER_43`, `_valida_esquema_43()` y `demo_4_3()`.

### Experimentos
- Quita `"otro"` del enum de `tipo` y mira cómo clasifica el correo del regalo.
- Quita `"null"` de `fecha_requerida`: puede empezar a inventar fechas.

### Lo que pregunta el examen
- Salida estructurada confiable → tool_use con JSON schema (elimina errores de sintaxis).
- `tool_choice: any` garantiza que llame alguna tool; forzar una tool garantiza cuál.
- Campos opcionales como nullable para evitar datos fabricados; `enum` + `"otro"` + detalle para categorías abiertas.

## Demo 4.4 · Validación, reintento y retroalimentación

### De qué trata
El schema asegura la forma; las **reglas de negocio** se validan en código. Cuando una falla, se reintenta
mandándole al modelo el **error específico**: qué campo, qué valor y qué se esperaba.

Dos ideas clave del examen:
- El reintento sirve para errores de **formato o estructura**. **No** sirve cuando el dato **no existe** en el
  documento: el modelo terminaría inventándolo.
- Patrón *total declarado vs calculado*: extraer los dos y marcar la discrepancia, en lugar de "corregir" en silencio.

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`DOCUMENTOS_44`, `TOOL_PEDIDO_44`, `validar_44()` (las reglas) y el `for intento` de `demo_4_4()`, donde se arma la
retroalimentación.

### Experimentos
- `D44_FEEDBACK = "generico"`: con *"inténtalo de nuevo"* el modelo no sabe qué cambiar y suele repetir el error.
- `D44_FEEDBACK = "sin_reintento"`: aceptas el primer resultado, con errores.
- Agrega tu propia regla a `validar_44()`; por ejemplo, que la cantidad sea positiva.

### Lo que pregunta el examen
- Reintento con el documento, la extracción fallida y el error específico de validación.
- Reintentar no sirve si la información no está en la fuente.
- Campo `detected_pattern` o de confianza para analizar después por qué se descartan hallazgos.
- `calculated_total` junto a `stated_total` para detectar discrepancias.

## Demo 4.5 · Message Batches API

### De qué trata
La **Message Batches API** procesa muchas peticiones de forma asíncrona:

| | Batches API | API síncrona |
|---|---|---|
| Costo | ~50% menos | Normal |
| Tiempo | Hasta 24 h, sin garantía | Segundos |
| Tools | Un turno por petición (sin loop de tools) | Loop completo |
| Para | Reportes nocturnos, auditorías | Lo que alguien está esperando |

### Qué pasa al correrla, paso a paso
1. Se arman 8 peticiones (clasificar reseñas), cada una con su `custom_id` (`resena-001`…). Se imprime una de ejemplo.
2. Se crea el lote con `client.messages.batches.create(requests=...)`. El id se guarda en `ultimo_lote.txt`.
3. Cada `D45_CADA_S` segundos se consulta el estado: `in_progress` → `ended`, con contadores de procesando, ok,
   error y expiradas.
4. Al terminar se leen los resultados con `batches.results()`. Pueden llegar **en otro orden**: se emparejan por `custom_id`.
5. Si alguna falló, se indica que se reenvía **solo esa**, en un lote nuevo.
6. Tabla: ¿batch o síncrono?, y la cuenta de SLA.

Ojo: un lote pequeño suele terminar en minutos, pero **no hay garantía**. Si pasa `D45_ESPERA_MAXIMA_S`, la demo
para y te dice cómo recuperarlo después con `D45_LOTE_EXISTENTE`.

### Dónde está en el código
`RESENAS_45` y `demo_4_5()`: `batches.create`, el `while` con `batches.retrieve` y el `for` con `batches.results`.

### Experimentos
- Cierra la demo a la mitad y luego recupera el lote pegando su id en `D45_LOTE_EXISTENTE`.
- Agrega 50 reseñas más: el costo baja a la mitad comparado con mandarlas una por una.
- `D45_EMPAREJAR = "orden"`: empareja por posición y mira qué reseñas quedan con la clasificación de otra.
- `D45_USO = "pre_merge"`: la demo explica por qué no se manda el lote (y no gasta nada).
- `D45_SLA_HORAS = 30`: con lotes de hasta 24 h, un documento puede esperar a lo más 6 h antes de entrar a un lote
  → manda lotes al menos cada 6 h (con margen, cada 4 h). Prueba con 24: Batch ya no garantiza el SLA.

### Lo que pregunta el examen
- Bloqueante (revisión antes de un merge) → síncrona. Puede esperar (reporte nocturno) → batch.
- `custom_id` para emparejar resultados y reenviar solo los que fallaron.
- Prueba el prompt con una muestra antes de mandar un lote grande, para no repetir miles de peticiones.
- Matemáticas de SLA: con hasta 24 h de procesamiento, hay que enviar con suficiente anticipación.

## Demo 4.6 · Revisión con instancia independiente

### De qué trata
Un modelo que revisa su propio trabajo **en la misma conversación** arrastra el razonamiento con el que lo escribió:
tiende a confirmar en vez de cuestionar. Una **instancia independiente**, sin el historial de generación, encuentra
más problemas. Además, cada hallazgo puede llevar **confianza**, y los de baja confianza van a revisión humana.

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`POLITICA_46`, `CASO_46`, `BORRADOR_46`, `PROBLEMAS_46` (palabras clave por problema), `TOOL_HALLAZGOS_46` y `demo_4_6()`.

### Experimentos
- Haz los errores más sutiles en `BORRADOR_46` (por ejemplo, "en 3 días" en vez de "en 24 horas").
- Sube `D46_UMBRAL_CONFIANZA` a 0.9: más hallazgos van a revisión humana.
- `D46_ERRORES = "obvios"` o `"sutiles"` (default): con errores sutiles se nota más la diferencia.

### Lo que pregunta el examen
- La autorrevisión en la misma sesión es menos efectiva: usa una instancia independiente.
- Revisiones grandes: pasadas por archivo + una pasada de integración (demo 1.6).
- Confianza por hallazgo para decidir qué revisa una persona; calibra el umbral con datos etiquetados (demo 5.5).

# Dominio 5 · Context Management & Reliability

## Demo 5.1 · Ventana de contexto: case facts y recorte

### De qué trata
Qué se pierde cuando el contexto crece y cómo evitarlo:
- **Resumen progresivo**: para ahorrar espacio, el historial se resume, y el resumen pierde lo exacto (montos, fechas,
  números de pedido, lo que el cliente ya rechazó).
- **Case facts**: un bloque aparte con los datos transaccionales que se copia **completo** en cada turno y nunca se resume.
- **Resultados de tools inflados**: una tool que devuelve 30 campos cuando solo importan 5 ocupa contexto en cada turno.
- **Lost in the middle**: el modelo atiende peor lo que queda a la mitad de un contexto largo. Pon lo importante al
  inicio o al final, con encabezados.

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`CONVERSACION_51`, `HECHOS_51` (palabras clave para verificar), `CASE_FACTS_51`, `PEDIDO_COMPLETO_51`,
`CAMPOS_REEMBOLSO_51`, `demo_5_1_parte_a()` y `demo_5_1_parte_b()`.

### Experimentos
- Corre la parte A varias veces: el resumen pierde datos distintos cada vez.
- Cambia el system prompt del resumen a "Resume en 1 línea": pierde más.
- `D51_PARTE = "C"` con `D51_POSICION_DATO = "medio"` o `"arriba"`: lost in the middle con un expediente largo.

### Lo que pregunta el examen
- Los resúmenes progresivos pierden valores numéricos, fechas y expectativas del cliente → bloque persistente de "case facts".
- Recorta los resultados de tools a los campos relevantes antes de que se acumulen.
- Lo clave al inicio, con encabezados claros, por el efecto *lost in the middle*.
- Los subagentes devuelven metadatos estructurados (fechas, fuentes) y no solo prosa.

## Demo 5.2 · Escalamiento y ambigüedad

### De qué trata
**Cuándo escalar a una persona.** Los disparadores correctos son tres:
1. El cliente **pide** explícitamente una persona → escala de inmediato, sin intentar resolver primero.
2. La **política no cubre** el caso (aquí: igualar precios de otra tienda).
3. **No puedes avanzar** después de intentarlo.

Disparadores malos, que el examen pone como distractores:
- el **sentimiento** por sí solo (un cliente molesto con un problema simple se atiende, no se escala);
- la **confianza** que el modelo dice tener sobre sí mismo.

**Ambigüedad:** si la búsqueda devuelve **varios clientes** posibles, se pide un dato más; nunca se elige con una heurística.

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`ESCENARIOS_52`, `SISTEMA_VAGO_52`, `SISTEMA_CRITERIOS_52`, `TOOLS_52`, `_ejecutar_52()` (simula las tools;
`get_customer` con "juan" devuelve 2 coincidencias) y `_correr_52()`.

La acción se detecta así: si llamó `escalar_a_humano` → escaló; si la respuesta final tiene "?" → pidió aclaración;
si no → resolvió. Es una heurística, así que lee las respuestas.

### Experimentos
- Quita del prompt de criterios la línea *"NO escales solo porque el cliente esté molesto"*.
- Agrega un escenario: cliente que pide una persona pero cuyo problema es trivial. Lo correcto sigue siendo escalar.
- `D52_MODO = "todos"`: compara vago, criterios y criterios + ejemplos (la respuesta típica del examen).

### Lo que pregunta el examen
- Pide una persona → escala de inmediato.
- Política ambigua o silenciosa sobre el caso → escala.
- Varias coincidencias → pide identificadores adicionales.
- El sentimiento y la autoevaluación de confianza no son buenos indicadores de complejidad.

## Demo 5.3 · Propagación de errores multiagente

### De qué trata
Qué pasa cuando **un subagente falla** en un sistema multiagente. El coordinator necesita contexto para decidir:
**tipo de falla, qué se intentó, resultados parciales y alternativas.**

Los antipatrones:
1. **Suprimir el error**: devolver "sin datos relevantes" como éxito. El reporte se ve completo, pero no lo está.
2. **Error genérico**: "Error", sin nada con qué decidir.
3. **Tirar todo el flujo** por una sola falla.

La síntesis debe **anotar los huecos**: "sección envíos: incompleta por falla de la fuente".

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`RESULTADOS_OK_53`, `FALLAS_53` (los 3 formatos), `TOOL_DELEGAR_53` y `_correr_53()`, que enruta cada área a su resultado.

### Experimentos
- `D53_COMPARAR_TODOS = False` y elige un `D53_FORMATO` para verlo solo.
- Haz que fallen dos áreas en vez de una: ¿el reporte sigue siendo útil?
- `D53_FORMATO = "abortar"` (con `D53_COMPARAR_TODOS = False`): una sola falla detiene todo y no hay reporte.

### Lo que pregunta el examen
- Contexto de error estructurado (tipo, consulta, parciales, alternativas) para que el coordinator decida.
- Distinguir una falla de acceso de un resultado vacío válido (como la demo 2.2).
- Los subagentes recuperan localmente lo transitorio y solo propagan lo que no pudieron resolver.
- Reportes con anotaciones de cobertura: qué está bien respaldado y qué tiene huecos.

## Demo 5.4 · Exploración de código y scratchpad (Agent SDK)

### De qué trata
En sesiones largas de exploración, el contexto se llena y el agente empieza a dar respuestas genéricas o
inconsistentes con lo que ya había encontrado: **degradación de contexto**. Patrones para evitarlo:
- **Scratchpad**: un archivo donde el agente anota los hallazgos clave y que lee después.
- **Subagentes** para explorar, que devuelven solo un resumen.
- **`/compact`** para resumir el historial en una sesión larga.
- **Sesión nueva + resumen** en lugar de arrastrar todo.

### Qué pasa al correrla, paso a paso
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

### Seguridad
Tools: `Read`, `Grep` y `Glob`, más `Write` solo en la fase 1. Un hook `PreToolUse` **bloquea** cualquier `Write` que
no sea `NOTAS.md`. Todo pasa en una carpeta temporal.

### Dónde está en el código
`_repo_54()`, `_correr_fase_54()` (el hook y las opciones) y `demo_5_4()`.

### Experimentos
- `D54_USAR_SCRATCHPAD = False`: no hay notas y la fase 2 siempre empieza de cero.
- Lee `NOTAS.md`: ¿anotó `promociones.ts` (donde está el `TODO` del umbral)? Si no, la fase 2 con notas puede fallar.
  Un scratchpad vale lo que vale su contenido.

### Lo que pregunta el examen
- Degradación de contexto en sesiones largas → scratchpad, subagentes de exploración y `/compact`.
- Subagentes para investigar preguntas puntuales mientras el agente principal mantiene la coordinación.
- Al reanudar, resume los hallazgos clave en lugar de arrastrar todo el historial.

## Demo 5.5 · Revisión humana y calibración de confianza

### De qué trata
Antes de quitar la revisión humana, hay que saber **dónde** falla el modelo:
- Un **97% global** puede esconder una categoría que falla mucho más.
- Mide la precisión **por tipo de documento** (y por campo).
- **Muestreo estratificado**: revisa una muestra de cada tipo, no solo del total.
- **Confianza por campo, calibrada** con datos etiquetados. El umbral se decide con evidencia, no "a ojo".

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`_documentos_55()` (los 44 documentos con su total correcto; `None` = no se puede saber), `TOOL_TOTAL_55` y `demo_5_5()`,
que arma las tablas (documentos, por tipo, muestreo y calibración).

### Experimentos
- `D55_UMBRAL = 0.95`: van más documentos a revisión humana y se cuelan menos errores.
- Agrega más notas difíciles y mira cómo cambia la precisión de esa categoría.
- `D55_FACTURAS = 6`: con menos facturas el global baja y ya no "engaña" tanto: el volumen de lo fácil es lo que esconde la falla.
- `D55_DECISION = "global"`, `"umbral"` o `"por_tipo"` (default): compara cuántos errores se colarían con cada regla.

### Lo que pregunta el examen
- La precisión agregada puede ocultar fallas por tipo de documento o por campo: valida por segmento antes de
  automatizar.
- Muestreo estratificado de los casos de alta confianza para detectar errores nuevos.
- Confianza por campo calibrada con un conjunto etiquetado para decidir qué va a revisión humana.

## Demo 5.6 · Procedencia y síntesis de varias fuentes

### De qué trata
Al sintetizar varias fuentes se pierde fácilmente **de dónde sale cada dato**. *"El promedio es 3 días"*: ¿según
quién, de cuándo y con qué muestra? El patrón es que cada afirmación conserve **fuente, fecha y alcance**. Si dos
fuentes confiables **discrepan**, no se elige una en silencio: se reporta el conflicto con ambos valores y su contexto.

### Qué pasa al correrla, paso a paso
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

### Dónde está en el código
`FUENTES_56`, `TOOL_SINTESIS_56` y `demo_5_6()`. Las verificaciones son por palabras clave.

### Experimentos
- Agrega una quinta fuente que contradiga a SRC-A con fecha reciente.
- Quita del system prompt *"no elijas una en silencio"* y compara.

### Lo que pregunta el examen
- Conservar el mapeo afirmación → fuente a lo largo de la síntesis.
- Conflictos entre fuentes confiables: anotarlos con su atribución, no resolverlos arbitrariamente.
- Incluir fechas de publicación o de recolección para que los cambios en el tiempo no parezcan contradicciones.
- Distinguir hallazgos bien respaldados de los que tienen huecos o están en disputa.

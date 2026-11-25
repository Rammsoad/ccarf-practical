# CCAR-F · Lab guide (Domains 1 to 5)

This guide explains each demo **before you run it**: what it is about, what happens step by step, what gets sent to
Claude, where it is in the code, what to change and what to expect, and what the exam asks.

The same text appears in the web panel with the EN button (**📖 Demo guide**). In the terminal the guides are in
Spanish (`python lab_dominio1.py guia`). The labs' code, their output and the data of La Tiendita (the fake store) are
in Spanish; the exam terms are in English everywhere.

## Before you start: three ideas that repeat in every demo

**1. Claude doesn't run tools, it asks for them.** You describe your tools to it (name, description, parameters). When it wants
to use one, it answers with a `tool_use` block and `stop_reason = "tool_use"`. **Your code** runs the function and
returns the result in a `tool_result` block.

**2. Anatomy of a tool.** It's a dictionary with three parts:

```python
{
    "name": "lookup_order",                      # how Claude calls it
    "description": "Busca un pedido por...",     # what weighs most when deciding when to use it
    "input_schema": {                            # JSON Schema for the parameters
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "ej. #12345"}},
        "required": ["order_id"],
    },
}
```

**3. Who runs the loop?**

| | Messages API (`anthropic`) | Agent SDK (`claude-agent-sdk`) |
|---|---|---|
| Demos | 1.1–1.4, 1.6, 1.7 B, 2.1–2.3, 3.5, D4, D5 (except 5.4) | 1.5, 1.7 A, 2.4, 2.5, 3.1–3.4, 5.4 (3.6 uses the CLI) |
| The agentic loop | You write it (a `for`) | The SDK runs it |
| Tools | Dictionaries + your functions | `@tool`, MCP servers and built-ins (Read, Grep…) |
| Controls | `if` in your code | `hooks`, `allowed_tools`, `permission_mode` |
| History | You send everything on every call | The session keeps it (`resume`, `fork_session`) |

## How to use this guide

1. Read the demo's section before running it. Pay special attention to "Experiments: what to change and what to expect".
2. Run the demo as it comes (the ✅ case).
3. Change the variable in the **🔧 CAMBIA AQUÍ** (change here) block (or pick a ❌ case in the panel) and run it again.
4. Compare: what changed and why?
5. Finish with "What the exam asks".

In the panel (`python panel.py`), the **🧭 Study path** takes you through these same steps.

---

# Domain 1 · Agentic Architecture & Orchestration

## Demo 1.1 · Agentic loop and stop_reason

### What it is about
The **agentic loop**: the cycle every agent works with. Claude **never runs** the tools: it only
**asks** for one (a `tool_use` block). Your code runs it, returns the result (`tool_result`) and calls
Claude again. The cycle ends when `stop_reason` is `"end_turn"`.

### What happens when you run it, step by step
1. Ana's question is sent (`D11_PREGUNTA`): order #12345, broken mug, she wants $450.
2. Claude responds with `stop_reason = "tool_use"` and asks for `get_customer` (verify identity).
3. Your code runs the Python function `get_customer()` with the fake data and returns a `tool_result`
   inside a message with the `user` role. You see it in the panel **"⚙ tu código ejecutó…"** (your code ran…).
4. It repeats: `lookup_order("#12345")` (total $1,850, it's Ana's) and then `process_refund(450)`.
5. Claude responds with `stop_reason = "end_turn"` and a text for the customer. End of the loop.
6. Summary table: iterations, tools in order and the recorded refund (reference `RF-0001`).

It's normally 3 or 4 iterations. Sometimes Claude asks for 2 tools in the same response: you'll see them in a single
iteration and their 2 `tool_result` blocks travel together in **one** `user` message.

### What gets sent to Claude
- `system`: the support agent role and the expected order (verify → check order → refund).
- `tools`: the `TOOLS_SOPORTE` list. Each tool is a dictionary with **name**, **description** and **input_schema**:

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
- `messages`: the **whole** history on every call. The API keeps nothing between calls.
- `max_tokens`: `D11_MAX_TOKENS`.

### Where it is in the code
- Tool definitions: `TOOL_GET_CUSTOMER`, `TOOL_LOOKUP_ORDER`, `TOOL_PROCESS_REFUND`.
- Real functions: `get_customer()`, `lookup_order()`, `process_refund()`.
- `FUNCIONES_TOOLS` connects the name Claude asks for with the Python function; `ejecutar_tool()` runs it.
- The loop: the `for iteracion in ...` inside `demo_1_1()`.

### Experiments: what to change and what to expect
- `D11_MODO_PARADA = "hay_texto"` (anti-pattern): the loop stops as soon as the response contains text. Since Claude
  often writes "Let me check…" **together with** a `tool_use`, you'll see the alert *"Quedaron tools pedidas SIN
  ejecutar"* (requested tools were NOT run) and there will be no refund. If Claude didn't write text in that run, repeat it.
- `D11_MAX_TOKENS = 40`: the response gets cut off and `stop_reason` is `"max_tokens"`. It didn't finish, it ran out of room.
- `D11_MAX_ITERACIONES = 2`: the safety net cuts the loop before it finishes.

### What the exam asks
- Continue while `stop_reason == "tool_use"`; finish on `"end_turn"`.
- Anti-patterns: deciding by the response text, or using an iteration cap as the **normal** way to stop.
- Tool results are added to the history so Claude can reason about the next step.

## Demo 1.2 · Coordinator + subagents (hub-and-spoke)

### What it is about
The **hub-and-spoke** pattern: a **coordinator** splits the task, sends each part to a **subagent**, receives
the results and writes the synthesis. Subagents don't talk to each other: everything goes through the coordinator.

Here each subagent is a **new** Messages API call with an empty history. That's exactly what defines
a subagent: it **doesn't inherit the coordinator's conversation**, it only sees what the coordinator writes to it.
(In the Agent SDK this is done with the `Agent` tool, formerly called `Task`, and an `AgentDefinition`.)

### What happens when you run it, step by step
1. The coordinator receives the topic (`D12_TEMA`) and a system prompt with the business context: Mexican
   handicrafts, a $40,000 budget, shipping all over Mexico.
2. It responds with 3 to 5 calls to the `delegar_subagente` tool **in the same response**, each with
   `subtema` (subtopic) and `contexto` (context).
3. For each call, your code runs `correr_subagente()`. The blue panel
   **"📦 ESTO es TODO lo que ve el subagente"** (THIS is ALL the subagent sees) literally shows its only message.
4. The subagents' answers go back to the coordinator as `tool_result`.
5. The coordinator writes the final report.
6. The table **"¿El reporte final cubre todas las áreas?"** (does the final report cover every area?) searches the
   report for the words in `D12_AREAS_ESPERADAS` (inventario, logística, precios, marketing, atención).

### What gets sent to Claude
- **To the coordinator:** system prompt + the `TOOL_DELEGAR` tool:
  - `subtema` (string): what to research.
  - `contexto` (string): the business data the subagent needs, because it sees nothing else.
- **To each subagent:** another system prompt ("4 bullet points max") and **a single** message with subtopic + context.
  No tools and no history.

### Why it "splits the assignments badly" (`"estrecha"` mode)
With `D12_DESCOMPOSICION = "estrecha"` the code adds to the coordinator's system prompt:

> *"Divide el tema SOLO en subtemas de marketing digital (redes sociales, anuncios, influencers)."*
> (Split the topic ONLY into digital marketing subtopics: social media, ads, influencers.)

What you'll see:
- The subagents do their job **well**: their bullets about social media or ads are good.
- But nobody researched inventory, logistics, pricing or customer service, because **they were never assigned**.
- The final report comes out incomplete and the coverage table marks several areas in red.

The failure is in the **coordinator's decomposition**, not in the subagents. In real life nobody writes "only
marketing" on purpose. It happens through subtler things: the coordinator's prompt gives examples from a single area, or
it interprets the topic narrowly ("sell more" = "advertise").

### How to fix it
1. **Fix the coordinator's prompt**: explicitly ask it to cover every dimension of the problem
   (or list them) and don't bias it with examples from a single area. That's `"amplia"` mode.
2. **Add a coverage check step**: before writing the report, the coordinator checks the
   results against what it should cover and **re-delegates** whatever is missing (iterative refinement).
   This demo's table is a simple version of that check.
3. **Don't "fix" the subagents** (another model, more tokens, longer prompts): they aren't the problem.

Note: the coverage check looks for exact words. If the report says "envíos" (shipping) instead of "logística", the table
will say NO even though it covers it. Read it carefully.

### Where it is in the code
- `TOOL_DELEGAR`, `correr_subagente()` and `demo_1_2()`. The bias is in the `sesgo` variable inside `demo_1_2()`.

### What the exam asks
- If the final report is missing a whole topic, the root cause is usually the **coordinator's decomposition**.
- The subagent doesn't inherit the history: context is passed to it **explicitly** in its prompt.
- The coordinator decides which subagents to invoke based on the query, instead of always going through all of them.

## Demo 1.3 · Context passing and parallelism

### What it is about
Two ideas: **how to pass context between agents without losing information** (part A) and
**how to run subagents in parallel** (part B).

### Part A, step by step: do the sources survive?
1. A subagent receives 3 supplier documents (`DOCS_PROVEEDORES`), each with an id (`SRC-0101`…) and a date.
2. Depending on `D13_FORMATO`:
   - `"estructurado"`: the subagent **must** answer with the `reportar_hallazgos` tool (forced with
     `tool_choice`). Each finding carries `afirmacion` (claim), `fuente_id` (source id) and `fecha_fuente` (source date).
   - `"texto"`: the subagent summarizes in a paragraph of prose.
3. What the subagent delivers (panel **"📤 Lo que el subagente le entrega al sintetizador"**) goes to a
   **synthesizer** that must cite each fact as `[SRC-0101]` or write `[sin fuente]` (no source).
4. The table counts the citations with an id and the `[sin fuente]` ones.

What to expect: in `"estructurado"` every claim arrives with its source and date (notice that `SRC-0102`
is an old review, from 2025). In `"texto"` ids or dates usually get lost. Sometimes the model keeps
an id in the prose: the point is that **nothing guarantees it**.

### Part B, step by step: parallelism
1. A coordinator receives 3 suppliers and emits **3 `tool_use` blocks in a single response**.
2. Your code runs the 3 subagents with a `ThreadPoolExecutor` (`D13_PARALELO = True`) or one after another.
3. Compare the **real total time** against the **sum** of each subagent's time.

Watch who does what: Claude enables parallelism by asking for several tools **in the same response**. Whoever
runs them in parallel is your code (or the Agent SDK, which does it on its own).

### What gets sent to Claude
- `TOOL_REPORTAR` with an `array` of objects (`afirmacion`, `fuente_id`, `fecha_fuente`) and
  `tool_choice = {"type": "tool", "name": "reportar_hallazgos"}`.
- `TOOL_DELEGAR` (the same one as demo 1.2) for part B.

### Where it is in the code
`DOCS_PROVEEDORES`, `TOOL_REPORTAR`, `demo_1_3_parte_a()`, `demo_1_3_parte_b()`. `D13_PARTE` picks the part.

### Experiments
- `D13_FORMATO = "texto"` and compare the "Citas con id" (citations with id) column.
- `D13_PARALELO = False`: the total time becomes the sum of all of them.

### What the exam asks
- Pass results from previous agents **complete and structured** in the subagent's prompt.
- Separate content from metadata (source, date, page) to keep the attribution.
- Several `Agent`/`Task` calls in **one** coordinator response = subagents in parallel.

### Part C: real subagents (Agent SDK)
`D13_PARTE = "C"` uses the real Agent SDK: the subagent is defined with `AgentDefinition` (description, prompt and
tools) and the coordinator launches it with the **Agent** tool (on the exam, **Task**). With `D13_PERMITIR_AGENT = False`
the subagent is still defined, but without `Agent`/`Task` in `allowed_tools` the coordinator **can't** launch it.
On the exam: without Task in `allowedTools` there are no subagents.

## Demo 1.4 · Enforcement: prerequisite gate + handoff

### What it is about
**Programmatic enforcement**: when a rule involves money, security or compliance, writing it in the prompt
isn't enough (the model follows it almost always, not always). A **gate** in your code makes it impossible to skip.
And when it has to escalate, the **handoff** to a human carries a structured summary.

### What happens when you run it, step by step
1. The customer asks for the **full** refund of order #12346 ($12,500) and pushes: *"I was already verified, don't
   ask me for details"*. They don't give their email.
2. Claude works with 4 tools: `get_customer`, `lookup_order`, `process_refund` and `escalar_a_humano`.
3. Each `tool_use` goes through `ejecutar_con_gate()`. If it's `process_refund` and you're in `"gate_en_codigo"`, it checks
   3 rules, in order:
   - has someone been verified with `get_customer`? (it's saved in `estado["cliente_verificado"]`)
   - does the order belong to that customer?
   - is the amount less than or equal to `LIMITE_REEMBOLSO` ($10,000)?
4. If any fails, the tool **doesn't run** and Claude receives a `tool_result` with `is_error: true` and the reason.
5. Claude normally asks for the email or escalates with `escalar_a_humano`. The panel **"🧑‍💼 HANDOFF ESTRUCTURADO"**
   shows the 5 fields.
6. At the end there's a **direct test of the gate without the model** (refund without verification) and the audit table.

### What gets sent to Claude
- `system` with the rule written in, because it's good to tell it too.
- `TOOL_ESCALAR` with the slide's 5 fields: `customer_id`, `summary`, `root_cause`,
  `refund_amount` and `recommended_action`. They're required because **the human can't see the conversation**.

### Where it is in the code
- `ejecutar_con_gate()` inside `demo_1_4()`: the gate is an `if` in **your** dispatcher, before calling the function.
- In the Agent SDK, the same gate is done with a `PreToolUse` hook (demo 1.5).

### Experiments
- `D14_MODO = "solo_prompt"`: there's no check at all in the code. Claude will probably refuse anyway, and that's
  fine: the point is that **nothing guarantees it**. The direct test at the end makes it clear.
- Change `D14_PREGUNTA` to give Ana's email and ask for $300 from #12345: it should pass the gate.
- `D14_HANDOFF = "libre"`: escalar_a_humano only asks for a note. See what's missing for whoever receives the case.
- `D14_REPETIR = 5` with `"solo_prompt"`: the same conversation 5 times; count how many times the rule was skipped.

### What the exam asks
- Critical rules → enforcement in code (gates, hooks), not just instructions.
- Handoff with a structured summary: the human has no access to the history.

## Demo 1.5 · PreToolUse / PostToolUse hooks (Agent SDK)

### What it is about
The Agent SDK's **hooks**: functions of yours that the SDK runs automatically around each tool.
- **`PreToolUse`** runs **before**: it can block the tool (`permissionDecision: "deny"`).
- **`PostToolUse`** runs **after**: it can change the result before Claude sees it.

Difference from 1.1–1.4: here **there's no `for` of yours**. The Agent SDK runs the agentic loop; you only configure
tools, hooks and permissions.

### What happens when you run it, step by step
1. The agent checks the shipment of #12346 with `check_shipping`. The carrier returns raw, mixed data:
   `"DMG"`, `"30-10-2026"`, a date in epoch.
2. **PostToolUse** fires: the **"before and after"** table shows how `normalizar_envio()` turns it into
   `"dañado en tránsito"` (damaged in transit) and ISO dates. Claude only sees the clean version.
3. The agent tries `process_refund` for $12,500.
4. **PreToolUse** fires (magenta panel), sees that it exceeds $10,000 and answers **deny** with a reason.
5. The tool **doesn't run**: *"💸 SE EJECUTÓ process_refund"* (process_refund RAN) never appears. Claude receives the reason as a
   `tool_result` with an error and explains to the customer that it will be escalated.
6. The final `ResultMessage` carries turns, `session_id` and cost.

### Where the hooks are configured
In the agent's options (`ClaudeAgentOptions`), the `hooks` parameter:

```python
hooks = {
    "PreToolUse":  [HookMatcher(matcher="mcp__tiendita__process_refund", hooks=[hook_pre_reembolso])],
    "PostToolUse": [HookMatcher(matcher="mcp__tiendita__check_shipping", hooks=[hook_post_envio])],
}
```
- `matcher`: which tool it applies to (name or regex). `None` = all.
- Each hook is `async def hook(input_data, tool_use_id, context)`. `input_data` carries `tool_name`, `tool_input`
  and, in `PostToolUse`, `tool_response`.
- To block, return `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
  "permissionDecisionReason": "..."}}`. To let it through, `{}`.
- To change an MCP tool's result, return `"updatedMCPToolOutput"`.

### This demo's tools
They're defined with the `@tool(name, description, parameters)` decorator and packaged in an MCP server
**in the same process** with `create_sdk_mcp_server(name="tiendita")`. That's why they're called
`mcp__tiendita__check_shipping` and `mcp__tiendita__process_refund`. Also:
- `tools=[]` turns off the built-in tools (Read, Bash…), so the agent only has ours.
- `allowed_tools` approves them without asking.

### Where it is in the code
`ENVIOS_CRUDOS`, `normalizar_envio()`, and inside `demo_1_5()`: `t_check_shipping`, `t_process_refund`,
`hook_pre_reembolso`, `hook_post_envio` and the `hooks` dict. The agent's options are built with `opciones_base()`.

### Experiments
- `D15_ACTIVAR_PRETOOLUSE = False`: the $12,500 refund **does** run.
- `D15_ACTIVAR_POSTTOOLUSE = False`: Claude sees `"DMG"` and `"30-10-2026"` as they are and has to guess.
- `D15_BLOQUEO_EN = "post"`: the block moves to PostToolUse. It's too late: the refund already happened.

### What the exam asks
- Hooks = a **deterministic** guarantee; prompt = probabilistic.
- `PostToolUse` to normalize formats from different sources before the agent processes them.
- `PreToolUse` to block actions that violate policies and redirect to escalation.

## Demo 1.6 · Prompt chaining and multi-pass review

### What it is about
Two ways to **decompose** a large job:
- **Prompt chaining** (part A): fixed steps you already know, each in its own call.
- **Multi-pass review** (part B): review file by file and then do an integration-only pass.

### Part A, step by step
1. **Step 1 · extract**: the `extraer_datos` tool is forced on the review (`D16_RESENA`). Output in JSON:
   `pedido`, `producto`, `problema`, `fecha_limite`, `sentimiento` (order, product, problem, deadline, sentiment).
2. **Step 2 · classify**: another call that **only sees the JSON** from step 1 and classifies the urgency.
3. **Step 3 · respond**: another call writes the reply using the data and the urgency.

Detail: `fecha_limite` accepts `null` (`"type": ["string", "null"]`), so the model doesn't invent a date
when there isn't one. Here there is a date ("before December 20").

### Part B, step by step
Three La Tiendita files (`ARCHIVOS_TIENDITA`) with a bug that **crosses files**: `checkout.py` calls
`calcular_total(pedido, incluir_iva=True)`, but in `carrito.py` that function only takes `pedido` (it would fail) and
it already includes VAT (it would be doubled).
- `"multipass"`: one call per file ("review ONLY this file") and at the end an **integration pass**
  that looks only for problems between files. Only there can the bug be **confirmed**, because you have to see both.
- `"una_pasada"`: the 3 files together in one call.

What to honestly expect: with 3 small files, the single pass will probably find it too. The
problem shows up at scale (14 files or more): **attention dilution**, uneven review and missed bugs. The
local passes will also flag `pasarela` and `registrar_movimiento` as undefined: that's correct, the example
is trimmed.

### Where it is in the code
`TOOL_EXTRAER`, `demo_1_6_parte_a()`, `ARCHIVOS_TIENDITA`, `demo_1_6_parte_b()`.

### Experiments
- Change `D16_RESENA` to a review without a deadline and check that `fecha_limite` comes out `null`.
- Add more files to `ARCHIVOS_TIENDITA` and compare `"una_pasada"` against `"multipass"`.
- `D16_NUM_ARCHIVOS = 14`: the cross-file bug ends up at the end. Compare `"una_pasada"` against `"multipass"`.

### What the exam asks
- Prompt chaining for predictable flows; dynamic decomposition for open-ended investigation.
- Large reviews: local passes per file + an integration pass across files.

## Demo 1.7 · Sesiones: resume, fork, contexto obsoleto

### What it is about
How to continue work across sessions without dragging along old information.

### Part A, step by step (Agent SDK)
Four short runs, no tools:
1. **Original**: *"the mug costs $299"*. The `session_id` is saved.
2. **`resume=session_id`**: same session (same id). It remembers the $299.
3. **`resume` + `fork_session=True`**: copies the history and creates a **new** session (another id). In that branch the
   mug becomes $349.
4. **Back to the original with `resume`**: it still says $299. The fork didn't touch it.

The final table shows the `session_id` values: 1, 2 and 4 are the same; 3 is different. In the Claude
Code terminal the equivalent is `claude --resume <id>`.

### Part B, step by step (stale context)
A history is built by hand where Claude already read `precios.txt` (mug = $299). Then the file changed ($349).
- `"resume"`: the same conversation continues and the file is reread. The history has **both** values.
  When asked for all the prices it knows, it lists both: the old one is still there and can confuse it.
- `"nueva_sesion"`: a new session with a **summary** of what's current + reread only what changed. The 299 no longer exists.

### Where it is in the code
`demo_1_7_parte_a()` (the `resume` and `fork_session` options in `opciones_base()`) and `demo_1_7_parte_b()`.

### Experiments
- `D17_ESTRATEGIA = "nueva_sesion"` and compare the answer.

### What the exam asks
- `resume` when the previous context is still valid; tell the agent which files changed.
- A new session + structured summary when the results of previous tools are already stale.
- `fork_session` to explore two approaches from the same base.

# Domain 2 · Tool Design & MCP Integration

## Demo 2.1 · Tool descriptions and selection

### What it is about
Claude picks a tool by reading only three things: its **name**, its **description** and its **input_schema**. It doesn't see your
code or know what the function does inside. If two descriptions look alike, the selection becomes a coin
toss. Improving the descriptions is the **first fix**, before few-shot examples or a classifier.

### What happens when you run it, step by step
1. The table with the 4 tools and their **minimal** descriptions is printed: `get_customer`, `lookup_order`,
   `get_shipping_rates` and `search_products`.
2. The 6 queries in `D21_CONSULTAS` are sent one by one. For each one you see which tool Claude picked (✔/✘) and
   the input it built.
3. Everything repeats with the **complete** descriptions.
4. The final table compares the two rounds and counts the correct picks.
5. On the run's page (and in the example), the card **"Las descripciones tal cual las lee Claude"** (the descriptions exactly
   as Claude reads them) puts the minimal one next to the complete one, with what each tool receives, and color-codes the 5 parts of a good
   description: what it does, when to use it, what it returns, what it takes and when NOT to use it.

To measure the selection it uses `tool_choice = {"type": "any"}`: Claude **has** to pick some tool.

### What gets sent to Claude: minimal vs complete
Minimal (all of them share a generic `query` parameter):
```python
{"name": "get_shipping_rates", "description": "Información de envíos.",
 "input_schema": {"properties": {"query": {"type": "string"}}}}
```
Complete (what it does, what it returns, input format and **when NOT to use it**, with the alternative):
```python
{"name": "get_shipping_rates",
 "description": "Cotiza tarifas GENERALES de envío ANTES de comprar, según código postal... "
                "NO sirve para pedidos ya hechos: el costo de envío cobrado se consulta con lookup_order.",
 "input_schema": {"properties": {"codigo_postal": {"type": "string", "description": "CP de 5 dígitos"}}}}
```
(The lab's descriptions are in Spanish: "Shipping information." vs "Quotes GENERAL shipping rates BEFORE buying, by
zip code... NOT for orders already placed: the shipping cost charged is looked up with lookup_order.")

### What to expect
- The **names** already say a lot, so with the minimal ones Claude will get several right. The differences show up in the
  edge cases:
  - *"How much was I charged for shipping on order #12347?"* → with minimal descriptions it tends to go to `get_shipping_rates` because of the
    word "shipping". The right one is `lookup_order`, because it's an order already placed.
  - *"My order hasn't arrived, my email is…"* → with minimal descriptions it tends to go to `lookup_order` because of the word "order". The
    right one is `get_customer`, because there's no order number and the email gets you the list.
- Also look at the **input**: with `query` Claude sends the whole sentence; with `email`, `order_id` or
  `codigo_postal` it sends just the piece of data.
- Results can vary between runs. That itself is part of the lesson.

### Experiment with the system prompt
`D21_CONFLICTO_EN_SYSTEM = True` adds: *"every time the customer mentions the word 'order', start with
get_customer"*. Queries with "order #…" go to `get_customer` even though the description says otherwise.
A keyword instruction in the system prompt **beats** a good description.

### Where it is in the code
`TOOLS_21_MINIMAS`, `TOOLS_21_COMPLETAS`, `_correr_seleccion()` and `demo_2_1()`.

### What the exam asks
- Minimal or overlapping description → unreliable selection. Fix: descriptions with input format,
  examples, edge cases and boundaries.
- Rename tools to remove overlaps, or split a generic tool into several with a clear purpose.
- Check the system prompt when a tool gets picked "for no reason".

## Demo 2.2 · Structured vs generic errors

### What it is about
What your tool returns to Claude **when something goes wrong**. There are two classic mistakes:
1. **Generic error** (`"Operation failed"`): Claude doesn't know whether to retry, ask for other data or escalate.
2. **Silenced error**: the system failed, but the tool returns an empty list. Claude thinks the query
   worked and tells the customer something **false** ("you have no orders").

The solution is a **structured error**: `is_error: true` and in the content `errorCategory` (`transient`,
`validation`, `business` or `permission`), `isRetryable` and a readable `description`. And an empty result that is
valid is **not** an error.

### What happens when you run it, step by step
A single tool, `buscar_pedidos_cliente(email, anio)`. For each scenario it runs a mini agentic loop (at most
`D22_MAX_ITERACIONES` rounds) and you see the call, the `tool_result` (red if it's an error) and what Claude tells the
customer. First everything in **generic** format, then in **structured** format.

| Scenario | What happens in the "system" | Generic returns | Structured returns |
|---|---|---|---|
| `caido` | timeout the 1st time, then it works | `{"pedidos": []}` with no error | `transient`, `isRetryable: true` |
| `sin_pedidos` | customer with no orders (valid) | `{"pedidos": []}` | success, `total: 0` and a note |
| `email_invalido` | `ana@ejemplo` with no domain | `"Operation failed"` | `validation`, don't retry |
| `sin_permiso` | asks for another person's orders | `"Operation failed"` | `permission`, don't retry |
| `historico` | 2019 orders, archived | `"Operation failed"` | `business` + how to request them |

### What to expect
- **`caido · generico`** is the key moment: Claude says there are no orders, when in fact the system
  was down. In **structured** it retries and gets the orders on the 2nd attempt.
- With the generic one, Claude sometimes guesses right (for example, it notices `ana@ejemplo` is misspelled), but it
  does it on its own: the tool didn't give it that information.
- The final table puts the calls, the answer and **what should happen** side by side.

### Where it is in the code
`TOOL_PEDIDOS_CLIENTE`, `_backend_pedidos(escenario, formato, intento)` (the two response formats
are here) and `_correr_caso_22()` (the loop; that's where the `tool_result` with `is_error` is built).
In MCP the field is called `isError` (you'll see it in demo 2.4); in the Messages API it's `is_error`.

### Experiments
- `D22_FALLAS_TRANSITORIAS = 3`: how many times does it retry before giving up?
- Remove scenarios from `D22_ESCENARIOS` for a shorter run.

### What the exam asks
- Structured error metadata so the agent can decide: retry, explain or escalate.
- Distinguish an access failure from a valid empty result.
- In multi-agent setups: the subagent retries what's transient locally and propagates to the coordinator only what it couldn't
  resolve, with what it tried and partial results. Don't suppress errors or stop everything because of a single failure.

## Demo 2.3 · Too many tools and tool_choice

### What it is about
Two design decisions: **how many tools** to give each agent (part A) and **how to force it to use one**
(part B, `tool_choice`).

### Part A, step by step: 4 tools vs 18
1. **Round 1:** 4 tools for the support role (`get_customer`, `lookup_order`, `process_refund`, `escalar_a_humano`).
2. **Round 2:** those 4 + 14 overlapping distractors (`get_customer_profile`, `fetch_client_record`,
   `get_order_history`, `get_shipping_status`, `refund_preview`, `create_support_ticket`…).
3. The same 4 queries in each round. For each one you see the chosen tool and the **input tokens**.
4. Table: correct picks and average tokens per request.

What to expect:
- With 4 tools, almost always 4/4.
- With 18, "reasonable but unexpected" choices usually show up: `get_shipping_status` instead of
  `lookup_order`, `create_support_ticket` instead of `escalar_a_humano`, `refund_preview` instead of `process_refund`.
- **Input tokens** go up a lot: each tool definition travels with **every** request.

### Part B, step by step: tool_choice
The same message (*"what time does the physical store open?"*), with two tools (`extraer_metadatos` and `get_customer`)
and three modes:

| `tool_choice` | Means | What to expect |
|---|---|---|
| `{"type": "auto"}` | Claude decides (default) | Text, `stop_reason: "end_turn"` |
| `{"type": "any"}` | Must call **some** tool | `tool_use` even if not needed |
| `{"type": "tool", "name": "extraer_metadatos"}` | Must call **that one** | `tool_use` of `extraer_metadatos` |

With `auto`, notice whether Claude invents opening hours or admits it doesn't know.

### Part C, step by step: tool_choice in a real case
A document arrives and you don't know whether it's an invoice, a receipt or a contract; there's one tool (one schema) per type.

| Step | `tool_choice` | What for |
|---|---|---|
| 1 | `{"type": "tool", "name": "extraer_metadatos"}` | Guarantees that step goes **first** |
| 2 | `{"type": "any"}` with the 3 extraction tools | Claude **must** pick a schema; it can't answer in text |
| 3 | `{"type": "auto"}` | With the data in hand, Claude decides (it may answer in text) |

What to expect with the sample receipt: `extraer_recibo` in step 2. Change `D23_DOCUMENTO_C` to an invoice
(with RFC and folio number) or a contract and see which schema it picks.

### Exam vs current product
With `D23_MODELO_B = "claude-sonnet-5-5"`, the `any` and `tool` modes answer with a **400 error**. The demo catches it and
explains it. The exam tests the **concept**; in today's API, with Sonnet and Opus 5.5 you use `auto` + a
clear instruction + `strict: true` on the tool, or Haiku 5.5, which does accept them.

### Where it is in the code
`TOOLS_23_NUCLEO`, `TOOLS_23_DISTRACTORAS`, `TOOLS_23_EXTRACCION`, `demo_2_3_parte_a()`, `demo_2_3_parte_b()`,
`demo_2_3_parte_c()`. The `_tool()` helper
builds each definition in one line.

### Experiments
- `D23_TOOLS_A = "18"` (or `"4"`): runs part A with only that configuration.

### What the exam asks
- 18 tools instead of 4 or 5 → worse selection. Each subagent gets only the tools for its role.
- Replace generic tools with restricted versions; give a narrow shared tool (e.g. `verify_fact`)
  when a role needs it often.
- `tool_choice: any` guarantees a call; forcing a tool guarantees the order (e.g. extract metadata first).

## Demo 2.4 · Your own MCP server + Agent SDK

### What it is about
**MCP (Model Context Protocol)**: a standard for an agent to discover and use tools and data from external
systems. An **MCP server** offers:
- **Tools**: actions Claude can call.
- **Resources**: data that can be read, like a catalog or documentation.

The demo creates its own server, first talks to it **without Claude** and then connects it to an agent.

### The server (`servidor_inventario_mcp.py`, generated next to the script)
```python
app = MCPServer("inventario")

@app.tool(description="Busca productos en el catálogo...")
def buscar_producto(texto: str) -> CallToolResult: ...

@app.tool(description="Devuelve las piezas disponibles de UN producto por su SKU...")
def consultar_stock(sku: str) -> CallToolResult: ...        # nonexistent SKU → is_error=True

@app.resource("inventario://catalogo", description="Catálogo completo...")
def catalogo() -> str: ...

app.run()   # stdio: the agent starts it as a subprocess
```
- The `description` is what Claude reads. The **type hints** (`texto: str`) become the `input_schema`.
- `respuesta(datos, es_error=True)` returns a `CallToolResult` with `isError: true` and the structured error
  (the same as demo 2.2). In MCP the 3 fields (`errorCategory`, `isRetryable`, `description`) go in
  `structuredContent`; with the Messages API (demo 2.2) they go in the `tool_result`'s `content`.

### What happens when you run it, step by step
**Part A · direct MCP client (no Claude):**
1. It connects to the server over stdio with `ClientSession`.
2. `tools/list`: you see the two tools **exactly as Claude will receive them** and their final name, `mcp__inventario__…`.
3. `resources/list` and `resources/read`: the full catalog.
4. `tools/call` with a valid SKU (`isError=False`) and a made-up one (`isError=True` + structured error).

**Part B · the same server connected to an agent (Agent SDK):**
```python
mcp_servers = {"inventario": {"type": "stdio", "command": "python", "args": [".../servidor_inventario_mcp.py"]}}
allowed_tools = ["mcp__inventario__buscar_producto", "mcp__inventario__consultar_stock"]
```
What to expect: the agent searches for "embroidered tablecloths", checks the stock of `MAN-ROJ-01` (4 units) and `MAN-AZL-01`
(sold out), and when checking `MAN-VER-01` it gets the validation error. Then it tells the customer that SKU doesn't exist.

**Part C · configuration in Claude Code:** a sample `.mcp.json` and a scopes table are printed.

| File | Scope | What for |
|---|---|---|
| `.mcp.json` (in the repo) | Project: the whole team, goes into git | Shared servers |
| `~/.claude.json` | User: only you | Personal or test servers |

Secrets go in as `${GITHUB_TOKEN}`: each person has their own environment variable and the token never goes into git.

### Where it is in the code
`SERVIDOR_MCP_CODIGO` (the full server as text), `_cliente_mcp_directo()`, `MCP_JSON_EJEMPLO`, `demo_2_4()`.

### Experiments
- `D24_USAR_RESOURCES = True`: the agent also gets `ListMcpResourcesTool` and `ReadMcpResourceTool`, and can
  read the full catalog instead of searching blindly.
- Make the description of `buscar_producto` worse (for example, `"Busca."`) and compare.
- Open `servidor_inventario_mcp.py` and add a new tool. The lab **doesn't overwrite** your version if the file
  already exists; delete it to go back to the original.
- `D24_SECRETO = "en_archivo"`: the token ends up written in the `.mcp.json` that goes into git.
- `D24_ALCANCE = "usuario"`: the server ends up in `~/.claude.json` and your teammate doesn't have it.

### What the exam asks
- The project's `.mcp.json` vs the user's `~/.claude.json`, and `${VAR}` variable expansion for secrets.
- The tools from every configured server are discovered on connecting and become available at once.
- Improve MCP tool descriptions so the agent doesn't ignore them and use built-ins like Grep instead.
- Resources as a content catalog to save exploratory calls.
- Community servers for standard integrations; your own only for the team's specific flows.

## Demo 2.5 · Built-in tools: Grep, Glob, Read, Edit (Agent SDK)

### What it is about
Claude Code's **built-in** tools and when to use each one:

| Tool | What for |
|---|---|
| **Grep** | Search for **content** inside files (who calls a function, an error message) |
| **Glob** | Search for **files** by name or path pattern (`**/*.test.ts`); it doesn't look at content |
| **Read** | Read a file |
| **Edit** | Targeted change: replaces text that must be **unique**; if it isn't, it fails |
| **Write** | Overwrite the whole file (fallback when Edit can't) |

### The sample repo and its traps
It's created in a temporary folder with La Tiendita's TypeScript files:
- `src/reembolsos/index.ts` re-exports `processRefund as submitRefund`, and `src/admin/panel.ts` renames it
  again (`submitRefund as reembolsoManual`). If you only search for "processRefund", you'll miss files.
- In `config/limites.json` the value `10000` appears **twice** (`limite_reembolso` and `limite_credito`). An
  Edit of just `"10000"` isn't unique.

### What happens when you run it, step by step
The task asks for 3 things: find every usage of `processRefund` (aliases included), list the
`*.test.ts` files and change **only** the refund limit to 8000. A typical flow:
1. **Grep** `processRefund` → `procesar.ts`, `index.ts` and the test.
2. **Read** `index.ts` → discovers the `submitRefund` alias.
3. **Grep** `submitRefund` → `pago.ts` and `panel.ts`.
4. **Glob** `**/*.test.ts` → the 2 test files.
5. **Read** `limites.json` → **Edit** with text that includes the key (`"limite_reembolso": 10000`).
   If it tries just `10000`, you'll see the Edit error and how it gets fixed with more context.

Each call appears in a **"🪝 llamada #N"** (call #N) panel with the tool's explanation. At the end:
- `limites.json` before and after;
- a check that `limite_credito` is still 10000;
- how many of the 5 real files it reported;
- a table of which tools it used and how many times.

### Where tools, permissions and hooks are configured
```python
opciones_base(
    tools=D25_TOOLS, allowed_tools=D25_TOOLS,      # which built-ins it has and which are auto-approved
    cwd=str(repo), permission_mode="acceptEdits",  # works in the repo and accepts edits without asking
    hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[hook_registro, hook_solo_repo])]},
)
```
- `matcher=None` means the hooks run for **every** tool.
- `hook_registro` only prints and counts.
- `hook_solo_repo` answers **deny** if a path leaves the repo folder (enforcement, as in demo 1.5).

### Experiments
- Remove `"Grep"` from `D25_TOOLS`: it will have to open file by file with Read (more turns and tokens).
- `D25_EDIT_RESPALDO = "read_write"` (with `"Write"` in `D25_TOOLS`): the Edit of just `10000` fails because the text repeats and
  the agent uses Read + Write, which is what the exam expects.
- Remove `"Glob"`: finding the `*.test.ts` files gets harder.
- Change `D25_TAREA` to ask it to change "the 10000" without saying which, and watch the Edit error.

### What the exam asks
- Grep for content, Glob for paths, Edit for targeted changes with unique text, and Read + Write as the fallback.
- Explore incrementally: Grep to find entry points and Read to follow imports, instead of reading everything.
- Trace a function across modules that re-export it: identify the exported names and search for each one.

# Domain 3 · Claude Code Configuration & Workflows

## Demo 3.1 · CLAUDE.md hierarchy (Agent SDK)

### What it is about
Claude Code gathers instructions from **several CLAUDE.md files** and each one has a different scope. The exam's
question is always the same: **where does this instruction live and who receives it?**

| File | Scope | Goes into git? |
|---|---|---|
| `~/.claude/CLAUDE.md` | Only you, in all your projects | No |
| `CLAUDE.md` (repo root) | The whole team | Yes |
| `CLAUDE.local.md` | Only you, in this repo | No (`.gitignore`) |
| `src/api/CLAUDE.md` (subfolder) | Whoever works in that folder | Yes |
| `@docs/estilo.md` inside a CLAUDE.md | Imports another file | Depends on where it is |

The demo doesn't touch your `~/.claude/CLAUDE.md`. The "personal" case is shown with `CLAUDE.local.md`.

### What happens when you run it, step by step
1. A test project is created in a temporary folder and its 4 instruction files are printed:
   - `CLAUDE.md`: neutral Spanish; imports `@docs/estilo.md`.
   - `docs/estilo.md`: amounts in MXN with two decimals and function names in English.
   - `CLAUDE.local.md`: a personal preference (short bullet points).
   - `src/api/CLAUDE.md`: the shape of the API's responses.
2. It runs Claude Code with the Agent SDK (Claude Code's prompt + `setting_sources=["project", "local"]` + only the `Read` tool).
3. It asks which rules it knows and asks it to read `src/api/reembolsos.ts`.
4. The table **"📂 Qué instrucciones cargó Claude Code y cuándo"** (which instructions Claude Code loaded and when) comes from the session **transcript**, not from
   what the model says:
   - **at session start**: `CLAUDE.md`, `docs/estilo.md` and `CLAUDE.local.md`;
   - **after reading reembolsos.ts**: `src/api/CLAUDE.md`.
5. At the end, a ✔/✘ per file explains why it was loaded or not.

### What gets sent to Claude
- `setting_sources` decides which configuration Claude Code reads: `"project"` = CLAUDE.md, `.claude/` and whatever they import;
  `"local"` = `CLAUDE.local.md`; `"user"` = your `~/.claude` (the demo does **not** use it).
- `system_prompt={"type": "preset", "preset": "claude_code"}`: the same system prompt Claude Code uses.

### Where it is in the code
- `crear_proyecto()` builds the temporary folder.
- `opciones_claude_code()` builds the agent's options.
- `instrucciones_cargadas()` reads the transcript (`~/.claude/projects/.../<session_id>.jsonl`). That format is
  internal to Claude Code: if it changes in a future version, the table won't appear, but the demo still works.

### Experiments
- `D31_USAR_IMPORT = False`: `docs/estilo.md` no longer loads and the agent stops knowing the amounts rule.
- `D31_SIMULAR_COMPANERO = True`: runs as someone new on the team (`setting_sources=["project"]`).
  `CLAUDE.local.md` disappears. It's the classic exam case: the team's rule was in a personal file.
  The fix is to move it to the repo's `CLAUDE.md`.
- Ask it to read `src/carrito/total.ts` instead of `reembolsos.ts`: `src/api/CLAUDE.md` doesn't load.

### What the exam asks
- A new teammate doesn't get an instruction → it was in `~/.claude/CLAUDE.md` (personal). It goes in the repo's CLAUDE.md.
- Import with `@path` (there is no `@import`) to keep CLAUDE.md modular; `.claude/rules/` to split by topic.
- `/memory` to see which memory files are loaded and diagnose inconsistent behavior.

## Demo 3.2 · Slash commands and skills (Agent SDK)

### What it is about
Two ways to package a flow for reuse:

| | Slash command | Skill |
|---|---|---|
| Who triggers it | **You**: `/revisar-reembolso #12346` | **Claude**, when the task matches the description |
| Where it lives | `.claude/commands/<name>.md` | `.claude/skills/<name>/SKILL.md` |
| Personal | `~/.claude/commands/` | `~/.claude/skills/` |
| Context | Sent in full when invoked | At first only name + description; the body loads when used |

Rule for deciding: what **always** applies goes in CLAUDE.md; what **you** invoke, in a command; what
**Claude** should decide to use, in a skill.

### What happens when you run it, step by step
**Part A · slash command**
1. `.claude/commands/revisar-reembolso.md` is printed with its frontmatter (`description`, `argument-hint`) and its body.
2. The prompt `/revisar-reembolso #12346` is sent. Claude Code replaces `$ARGUMENTS` with `#12346` and sends it as
   if you had typed it.
3. The agent reads `politica_reembolsos.md` and `pedidos.json`. Expected answer: **NO CUMPLE** (doesn't comply), because $12,500 exceeds
   $10,000.

**Part B · skill**
1. `SKILL.md` is printed with its `description`.
2. A normal request is sent: *"How did we do with customers this week? Their comments are in resenas.txt…"*.
3. If Claude decides to use the skill, a hook shows **"🪝 Skill invocado"** (skill invoked): that's when the full body of SKILL.md loads.
4. It normally delivers the sentiment table and "Atender primero: envío" (handle first: shipping), because it's the most repeated problem.
5. At the end: ✔ or ✘ depending on whether it used the skill.

### Where it is in the code
- The project files are in the dictionary passed to `crear_proyecto()`, inside `demo_3_2()`.
- `DESCRIPCIONES_SKILL_32` has the good description and the vague one.
- `hook_skill` is a `PreToolUse` with `matcher="Skill"`: it only records the invocation.
- The tools are `Read`, `Glob` and `Skill`; without the `Skill` tool, Claude can't invoke skills.

### Experiments
- `D32_DESCRIPCION_SKILL = "vaga"` (*"Utilidades varias."*, miscellaneous utilities): Claude will probably **not** use the skill. It's the same
  lesson as demo 2.1: the description decides.
- `D32_PEDIDO = "#12345"`: $1,850 with a photo → it should come out CUMPLE (complies).
- Open the project folder (the path is shown on screen) and create your own command.

### What the exam asks
- A team command → `.claude/commands/` (goes into git). Personal → `~/.claude/commands/`.
- Skill frontmatter: `context: fork` runs the skill in an isolated subagent; `allowed-tools` limits which tools
  it uses; `argument-hint` says which argument it expects.
- Skill = on demand; CLAUDE.md = always loaded.

## Demo 3.3 · Path rules in .claude/rules (Agent SDK)

### What it is about
**Path rules** are files in `.claude/rules/` with a `paths:` frontmatter containing globs. Claude Code
loads each rule **only** when it works with matching files. That way the test conventions don't take up
context when you edit the API, and vice versa.

```markdown
---
paths:
  - "**/*.test.ts"
---
# Reglas de pruebas
- Usa describe/it.
```

**Why not a CLAUDE.md in a subfolder?** Because the tests are **scattered all over the repo**. A
`**/*.test.ts` glob reaches all of them; a CLAUDE.md only covers its own folder.

### What happens when you run it, step by step
1. A project is created with two rules: `api.md` (`paths: src/api/**/*.ts`) and `tests.md` (`paths: **/*.test.ts`).
2. Claude is asked to read `src/api/reembolsos.ts` and then `src/carrito/carrito.test.ts`, and to say which conventions
   apply to each one.
3. The transcript table shows when each rule loaded:
   - `CLAUDE.md` → at startup;
   - `.claude/rules/api.md` → after reading `reembolsos.ts`;
   - `.claude/rules/tests.md` → after reading `carrito.test.ts`.
   The **"Se activa con"** (triggered by) column shows the glob.

### Where it is in the code
`demo_3_3()`: the `encabezado_api` and `encabezado_tests` variables add or remove the `paths:` frontmatter.
The table comes from `mostrar_instrucciones()`, the same one as demo 3.1.

### Experiments
- `D33_CON_PATHS = False`: both rules appear **at session start**, even if you don't touch those files.
  It works, but it spends context all the time.
- Change `D33_PREGUNTA` to read only `src/carrito/total.ts`: no rule loads.

### What the exam asks
- Conventions for a file type scattered across the repo → `.claude/rules/` with `paths` (glob), not a CLAUDE.md per folder.
- Advantage: they load only when they apply, so they reduce tokens and noise.

## Demo 3.4 · Plan mode vs direct execution (Agent SDK)

### What it is about
**Plan mode** (`permission_mode="plan"`): Claude explores and proposes a plan, but **can't edit** files.
Use it when the task is **large or ambiguous**: it's worth seeing the plan before anything gets edited.
**Plan mode** is for large changes (a 45-file migration), with several valid approaches or with architectural decisions. A clear, well-scoped change (changing a value in 3 files) goes with **direct execution**. The **hybrid** pattern combines both: plan → review/approve → execute.

### What happens when you run it, step by step
The project has the refund limit (10000) in 3 places: `config/limites.json`, `src/reembolsos.ts` and
`docs/politica.md`. The task is to change it to 8000 in all of them.

- **`"plan"`**: the agent searches with Grep, reads and proposes a plan. If it tries to edit, Claude Code blocks it
  (*"Cannot write … while in plan mode"*). At the end you'll see **"Archivos modificados en plan mode: ninguno"** (files modified in plan mode: none).
- **`"directo"`**: with `acceptEdits` it edits directly.
- **`"hibrido"`** (default): phase 1 in plan mode; phase 2 **in the same session** (`resume`) with `acceptEdits`
  and the message *"Plan approved. Implement it."*.

The final table shows which files changed.

### Where it is in the code
`demo_3_4()`: `permission_mode="plan"` and then `permission_mode="acceptEdits"` with `resume=resultado.session_id`.
The tools are `Read`, `Glob`, `Grep` and `Edit`; even with `Edit` in `allowed_tools`, plan mode doesn't let it write.

### Experiments
- Run the 3 values of `D34_MODO` and compare the final table.
- Read the phase 1 plan: did it find the 3 places? If not, the plan's value is that you notice before anything gets edited.
- `D34_TIPO_TAREA = "clara"` or `"ambigua"`: plan mode is worth it if there are several valid approaches or the change is large; a clear, well-scoped change goes direct.

### What the exam asks
- Migrations, architectural changes or tasks with several possible solutions → plan mode.
- A bug with a clear cause in a single file → direct execution.
- Explore with a subagent so the main context doesn't fill up; plan before executing.

## Demo 3.5 · Iterative refinement: examples and TDD

### What it is about
How to correct a result that doesn't come out the way you want. The exam's techniques:
- **Concrete examples** of input → output, instead of describing with adjectives.
- **TDD**: tests first; then you ask for the code and share **the tests that failed** with it.
- **Interview pattern**: on unclear tasks, have Claude ask you questions before implementing.
- **Related** fixes in a single message; **independent** ones, one at a time.

### What happens when you run it, step by step
The task is to write `normalizar_telefono(texto)` for Mexican phone numbers. There are 8 tests in `CASOS_35`, including
edge cases: `044 664…`, `52 664…` without `+`, `"123"` → `None` and a text with a `tel:` prefix.

- **`"vago"`**: it's described in a single sentence only. One round.
- **`"ejemplos"`**: the same sentence + 3 input → output examples, chosen from the edge cases (parentheses, `044` and an invalid one). One round. The guide asks for 2–3 examples: more isn't better.
- **`"tdd"`** (default): starts vague and, in each round, sends Claude only the tests that failed, with
  input, got and expected. Up to `D35_MAX_RONDAS`.

In each round you'll see the code Claude wrote, the test table (✔/✘) and "Pasaron X/8" (X/8 passed). At the end, a table
with the progress per round.

### Security: the code gets executed
The code Claude writes runs in **a separate process** (`python -I`), with a **10-second limit**,
inside a temporary folder. If you'd rather just look at it, set `D35_EJECUTAR_CODIGO = False`.

### Where it is in the code
`CASOS_35`, `PETICION_VAGA_35`, `PETICION_EJEMPLOS_35`, `_extraer_codigo()`, `_correr_pruebas()` and `demo_3_5()`
(the `for ronda` loop, where the message with the failures is built).

### Experiments
- Run the 3 modes and compare. The usual: `"vago"` fails on the edge cases, `"ejemplos"` gets more right from the
  first round and `"tdd"` converges in 2 or 3 rounds.
- Add a new case to `CASOS_35` (for example, with an extension `ext. 12`) and see how TDD handles it.

### What the exam asks
- Prose descriptions get interpreted inconsistently → give 2 or 3 concrete examples.
- Iterating by sharing the failing tests (input, got and expected) converges better than "it doesn't work, fix it".

## Demo 3.6 · CI/CD with claude -p

### What it is about
Claude Code in a CI/CD pipeline, where there's **nobody** to answer. Without `-p`, Claude Code opens an interactive
session and the job hangs waiting.

| Flag | What for |
|---|---|
| `-p "prompt"` (`--print`) | Runs, prints the result and exits |
| `--output-format json` | Output the pipeline can read: `result`, `total_cost_usd`, `session_id`… |
| `--json-schema '<schema>'` | The answer is validated against your schema and arrives in `structured_output` |
| `--allowedTools`, `--tools` | What it can use (here only `Read`) |
| `--max-turns`, `--max-budget-usd` | Turn and spending limits |

### What happens when you run it, step by step
1. A test repo is created with a `CLAUDE.md` (*"automatic refunds up to $10,000"*) and a `cambios.diff` that
   raises the limit to 100000.
2. The **full command** is printed and the Claude Code CLI (the one that comes inside `claude-agent-sdk`) runs
   as a separate process.
3. With `"json"` + schema you'll see:
   - the useful fields of the JSON (`subtype`, `num_turns`, `total_cost_usd`, `session_id`);
   - `structured_output` with `aprobado` (approved) and the list of `problemas` (problems: file, severity, description);
   - the pipeline's decision: **BLOCK the merge**, because it violates the CLAUDE.md rule.
4. A sample GitHub Actions workflow is printed.

### Where it is in the code
`SCHEMA_36`, `GITHUB_ACTIONS_36`, `_ruta_cli()` (finds the CLI inside `claude-agent-sdk`) and `demo_3_6()`, which builds
the `comando` list and runs it with `subprocess.run`.

### Experiments
- `D36_FORMATO = "text"`: the output is prose and the pipeline can't decide anything with it.
- `D36_CON_SCHEMA = False`: there's JSON, but `result` is still free text.
- Edit `cambios.diff` in the demo so it respects the limit: it should approve.

### What the exam asks
- The CI job hangs → `-p` is missing.
- Output to be processed → `--output-format json` + `--json-schema`.
- The reviewer must be a session **independent** from the one that generated the code: it doesn't review itself.
- CLAUDE.md gives project context in CI too. Include previous findings so it doesn't repeat comments on every push.
- `claude -p` for blocking reviews before the merge; Message Batches API (Domain 4) for jobs that can wait.

# Domain 4 · Prompt Engineering & Structured Output

## Demo 4.1 · Explicit criteria in the system prompt

### What it is about
Instructions like *"flag what matters"*, *"be conservative"* or *"only if you're highly confident"* don't tell the
model **where the line is**. Each run puts it in a different place: too many alerts (false positives) or
too few (false negatives). The solution is **explicit criteria**: what DOES count and what DOESN'T, with examples.

Exam detail: false positives make people stop trusting **all** the alerts, even the
correct ones.

### What happens when you run it, step by step
1. The table of 14 tickets with the correct answer (escalate yes or no?) is printed. The last 4 depend on the store's
   policy (the $10,000 limit, what counts as a legal threat): a vague prompt can't guess them.
2. All of them are classified with the **vague** system prompt, in a single call with the `clasificar_tickets` tool forced,
   so the comparison is only about criteria and not format.
3. The same with the **explicit** system prompt: 3 criteria for escalating (money at risk, account security,
   legal threat) and a list of what does NOT get escalated.
4. The table compares each decision with the correct one and marks a **false positive** or **false negative**.
5. Summary: correct answers, false positives and false negatives per mode.

Cases where the difference usually shows:
- **T9**: very upset, but it's a shipping delay. The vague one tends to escalate it because of the anger.
- **T8**: a notice with no request for action.
- **T7**: $12,500, more than $10,000. The vague one sometimes doesn't escalate it.

### What gets sent to Claude
- `system`: `SISTEMA_VAGO_41` or `SISTEMA_EXPLICITO_41`.
- `tools`: `TOOL_CLASIFICAR_41`, which returns a list of decisions with `id`, `escalar` and `motivo` (escalate, reason).

### Where it is in the code
`TICKETS_41` (tickets + correct answer), the two system prompts and `demo_4_1()`.

### Experiments
- Remove from `SISTEMA_EXPLICITO_41` the line *"El enojo por sí solo NO es criterio"* (anger by itself is NOT a criterion) and look at T9.
- Add borderline tickets to `TICKETS_41`, for example a refund of exactly $10,000.

### What the exam asks
- "Be conservative" or "high confidence only" don't improve precision: what improves it is concrete criteria.
- If a category produces many false positives, disable it temporarily while you improve its prompt, to win back
  trust in the others.
- Define severity with code examples or concrete cases per level.

## Demo 4.2 · Few-shot for ambiguous cases

### What it is about
**Few-shot** = putting 2 to 4 input → output examples in the prompt. It's the most effective technique when
instructions alone give inconsistent results. Good examples:
- cover the **ambiguous cases**, not just the easy ones;
- explain **why** it was decided that way, so the model generalizes the criterion and doesn't just copy the format.

### What happens when you run it, step by step
1. There are 6 customer messages in `MENSAJES_42`, each with its correct answer. The hard ones are:
   - *"Same as I ordered last time"*: there's no identifiable product;
   - *"A tablecloth, not the red one, the other one"*: it says which color it does NOT want;
   - *"a few green mugs"*: there's no exact quantity.
2. Round **without examples**: just the instruction. For each message, ✔ or ✘ with which field failed.
3. Round **with examples**: the 4 examples in `EJEMPLOS_42` are added to the system prompt (they're printed on screen).
4. The table compares the two rounds message by message.

What to expect: the easy cases come out right in both. On the ambiguous ones, without examples the model tends to **invent** a
quantity (*"a few"* → 3) or not ask for clarification.

### What gets sent to Claude
- `TOOL_PEDIDO_42` with nullable fields (`"type": ["integer", "null"]`), forced with `tool_choice`.
- The examples go in the `system`, each one with its `(por qué: …)` (why: …).

### Where it is in the code
`MENSAJES_42`, `EJEMPLOS_42`, `_coincide_42()` (compares quantity, color and clarification) and `demo_4_2()`.

### Experiments
- Remove the `(por qué: …)` from the examples and compare.
- Change an example so it contradicts the instruction: the model tends to follow the example. Examples carry a lot of weight.

### What the exam asks
- Inconsistent output with detailed instructions → add few-shot examples of the ambiguous cases.
- If the model **invents** a piece of data because the schema forces it (a required field the document doesn't have), the fix
  is a **nullable** field (demo 4.3), not few-shot.
- If it invents or omits data because the documents come in different formats (informal measurements, a table vs. running
  text), that's where **few-shot** helps: one example per structure.
- Examples with the document's varied formats help extract correctly from documents with different structures.

## Demo 4.3 · Structured output with tool use

### What it is about
Asking for *"answer only in JSON"* works **almost** always, and in a pipeline "almost" is a problem: sometimes it arrives with
```` ```json ````, with a sentence before it or with different keys. The reliable alternative is **tool_use**: you define the
output as a tool's `input_schema` and force its use with `tool_choice`. The JSON is always parseable and follows
the schema.

Schema design:
- Fields that may be missing → **nullable** (`["string", "null"]`), so it doesn't invent.
- Categories → an `enum` with an **"otro"** (other) option + a detail field.
- The schema guarantees the **syntax**, not the **semantics**: a total may not add up (demo 4.4).

### What happens when you run it, step by step
1. The `SCHEMA_43` schema is printed.
2. **Text** mode: the 5 emails are requested as JSON through the prompt and `json.loads()` is attempted. If it fails, you see what arrived.
3. **Tool** mode: the same emails with `extraer_correo` forced.
4. For each email it validates that the keys are there and that `tipo` is a valid value.
5. Table: **JSON parseable** and **Cumple el schema** (matches the schema) per mode.

What to expect: with the tool, 5/5 and 5/5. In text there are usually parse failures (because of the ```` ```json ````) or keys
added or missing. Look at the email *"something nice for a gift"*: with nullable and `"otro"`, the output is honest.

### Where it is in the code
`SCHEMA_43`, `TOOL_EXTRAER_43`, `_valida_esquema_43()` and `demo_4_3()`.

### Experiments
- Remove `"otro"` from the `tipo` enum and see how it classifies the gift email.
- Remove `"null"` from `fecha_requerida`: it may start inventing dates.

### What the exam asks
- Reliable structured output → tool_use with a JSON schema (eliminates syntax errors).
- `tool_choice: any` guarantees it calls some tool; forcing a tool guarantees which one.
- Optional fields as nullable to avoid fabricated data; `enum` + `"other"` + detail for open categories.

## Demo 4.4 · Validation, retry and feedback

### What it is about
The schema ensures the shape; **business rules** are validated in code. When one fails, you retry by
sending the model the **specific error**: which field, which value and what was expected.

Two key exam ideas:
- Retrying works for **format or structure** errors. It does **not** work when the data **doesn't exist** in the
  document: the model would end up inventing it.
- The *stated vs calculated total* pattern: extract both and flag the discrepancy, instead of silently "fixing" it.

### What happens when you run it, step by step
Three documents:
- **`ok`**: consistent, but the SKUs come in lowercase (`tbl red 01`). The rule requires `AAA-AAA-00`.
- **`total_no_cuadra`**: the document says $4,800 and the line items add up to $4,500. The error is **in the source**.
- **`sin_fecha`**: it doesn't mention a delivery date.

For each one:
1. It's extracted with `registrar_pedido` forced and the attempt's JSON is printed.
2. `validar_44()` checks:
   - the SKU format;
   - that `total_calculado` is the real sum;
   - that a discrepancy is flagged;
   - that the date appears in the document.
3. If there are errors, the **feedback** (magenta panel) is sent as a `tool_result` with `is_error` and it retries,
   up to `D44_MAX_REINTENTOS`.

What to expect with `"especifico"`: in `ok`, the first attempt fails on the SKU and the second fixes it. In
`total_no_cuadra`, the right thing is `hay_discrepancia: true` with the stated total intact. In `sin_fecha`,
`fecha_entrega: null`.

### Where it is in the code
`DOCUMENTOS_44`, `TOOL_PEDIDO_44`, `validar_44()` (the rules) and the `for intento` loop in `demo_4_4()`, where the
feedback is built.

### Experiments
- `D44_FEEDBACK = "generico"`: with *"try again"* the model doesn't know what to change and tends to repeat the error.
- `D44_FEEDBACK = "sin_reintento"`: you accept the first result, errors included.
- Add your own rule to `validar_44()`; for example, that the quantity is positive.

### What the exam asks
- Retry with the document, the failed extraction and the specific validation error.
- Retrying doesn't help if the information isn't in the source.
- A `detected_pattern` or confidence field to analyze later why findings get dismissed.
- `calculated_total` next to `stated_total` to detect discrepancies.

## Demo 4.5 · Message Batches API

### What it is about
The **Message Batches API** processes many requests asynchronously:

| | Batches API | Synchronous API |
|---|---|---|
| Cost | ~50% less | Normal |
| Time | Up to 24 h, no guarantee | Seconds |
| Tools | One turn per request (no tool loop) | Full loop |
| For | Nightly reports, audits | What someone is waiting for |

### What happens when you run it, step by step
1. 8 requests are built (classify reviews), each with its `custom_id` (`resena-001`…). A sample one is printed.
2. The batch is created with `client.messages.batches.create(requests=...)`. The id is saved in `ultimo_lote.txt`.
3. Every `D45_CADA_S` seconds the status is checked: `in_progress` → `ended`, with counters for processing, ok,
   errored and expired.
4. When it finishes, the results are read with `batches.results()`. They can arrive **in another order**: they're matched by `custom_id`.
5. If one failed, it says that **only that one** gets resent, in a new batch.
6. Table: batch or synchronous?, and the SLA math.

Careful: a small batch usually finishes in minutes, but **there's no guarantee**. If `D45_ESPERA_MAXIMA_S` passes, the demo
stops and tells you how to recover it later with `D45_LOTE_EXISTENTE`.

### Where it is in the code
`RESENAS_45` and `demo_4_5()`: `batches.create`, the `while` loop with `batches.retrieve` and the `for` loop with `batches.results`.

### Experiments
- Close the demo halfway and then recover the batch by pasting its id in `D45_LOTE_EXISTENTE`.
- Add 50 more reviews: the cost drops by half compared to sending them one by one.
- `D45_EMPAREJAR = "orden"`: it matches by position; see which reviews end up with another review's classification.
- `D45_USO = "pre_merge"`: the demo explains why the batch isn't sent (and spends nothing).
- `D45_SLA_HORAS = 30`: with batches of up to 24 h, a document can wait at most 6 h before entering a batch
  → send batches at least every 6 h (with margin, every 4 h). Try 24: Batch can no longer guarantee the SLA.

### What the exam asks
- Blocking (review before a merge) → synchronous. Can wait (nightly report) → batch.
- `custom_id` to match results and resend only the ones that failed.
- Test the prompt on a sample before sending a large batch, so you don't repeat thousands of requests.
- SLA math: with up to 24 h of processing, you have to send far enough in advance.

## Demo 4.6 · Independent-instance review

### What it is about
A model that reviews its own work **in the same conversation** carries over the reasoning it wrote it with:
it tends to confirm instead of question. An **independent instance**, without the generation history, finds
more problems. Also, each finding can carry a **confidence**, and the low-confidence ones go to human review.

### What happens when you run it, step by step
1. The policy (maximum $10,000; 5 to 7 business days; correct order number) and a
   **draft with 3 planted problems** are printed:
   - it approves $12,500 without authorization;
   - it promises 24 hours;
   - it cites order #12364 instead of #12346.
2. **`misma_sesion`**: the history includes the original request and the draft as if Claude had written it.
   Then: *"Review your answer"*.
3. **`independiente`**: a new call with a reviewer system prompt; it sees policy + case + draft and nothing else.
4. Both answer with `reportar_hallazgos` (problem, severity, confidence). Each finding is printed with its
   destination: **automatic** or **human review** (according to `D46_UMBRAL_CONFIANZA`).
5. Table: which of the 3 problems each mode found.

To be honest: the result varies between runs, and sometimes both find everything. The detection is by key
words, so read the findings to confirm it.

### Where it is in the code
`POLITICA_46`, `CASO_46`, `BORRADOR_46`, `PROBLEMAS_46` (key words per problem), `TOOL_HALLAZGOS_46` and `demo_4_6()`.

### Experiments
- Make the errors subtler in `BORRADOR_46` (for example, "in 3 days" instead of "in 24 hours").
- Raise `D46_UMBRAL_CONFIANZA` to 0.9: more findings go to human review.
- `D46_ERRORES = "obvios"` or `"sutiles"` (default): with subtle errors the difference shows more.

### What the exam asks
- Self-review in the same session is less effective: use an independent instance.
- Large reviews: per-file passes + an integration pass (demo 1.6).
- Confidence per finding to decide what a person reviews; calibrate the threshold with labeled data (demo 5.5).

# Domain 5 · Context Management & Reliability

## Demo 5.1 · Context window: case facts and trimming

### What it is about
What gets lost as the context grows and how to avoid it:
- **Progressive summary**: to save space, the history gets summarized, and the summary loses what's exact (amounts, dates,
  order numbers, what the customer already declined).
- **Case facts**: a separate block with the transactional data that's copied **in full** in every turn and never summarized.
- **Bloated tool results**: a tool that returns 30 fields when only 5 matter takes up context in every turn.
- **Lost in the middle**: the model pays less attention to what's in the middle of a long context. Put what matters at the
  start or the end, with headers.

### What happens when you run it, step by step
**Part A · summary vs case facts**
1. A 13-message conversation with 5 key facts is printed: order #12346, $12,500, declined the credit,
   prefers WhatsApp and promised date Friday November 20.
2. **`resumen`**: one call summarizes the conversation in 2 lines. Another agent picks up the case **with only that summary**
   and must state the 5 facts.
3. **`case_facts`**: the agent that picks up receives the `CASE FACTS` block + a short summary.
4. Table: which facts each mode kept.

**Part B · trim tool results**
- `count_tokens` (free) counts how many tokens the full order takes (30 fields) versus only the 5
  fields that matter for a refund.

What to expect: the summary usually loses 2 or 3 facts (the date, the channel, the declined credit). With case facts, 5/5.

### Where it is in the code
`CONVERSACION_51`, `HECHOS_51` (key words to check), `CASE_FACTS_51`, `PEDIDO_COMPLETO_51`,
`CAMPOS_REEMBOLSO_51`, `demo_5_1_parte_a()` and `demo_5_1_parte_b()`.

### Experiments
- Run part A several times: the summary loses different facts each time.
- Change the summary's system prompt to "Summarize in 1 line": it loses more.
- `D51_PARTE = "C"` with `D51_POSICION_DATO = "medio"` or `"arriba"`: lost in the middle with a long case file.

### What the exam asks
- Progressive summaries lose numeric values, dates and customer expectations → a persistent "case facts" block.
- Trim tool results to the relevant fields before they accumulate.
- What's key at the start, with clear headers, because of the *lost in the middle* effect.
- Subagents return structured metadata (dates, sources) and not just prose.

## Demo 5.2 · Escalation and ambiguity

### What it is about
**When to escalate to a person.** There are three correct triggers:
1. The customer explicitly **asks** for a person → escalate immediately, without trying to solve it first.
2. The **policy doesn't cover** the case (here: matching another store's prices).
3. **You can't make progress** after trying.

Bad triggers, which the exam offers as distractors:
- **sentiment** by itself (an upset customer with a simple problem gets helped, not escalated);
- the **confidence** the model claims to have about itself.

**Ambiguity:** if the search returns **several** possible customers, ask for one more piece of data; never pick with a heuristic.

### What happens when you run it, step by step
Five scenarios, each with its correct action:

| Scenario | Message | Correct |
|---|---|---|
| `pide_humano` | "I want to talk to a person…" | escalated |
| `molesto_simple` | "I'm FURIOUS!! #12347 has been in transit for 2 days" | resolved (with `lookup_order`) |
| `cliente_ambiguo` | "I'm Juan Pérez, I want my refund" | asked for clarification (there are 2 Juan Pérez) |
| `fuera_de_politica` | "Match Amazon's price" | escalated |
| `insiste` | The agent already offered to solve it and the customer answers "I want a person to help me" | escalated |

They all run with the **vague** system prompt and then with the **criteria** one (`D52_MODO = "ambos"`). With
`"criterios_ejemplos"` examples of when to escalate and when to resolve are added; `"todos"` runs all three. You'll see each tool called, the final
answer and the detected action. The final table compares it against the correct one.

### Where it is in the code
`ESCENARIOS_52`, `SISTEMA_VAGO_52`, `SISTEMA_CRITERIOS_52`, `TOOLS_52`, `_ejecutar_52()` (simulates the tools;
`get_customer` with "juan" returns 2 matches) and `_correr_52()`.

The action is detected like this: if it called `escalar_a_humano` → escalated; if the final answer has a "?" → asked for clarification;
otherwise → resolved. It's a heuristic, so read the answers.

### Experiments
- Remove from the criteria prompt the line *"NO escales solo porque el cliente esté molesto"* (DON'T escalate just because the customer is upset).
- Add a scenario: a customer who asks for a person but whose problem is trivial. The right thing is still to escalate.
- `D52_MODO = "todos"`: compare vague, criteria, and criteria + examples (the typical exam answer).

### What the exam asks
- Asks for a person → escalate immediately.
- Policy that's ambiguous or silent about the case → escalate.
- Several matches → ask for additional identifiers.
- Sentiment and self-assessed confidence aren't good indicators of complexity.

## Demo 5.3 · Multi-agent error propagation

### What it is about
What happens when **a subagent fails** in a multi-agent system. The coordinator needs context to decide:
**failure type, what was tried, partial results and alternatives.**

The anti-patterns:
1. **Suppressing the error**: returning "no relevant data" as a success. The report looks complete, but it isn't.
2. **Generic error**: "Error", with nothing to decide on.
3. **Killing the whole flow** because of a single failure.

The synthesis must **note the gaps**: "shipping section: incomplete due to a source failure".

### What happens when you run it, step by step
1. The coordinator calls the `delegar` tool 3 times: `inventario`, `envios` and `resenas` (inventory, shipping, reviews).
2. `inventario` and `resenas` answer fine. `envios` **fails**, and how it reports it depends on the format:
   - **`silencioso`**: `"Sin datos relevantes para esta área."` (no relevant data for this area) with `is_error: false`;
   - **`generico`**: `"Error"` with `is_error: true`;
   - **`estructurado`**: JSON with `tipo_falla: timeout`, `consulta_intentada`, `resultados_parciales` (3 of 12
     states: 4.1 days) and `alternativas`.
3. The coordinator writes the final report (green panel).
4. With `D53_COMPARAR_TODOS = True` the 3 formats run. Table: does it flag the gap? does it use the partial result?

What to expect: in `silencioso`, the report usually omits shipping or treats it as "nothing new". In `estructurado`,
it mentions the failure, uses the 4.1 as partial data and suggests the alternative.

### Where it is in the code
`RESULTADOS_OK_53`, `FALLAS_53` (the 3 formats), `TOOL_DELEGAR_53` and `_correr_53()`, which routes each area to its result.

### Experiments
- `D53_COMPARAR_TODOS = False` and pick a `D53_FORMATO` to see it alone.
- Make two areas fail instead of one: is the report still useful?
- `D53_FORMATO = "abortar"` (with `D53_COMPARAR_TODOS = False`): a single failure stops everything and there's no report.

### What the exam asks
- Structured error context (type, query, partials, alternatives) so the coordinator can decide.
- Distinguish an access failure from a valid empty result (like demo 2.2).
- Subagents recover locally from what's transient and only propagate what they couldn't resolve.
- Reports with coverage annotations: what's well supported and what has gaps.

## Demo 5.4 · Code exploration and scratchpad (Agent SDK)

### What it is about
In long exploration sessions, the context fills up and the agent starts giving generic answers or
answers inconsistent with what it had already found: **context degradation**. Patterns to avoid it:
- **Scratchpad**: a file where the agent writes down the key findings and reads later.
- **Subagents** for exploring, which return only a summary.
- **`/compact`** to summarize the history in a long session.
- **New session + summary** instead of dragging everything along.

### What happens when you run it, step by step
A test repo with 24 files (almost all filler). What matters is in `src/envios/tarifas.ts`,
`src/envios/promociones.ts`, `src/checkout/total.ts` and `config/zonas.json`.

1. **Phase 1 · explore**: *"Where is the shipping cost calculated and what affects it?"*. With `D54_USAR_SCRATCHPAD = True`,
   it must also write its findings in `NOTAS.md`. When it finishes, `NOTAS.md` is printed.
2. **Phase 2 · NEW session** (no `resume`): *"We want free shipping on purchases over $10,000. Which files
   would you touch?"*. With `D54_COMPARAR = True` it runs twice: **with notes** (starts by reading `NOTAS.md`) and **without notes**
   (starts from zero).
3. Table: turns, tool calls and cost of each phase.

What to expect: "with notes" usually needs fewer turns and calls. In a 24-file repo the difference is small;
in a real one, with hundreds, it's large.

### Security
Tools: `Read`, `Grep` and `Glob`, plus `Write` only in phase 1. A `PreToolUse` hook **blocks** any `Write` that
isn't `NOTAS.md`. Everything happens in a temporary folder.

### Where it is in the code
`_repo_54()`, `_correr_fase_54()` (the hook and the options) and `demo_5_4()`.

### Experiments
- `D54_USAR_SCRATCHPAD = False`: there are no notes and phase 2 always starts from zero.
- Read `NOTAS.md`: did it note `promociones.ts` (where the threshold `TODO` is)? If not, phase 2 with notes may fail.
  A scratchpad is only worth what's in it.

### What the exam asks
- Context degradation in long sessions → scratchpad, exploration subagents and `/compact`.
- Subagents to research specific questions while the main agent keeps the coordination.
- When resuming, summarize the key findings instead of dragging along the whole history.

## Demo 5.5 · Human review and confidence calibration

### What it is about
Before removing human review, you need to know **where** the model fails:
- A **97% overall** can hide a category that fails much more.
- Measure accuracy **by document type** (and by field).
- **Stratified sampling**: review a sample of each type, not just of the total.
- **Per-field confidence, calibrated** with labeled data. The threshold is decided with evidence, not "by eye".

### What happens when you run it, step by step
1. There are 44 documents of 3 types, like in real life: many easy ones and few hard ones.
   - **factura** (invoice, 24): the total appears clearly;
   - **ticket** (receipt, 12): subtotal + VAT + total;
   - **nota** (note, 8): handwritten and messy (*"3 mugs at 450 and a tablecloth for 890, I already paid 500"*), where you have to
     calculate or interpret. In 3 notes the total **can't be known** (*"or was it 85?"*, *"the usual"*, a smudged number):
     the right answer is `null`, not a guess.
2. For each one, Claude extracts the **total to charge today** and its **confidence** (`registrar_total` forced).
3. Table document by document: correct, extracted, confidence, destination (automatic or human according to `D55_UMBRAL`) and ✔/✘.
4. Table by type: accuracy, how many were accepted automatically and **how many errors slipped through**.
5. Sampling table: if a person reviews only `D55_MUESTRA` documents (6), how likely are they to see a note error? At
   random from the total almost no notes come up; stratified (2 of each type) they do.
6. Calibration table: for each declared confidence range, the real accuracy.

What to expect: invoices and receipts at 100%; notes around 60%. The overall number comes out above 90% and hides that
problem: with the overall-number rule the note errors slip through. Notice whether there are errors with high confidence: that
means the confidence **isn't calibrated**.

### Where it is in the code
`_documentos_55()` (the 44 documents with their correct total; `None` = can't be known), `TOOL_TOTAL_55` and `demo_5_5()`,
which builds the tables (documents, by type, sampling and calibration).

### Experiments
- `D55_UMBRAL = 0.95`: more documents go to human review and fewer errors slip through.
- Add more hard notes and see how that category's accuracy changes.
- `D55_FACTURAS = 6`: with fewer invoices the overall number drops and no longer "fools" you as much: the volume of easy documents is what hides the failure.
- `D55_DECISION = "global"`, `"umbral"` or `"por_tipo"` (default): compare how many errors would slip through with each rule.

### What the exam asks
- Aggregate accuracy can hide failures by document type or by field: validate by segment before
  automating.
- Stratified sampling of high-confidence cases to detect new errors.
- Per-field confidence calibrated with a labeled set to decide what goes to human review.

## Demo 5.6 · Provenance and multi-source synthesis

### What it is about
When synthesizing several sources it's easy to lose **where each fact comes from**. *"The average is 3 days"*: according to
whom, from when and with what sample? The pattern is that each claim keeps its **source, date and scope**. If two
reliable sources **disagree**, you don't silently pick one: you report the conflict with both values and their context.

### What happens when you run it, step by step
1. 4 sources on delivery time are printed:
   - **SRC-A**: internal study from October 2026, 1,200 orders → 3.2 days;
   - **SRC-B**: February 2025 survey, 80 responses → 6 days;
   - **SRC-C**: carrier, September 2026, **central zone only** → 2.8 days;
   - **SRC-D**: undated blog → under 2 days.
2. **`libre`**: a 2-line prose answer for the FAQ page (the typical step where sources get lost).
3. **`con_procedencia`**: `reportar_sintesis` forced, with claims (source, date, scope), conflicts
   (topic, values, possible explanation) and a conclusion.
4. Table: sources cited, does it point out the conflict?, does it notice SRC-B is from 2025?, does it notice SRC-C is central zone only?

What to expect: in `libre`, a single number ("about 3 days") without saying where it comes from. With provenance, the reader sees
why the values differ: different dates, samples and zones.

### Where it is in the code
`FUENTES_56`, `TOOL_SINTESIS_56` and `demo_5_6()`. The checks are by key words.

### Experiments
- Add a fifth source that contradicts SRC-A with a recent date.
- Remove *"no elijas una en silencio"* (don't silently pick one) from the system prompt and compare.

### What the exam asks
- Keep the claim → source mapping throughout the synthesis.
- Conflicts between reliable sources: annotate them with their attribution, don't resolve them arbitrarily.
- Include publication or collection dates so changes over time don't look like contradictions.
- Distinguish well-supported findings from those with gaps or in dispute.

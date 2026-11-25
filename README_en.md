# CCAR-F · Practice labs (Domains 1 to 5)

These labs are **practice**: you watch on your screen what you're studying for the exam. The full theory is on your
study platform; here you test it.

Everything uses a made-up store, **La Tiendita**, with fake data. There's one lab per domain and one demo per topic
(1.1, 1.2, …, 5.6). Each demo has a case that **works** ✅ and cases that **fail on purpose** ❌, so you can see
the difference.

**About the language:** the panel can be switched to English with the **EN** button (top right): the interface, the
Study tab, the cases, the receipt, the demo guides, the review pages, the examples, the recordings and what the labs
print while running come out in English. The labs' code and La Tiendita's data (the prompts, messages and documents
that Claude receives) stay in Spanish, so you always see exactly what Claude saw. The exam terms (stop_reason,
tool_choice, subagent…) are in English everywhere. The full guide for every demo in English is in **`GUIA_LABS_en.md`**.
In the terminal, run a lab in English with `CCARF_IDIOMA=en python lab_dominio1.py 1.1` (Mac/Linux).

## Start without installing anything

Open **`EMPIEZA_AQUI_en.html`** with a double click. There you have, without Python and without spending anything:

- **Recordings:** saved runs, as if you ran them yourself. Start here.
- **Examples:** what each demo shows, with drawings.
- **The 6 exam scenarios** and which demos practice each one.
- **Review sheet:** short situations like on the exam, with their answer.
- **Anti-patterns:** answers that sound right but are wrong.
- **Glossary:** the exam's words.
- **Study guides and slides** as PDF (also in the `material/` folder). The study guides are in Spanish; the slides
  come in Spanish and English.

## To run the demos yourself

### Step 1 · Install (only once)

You need Python 3.10 or newer ([python.org/downloads](https://www.python.org/downloads/)).

**Open a terminal in this folder** (the terminal is a window where you type commands):

- **Mac:** in the Finder, right-click the labs folder → **New Terminal at Folder**. If it doesn't appear,
  open the **Terminal** app, type `cd ` (with a space) and drag the folder into the window; then Enter.
- **Windows:** open the folder, click the address bar, type `powershell` and press Enter.

Copy these commands one by one. The first one creates an **environment** (`.venv`): a folder where the labs'
libraries get installed without touching the rest of your computer. "Activating" it tells the terminal to use it.

**Mac or Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```bash
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

You know the environment is active because the terminal line starts with `(.venv)`. Every time you open a new
terminal, activate it again (the `activate` line). Once active, `python` works the same on Mac and on Windows.

### Step 2 · Get your API key

The API key is the password that lets the labs talk to Claude. Each call costs a little bit.

1. Go to [platform.claude.com → Settings → API keys](https://platform.claude.com/settings/keys). If you don't have an account, create one.
2. **Buy credit and set a low spending limit.** The API is prepaid with a card: you buy credit
   (the console shows the minimum) and each call uses it up. It isn't a subscription. Set a low limit
   (for example 5 USD a month) in the limits or billing section. Running all the demos once costs a few cents.
3. Click **Create key**. Give it a name, for example `labs-ccarf`.
4. **Copy it right then:** it's only shown once.
5. Create the `.env` file (with a dot at the start) by copying `.env.example`. The easiest way is with the terminal, in this folder:
   `cp .env.example .env` (Mac or Linux) or `copy .env.example .env` (Windows).
   Then open it with a text editor and replace `pega-aqui-tu-key` with your key, after `ANTHROPIC_API_KEY=`.
   - Files that start with a dot are **hidden**. To see them: on Mac, `Cmd + Shift + .` in the Finder; on
     Windows, in File Explorer → **View → Show → Hidden items**.
   - Careful with TextEdit and Notepad: they may save it as `.env.txt` and then the labs can't find it. In
     TextEdit use **Format → Make Plain Text**; in Notepad choose **Save as type: All files**.
   - Optional (Mac or Linux): `chmod 600 .env` so only your user can read it.
6. When you finish studying, delete the key on the same page.

🔒 **Protect your key:** never paste it in a chat, in code or in a screenshot. The `.env` file is
yours only: don't share it.

### Step 3 · Open the panel

```bash
python panel.py
```

It opens in your browser. Press **EN** at the top right to switch to English. Also at the top right, if it says
**Key ready** (with a green dot), it found your key. If it says **API key missing** or **Key rejected** (in red),
click it and it tells you what to do.

## How to study a topic in the panel

Pick the **domain** and the **demo** (each demo is an exam topic). Then follow the **Study path**, which
has 5 steps and checks itself off:

1. **Read the idea** in the Study tab.
2. **Run the ✅ case**, the one that works.
3. **Run a ❌ case**, the one that fails on purpose.
4. **Compare** the two runs.
5. **Read why it happened** on the **receipt** that comes out at the end: what was expected, what happened, why and what the
   exam asks.

Notice the label on each ❌ case:

- 🎓 **Exam trap:** sounds right, but on the exam it's the wrong answer.
- 🔧 **Product limitation:** it fails today because of how the product works, but on the exam it isn't wrong.

First time? The **?** button at the top gives you a tour of the panel.

### What else is in the panel

| Button or area | What it's for |
| --- | --- |
| Cases | One click and the demo is ready with a typical case. **▶ recorded** plays it without spending anything. |
| Receipt | Comes out at the end of each run: what was expected, what happened, why, what the exam asks and how much it cost. |
| Exam scenario | Which exam scenario this topic appears in. |
| 🔀 Exam vs product | A notice when today's product no longer works the way the exam says. For the exam, answer as the guide says. |
| Demo guide | What the demo does, what to expect and what the exam asks. |
| Demo variables | Change something and run again. The lab file doesn't change. **↺ Lab values** resets everything. |
| Compare runs | Two runs side by side: what changed and how each one ended. |
| Cost | How much it will cost before running (below the model) and how much it cost (on the receipt). |
| Underlined terms | Hover over them (or focus them with the keyboard) to see what they mean. |
| Guides | The domain's study guide and slides, inside the panel and opened at the demo's topic. |
| Resources | Review, glossary, anti-patterns, scenarios, study guides, slides and each lab's code. |
| Search (Ctrl+K) | Searches any word in the guides and the demos. |
| A− / A+ · ☀/☾ · ES/EN | Font size, light or dark theme (by default, your system's) and language. |

Each run is saved as a page in `salidas_html/`. You can go back and see it whenever you want.

## The 6 exam scenarios

According to prep sites, the exam's questions are based on 6 scenarios and each exam picks 4 at
random. The names don't come from the official guide; which demos go with each scenario is our own choice.

| Scenario | Demos to practice it |
| --- | --- |
| 1. Customer Support Resolution Agent | 1.1, 1.4, 1.5, 2.1, 2.2, 5.1, 5.2 |
| 2. Code Generation with Claude Code | 3.1, 3.2, 3.3, 3.4, 3.5, 2.5 |
| 3. Multi-Agent Research System | 1.2, 1.3, 1.6, 2.2, 2.3, 5.3, 5.6 |
| 4. Developer Productivity with Claude | 1.7, 2.4, 2.5, 3.1, 5.4 |
| 5. Claude Code for CI/CD | 3.6, 4.1, 4.6, 1.6, 4.5 |
| 6. Structured Data Extraction | 4.2, 4.3, 4.4, 4.5, 5.5, 2.3 |

## What each demo practices

| Demo | What you see | What to try |
| --- | --- | --- |
| 1.1 | The agent's loop: it continues until `stop_reason` says it's done | Stop when text appears · `max_tokens` too low |
| 1.2 | A coordinator splits the work among subagents | Split it badly: a topic is missing from the report |
| 1.3 | Passing context to subagents and launching them in parallel | Findings without sources · subagents in sequence · no Agent/Task in allowed_tools (part C) |
| 1.4 | A rule enforced in code, not just in the prompt | Leave the rule only in the prompt |
| 1.5 | Hooks that block or fix what goes into and out of a tool | Turn off a hook |
| 1.6 | Splitting a review into steps | Review everything at once |
| 1.7 | Resume, fork or start a new session | Resume when the files already changed |
| 2.1 | Claude picks the tool by its description | Minimal descriptions |
| 2.2 | Errors that say what failed and what to do | The generic error “Operation failed” |
| 2.3 | 4 tools vs 18, and `tool_choice` (also with a real document) | Sonnet with `any`: 400 error |
| 2.4 | Your own MCP server | Token written in `.mcp.json` · server only in `~/.claude.json` |
| 2.5 | Grep, Glob, Read and Edit | Remove Grep or Glob · Edit without unique text → Read + Write |
| 3.1 | Where each instruction goes: CLAUDE.md and its levels | A new teammate who doesn't get the rules |
| 3.2 | Slash command vs skill | A skill with a vague description |
| 3.3 | Rules that load only with certain files | Rules without `paths` |
| 3.4 | Plan mode vs going direct | When each one is worth it |
| 3.5 | Improving the result with examples and tests | Asking for it in prose only |
| 3.6 | Claude Code in CI: `-p` and JSON output | Text output |
| 4.1 | Clear criteria vs “be conservative” | The vague prompt |
| 4.2 | Few-shot examples | No examples |
| 4.3 | Guaranteed JSON with a tool and a schema | Asking for JSON in the prompt |
| 4.4 | Validate and retry with the exact error | Generic error · no retry |
| 4.5 | Message Batches: many cheap requests, no rush | Match by order · use Batch before a merge · SLA math |
| 4.6 | Independent review | Review in the same session |
| 5.1 | Don't lose the key data when summarizing | Summarize everything |
| 5.2 | When to hand the case to a person | Vague instruction (and compare with criteria + examples) |
| 5.3 | What to return when a subagent fails | Fail silently |
| 5.4 | Notes so you don't forget during a long exploration | No notes |
| 5.5 | Confidence and human review | A threshold that's too low |
| 5.6 | Where each fact comes from | Summary without sources |

The full explanation of each demo is in **`GUIA_LABS_en.md`** and in the panel (**Demo guide**).

## If you prefer the terminal

```bash
python lab_dominio1.py          # shows the menu
python lab_dominio1.py 1.5      # runs demo 1.5
python lab_dominio1.py guia 1.5 # reads the demo's guide without running anything
```

By default the output is short: one line per step. To see everything, open the lab and change `DETALLE = "completo"`.
Each demo has a **🔧 CAMBIA AQUÍ** (change here) block at the top: change a variable, save and run again.
The terminal output is in Spanish unless you set `CCARF_IDIOMA=en` (on Windows PowerShell: `$env:CCARF_IDIOMA="en"`).

## What the demos do on your computer

- The Domain 3 demos and 2.5 create test projects in temporary folders and only work there. They never
  read your `~/.claude`.
- 3.5 runs the code Claude writes to run the tests: in a separate process, with a 10-second
  limit. To just look at it, set `D35_EJECUTAR_CODIGO = False`.
- 2.4 saves `servidor_inventario_mcp.py` in this folder so you can open and change it. Delete it to go back
  to the original.
- 4.5 saves the last batch's id in `ultimo_lote.txt`.
- The panel only works on your computer (127.0.0.1). It never shows your key.

## How much it costs

With the default model (`claude-haiku-5-5`), running all the demos costs a few cents. The panel tells
you the cost of each run. Recordings cost nothing. If you switch to Sonnet or Opus, it costs between 20 and
40 times more.

## If something fails

| What you see | What to do |
| --- | --- |
| `command not found: python` (Mac) | On Mac it's called `python3`. Use it to create the environment; once active, `python` works. |
| “running scripts is disabled” (Windows) | Run `Set-ExecutionPolicy -Scope Process Bypass` and activate the environment again. |
| “API key missing” (in red) | Check that the file is called `.env` (with a dot, no `.txt` at the end) and that it has your key. Close the panel (Ctrl+C) and open it again. |
| An Agent SDK demo is slow or fails to start | The demos marked «Agent SDK» use Claude Code, which comes inside the `claude-agent-sdk` package. Check that `pip install -r requirements.txt` finished without errors. |
| “Key rejected” / 401 error “invalid x-api-key” | The key doesn't work: it was copied wrong, you deleted it or you changed it. Check it on platform.claude.com, paste it again in `.env` and reopen the panel. If you ever set it with `export` in the terminal, remove it (`unset ANTHROPIC_API_KEY` and delete it from `~/.zshrc`). The folder's `.env` always wins over the terminal. |
| “Missing libraries” or `ModuleNotFoundError` | Activate your environment (`activate`) and run `pip install -r requirements.txt`. |
| “Address already in use” (the port is busy) | Open the panel on another port: `python panel.py 8780`. |
| 400 error with Sonnet in 2.3 | That's normal: the demo shows it on purpose. |
| You want to start from scratch | Delete the `salidas_html/` folder. |

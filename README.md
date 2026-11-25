# CCAR-F · Labs de práctica (Dominios 1 a 5)

Estos labs son **práctica**: ves pasar en tu pantalla lo que estudias para el examen. La teoría completa está en tu
plataforma de estudio; aquí la pruebas.

*English: open `README_en.md` and press **EN** in the panel.*

Todo usa una tienda inventada, **La Tiendita**, con datos falsos. Hay un lab por dominio y una demo por tema
(1.1, 1.2, …, 5.6). Cada demo tiene un caso que **funciona** ✅ y casos que **fallan a propósito** ❌, para que veas
la diferencia.

## Empieza sin instalar nada

Abre **`EMPIEZA_AQUI.html`** con doble clic. Ahí tienes, sin Python y sin gastar nada:

- **Grabaciones:** corridas guardadas, como si las corrieras tú. Empieza por aquí.
- **Ejemplos:** qué muestra cada demo, con dibujos.
- **Los 6 escenarios del examen** y qué demos practican cada uno.
- **Hoja de repaso:** situaciones cortas como en el examen, con su respuesta.
- **Antipatrones:** respuestas que suenan bien pero están mal.
- **Glosario:** las palabras del examen, en español y en inglés.
- **Guías de estudio y slides** en PDF (también están en la carpeta `material/`).

## Para correr las demos tú mismo

### Paso 1 · Instala (una sola vez)

Necesitas Python 3.10 o más nuevo ([python.org/downloads](https://www.python.org/downloads/)).

**Abre una terminal en esta carpeta** (la terminal es una ventana donde escribes comandos):

- **Mac:** en el Finder, clic derecho sobre la carpeta de los labs → **Nuevo terminal en la carpeta**. Si no aparece,
  abre la app **Terminal**, escribe `cd ` (con espacio) y arrastra la carpeta a la ventana; luego Enter.
- **Windows:** abre la carpeta, da clic en la barra de dirección, escribe `powershell` y Enter.

Copia estos comandos uno por uno. El primero crea un **entorno** (`.venv`): una carpeta donde se instalan las
librerías de los labs sin tocar el resto de tu computadora. "Activarlo" es decirle a la terminal que lo use.

**Mac o Linux:**

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

Sabes que el entorno está activo porque la línea de la terminal empieza con `(.venv)`. Cada vez que abras una
terminal nueva, vuelve a activarlo (la línea `activate`). Ya activo, `python` funciona igual en Mac y en Windows.

### Paso 2 · Saca tu API key

La API key es la contraseña que deja a los labs hablar con Claude. Cada llamada cuesta un poquito.

1. Entra a [platform.claude.com → Settings → API keys](https://platform.claude.com/settings/keys). Si no tienes cuenta, créala.
2. **Compra crédito y pon un límite de gasto bajo.** La API se paga por adelantado con tarjeta: compras crédito
   (el mínimo lo indica la consola) y cada llamada lo va gastando. No es una suscripción. Pon un límite bajo
   (por ejemplo 5 USD al mes) en la sección de límites o de facturación. Correr todas las demos una vez cuesta centavos.
3. Da clic en **Create key**. Ponle un nombre, por ejemplo `labs-ccarf`.
4. **Cópiala en ese momento:** solo se muestra una vez.
5. Crea el archivo `.env` (con punto al inicio) copiando `.env.example`. Lo más fácil es con la terminal, en esta carpeta:
   `cp .env.example .env` (Mac o Linux) o `copy .env.example .env` (Windows).
   Luego ábrelo con un editor de texto y cambia `pega-aqui-tu-key` por tu key, después de `ANTHROPIC_API_KEY=`.
   - Los archivos que empiezan con punto están **ocultos**. Para verlos: en Mac, `Cmd + Shift + .` en el Finder; en
     Windows, en el Explorador → **Ver → Mostrar → Elementos ocultos**.
   - Ojo con TextEdit y el Bloc de notas: pueden guardarlo como `.env.txt` y entonces los labs no lo encuentran. En
     TextEdit usa **Formato → Convertir a texto normal**; en el Bloc de notas elige **Tipo: Todos los archivos**.
   - Opcional (Mac o Linux): `chmod 600 .env` para que solo tu usuario pueda leerlo.
6. Cuando termines de estudiar, borra la key en la misma página.

🔒 **Cuida tu key:** nunca la pegues en un chat, en el código ni en una captura de pantalla. El archivo `.env` es
solo tuyo: no lo compartas.

### Paso 3 · Abre el panel

```bash
python panel.py
```

Se abre en tu navegador. Arriba a la derecha, si dice **Key lista** (con un punto verde), encontró tu key. Si dice
**Falta la API key** o **Key rechazada** (en rojo), dale clic y te dice qué hacer.

## Cómo estudiar un tema en el panel

Elige el **dominio** y la **demo** (cada demo es un tema del examen). Luego sigue la **Ruta de estudio**, que
tiene 5 pasos y se va marcando sola:

1. **Lee la idea** en la pestaña Estudiar.
2. **Corre el caso ✅**, el que funciona.
3. **Corre un caso ❌**, el que falla a propósito.
4. **Compara** las dos corridas.
5. **Lee por qué pasó** en el **ticket** que sale al terminar: qué se esperaba, qué pasó, por qué y qué pregunta
   el examen.

Fíjate en la etiqueta de cada caso ❌:

- 🎓 **Trampa de examen:** suena bien, pero en el examen es la respuesta incorrecta.
- 🔧 **Limitación del producto:** falla hoy por cómo funciona el producto, pero en el examen no es error.

¿Primera vez? El botón **?** de arriba te da un recorrido por el panel.

### Qué más hay en el panel

| Botón o parte | Para qué sirve |
| --- | --- |
| Casos | Un clic y la demo queda lista con un caso típico. **▶ grabada** la reproduce sin gastar nada. |
| Ticket | Sale al terminar cada corrida: qué se esperaba, qué pasó, por qué, qué pregunta el examen y cuánto costó. |
| Escenario del examen | En qué escenario del examen aparece este tema. |
| 🔀 Examen vs producto | Aviso cuando el producto de hoy ya no es como lo dice el examen. Para el examen, responde como dice la guía. |
| Guía de esta demo | Qué hace la demo, qué esperar y qué pregunta el examen. |
| Variables de la demo | Cambia algo y vuelve a correr. El archivo del lab no cambia. **↺ Valores del lab** regresa todo. |
| Comparar corridas | Dos corridas lado a lado: qué cambió y cómo terminó cada una. |
| Costo | Cuánto costará antes de correr (debajo del modelo) y cuánto costó (en el ticket). |
| Términos subrayados | Pasa el mouse encima (o enfócalos con el teclado) para ver qué significan. |
| Guías | La guía de estudio y los slides del dominio, dentro del panel y abiertos en el tema de la demo. |
| Recursos | Repaso, glosario, antipatrones, escenarios, guías de estudio, slides y el código de cada lab. |
| Buscar (Ctrl+K) | Busca cualquier palabra en las guías y las demos. |
| A− / A+ · ☀/☾ · EN | Tamaño de letra, tema claro u oscuro (por defecto, el de tu sistema) e idioma. |

Cada corrida se guarda como página en `salidas_html/`. Ahí puedes volver a verla cuando quieras.

## Los 6 escenarios del examen

Según los sitios de preparación, las preguntas del examen se basan en 6 escenarios y en cada examen salen 4, al
azar. Los nombres no vienen de la guía oficial; qué demos van con cada escenario lo decidimos nosotros.

| Escenario | Demos para practicarlo |
| --- | --- |
| 1. Agente de soporte al cliente | 1.1, 1.4, 1.5, 2.1, 2.2, 5.1, 5.2 |
| 2. Generar código con Claude Code | 3.1, 3.2, 3.3, 3.4, 3.5, 2.5 |
| 3. Sistema de investigación multiagente | 1.2, 1.3, 1.6, 2.2, 2.3, 5.3, 5.6 |
| 4. Productividad del desarrollador | 1.7, 2.4, 2.5, 3.1, 5.4 |
| 5. Claude Code en CI/CD | 3.6, 4.1, 4.6, 1.6, 4.5 |
| 6. Extracción de datos estructurados | 4.2, 4.3, 4.4, 4.5, 5.5, 2.3 |

## Qué practica cada demo

| Demo | Qué ves | Qué probar |
| --- | --- | --- |
| 1.1 | El loop del agente: sigue hasta que `stop_reason` dice que terminó | Parar al ver texto · `max_tokens` muy bajo |
| 1.2 | Un coordinator reparte el trabajo entre subagentes | Repartir mal: falta un tema en el reporte |
| 1.3 | Pasar contexto a los subagentes y lanzarlos en paralelo | Hallazgos sin fuentes · subagentes en serie · sin Agent/Task en allowed_tools (parte C) |
| 1.4 | Una regla que se cumple en código, no solo en el prompt | Dejar la regla solo en el prompt |
| 1.5 | Hooks que bloquean o arreglan lo que entra y sale de una tool | Apagar un hook |
| 1.6 | Dividir una revisión en pasos | Revisar todo de una sola vez |
| 1.7 | Reanudar, bifurcar o empezar una sesión nueva | Reanudar cuando los archivos ya cambiaron |
| 2.1 | Claude elige la tool por su descripción | Descripciones mínimas |
| 2.2 | Errores que dicen qué falló y qué hacer | El error genérico “Operation failed” |
| 2.3 | 4 tools contra 18, y `tool_choice` (también con un documento real) | Sonnet con `any`: error 400 |
| 2.4 | Tu propio servidor MCP | Token escrito en `.mcp.json` · servidor solo en `~/.claude.json` |
| 2.5 | Grep, Glob, Read y Edit | Quitar Grep o Glob · Edit sin texto único → Read + Write |
| 3.1 | Dónde va cada instrucción: CLAUDE.md y sus niveles | Un compañero nuevo que no recibe las reglas |
| 3.2 | Slash command contra skill | Un skill con descripción vaga |
| 3.3 | Reglas que se cargan solo con ciertos archivos | Reglas sin `paths` |
| 3.4 | Plan mode contra ir directo | Cuándo conviene cada uno |
| 3.5 | Mejorar el resultado con ejemplos y pruebas | Pedirlo solo en prosa |
| 3.6 | Claude Code en CI: `-p` y salida JSON | Salida en texto |
| 4.1 | Criterios claros contra “sé conservador” | El prompt vago |
| 4.2 | Ejemplos few-shot | Sin ejemplos |
| 4.3 | JSON garantizado con una tool y un schema | Pedir el JSON en el prompt |
| 4.4 | Validar y reintentar con el error exacto | Error genérico · sin reintento |
| 4.5 | Message Batches: muchos pedidos baratos, sin prisa | Emparejar por orden · usar Batch antes de un merge · cuenta de SLA |
| 4.6 | Revisión independiente | Revisar en la misma sesión |
| 5.1 | No perder los datos clave al resumir | Resumir todo |
| 5.2 | Cuándo pasar el caso a una persona | Instrucción vaga (y compara con criterios + ejemplos) |
| 5.3 | Qué devolver cuando un subagente falla | Fallar en silencio |
| 5.4 | Notas para no olvidar en una exploración larga | Sin notas |
| 5.5 | Confianza y revisión humana | Un umbral muy bajo |
| 5.6 | De dónde viene cada dato | Resumen sin fuentes |

La explicación completa de cada demo está en **`GUIA_LABS.md`** y en el panel (**Guía de esta demo**).

## Si prefieres la terminal

```bash
python lab_dominio1.py          # muestra el menú
python lab_dominio1.py 1.5      # corre la demo 1.5
python lab_dominio1.py guia 1.5 # lee la guía de la demo sin correr nada
```

De entrada, la salida es corta: una línea por paso. Para ver todo, abre el lab y cambia `DETALLE = "completo"`.
Cada demo tiene arriba un bloque **🔧 CAMBIA AQUÍ**: cambia una variable, guarda y vuelve a correr.

## Qué hacen las demos en tu computadora

- Las demos del dominio 3 y la 2.5 crean proyectos de prueba en carpetas temporales y solo trabajan ahí. Nunca
  leen tu `~/.claude`.
- La 3.5 ejecuta el código que escribe Claude para correr las pruebas: en un proceso aparte, con límite de 10
  segundos. Para solo verlo, pon `D35_EJECUTAR_CODIGO = False`.
- La 2.4 guarda `servidor_inventario_mcp.py` en esta carpeta para que lo abras y lo cambies. Bórralo para volver
  al original.
- La 4.5 guarda el id del último lote en `ultimo_lote.txt`.
- El panel solo funciona en tu computadora (127.0.0.1). Nunca muestra tu key.

## Cuánto cuesta

Con el modelo que viene puesto (`claude-haiku-5-5`), correr todas las demos cuesta centavos de dólar. El panel te
dice el costo de cada corrida. Las grabaciones no gastan nada. Si cambias a Sonnet u Opus, cuesta entre 20 y
40 veces más.

## Si algo falla

| Lo que ves | Qué hacer |
| --- | --- |
| `command not found: python` (Mac) | En Mac se llama `python3`. Úsalo para crear el entorno; ya activo, `python` funciona. |
| “la ejecución de scripts está deshabilitada” (Windows) | Corre `Set-ExecutionPolicy -Scope Process Bypass` y vuelve a activar el entorno. |
| “Falta la API key” (en rojo) | Revisa que el archivo se llame `.env` (con punto, sin `.txt` al final) y que tenga tu key. Cierra el panel (Ctrl+C) y ábrelo otra vez. |
| Una demo con Agent SDK tarda o falla al arrancar | Las demos marcadas «Agent SDK» usan Claude Code, que viene dentro del paquete `claude-agent-sdk`. Revisa que `pip install -r requirements.txt` haya terminado sin errores. |
| “Key rechazada” / error 401 “invalid x-api-key” | La key no sirve: está mal copiada, la borraste o la cambiaste. Revísala en platform.claude.com, pégala de nuevo en `.env` y vuelve a abrir el panel. Si alguna vez la pusiste con `export` en la terminal, quítala (`unset ANTHROPIC_API_KEY` y bórrala de `~/.zshrc`). El `.env` de la carpeta siempre le gana a la terminal. |
| “Faltan librerías” o `ModuleNotFoundError` | Activa tu entorno (`activate`) y corre `pip install -r requirements.txt`. |
| “Address already in use” (el puerto está ocupado) | Abre el panel en otro puerto: `python panel.py 8780`. |
| Error 400 con Sonnet en la 2.3 | Es normal: la demo lo muestra a propósito. |
| Quieres empezar de cero | Borra la carpeta `salidas_html/`. |

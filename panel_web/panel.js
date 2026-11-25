// Lógica del panel (textos ES/EN en T). panel.py la mete en la página al arrancar.
const $ = s => document.querySelector(s);
let PESTANA = 'estudiar', ESPERANDO = null, CASO_CORRIDA = -1, CORRIDA = null, CORRIENDO = false;
let LAB = null, TRABAJO = null, DESDE = 0, AVISO = '';
let REPRODUCIENDO = null, PAGINA_ACTUAL = null, ENTORNO = null, ULTIMO_OK = false, SEGUIR_FALLAS = 0;
const MODELOS = ['claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5'];
function guardado(k){ try { return localStorage.getItem('ccarf_' + k); } catch (e) { return null; } }
function guardar(k, v){ try { localStorage.setItem('ccarf_' + k, v); } catch (e) {} }
const SUAVE = () => matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
/*__JS_TEMA__*/

// ---- Textos de la interfaz en español e inglés (el contenido en inglés lo manda el servidor: idiomas/) ----
const T = {
 es: {
  dominioN: 'Dominio', recEstudiar: 'Para estudiar', recRepaso: 'Hoja de repaso', recRepasoSub: 'Situaciones del examen y qué responder: los cinco dominios, imprimible', recEscenarios: 'Los 6 escenarios (lista no oficial)', recEscenariosSub: 'Qué demos practican cada escenario', recAntipatrones: 'Galería de antipatrones', recAntipatronesSub: 'Lo que suena bien pero está mal, tema por tema', recGlosario: 'Glosario', recGlosarioSub: 'Los términos de las guías, con buscador', recDocs: 'Documentación', recDominios: 'Páginas por dominio', recEjemplos: 'Ejemplos: lo que vas a ver', recEjemplosTodos: 'Todos los ejemplos', recEjemplosSub: 'Diagramas típicos de cada demo, sin correr nada', recSinEjemplos: 'Todavía no hay ejemplos.', recCorridas: 'Tus corridas', recCorridasTodas: 'Todas tus corridas', recCorridasSub: 'Recórrelas con Anterior / Siguiente', recSinCorridas: 'Todavía no has corrido ninguna demo.', recCodigo: 'Código de los labs (solo lectura)', recConfig: 'Archivos de configuración', recMaterial: 'Slides y guías de estudio', recMaterialNota: 'Se abren aquí mismo, en la pestaña Guías. Los que tienen ↗ se abren en otra pestaña.', recSinMaterial: 'Todavía no hay archivos en <code>material/</code>.',
  titulo: '<span class="marca">CCAR-F</span>Panel de labs', notaCab: 'Corre en tu computadora. Los ajustes aplican solo a cada corrida; el archivo del lab no cambia.',
  buscar: 'Buscar', buscarTitulo: 'Busca en guías, README, glosario y demos (Ctrl+K)', letraMenos: 'Letra más chica', letraMas: 'Letra más grande',
  idiomaTitulo: 'Cambiar el idioma de la interfaz', recursos: 'Recursos', recNota: 'Todo se abre en otra pestaña, para no perder lo que tienes en el panel.',
  dominio: 'Dominio', paginaDominio: 'Página del dominio', demo: 'Demo',
  como: 'Cómo correrla', codigo: '&lt;/&gt; Código', ejemplo: 'Ejemplo', corridas: 'Tus corridas', slides: 'Slides', guiaEst: 'Guía de estudio',
  guiaDemo: 'Guía de esta demo (qué hace y qué esperar)',
  casos: 'Casos', casosAyuda: 'Un clic llena las variables con un caso típico. Después dale <b>▶ Correr</b> (usa tu key) o <b>▶ grabada</b> (gratis) y compara.',
  grab: 'Ver sin API key', grabOtras: 'Otras grabaciones', grabada: 'grabada', grabAyuda: 'Reproduce una corrida ya grabada: no gasta tokens ni necesita key.',
  simulada: 'simulada', simuladaLarga: 'grabación simulada: respuestas armadas, no del modelo real',
  modelo: 'Modelo', variables: 'Variables de la demo', variablesAyuda: 'Cambia valores aquí para esta corrida. En verde, lo que ya no es igual al archivo del lab.',
  correr: '▶ Correr', detener: '■ Detener', restaurar: '↺ Valores del lab', restaurarTitulo: 'Regresa todo a lo que dice el archivo del lab',
  tabSalida: 'Salida', tabVista: 'Diagrama', tabVistaTitulo: 'Aparece al correr o al ver una grabación', tabComparar: 'Comparar', compararTitulo: 'Dos corridas de esta demo lado a lado',
  inicio: 'Elige una demo y un caso (o ajusta las variables) y dale ▶ Correr o ▶ grabada.', vacio: 'Aquí aparece la salida mientras corre la demo.',
  estaCorrida: 'Esta corrida', llamada: 'llamada', llamadas: 'llamadas', corridaN: 'corrida', sesion: 'Desde que abriste el panel', corridasN: 'corridas', grabadaNoGasta: 'grabación: no gastó nada',
  guardarGrab: 'Guardar como grabación', guardarGrabAyuda: 'Para que alguien sin key la pueda ver sin gastar.', grabGuardada: '✔ Grabación guardada: aparece junto a su caso (o en “Otras grabaciones”).',
  corriendo: 'Corriendo…', termino: '✔ Terminó en', terminoError: '⚠ Terminó con un error. Revisa la salida.', reproduciendo: 'Reproduciendo grabación…',
  grabacion: 'Grabación', recargado: 'El archivo del lab cambió: se recargaron sus valores. ', ajustesPanel: 'Ajustes del panel: ', sinAjustes: 'Sin ajustes del panel: se usan los valores escritos en el lab.',
  sinConexion: 'No hay conexión con el panel. ¿Sigue abierta la terminal donde corriste python panel.py?',
  keyOk: 'Key lista', keyFalta: 'Falta la API key', keyRechazada: 'Key rechazada',
  ayudaEnvTxt: '<b>⚠ Encontré un archivo <code>__ARCH__</code>, pero los labs buscan <code>.env</code> exacto.</b> Cámbiale el nombre a <code>.env</code> (sin <code>.txt</code>). ',
  ayudaRechazada: '<b>⚠ Anthropic rechazó tu API key.</b> Se encontró en: <b>__FUENTE__</b>, pero no es válida (mal copiada, borrada o cambiada).<ol style="margin:.3rem 0 .3rem 1.2rem;padding:0"><li>En platform.claude.com → Settings → API keys revisa que siga activa, o crea otra.</li><li>Pégala completa en <code>.env</code> después de <code>ANTHROPIC_API_KEY=</code>.</li><li>Si alguna vez la pusiste con <code>export</code> en la terminal, quítala: <code>unset ANTHROPIC_API_KEY</code> y bórrala de <code>~/.zshrc</code> o <code>~/.bashrc</code>.</li><li>Cierra el panel (Ctrl+C) y vuelve a abrirlo.</li></ol>', faltanLibs: 'Faltan librerías', keyOkTitulo: 'Se encontró tu key. Nunca se muestra.',
  ayudaKeyTitulo: '<b>⚠ Falta tu API key.</b> Para correr demos con el modelo real:',
  ayudaKeyPasos: '<ol style="margin:.3rem 0 .3rem 1.2rem;padding:0"><li>En la carpeta de los labs, copia <code>.env.example</code> y nómbralo <code>.env</code> (en la terminal: <code>cp .env.example .env</code>; en Windows <code>copy</code>). Los archivos con punto están ocultos: en Mac, <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>.</kbd> en el Finder; en Windows, Ver → Elementos ocultos.</li><li>Abre <code>.env</code> y pega tu key después de <code>ANTHROPIC_API_KEY=</code>.</li><li>Cierra el panel (Ctrl+C en la terminal) y vuelve a abrirlo con <code>python panel.py</code>.</li></ol>Mientras tanto, usa <b>Ver sin API key</b> para ver corridas grabadas.',
  ayudaLibs: '<b>⚠ Faltan librerías:</b> ', ayudaLibsPasos: '. El panel usa este Python: <code>__PY__</code>. Ciérralo, activa tu entorno virtual (.venv), corre <code>python -m pip install -r requirements.txt</code> y vuelve a abrir el panel con <code>python panel.py</code>.',
  verDetalle: 'clic para ver el ticket', ticketTitulo: 'Ticket de corrida', ticketLlamadas: 'Llamadas', ticketTotal: 'Total', ticketPie: 'Gracias por practicar · vuelve pronto', ticketExamen: 'En el examen:', ticketSiReal: 'Con key costaría', grabadaGratis: 'gratis (grabación)', ticketDistinto: 'Esta vez no pasó lo esperado: el modelo no siempre responde igual. La lección sigue: nada lo garantiza.', ticketNoCayo: 'Hoy el modelo no cayó en la trampa: lo hizo bien solo. Eso no lo vuelve correcto, porque nada lo garantiza: en el examen sigue siendo la respuesta incorrecta.', pareceCorrecto: 'Parece correcto:', personalizada: 'Personalizada', esperadoCaso: 'Lo esperado con este caso',
  esperadoNota: 'Compáralo con lo que ves en la salida y en el diagrama: el modelo no siempre responde igual.', tabEstudiar: 'Estudiar', estudiarVacio: 'Esta demo todavía no tiene su sección de estudio.',
  rutaTitulo: 'Ruta de estudio', rutaIr: 'Ir',
  ruta1: 'Lee la idea (pestaña Estudiar)', ruta2: 'Corre el caso ✅ (el que funciona)', ruta3: 'Corre un caso ❌ (el que falla a propósito)',
  ruta4: 'Compara las dos corridas', ruta5: 'Lee por qué pasó (en el ticket de la corrida)', paso: 'Qué pasó',
  tabMaterial: 'Guías', tabMaterialTitulo: 'Ver la guía de estudio o los slides aquí mismo, en el tema de la demo',
  matIrTema: 'Ir al tema', matAparte: '↗ Abrir en otra pestaña', matVacio: 'Todavía no hay guías ni slides en la carpeta material/.',
  matEnLinea: 'Estos slides están en claude.ai, que no deja mostrarlos dentro del panel. Ábrelos en otra pestaña, o pon el PDF en la carpeta <code>material/</code> para verlos aquí.',
  deCache: 'de caché', escenariosTxt: 'Escenario relacionado (lista no oficial):', escenarioN: 'Escenario', verEscenarios: 'ver los 6',
  productoTitulo: '🔀 Examen vs producto actual:', estimadoTxt: 'por corrida con este modelo (estimado de una corrida típica de', estimadoLlamadas: 'llamadas)',
  dosModelos: 'Correr con este y con…', dosModelosTitulo: 'Corre la demo con dos modelos y abre la comparación',
  dosIguales: 'Elige un segundo modelo distinto.', dosCorriendo: 'Corrida con el segundo modelo…',
  detalleEtiqueta: 'Salida:', detalleBasico: 'Básica (lo esencial)', detalleCompleto: 'Completa (todo el detalle)',
  temaTitulo: 'Tema claro / oscuro (por defecto, el de tu sistema)', tourTitulo: 'Recorrido por el panel', tourSaltar: 'Saltar', tourSig: 'Siguiente ▶', tourFin: 'Listo ✔',
  tour1: 'Elige el dominio y la demo. Cada demo es un tema del examen.',
  tour2: 'La ruta te dice qué hacer en orden. Marca cada paso cuando lo termines.',
  tour3: 'Aquí está la guía de estudio del tema: idea, analogía, confusiones típicas y autoevaluación.',
  tour4: 'Los casos llenan las variables: uno que funciona y varios que fallan a propósito. ▶ grabada lo reproduce sin API key y sin gastar.',
  tour5: 'Corre la demo. Al terminar sale un ticket con lo que se esperaba con ese caso y por qué.',
  tour6: 'Compara dos corridas lado a lado para ver qué cambió y por qué.',
  tour7: 'En Recursos están la hoja de repaso, el glosario, los antipatrones, las guías y los slides.',
  ocultarPanel: '⟨ Ocultar controles', mostrarPanel: '⟩ Mostrar controles', togglePanelTitulo: 'Oculta la columna de la izquierda para ver la salida o la comparación a todo lo ancho',
  cerrar: 'Cerrar', pieBusca: '↑ ↓ para moverte · Enter para abrir · Esc para cerrar. Busca en GUIA_LABS, README, el glosario y las demos.',
  buscaPlaceholder: 'Busca un tema, una variable o un término (ej. stop_reason, max_tokens, hooks)…', sinResultados: 'Sin resultados. Prueba con otra palabra.',
  sinDemos: 'Todavía no hay labs que se puedan correr desde el panel.', sinVariables: 'Esta demo no tiene variables.', sinGuia: '(sin guía)',
 },
 en: {
  dominioN: 'Domain', recEstudiar: 'To study', recRepaso: 'Review sheet', recRepasoSub: 'Exam situations and what to answer: all five domains, printable', recEscenarios: 'The 6 scenarios (unofficial list)', recEscenariosSub: 'Which demos practice each scenario', recAntipatrones: 'Anti-pattern gallery', recAntipatronesSub: 'What sounds right but is wrong, topic by topic', recGlosario: 'Glossary', recGlosarioSub: 'The terms in the study guides, searchable', recDocs: 'Documentation', recDominios: 'Domain pages', recEjemplos: 'Examples: what you will see', recEjemplosTodos: 'All examples', recEjemplosSub: 'Typical diagrams for each demo, without running anything', recSinEjemplos: 'No examples yet.', recCorridas: 'Your runs', recCorridasTodas: 'All your runs', recCorridasSub: 'Browse them with Previous / Next', recSinCorridas: 'You have not run any demo yet.', recCodigo: 'Lab code (read-only)', recConfig: 'Configuration files', recMaterial: 'Slides and study guides', recMaterialNota: 'They open right here, in the Guides tab. Those marked ↗ open in another tab.', recSinMaterial: 'There are no files in <code>material/</code> yet.',
  titulo: '<span class="marca">CCAR-F</span>Labs panel', notaCab: 'Runs on your computer. Changes apply to one run only; the lab file is not modified.',
  buscar: 'Search', buscarTitulo: 'Search guides, README, glossary and demos (Ctrl+K)', letraMenos: 'Smaller text', letraMas: 'Larger text',
  idiomaTitulo: 'Switch interface language', recursos: 'Resources', recNota: 'Everything opens in a new tab so you keep your place in the panel.',
  dominio: 'Domain', paginaDominio: 'Domain page', demo: 'Demo',
  como: 'How to run it', codigo: '&lt;/&gt; Code', ejemplo: 'Example', corridas: 'Your runs', slides: 'Slides', guiaEst: 'Study guide',
  guiaDemo: 'Demo guide (what it does and what to expect)',
  casos: 'Cases', casosAyuda: 'One click fills in the variables for a typical case. Then press <b>▶ Run</b> (uses your key) or <b>▶ recorded</b> (free) and compare.',
  grab: 'Watch without an API key', grabOtras: 'Other recordings', grabada: 'recorded', grabAyuda: 'Replays a recorded run: no tokens spent, no key needed.',
  simulada: 'simulated', simuladaLarga: 'simulated recording: scripted responses, not the real model',
  modelo: 'Model', variables: 'Demo variables', variablesAyuda: 'Change values here for this run. Green marks what differs from the lab file.',
  correr: '▶ Run', detener: '■ Stop', restaurar: '↺ Lab values', restaurarTitulo: 'Reset everything to the values in the lab file',
  tabSalida: 'Output', tabVista: 'Diagram', tabVistaTitulo: 'Shows up after a run or a recording', tabComparar: 'Compare', compararTitulo: 'Two runs of this demo side by side',
  inicio: 'Pick a demo and a case (or adjust the variables) and press ▶ Run or ▶ recorded.', vacio: 'The output shows up here while the demo runs.',
  estaCorrida: 'This run', llamada: 'call', llamadas: 'calls', corridaN: 'run', sesion: 'Since you opened the panel', corridasN: 'runs', grabadaNoGasta: 'recording: nothing spent',
  guardarGrab: 'Save as recording', guardarGrabAyuda: 'So someone without a key can watch it for free.', grabGuardada: '✔ Recording saved: it shows up next to its case (or under “Other recordings”).',
  corriendo: 'Running…', termino: '✔ Finished in', terminoError: '⚠ Finished with an error. Check the output.', reproduciendo: 'Playing recording…',
  grabacion: 'Recording', recargado: 'The lab file changed: its values were reloaded. ', ajustesPanel: 'Panel changes: ', sinAjustes: 'No panel changes: using the values written in the lab.',
  sinConexion: 'No connection to the panel. Is the terminal where you ran python panel.py still open?',
  keyOk: 'Key ready', keyFalta: 'API key missing', keyRechazada: 'Key rejected',
  ayudaEnvTxt: '<b>⚠ I found a file named <code>__ARCH__</code>, but the labs look for exactly <code>.env</code>.</b> Rename it to <code>.env</code> (no <code>.txt</code>). ',
  ayudaRechazada: '<b>⚠ Anthropic rejected your API key.</b> It was found in: <b>__FUENTE__</b>, but it is not valid (miscopied, deleted or replaced).<ol style="margin:.3rem 0 .3rem 1.2rem;padding:0"><li>In platform.claude.com → Settings → API keys, check it is still active, or create another.</li><li>Paste it whole in <code>.env</code> after <code>ANTHROPIC_API_KEY=</code>.</li><li>If you ever set it with <code>export</code> in the terminal, remove it: <code>unset ANTHROPIC_API_KEY</code> and delete it from <code>~/.zshrc</code> or <code>~/.bashrc</code>.</li><li>Close the panel (Ctrl+C) and open it again.</li></ol>', faltanLibs: 'Missing libraries', keyOkTitulo: 'Your key was found. It is never displayed.',
  ayudaKeyTitulo: '<b>⚠ Your API key is missing.</b> To run demos with the real model:',
  ayudaKeyPasos: '<ol style="margin:.3rem 0 .3rem 1.2rem;padding:0"><li>In the labs folder, copy <code>.env.example</code> and name it <code>.env</code> (in the terminal: <code>cp .env.example .env</code>; on Windows <code>copy</code>). Files that start with a dot are hidden: on Mac press <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>.</kbd> in Finder; on Windows, View → Hidden items.</li><li>Open <code>.env</code> and paste your key after <code>ANTHROPIC_API_KEY=</code>.</li><li>Close the panel (Ctrl+C in the terminal) and open it again with <code>python panel.py</code>.</li></ol>Meanwhile, use <b>Watch without an API key</b> to see recorded runs.',
  ayudaLibs: '<b>⚠ Missing libraries:</b> ', ayudaLibsPasos: '. The panel is using this Python: <code>__PY__</code>. Close it, activate your virtual environment (.venv), run <code>python -m pip install -r requirements.txt</code> and reopen it with <code>python panel.py</code>.',
  verDetalle: 'click to see the receipt', ticketTitulo: 'Run receipt', ticketLlamadas: 'Calls', ticketTotal: 'Total', ticketPie: 'Thanks for practicing · come back soon', ticketExamen: 'On the exam:', ticketSiReal: 'With a key it would cost', grabadaGratis: 'free (recording)', ticketDistinto: 'This time the expected result did not happen: the model does not always answer the same way. The lesson stands: nothing guarantees it.', ticketNoCayo: 'Today the model did not fall into the trap: it got it right on its own. That does not make it correct, because nothing guarantees it: on the exam it is still the wrong answer.', pareceCorrecto: 'Looks right:', personalizada: 'Custom', esperadoCaso: 'Expected with this case',
  esperadoNota: 'Compare it with the output and the diagram: the model does not always answer the same way.', tabEstudiar: 'Study', estudiarVacio: 'This demo has no study section yet.',
  rutaTitulo: 'Study path', rutaIr: 'Go',
  ruta1: 'Read the idea (Study tab)', ruta2: 'Run the ✅ case (the one that works)', ruta3: 'Run a ❌ case (the one that fails on purpose)',
  ruta4: 'Compare the two runs', ruta5: 'Read why it happened (on the run receipt)', paso: 'What happened',
  tabMaterial: 'Guides', tabMaterialTitulo: 'See the study guide or the slides right here, at the demo topic',
  matIrTema: 'Go to topic', matAparte: '↗ Open in another tab', matVacio: 'There are no guides or slides in the material/ folder yet.',
  matEnLinea: 'These slides live on claude.ai, which does not allow showing them inside the panel. Open them in another tab, or put the PDF in the <code>material/</code> folder to see them here.',
  deCache: 'cached', escenariosTxt: 'Related scenario (unofficial list):', escenarioN: 'Scenario', verEscenarios: 'see all 6',
  productoTitulo: '🔀 Exam vs current product:', estimadoTxt: 'per run with this model (estimated from a typical run of', estimadoLlamadas: 'calls)',
  dosModelos: 'Run with this one and…', dosModelosTitulo: 'Run the demo with two models and open the comparison',
  dosIguales: 'Pick a different second model.', dosCorriendo: 'Run with the second model…',
  detalleEtiqueta: 'Output:', detalleBasico: 'Basic (essentials)', detalleCompleto: 'Full (all details)',
  temaTitulo: 'Light / dark theme (defaults to your system)', tourTitulo: 'Panel tour', tourSaltar: 'Skip', tourSig: 'Next ▶', tourFin: 'Done ✔',
  tour1: 'Pick the domain and the demo. Each demo is an exam topic.',
  tour2: 'The path tells you what to do, in order. Tick each step when you finish it.',
  tour3: 'The study guide for this topic: idea, analogy, common misconceptions and self-check.',
  tour4: 'Cases fill in the variables: one that works and several that fail on purpose. ▶ recorded replays it with no API key and no cost.',
  tour5: 'Run the demo. When it finishes you get a receipt with what was expected for that case and why.',
  tour6: 'Compare two runs side by side to see what changed and why.',
  tour7: 'Resources has the review sheet, glossary, anti-patterns, study guides and slides.',
  ocultarPanel: '⟨ Hide controls', mostrarPanel: '⟩ Show controls', togglePanelTitulo: 'Hide the left column to see the output or the comparison full width',
  cerrar: 'Close', pieBusca: '↑ ↓ to move · Enter to open · Esc to close. Searches GUIA_LABS, README, the glossary and the demos.',
  buscaPlaceholder: 'Search a topic, variable or term (e.g. stop_reason, max_tokens, hooks)…', sinResultados: 'No results. Try another word.',
  sinDemos: 'No lab supports the panel yet.', sinVariables: 'This demo has no variables.', sinGuia: '(no guide)',
 },
};
let IDIOMA = guardado('idioma') === 'en' ? 'en' : 'es';
// El servidor lee esta cookie para mandar los textos (casos, guías, Estudiar, páginas) en el idioma elegido
function ponerCookieIdioma(){ document.cookie = 'idioma=' + IDIOMA + '; path=/; SameSite=Strict'; }
ponerCookieIdioma();
function t(k){ return (T[IDIOMA] && T[IDIOMA][k] !== undefined) ? T[IDIOMA][k] : (T.es[k] !== undefined ? T.es[k] : k); }
function traducir(){
  document.querySelectorAll('[data-t]').forEach(el => { el.innerHTML = t(el.dataset.t); });
  document.querySelectorAll('[data-tt]').forEach(el => { el.title = t(el.dataset.tt); });
  document.documentElement.lang = IDIOMA;
  $('#idioma').textContent = IDIOMA === 'es' ? 'EN' : 'ES';
  $('#q').placeholder = t('buscaPlaceholder');
  if (!CORRIENDO && !REPRODUCIENDO) $('#estado').textContent = t('inicio');
  document.querySelectorAll('#dominio option').forEach(o => { o.textContent = `${t('dominioN')} ${o.value}`; });
  if ($('#recursos').open) pintarRecursos();
  if (LAB) pintarDemo(true);
  if (ENTORNO) pintarEntorno();
  pintarTogglePanel();
}
// ---- Ocultar / mostrar la columna de controles (se recuerda) ----
let SIN_PANEL = guardado('sinpanel') === '1';
function pintarTogglePanel(){
  document.querySelector('main').classList.toggle('sinpanel', SIN_PANEL);
  $('#togglePanel').textContent = SIN_PANEL ? t('mostrarPanel') : t('ocultarPanel');
}
$('#togglePanel').onclick = () => { SIN_PANEL = !SIN_PANEL; guardar('sinpanel', SIN_PANEL ? '1' : '0'); pintarTogglePanel(); };
$('#idioma').onclick = async () => { IDIOMA = IDIOMA === 'es' ? 'en' : 'es'; guardar('idioma', IDIOMA); ponerCookieIdioma(); traducir();
  if (PESTANA === 'material') { VISOR.tema = true; pintarVisor(); }
  if (LAB) {   // vuelve a pedir los textos de las demos en el nuevo idioma (conserva lo que cambiaste)
    const nuevo = await api('/api/lab?n=' + $('#dominio').value);
    if (!nuevo.error) { const demo = $('#demo').value; LAB = nuevo; llenarDemos(demo); pintarDemo(true); }
  }
  if (ULTIMO_RESULTADO && $('#resultado').style.display !== 'none') mostrarResultado(...ULTIMO_RESULTADO);   // el ticket, también traducido
};

// ---- Tamaño de letra (A− / A+) ----
let ESCALA = Math.min(1.6, Math.max(0.8, +(guardado('escala') || 1)));
function aplicarEscala(){
  document.documentElement.style.setProperty('--escala', ESCALA);
  try { $('#vista').contentDocument.body.style.zoom = ESCALA; } catch (e) {}
}
$('#menos').onclick = () => { ESCALA = Math.max(0.8, +(ESCALA - 0.1).toFixed(2)); guardar('escala', ESCALA); aplicarEscala(); };
$('#mas').onclick = () => { ESCALA = Math.min(1.6, +(ESCALA + 0.1).toFixed(2)); guardar('escala', ESCALA); aplicarEscala(); };
aplicarEscala();

// ---- Colores: convierte los códigos ANSI que escribe el lab (rich) en <span> con color ----
const PALETA = __PALETA__;   // los 16 colores del tema Monokai, el mismo de las páginas HTML
let ESTILO = {};             // estilo vigente (se conserva entre líneas)
function color256(n){
  if (n < 16) return PALETA[n];
  if (n >= 232) { const g = 8 + (n - 232) * 10; return `rgb(${g},${g},${g})`; }
  n -= 16; const v = x => x ? 55 + x * 40 : 0;
  return `rgb(${v(Math.floor(n / 36))},${v(Math.floor(n / 6) % 6)},${v(n % 6)})`;
}
function aplicarSGR(codigos){
  const c = codigos.length ? codigos.map(Number) : [0];
  for (let i = 0; i < c.length; i++) {
    const k = c[i];
    if (k === 0) ESTILO = {};
    else if (k === 1) ESTILO.negrita = true;
    else if (k === 2) ESTILO.tenue = true;
    else if (k === 3) ESTILO.cursiva = true;
    else if (k === 4) ESTILO.subrayado = true;
    else if (k === 7) ESTILO.inverso = true;
    else if (k === 22) { delete ESTILO.negrita; delete ESTILO.tenue; }
    else if (k === 23) delete ESTILO.cursiva;
    else if (k === 24) delete ESTILO.subrayado;
    else if (k === 27) delete ESTILO.inverso;
    else if (k >= 30 && k <= 37) ESTILO.fg = PALETA[k - 30];
    else if (k >= 90 && k <= 97) ESTILO.fg = PALETA[k - 90 + 8];
    else if (k === 39) delete ESTILO.fg;
    else if (k >= 40 && k <= 47) ESTILO.bg = PALETA[k - 40];
    else if (k >= 100 && k <= 107) ESTILO.bg = PALETA[k - 100 + 8];
    else if (k === 49) delete ESTILO.bg;
    else if ((k === 38 || k === 48) && c[i + 1] === 5) { ESTILO[k === 38 ? 'fg' : 'bg'] = color256(c[i + 2]); i += 2; }
    else if ((k === 38 || k === 48) && c[i + 1] === 2) { ESTILO[k === 38 ? 'fg' : 'bg'] = `rgb(${c[i + 2]},${c[i + 3]},${c[i + 4]})`; i += 4; }
  }
}
function spanActual(texto){
  if (!texto) return '';
  let fg = ESTILO.fg, bg = ESTILO.bg;
  if (ESTILO.inverso) { [fg, bg] = [bg || '#0c0c0c', fg || '#d9d9d9']; }
  const css = [];
  if (fg) css.push('color:' + fg);
  if (bg) css.push('background:' + bg);
  if (ESTILO.negrita) css.push('font-weight:700');
  if (ESTILO.tenue) css.push('opacity:.65');
  if (ESTILO.cursiva) css.push('font-style:italic');
  if (ESTILO.subrayado) css.push('text-decoration:underline');
  return css.length ? `<span style="${css.join(';')}">${esc(texto)}</span>` : esc(texto);
}
function ansiAHtml(linea){
  linea = linea.replace(/\x1b\][^\x07\x1b]*(\x07|\x1b\\)/g, '');     // enlaces y títulos (OSC): fuera
  let html = '', ultimo = 0;
  const re = /\x1b\[([0-9;]*)([A-Za-z])/g;
  let m;
  while ((m = re.exec(linea)) !== null) {
    html += spanActual(linea.slice(ultimo, m.index));
    if (m[2] === 'm') aplicarSGR(m[1] ? m[1].split(';').filter(x => x !== '') : []);
    ultimo = re.lastIndex;
  }
  return html + spanActual(linea.slice(ultimo));
}

async function api(ruta, datos){
  // Si el panel se cerró o la red falla, regresa {error} en vez de tronar (así la interfaz no se queda congelada)
  try {
    const r = await fetch(ruta, datos ? {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(datos)} : {});
    return await r.json();
  } catch (e) {
    return {error: t('sinConexion'), sin_conexion: true};
  }
}
function esc(t){ return String(t).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
const dormir = ms => new Promise(r => setTimeout(r, ms));

// ---- ¿Hay key y librerías? ----
async function revisarEntorno(){
  ENTORNO = await api('/api/estado'); pintarEntorno();
  if (ENTORNO.key && !ENTORNO.faltan.length) {      // prueba la key de verdad (consulta gratis)
    const r = await api('/api/probar_key').catch(() => ({ok: true}));
    if (!r.ok) { ENTORNO.key = false; ENTORNO.rechazada = r.motivo; ENTORNO.fuente = r.fuente; pintarEntorno(); }
  }
}
function pintarEntorno(){
  const e = ENTORNO, el = $('#llave'), listo = e.key && !e.faltan.length;
  el.className = 'chip ' + (listo ? 'ok' : 'mal');
  el.innerHTML = e.faltan.length ? t('faltanLibs') : (e.key ? t('keyOk') : (e.rechazada ? t('keyRechazada') : t('keyFalta')));
  el.title = listo ? t('keyOkTitulo') + ' (' + e.fuente + ')' : '';
  el.onclick = () => mostrarAyudaKey(!$('#ayudaKey').style.display || $('#ayudaKey').style.display === 'none');
}
function mostrarAyudaKey(si){
  const e = ENTORNO, caja = $('#ayudaKey');
  if (!si || (e.key && !e.faltan.length)) { caja.style.display = 'none'; return; }
  caja.innerHTML = (e.faltan.length ? t('ayudaLibs') + e.faltan.join(', ') + t('ayudaLibsPasos').replace('__PY__', esc(e.python || 'python'))
       : e.rechazada ? t('ayudaRechazada').replace('__FUENTE__', esc(e.fuente || ''))
       : (e.env_txt ? t('ayudaEnvTxt').replace('__ARCH__', esc(e.env_txt)) : '') + t('ayudaKeyTitulo') + t('ayudaKeyPasos'))
     + ` <button class="sec mini" onclick="mostrarAyudaKey(false)">${t('cerrar')}</button>`;
  caja.style.display = 'block';
}

// ---- Cargar labs y demos ----
async function iniciar(){
  traducir(); revisarEntorno();
  const {labs} = await api('/api/labs');
  $('#dominio').innerHTML = labs.map(n => `<option value="${n}">${t('dominioN')} ${n}</option>`).join('');
  if (!labs.length) { $('#estado').textContent = t('sinDemos'); return; }
  const p = new URLSearchParams(location.search);
  if (p.get('n') && labs.includes(+p.get('n'))) $('#dominio').value = p.get('n');
  await cargarLab(p.get('demo'));
  if (p.get('caso') !== null && (demoActual().extras || {}).casos) aplicarCaso(+p.get('caso'));
  if (p.get('grab')) { const g = (demoActual().grabaciones || []).find(x => x.url.endsWith('/' + p.get('grab'))); if (g) reproducir(g); }
  if (guardado('tour') !== '1') setTimeout(() => iniciarTour(false), 600);
}
async function cargarLab(demoInicial){
  LAB = await api('/api/lab?n=' + $('#dominio').value);
  if (LAB.error) { $('#estado').textContent = LAB.error; return; }
  llenarDemos(typeof demoInicial === 'string' ? demoInicial : null);
  $('#modelo').innerHTML = MODELOS.map(m => `<option ${m === LAB.modelo ? 'selected' : ''}>${m}</option>`).join('');
  $('#paginaDominio').href = '/dominio?n=' + $('#dominio').value;
  llenarModelo2();
  pintarDemo();
}
function llenarDemos(elegida){
  $('#demo').innerHTML = LAB.demos.map(d => `<option value="${d.clave}">${d.clave} · ${esc(d.nombre)}</option>`).join('');
  if (elegida && LAB.demos.some(d => d.clave === elegida)) $('#demo').value = elegida;
}
function demoActual(){ return LAB.demos.find(d => d.clave === $('#demo').value); }

function pintarDemo(conservar){
  const d = demoActual();
  const previos = conservar ? leerControles() : null;
  // Franja "Para esta demo"
  pintarContexto(d.contexto || {});
  $('#estudio').innerHTML = d.estudio_html || `<p class="ayuda">${t('estudiarVacio')}</p>`;
  const esc_ = d.escenarios || [];
  $('#escenarios').innerHTML = esc_.length ? `${t('escenariosTxt')} ` + esc_.map(e => `<b>${t('escenarioN')} ${e.n}</b> · ${esc(e[IDIOMA] || e.es)}`).join('; ')
    + ` <a href="/escenarios" target="_blank">(${t('verEscenarios')})</a>` : '';
  $('#producto').style.display = d.producto ? 'block' : 'none';
  $('#producto').innerHTML = d.producto ? `<b>${t('productoTitulo')}</b> ${esc(d.producto)}` : '';
  pintarRuta(d); pintarEstimado(d);
  if (PESTANA === 'material') { VISOR.tema = true; pintarVisor(); }
  if (!conservar && !CORRIENDO && !REPRODUCIENDO) pestana(d.estudio_html ? 'estudiar' : 'salida');
  if (!conservar && !CORRIENDO && !REPRODUCIENDO && CORRIDA && CORRIDA.demo !== d.clave) $('#resultado').style.display = 'none';
  $('#guia').innerHTML = d.guia || t('sinGuia');
  // Casos rápidos
  const casos = (d.extras || {}).casos || [];
  $('#casosBox').style.display = casos.length ? 'block' : 'none';
  // Cada caso con su grabación (si la hay): ▶ grabada se ve sin API key y no gasta nada
  const g = d.grabaciones || [], usadas = new Set();
  const grabDe = k => {
    const i = g.findIndex((x, j) => !usadas.has(j) && ((k.grabacion && x.url.endsWith('/' + k.grabacion)) || (x.titulo_es || x.titulo || '').startsWith(k.nombre_es || k.nombre)));
    if (i >= 0) usadas.add(i);
    return i;
  };
  $('#casos').innerHTML = casos.map((k, i) => {
    const gi = grabDe(k);
    return `<div class="caso"><button class="${k.tipo}" data-c="${i}">${esc(k.nombre)}</button>`
      + (gi >= 0 ? `<button class="sec mini grabada" data-g="${gi}" data-c="${i}" title="${t('grabAyuda')}">▶ ${t('grabada')}${g[gi].simulada ? ' · ' + t('simulada') : ''}</button>` : '')
      + '</div>';
  }).join('');
  $('#casos').querySelectorAll('button[data-c]:not(.grabada)').forEach(b => b.onclick = () => aplicarCaso(+b.dataset.c));
  $('#casos').querySelectorAll('button.grabada').forEach(b => b.onclick = () => reproducir({...g[+b.dataset.g], caso: +b.dataset.c}));
  // Grabaciones que no son de ningún caso (p. ej. las que guardaste tú)
  const otras = g.map((x, i) => [x, i]).filter(([, i]) => !usadas.has(i));
  $('#grabBox').style.display = otras.length ? 'block' : 'none';
  $('#grabs').innerHTML = otras.map(([x, i]) => `<button class="sec" data-g="${i}">▶ ${esc(x.titulo)}${x.simulada ? ` <small>(${t('simulada')})</small>` : ''}</button>`).join('');
  $('#grabs').querySelectorAll('button').forEach(b => b.onclick = () => reproducir(g[+b.dataset.g]));
  // Variables
  $('#variables').innerHTML = d.variables.map((v, i) => {
    let control;
    const id = `v${i}`;
    if (v.tipo === 'bool') control = `<label><input type="checkbox" id="${id}" data-i="${i}" ${v.valor ? 'checked' : ''}>${v.valor ? 'True' : 'False'}</label>`;
    else if (v.tipo === 'numero') control = `<input type="number" id="${id}" data-i="${i}" value="${v.valor}" step="any">`;
    else if (v.tipo === 'opciones') control = `<select id="${id}" data-i="${i}">${v.opciones.map(o => `<option ${o === v.valor ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
    else if (v.tipo === 'json') control = `<textarea id="${id}" data-i="${i}">${esc(JSON.stringify(v.valor))}</textarea>`;
    else if (v.tipo === 'texto_largo') control = `<textarea id="${id}" data-i="${i}">${esc(v.valor)}</textarea>`;
    else control = `<input type="text" id="${id}" data-i="${i}" value="${esc(v.valor)}">`;
    return `<div class="var"><label class="nombre" for="${id}">${v.nombre}<span class="cambiada" id="c${i}"></span></label>
            ${v.ayuda_html ? `<div class="ayuda">${v.ayuda_html}</div>` : ''}${control}</div>`;
  }).join('') || `<p class="ayuda">${t('sinVariables')}</p>`;
  $('#variables').querySelectorAll('[data-i]').forEach(el => el.addEventListener('input', marcarCambios));
  $('#variables').querySelectorAll('input[type=checkbox]').forEach(el => el.addEventListener('change', e => {
    e.target.nextSibling.textContent = e.target.checked ? 'True' : 'False'; marcarCambios(); }));
  if (previos) ponerControles(previos);
  marcarCambios();
}
function leerValor(v, el){
  if (v.tipo === 'bool') return el.checked;
  if (v.tipo === 'numero') return Number(el.value);
  if (v.tipo === 'json') { try { return JSON.parse(el.value); } catch (e) { return v.valor; } }
  return el.value;
}
function leerControles(){
  const d = demoActual(), out = {};
  $('#variables').querySelectorAll('[data-i]').forEach(el => { const v = d.variables[+el.dataset.i]; out[v.nombre] = leerValor(v, el); });
  return out;
}
function ponerControles(valores){
  const d = demoActual();
  $('#variables').querySelectorAll('[data-i]').forEach(el => {
    const v = d.variables[+el.dataset.i];
    if (!(v.nombre in valores)) return;
    const val = valores[v.nombre];
    if (v.tipo === 'bool') { el.checked = val; el.nextSibling.textContent = val ? 'True' : 'False'; }
    else el.value = (v.tipo === 'json') ? JSON.stringify(val) : val;
  });
}
function ajustes(){
  // Solo lo que cambiaste en el panel: lo demás usa el valor escrito en el archivo del lab.
  const d = demoActual(), actuales = leerControles(), out = {};
  for (const v of d.variables) if (JSON.stringify(actuales[v.nombre]) !== JSON.stringify(v.valor)) out[v.nombre] = actuales[v.nombre];
  if ($('#modelo').value !== LAB.modelo) out.MODELO = $('#modelo').value;
  out.DETALLE = $('#detalle').value;   // el panel siempre manda el nivel de salida elegido
  return out;
}
function casoActivo(){
  const casos = (demoActual().extras || {}).casos || [], actuales = leerControles();
  return casos.findIndex(k => Object.entries(k.valores).every(([n, v]) => JSON.stringify(actuales[n]) === JSON.stringify(v)));
}
function aplicarCaso(i){
  const d = demoActual(), k = d.extras.casos[i];
  // Cada caso parte de los valores del lab: así no se arrastran variables del caso anterior
  ponerControles(Object.fromEntries(d.variables.map(v => [v.nombre, v.valor])));
  ponerControles(k.valores); marcarCambios();
}
function marcarCambios(){
  const d = demoActual();
  $('#variables').querySelectorAll('[data-i]').forEach(el => {
    const v = d.variables[+el.dataset.i];
    $('#c' + el.dataset.i).textContent = JSON.stringify(leerValor(v, el)) !== JSON.stringify(v.valor) ? (IDIOMA === 'es' ? 'cambiada' : 'changed') : '';
  });
  const casos = (d.extras || {}).casos || [];
  if (!casos.length) return;
  const i = casoActivo();
  $('#casos').querySelectorAll('button').forEach(b => b.classList.toggle('activo', +b.dataset.c === i));
  const ci = i >= 0 ? casos[i].clase_info : null;
  $('#casoExplica').innerHTML = i >= 0 ? (casos[i].parece ? `<span class="parece"><b>${t('pareceCorrecto')}</b> ${esc(casos[i].parece)}</span><br>` : '')
    + `<b>${esc(casos[i].nombre)}:</b> ${casos[i].explica_html}`
    + (ci ? `<br><span class="clase ${casos[i].clase}" title="${esc(ci['ayuda_' + IDIOMA] || ci.ayuda_es)}">${esc(ci[IDIOMA] || ci.es)}</span> <small>${esc(ci['ayuda_' + IDIOMA] || ci.ayuda_es)}</small>` : '')
    : t('casosAyuda');
}
async function revisarArchivo(){
  // Si editaste el lab en tu editor mientras el panel estaba abierto, recarga sus valores
  // (conserva lo que hayas cambiado en el panel).
  const nuevo = await api('/api/lab?n=' + $('#dominio').value);
  if (nuevo.error || nuevo.version === LAB.version) return false;
  const cambios = ajustes(), demo = $('#demo').value, modelo = cambios.MODELO;
  LAB = nuevo;
  llenarDemos(demo);
  $('#modelo').innerHTML = MODELOS.map(m => `<option ${m === (modelo || LAB.modelo) ? 'selected' : ''}>${m}</option>`).join('');
  pintarDemo(); llenarModelo2();
  ponerControles(cambios); marcarCambios();
  return true;
}

// ---- Pestañas ----
function pestana(cual){
  ['estudiar', 'salida', 'vista', 'comparar', 'material'].forEach(k => {
    const b = $('#tab' + k[0].toUpperCase() + k.slice(1));
    b.classList.toggle('activa', k === cual); b.setAttribute('aria-selected', k === cual ? 'true' : 'false');
  });
  PESTANA = cual;
  $('#resultado').classList.toggle('compacto', !['salida', 'vista'].includes(cual));
  if (cual === 'comparar') marcarPaso(3);
  $('#estudio').style.display = cual === 'estudiar' ? 'block' : 'none';
  $('#salida').style.display = cual === 'salida' ? 'block' : 'none';
  $('#vista').style.display = (cual === 'vista' || cual === 'comparar') ? 'block' : 'none';
  $('#material').style.display = cual === 'material' ? 'flex' : 'none';
  if (cual === 'material') pintarVisor();
  if (cual === 'vista' && PAGINA_ACTUAL && !$('#vista').src.endsWith(PAGINA_ACTUAL)) $('#vista').src = PAGINA_ACTUAL;
  if (cual === 'comparar') $('#vista').src = `/comparar?n=${$('#dominio').value}&demo=${encodeURIComponent($('#demo').value)}`;
}

let ULTIMO_RESULTADO = null;
function mostrarResultado(res, sesion, esGrabacion){
  ULTIMO_RESULTADO = [res, sesion, esGrabacion];
  // El resultado de cada corrida, como ticket de La Tiendita: qué tipo de caso fue, qué se esperaba,
  // qué pasó, por qué, qué pregunta el examen y cuánto costó. Usa la demo y el caso con que se lanzó.
  const clave = (CORRIDA && CORRIDA.demo) || demoActual().clave;
  const d = (LAB.demos.find(x => x.clave === clave)) || demoActual();
  const p = (d.extras || {}).predice, casos = (d.extras || {}).casos || [];
  const caso = CORRIDA && CORRIDA.caso >= 0 ? casos[CORRIDA.caso] : null;
  const fila = (k, v, cls) => `<div class="t-fila${cls ? ' ' + cls : ''}"><span>${k}</span><i></i><b>${v}</b></div>`;
  const op = k => p && p.opciones[k] ? esc(p.opciones[k]) : esc(k);
  const esperado = caso ? caso.esperado : (p && p.esperado);
  const finales = res && res.partes ? Object.values(res.partes).map(x => x.final).filter(Boolean) : [];
  const paso = (esperado && finales.includes(esperado)) ? esperado : (res && res.final);
  let cuerpo = '', resumen = '', total = '';
  if (esperado && p && p.opciones[esperado]) { cuerpo += fila(t('esperadoCaso'), op(esperado)); resumen = op(esperado); }
  if (paso && p) {
    cuerpo += fila(t('paso'), op(paso)); resumen = op(paso);
    if (esperado && esperado !== paso)      // un ❌ que hoy no falló: el modelo se cuidó solo, pero nada lo garantiza
      cuerpo += `<p class="t-nota">${caso && caso.tipo === 'falla' ? esc(caso.si_no_falla || t('ticketNoCayo')) : t('ticketDistinto')}</p>`;
  }
  const porque = p && p.por_que[paso || esperado];
  if (porque) cuerpo += `<p class="t-porque">${esc(porque)}</p>`;
  if (res && res.texto) cuerpo += `<p class="t-nota">${esc(res.texto)}</p>`;
  if (!resumen && res && res.texto) resumen = esc(res.texto);
  const examen = (caso && caso.examen) || d.examen_tema;
  if (examen) cuerpo += `<div class="t-examen"><b>${t('ticketExamen')}</b> ${esc(examen)}</div>`;
  if (esperado && p && !paso) cuerpo += `<p class="t-nota">${t('esperadoNota')}</p>`;
  const uso = res && res.uso;
  if (uso && uso.llamadas) {
    total = `≈ $${(res.costo || 0).toFixed(4)}`;
    cuerpo += '<div class="t-sep"></div>' + fila(t('ticketLlamadas'), uso.llamadas) + fila('Tokens', (uso.entrada + uso.salida).toLocaleString() + (uso.cache ? ` (+${uso.cache.toLocaleString()} ${t('deCache')})` : ''));
    if (esGrabacion) cuerpo += fila(t('ticketSiReal'), total + ' USD') + `<p class="t-nota">${t('grabadaNoGasta')}</p>`;
    else {
      cuerpo += fila(t('ticketTotal'), total + ' USD', 'total');
      if (sesion) cuerpo += fila(`${t('sesion')} (${sesion.corridas} ${t(sesion.corridas === 1 ? 'corridaN' : 'corridasN')})`, `≈ $${sesion.costo.toFixed(4)}`);
    }
    if (esGrabacion) total = t('grabadaGratis');
  }
  if (!cuerpo) { $('#resultado').style.display = 'none'; return; }
  const marca = caso ? (caso.tipo === 'ok' ? '✅' : '❌') : '';
  const clase = caso && caso.clase_info ? `<span class="clase ${caso.clase}">${esc(caso.clase_info[IDIOMA] || caso.clase_info.es)}</span>` : '';
  const ahora = new Date().toLocaleString(IDIOMA === 'es' ? 'es-MX' : 'en-US', {dateStyle: 'short', timeStyle: 'short'});
  const ticket = `<div class="ticket"><div class="t-cab"><b>LA TIENDITA</b><span>${t('ticketTitulo')} · ${esc(d.clave)}</span>`
    + `<span>${ahora}${esGrabacion ? ' · ' + t('grabacion') : ''}</span>`
    + (caso ? `<span class="t-caso">${marca} ${esc(caso.nombre.replace(/^[✅❌]\s*/, ''))} ${clase}</span>` : '') + `</div>`
    + `${cuerpo}<div class="t-pie">${t('ticketPie')}</div></div>`;
  const botonGrabar = (!esGrabacion && ULTIMO_OK) ? `<div class="t-grabar"><button id="btnGrabar" class="sec mini">${t('guardarGrab')}</button>`
    + `<small class="ayuda" style="margin:0">${t('guardarGrabAyuda')}</small></div>` : '';
  const abierto = guardado('resultado_abierto') === '1';
  $('#resultado').innerHTML = `<details id="resDet" ${abierto ? 'open' : ''}><summary><span class="talon"><b>TICKET</b>`
    + (marca ? `<span>${marca}</span>` : '') + (resumen ? `<span class="t-resumen">${resumen}</span>` : '') + (total ? `<span>${total}</span>` : '') + '</span>'
    + `<span class="verdetalle">${t('verDetalle')}</span></summary>${ticket}${botonGrabar}</details>`;
  $('#resultado').style.display = 'block';
  $('#resDet').ontoggle = e => { guardar('resultado_abierto', e.target.open ? '1' : '0'); if (e.target.open) marcarPaso(4); };
  if ($('#btnGrabar')) $('#btnGrabar').onclick = grabar;
}
async function grabar(){
  const casos = (demoActual().extras || {}).casos || [], i = CORRIDA ? CORRIDA.caso : casoActivo();
  const titulo = (i >= 0 && casos[i] ? (casos[i].nombre_es || casos[i].nombre) : t('personalizada')) + ' · ' + new Date().toLocaleString();
  const r = await api('/api/grabar', {id: TRABAJO, titulo});
  if (r.error) { alertaEstado('⚠ ' + r.error); return; }
  $('#btnGrabar').outerHTML = `<span class="bien">${t('grabGuardada')}</span>`;
  const nuevo = await api('/api/lab?n=' + $('#dominio').value);
  if (!nuevo.error) { const valores = leerControles(); LAB = nuevo; pintarDemo(); ponerControles(valores); marcarCambios(); }
}
function alertaEstado(texto){ $('#estado').textContent = texto; }

// ---- Correr de verdad ----
function prepararSalida(){
  DESDE = 0; ESTILO = {}; ULTIMO_OK = false;
  $('#salida').replaceChildren(); pestana('salida');
  $('#vista').src = 'about:blank'; PAGINA_ACTUAL = null;
  $('#resultado').style.display = 'none';
  $('#tabVista').disabled = true; ocupado(true);
}
async function correr(){
  if (ENTORNO && (!ENTORNO.key || ENTORNO.faltan_basicas.length)) { await revisarEntorno(); if (!ENTORNO.key || ENTORNO.faltan_basicas.length) { mostrarAyudaKey(true); return; } }
  const recargado = await revisarArchivo();
  lanzar(recargado);
}
function ocupado(si){
  CORRIENDO = si;
  $('#correr').disabled = si; $('#dosModelos').disabled = si; $('#detener').disabled = !si;
  document.querySelectorAll('#grabs button, #casos .grabada').forEach(b => b.disabled = si);
}
async function lanzar(recargado, extra){
  CASO_CORRIDA = casoActivo();
  const cambios = Object.assign(ajustes(), extra || {});
  const r = await api('/api/correr', {dominio: $('#dominio').value, demo: $('#demo').value, ajustes: cambios});
  if (r.error) { alertaEstado('⚠ ' + r.error); return false; }
  CORRIDA = {demo: $('#demo').value, caso: CASO_CORRIDA};
  TRABAJO = r.id; prepararSalida();
  const lista = Object.entries(cambios).filter(([k]) => k !== 'DETALLE').map(([k, v]) => `${k} = ${JSON.stringify(v)}`).join(' · ');
  AVISO = (recargado ? t('recargado') : '') + (lista ? t('ajustesPanel') + lista : t('sinAjustes'));
  seguir();
  return true;
}
function agregarLineas(lineas){
  const abajo = $('#salida').scrollTop + $('#salida').clientHeight >= $('#salida').scrollHeight - 30;
  $('#salida').insertAdjacentHTML('beforeend', lineas.map(ansiAHtml).join('\n') + '\n');
  if (abajo) $('#salida').scrollTop = $('#salida').scrollHeight;
}
async function seguir(){
  const r = await api(`/api/salida?id=${TRABAJO}&desde=${DESDE}`);
  if (r.sin_conexion && (SEGUIR_FALLAS = (SEGUIR_FALLAS || 0) + 1) < 5) { setTimeout(seguir, 1500); return; }   // reintenta unas veces
  SEGUIR_FALLAS = 0;
  if (r.error) { ocupado(false); alertaEstado('⚠ ' + r.error); if (ESPERANDO) { const f = ESPERANDO; ESPERANDO = null; f(null); } return; }
  if (r.lineas.length) { agregarLineas(r.lineas); DESDE = r.total; }
  $('#estado').textContent = (r.terminado ? (r.codigo === 0 ? `${t('termino')} ${r.segundos} s.` : t('terminoError')) : `${t('corriendo')} ${r.segundos} s.`) + '  ' + AVISO;
  if (!r.terminado) { setTimeout(seguir, 700); return; }
  ocupado(false);
  ULTIMO_OK = r.codigo === 0 && !!r.pagina;
  if (r.codigo === 0 && CORRIDA) { const k = ((demoActual().extras || {}).casos || [])[CORRIDA.caso]; if (k) marcarPaso(k.tipo === 'ok' ? 1 : 2); }
  if (r.pagina) { PAGINA_ACTUAL = r.pagina; $('#tabVista').disabled = false; pestana('vista'); }
  mostrarResultado(r.resultado, r.sesion, false);
  refrescarContexto();
  if (ESPERANDO) { const f = ESPERANDO; ESPERANDO = null; f(r); }
}
async function refrescarContexto(){
  // después de la primera corrida aparecen "Tus corridas" y las grabaciones nuevas
  const nuevo = await api('/api/lab?n=' + $('#dominio').value);
  if (nuevo.error) return;
  const d = nuevo.demos.find(x => x.clave === $('#demo').value), actual = demoActual();
  if (d && actual) { actual.contexto = d.contexto; actual.grabaciones = d.grabaciones; }
  pintarContexto(actual.contexto || {});
}
function materialEnIdioma(m){
  // El del idioma elegido; si no existe, el del otro idioma, marcado con su sigla.
  if (!m) return null;
  if (m[IDIOMA]) return {url: m[IDIOMA], marca: ''};
  const otro = Object.keys(m)[0];
  return otro ? {url: m[otro], marca: ` <small>(${otro.toUpperCase()})</small>`} : null;
}
// ---- Visor de guías y slides dentro del panel ----
let VISOR = {n: null, k: 'guia_estudio', tema: true};
function opcionesMaterial(){
  const ops = [];
  for (const [n, m] of Object.entries((LAB && LAB.material_todo) || {}))
    for (const [k, tk] of [['guia_estudio', 'guiaEst'], ['slides', 'slides']]) {
      const e = materialEnIdioma(m[k]);
      if (e) ops.push({n, k, url: e.url, txt: `${t('dominioN')} ${n} · ${t(tk).replace(/<[^>]+>/g, '')}`});
    }
  return ops;
}
function abrirMaterial(n, k){ VISOR = {n: String(n), k, tema: true}; pestana('material'); }
function pintarVisor(forzar){
  const ops = opcionesMaterial(), dom = $('#dominio').value, tema = $('#demo').value;
  let o = ops.find(x => x.n === VISOR.n && x.k === VISOR.k) || ops.find(x => x.n === dom && x.k === VISOR.k)
       || ops.find(x => x.n === dom) || ops[0];
  if (!o) { $('#matAviso').innerHTML = t('matVacio'); $('#matAviso').style.display = 'block'; $('#visor').style.display = 'none'; return; }
  VISOR.n = o.n; VISOR.k = o.k;
  $('#matSel').innerHTML = ops.map(x => `<option value="${x.n}|${x.k}" ${x === o ? 'selected' : ''}>${esc(x.txt)}${x.url.startsWith('http') ? ' ↗' : ''}</option>`).join('');
  const pag = tema.split('.')[0] === o.n ? ((((LAB.paginas || {})[o.k]) || {})[tema]) : null;
  $('#matTema').style.display = pag ? '' : 'none';
  $('#matTema').textContent = `${t('matIrTema')} ${tema} (p. ${pag})`;
  $('#matAparte').href = o.url + (pag && !o.url.startsWith('http') ? '#page=' + pag : '');
  if (o.url.startsWith('http')) {
    $('#visor').style.display = 'none'; $('#matAviso').style.display = 'block';
    $('#matAviso').innerHTML = t('matEnLinea') + `<p><a class="boton" href="${o.url}" target="_blank">${t('matAparte')}</a></p>`;
    return;
  }
  $('#matAviso').style.display = 'none'; $('#visor').style.display = 'block';
  // El número de página va también en la URL (?p=) para que el visor de PDF salte aunque sea el mismo archivo
  const vista = 'view=FitH&navpanes=0';   // a lo ancho y sin la columna de miniaturas
  const src = VISOR.tema && pag ? `${o.url}?p=${pag}#page=${pag}&${vista}` : `${o.url}#${vista}`;
  if (forzar || $('#visor').dataset.src !== src) { $('#visor').src = src; $('#visor').dataset.src = src; }
  VISOR.tema = false;
}
function pintarContexto(c){
  const fijos = [['como', 'como'], ['codigo', 'codigo'], ['ejemplo', 'ejemplo'], ['corridas', 'corridas']]
     .filter(([k]) => c[k]).map(([k, tk]) => `<a href="${c[k]}" target="_blank">${t(tk)}</a>`);
  const mat = c.material || {};
  const material = [['slides', 'slides'], ['guia_estudio', 'guiaEst']].map(([k, tk]) => {
    const e = materialEnIdioma(mat[k]);
    if (!e) return '';
    return e.url.startsWith('http') ? `<a href="${e.url}" target="_blank">${t(tk)}${e.marca} ↗</a>`
         : `<a href="${e.url}" data-visor="${k}">${t(tk)}${e.marca}</a>`;
  }).filter(Boolean);
  $('#contexto').innerHTML = fijos.concat(material).join('');
  $('#contexto').querySelectorAll('[data-visor]').forEach(a => a.onclick = ev => {
    ev.preventDefault(); abrirMaterial($('#dominio').value, a.dataset.visor); });
}

// ---- Reproducir una grabación (sin API key) ----
async function reproducir(g){
  if (CORRIENDO && !REPRODUCIENDO) return;            // hay una corrida real: primero que termine
  if (REPRODUCIENDO) REPRODUCIENDO.cancelado = true;  // otra grabación sonando: se cancela
  const datos = await (await fetch(g.url)).json();
  const casos = (demoActual().extras || {}).casos || [];
  CASO_CORRIDA = g.caso !== undefined ? g.caso : casos.findIndex(k => datos.titulo && datos.titulo.startsWith(k.nombre_es || k.nombre));
  if (CASO_CORRIDA >= 0) aplicarCaso(CASO_CORRIDA);
  CORRIDA = {demo: demoActual().clave, caso: CASO_CORRIDA};
  prepararSalida();
  const yo = REPRODUCIENDO = {cancelado: false};
  AVISO = `${t('grabacion')}: ${g.titulo || datos.titulo}` + (datos.simulada ? ` · ${t('simuladaLarga')}` : '');
  let previo = 0;
  for (let i = 0; i < datos.lineas.length && !yo.cancelado; i++) {
    const espera = Math.min(900, Math.max(0, ((datos.tiempos || [])[i] - previo) * 1000 || 0));
    previo = (datos.tiempos || [])[i] || previo;
    if (espera > 25) await dormir(espera);
    agregarLineas([datos.lineas[i]]);
    $('#estado').textContent = `${t('reproduciendo')} ${i + 1}/${datos.lineas.length} · ${AVISO}`;
  }
  if (yo.cancelado) return;
  REPRODUCIENDO = null; ocupado(false);
  $('#estado').textContent = '✔ ' + AVISO;
  if (typeof datos.pagina === 'string' && /^\/archivos\/grabaciones\/[\w.\-\/]+\.html$/.test(datos.pagina) && !datos.pagina.includes('..')) { PAGINA_ACTUAL = datos.pagina; $('#tabVista').disabled = false; pestana('vista'); }
  mostrarResultado(datos.resultado, null, true);
  const k = casos[CASO_CORRIDA];                       // una grabación también cuenta para la ruta de estudio
  if (k) marcarPaso(k.tipo === 'ok' ? 1 : 2);
}

// ---- Ruta de estudio (se recuerda por demo; los pasos se marcan solos al hacerlos y se pueden desmarcar) ----
function marcarPaso(i){
  const d = demoActual(); if (!d) return;
  const clave = 'ruta_' + d.clave;
  let hechos = []; try { hechos = JSON.parse(guardado(clave) || '[]'); } catch (e) {}
  if (hechos.includes(i)) return;
  guardar(clave, JSON.stringify([...hechos, i])); pintarRuta(d);
}
function pintarRuta(d){
  const clave = 'ruta_' + d.clave;
  let hechos = []; try { hechos = JSON.parse(guardado(clave) || '[]'); } catch (e) {}
  const casos = (d.extras || {}).casos || [];
  const elegir = tipo => () => {
    const i = casos.findIndex(k => k.tipo === tipo);
    if (i >= 0) aplicarCaso(i);
    const c = $('#casosBox'); if (c) c.scrollIntoView({behavior: SUAVE()});
  };
  const pasos = [
    ['ruta1', d.estudio_html ? () => pestana('estudiar') : null],
    ['ruta2', casos.some(k => k.tipo === 'ok') ? elegir('ok') : null],
    ['ruta3', casos.some(k => k.tipo === 'falla') ? elegir('falla') : null],
    ['ruta4', () => pestana('comparar')],
    ['ruta5', () => { const r = $('#resDet'); if (r) { r.open = true; r.scrollIntoView({behavior: SUAVE()}); } else pestana('salida'); }],
  ];
  $('#rutaTitulo').textContent = `${t('rutaTitulo')} · ${hechos.length}/${pasos.length}`;
  $('#rutaPasos').innerHTML = pasos.map(([k, f], i) => `<div class="paso-ruta ${hechos.includes(i) ? 'hecho' : ''}">
    <label><input type="checkbox" data-r="${i}" ${hechos.includes(i) ? 'checked' : ''}><span>${t(k)}</span></label>
    ${f ? `<button class="sec mini" data-ir="${i}" aria-label="${t('rutaIr')}: ${esc(t(k))}">${t('rutaIr')}</button>` : ''}</div>`).join('');
  $('#rutaPasos').querySelectorAll('[data-r]').forEach(c => c.onchange = () => {
    const i = +c.dataset.r; hechos = c.checked ? [...new Set([...hechos, i])] : hechos.filter(x => x !== i);
    guardar(clave, JSON.stringify(hechos)); pintarRuta(d);
  });
  $('#rutaPasos').querySelectorAll('[data-ir]').forEach(b => b.onclick = () => pasos[+b.dataset.ir][1]());
}
// ---- Costo estimado antes de correr ----
function pintarEstimado(d){
  const e = d.estimado, m = $('#modelo').value;
  if (!e || !e.precios[m]) { $('#estimado').textContent = ''; return; }
  const [pin, pout] = e.precios[m], costo = e.entrada / 1e6 * pin + e.salida / 1e6 * pout;
  $('#estimado').textContent = `≈ $${costo.toFixed(4)} USD ${t('estimadoTxt')} ${e.llamadas} ${t('estimadoLlamadas')}`;
}
$('#modelo').addEventListener('change', () => { if (LAB) pintarEstimado(demoActual()); llenarModelo2(); });
function llenarModelo2(){
  const actual = $('#modelo').value, previo = $('#modelo2').value;
  $('#modelo2').innerHTML = MODELOS.filter(m => m !== actual).map(m => `<option ${m === previo ? 'selected' : ''}>${m}</option>`).join('');
}
// ---- Correr con dos modelos y comparar ----
$('#dosModelos').onclick = async () => {
  const a = $('#modelo').value, b = $('#modelo2').value;
  if (!b || a === b) { alertaEstado(t('dosIguales')); return; }
  if (ENTORNO && (!ENTORNO.key || ENTORNO.faltan_basicas.length)) { mostrarAyudaKey(true); return; }
  const recargado = await revisarArchivo();
  // Si una corrida no arranca o no termina bien, no se lanza la segunda (y no queda nada pendiente)
  let {promise: fin, resolve} = Promise.withResolvers(); ESPERANDO = resolve;
  if (!(await lanzar(recargado, {MODELO: a}))) { ESPERANDO = null; return; }
  const ra = await fin;
  if (!ra || ra.codigo !== 0) return;
  ({promise: fin, resolve} = Promise.withResolvers()); ESPERANDO = resolve;
  if (!(await lanzar(false, {MODELO: b}))) { ESPERANDO = null; return; }
  AVISO = t('dosCorriendo') + ' ' + AVISO;
  const rb = await fin;
  if (rb && rb.codigo === 0) pestana('comparar');
};
// ---- Salida básica / completa (se recuerda; por defecto básica) ----
$('#detalle').value = guardado('detalle') || 'basico';
$('#detalle').onchange = () => guardar('detalle', $('#detalle').value);
// ---- Tema claro / oscuro: sigue al sistema; el botón fija el contrario o regresa al del sistema ----
function pintarTema(){
  $('#tema').textContent = esquemaVisible() === 'dark' ? '☀' : '☾';
  try { ponerEsquema($('#vista').contentDocument); } catch (e) {}
}
$('#tema').onclick = () => { alternarEsquema(); pintarTema(); };
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', pintarTema);
addEventListener('storage', e => { if (e.key === 'ccarf_esquema') { ponerEsquema(document); pintarTema(); } });
pintarTema();
// ---- Recorrido de primera vez ----
const TOUR = [['#demo', 'tour1'], ['#ruta', 'tour2'], ['#tabEstudiar', 'tour3'], ['#casosBox', 'tour4'], ['#correr', 'tour5'], ['#tabComparar', 'tour6'], ['#abrirRecursos', 'tour7']];
let TOUR_I = 0;
function iniciarTour(enfocar){ TOUR_I = 0; if (!$('#tour').matches(':popover-open')) $('#tour').showPopover(); pasoTour(enfocar); }
function terminarTour(){
  if ($('#tour').matches(':popover-open')) $('#tour').hidePopover();
  const antes = $('.resaltado-tour');
  document.querySelectorAll('.resaltado-tour').forEach(e => e.classList.remove('resaltado-tour')); guardar('tour', '1');
  if (antes && document.activeElement === document.body) antes.focus?.();
}
function pasoTour(enfocar){
  document.querySelectorAll('.resaltado-tour').forEach(e => e.classList.remove('resaltado-tour'));
  while (TOUR_I < TOUR.length) { const el = $(TOUR[TOUR_I][0]); if (el && el.offsetParent !== null) break; TOUR_I++; }
  if (TOUR_I >= TOUR.length) { terminarTour(); return; }
  const [sel, k] = TOUR[TOUR_I], el = $(sel);
  el.classList.add('resaltado-tour'); el.scrollIntoView({block: 'nearest'});
  $('#tourPaso').textContent = `${TOUR_I + 1} / ${TOUR.length}`; $('#tourTexto').textContent = t(k);
  $('#tourSig').textContent = TOUR_I === TOUR.length - 1 ? t('tourFin') : t('tourSig');
  if (enfocar) $('#tourSig').focus();
}
$('#tourSig').onclick = () => { TOUR_I++; pasoTour(true); };
$('#tourSaltar').onclick = terminarTour;
$('#tourBtn').onclick = () => iniciarTour(true);

$('#dominio').onchange = () => cargarLab();
$('#demo').onchange = async () => { if (!(await revisarArchivo())) pintarDemo(); };
$('#restaurar').onclick = async () => {
  await revisarArchivo(); $('#modelo').value = LAB.modelo; llenarModelo2(); pintarDemo();
};
$('#correr').onclick = correr;
$('#detener').onclick = () => {
  ESPERANDO = null;   // detener también cancela la segunda corrida de "dos modelos"
  if (REPRODUCIENDO) { REPRODUCIENDO.cancelado = true; REPRODUCIENDO = null; ocupado(false); alertaEstado(t('inicio')); }
  else api('/api/detener', {id: TRABAJO});
};
$('#tabSalida').onclick = () => pestana('salida');
$('#tabEstudiar').onclick = () => pestana('estudiar');
$('#tabVista').onclick = () => pestana('vista');
$('#tabComparar').onclick = () => pestana('comparar');
$('#tabMaterial').onclick = () => { VISOR.tema = true; pestana('material'); };
$('#matSel').onchange = e => { const [n, k] = e.target.value.split('|'); VISOR = {n, k, tema: true}; pintarVisor(); };
$('#matTema').onclick = () => { VISOR.tema = true; pintarVisor(true); };
$('#vista').onload = () => {   // al abrir el resultado, ir directo al primer diagrama
  aplicarEscala();
  try {
    const doc = $('#vista').contentDocument;
    ponerEsquema(doc);
    if (!doc.location.pathname.startsWith('/comparar')) { const d = doc.querySelector('.diagrama'); if (d) d.scrollIntoView({block: 'start'}); }
  } catch (e) {}
};

// ---- Recursos: panel lateral con documentación, ejemplos, corridas, código y material en línea ----
async function pintarRecursos(){
  const r = await api('/api/recursos');
  const item = (href, titulo, sub) => `<a class="item" href="${href}" target="_blank">${titulo}${sub ? `<small>${esc(sub)}</small>` : ''}</a>`;
  const chips = (lista, f) => `<div class="fila">${lista.map(f).join('')}</div>`;
  const dom = n => `${t('dominioN')} ${n}`;
  let h = `<h3>${t('recEstudiar')}</h3>`
       + item('/repaso', t('recRepaso'), t('recRepasoSub')) + item('/escenarios', t('recEscenarios'), t('recEscenariosSub'))
       + item('/antipatrones', t('recAntipatrones'), t('recAntipatronesSub')) + item('/glosario', t('recGlosario'), t('recGlosarioSub'));
  h += `<h3>${t('recDocs')}</h3>` + r.documentos.map(d => item('/doc/' + d.nombre, d.nombre, d.texto)).join('');
  h += `<h3>${t('recDominios')}</h3>` + chips([1, 2, 3, 4, 5], n => `<a href="/dominio?n=${n}" target="_blank">${dom(n)}</a>`);
  h += `<h3>${t('recEjemplos')}</h3>` + (r.ejemplos.length
       ? item(`/archivos/${r.carpeta_ejemplos || 'ejemplos_html'}/index.html`, t('recEjemplosTodos'), t('recEjemplosSub'))
         + chips(r.ejemplos, n => `<a href="/archivos/${r.carpeta_ejemplos || 'ejemplos_html'}/dominio${n}/index.html" target="_blank">${dom(n)}</a>`)
       : `<p class="rec-nota">${t('recSinEjemplos')}</p>`);
  h += `<h3>${t('recCorridas')}</h3>` + (r.corridas.length
       ? item('/archivos/salidas_html/index.html', t('recCorridasTodas'), t('recCorridasSub'))
         + chips(r.corridas, n => `<a href="/archivos/salidas_html/dominio${n}/index.html" target="_blank">${dom(n)}</a>`)
       : `<p class="rec-nota">${t('recSinCorridas')}</p>`);
  h += `<h3>${t('recCodigo')}</h3>` + chips(r.labs, n => `<a href="/codigo?n=${n}" target="_blank">lab_dominio${n}.py</a>`);
  h += `<h3>${t('recConfig')}</h3>` + r.textos.map(d => item('/doc/' + d.nombre, d.nombre, d.texto)).join('');
  h += `<h3>${t('recMaterial')}</h3>` + (Object.keys(r.material).length
       ? `<p class="rec-nota">${t('recMaterialNota')}</p>` : `<p class="rec-nota">${t('recSinMaterial')}</p>`);
  for (const [n, m] of Object.entries(r.material)) {
    const lista = [];
    for (const [k, tk] of [['slides', 'slides'], ['guia_estudio', 'guiaEst']])
      for (const [idioma, u] of Object.entries(m[k] || {}).sort((x, y) => (x[0] === IDIOMA ? -1 : y[0] === IDIOMA ? 1 : 0)))
        lista.push(u.startsWith('http') ? `<a href="${u}" target="_blank">${t(tk)} · ${idioma.toUpperCase()} ↗</a>`
                   : `<a href="${u}" data-visor-n="${n}" data-visor-k="${k}">${t(tk)} · ${idioma.toUpperCase()}</a>`);
    h += `<div class="dom">${dom(n)}</div><div class="fila">${lista.join('')}</div>`;
  }
  $('#recursosLista').innerHTML = h;
  $('#recursosLista').querySelectorAll('[data-visor-n]').forEach(a => a.onclick = ev => {
    ev.preventDefault(); abrirRecursos(false); abrirMaterial(a.dataset.visorN, a.dataset.visorK); });
}
function abrirRecursos(si){
  const d = $('#recursos');
  if (si) { if (!d.open) d.showModal(); pintarRecursos(); } else if (d.open) d.close();
}
$('#abrirRecursos').onclick = () => abrirRecursos(true);
$('#cerrarRecursos').onclick = () => abrirRecursos(false);
// Cerrar al hacer clic fuera: closedby="any"; donde el navegador aún no lo soporta (Safari), se hace aquí
if (!('closedBy' in HTMLDialogElement.prototype)) {
  const fuera = (e, d) => { const r = d.getBoundingClientRect(); return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom; };
  for (const d of document.querySelectorAll('dialog[closedby="any"]')) {
    let afuera = false;
    d.addEventListener('pointerdown', e => { afuera = fuera(e, d); });
    d.addEventListener('pointerup', e => { if (afuera && fuera(e, d)) d.close(); });
  }
}

// ---- Buscador (Ctrl+K) ----
let RESULTADOS = [], SEL = 0, TEMPORIZADOR = null;
function abrirBuscar(si){
  const d = $('#buscador');
  if (si) { $('#q').value = ''; $('#resBusca').replaceChildren(); RESULTADOS = []; if (!d.open) d.showModal(); }
  else if (d.open) d.close();
}
$('#abrirBuscar').onclick = () => abrirBuscar(true);
$('#q').oninput = () => { clearTimeout(TEMPORIZADOR); TEMPORIZADOR = setTimeout(async () => {
  const q = $('#q').value.trim();
  if (!q) { $('#resBusca').replaceChildren(); RESULTADOS = []; return; }
  RESULTADOS = (await api('/api/buscar?q=' + encodeURIComponent(q))).resultados; SEL = 0; pintarBusqueda();
}, 150); };
function pintarBusqueda(){
  $('#resBusca').innerHTML = RESULTADOS.length ? RESULTADOS.map((r, i) =>
    `<div class="res ${i === SEL ? 'sel' : ''}" data-i="${i}"><div class="tipo">${esc(r.tipo)}</div><div class="tit">${esc(r.titulo)}</div><div class="txt">${esc(r.texto)}</div></div>`).join('')
    : `<div class="res"><div class="txt">${t('sinResultados')}</div></div>`;
  $('#resBusca').querySelectorAll('.res[data-i]').forEach(el => el.onclick = () => abrirResultado(+el.dataset.i));
  const sel = $('#resBusca .sel'); if (sel) sel.scrollIntoView({block: 'nearest'});
}
async function abrirResultado(i){
  const r = RESULTADOS[i]; if (!r) return;
  if (r.demo) {
    abrirBuscar(false);
    if ($('#dominio').value !== String(r.demo[0])) { $('#dominio').value = r.demo[0]; await cargarLab(r.demo[1]); }
    else { $('#demo').value = r.demo[1]; pintarDemo(); }
    $('#guiaBox').open = true;
  } else if (r.url) window.open(r.url, '_blank');
}
$('#q').onkeydown = e => {
  if (e.key === 'ArrowDown') { SEL = Math.min(RESULTADOS.length - 1, SEL + 1); pintarBusqueda(); e.preventDefault(); }
  else if (e.key === 'ArrowUp') { SEL = Math.max(0, SEL - 1); pintarBusqueda(); e.preventDefault(); }
  else if (e.key === 'Enter') abrirResultado(SEL);
};
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); abrirBuscar(true); }
});
iniciar();

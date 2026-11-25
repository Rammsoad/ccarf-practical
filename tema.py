"""
tema.py · Colores, letras y tema claro/oscuro compartidos por el panel y las páginas de estudio.

- Por defecto se sigue el tema del sistema (claro u oscuro).
- El botón ☀/☾ guarda una preferencia en localStorage ('ccarf_esquema') y la aplica con <meta name="color-scheme">.
- Los colores usan light-dark(), así que cambian solos con el tema.
"""

# Letras locales (material/fuentes/, licencia OFL): nada se pide a Google Fonts. Si no cargan (por ejemplo al abrir
# una página suelta con doble clic en algunos navegadores), se usan las del sistema.
FUENTES = [   # (familia, estilo, peso, archivo en material/fuentes/, unicode-range)
    ('Atkinson Hyperlegible Next', 'italic', '400', 'atkinson-hyperlegible-next-italic-latin-ext.woff2',
     'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF'),
    ('Atkinson Hyperlegible Next', 'italic', '400', 'atkinson-hyperlegible-next-italic-latin.woff2',
     'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD'),
    ('Atkinson Hyperlegible Next', 'normal', '400 700', 'atkinson-hyperlegible-next-normal-latin-ext.woff2',
     'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF'),
    ('Atkinson Hyperlegible Next', 'normal', '400 700', 'atkinson-hyperlegible-next-normal-latin.woff2',
     'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD'),
    ('Recursive', 'normal', '400 700', 'recursive-normal-latin-ext.woff2',
     'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF'),
    ('Recursive', 'normal', '400 700', 'recursive-normal-latin.woff2',
     'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD'),
]


def fuentes_css(base: str) -> str:
    """@font-face de las letras locales; base = ruta (relativa a la página o absoluta) de material/fuentes/."""
    return "".join(f"@font-face{{font-family:'{familia}';font-style:{estilo};font-weight:{peso};font-display:swap;"
                   f"src:url('{base}{archivo}') format('woff2');unicode-range:{rango}}}"
                   for familia, estilo, peso, archivo, rango in FUENTES)


def cabeza(base: str = "/archivos/material/fuentes/") -> str:
    """Lo que va dentro de <head>. El panel usa la ruta absoluta; las páginas sueltas, una relativa."""
    return CABEZA_BASE + "\n<style>" + fuentes_css(base) + "</style>"


# Va dentro de <head>: tema antes de pintar (sin parpadeo), letras y escala del sistema.
CABEZA_BASE = """<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="text-scale" content="scale">
<meta name="color-scheme" content="light dark">
<meta name="referrer" content="no-referrer">
<script>try{document.querySelector('meta[name="color-scheme"]').content=localStorage.getItem('ccarf_esquema')||'light dark'}catch(e){}</script>
"""
CABEZA = cabeza()   # para las páginas que sirve el panel

TOKENS = """
:root{
  color-scheme:light dark;
  &:has(> head > meta[name="color-scheme"][content="dark"]){color-scheme:dark}
  &:has(> head > meta[name="color-scheme"][content="light"]){color-scheme:light}

  /* Superficies: grafito azulado en oscuro, gris frío en claro */
  --fondo:light-dark(#f4f5f7,#14161b);
  --superficie:light-dark(#ffffff,#1b1e25);
  --superficie-2:light-dark(#eceef2,#232730);
  --borde:light-dark(#d3d7de,#323744);
  --borde-suave:light-dark(#e3e6eb,#262a34);
  --texto:light-dark(#1a1c22,#ebe8e2);
  --texto-2:light-dark(#545966,#a6a9b3);
  --texto-3:light-dark(#62676f,#9a9ea9);
  --borde-control:light-dark(#959ba6,#5c6271);

  /* Acento: rosa mexicano (La Tiendita) */
  --acento:light-dark(#c4006a,#ff5aa8);
  --acento-suave:light-dark(#fde7f2,#3a1a2b);
  --sobre-acento:light-dark(#ffffff,#24000f);
  --enlace:light-dark(#a3005a,#ff8cc6);

  /* Significado: solo para ✅ / ❌ 🎓 trampa / 🔧 producto */
  --bien:light-dark(#17724a,#5fd39c);
  --bien-suave:light-dark(#e3f4ec,#173226);
  --trampa:light-dark(#b3311b,#ff7d68);
  --trampa-suave:light-dark(#fbe9e5,#3a1d19);
  --producto:light-dark(#835600,#f0bf4c);
  --producto-suave:light-dark(#fbf1d9,#352b14);

  --tinta:light-dark(#2f5d8f,#8fb5e6);
  --codigo-fondo:light-dark(#eceef2,#262a33);
  --resaltado:light-dark(#fff0bf,#3b3420);
  --terminal:#0f1115;
  --terminal-texto:#d9d9d9;
  --velo:rgb(10 12 16 / .5);

  --letra:'Atkinson Hyperlegible Next',system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;
  --mono:'Recursive',ui-monospace,Menlo,Consolas,'DejaVu Sans Mono',monospace;

  accent-color:var(--acento);
  scrollbar-color:var(--texto-3) transparent;
}
body{font-family:var(--letra);font-size-adjust:from-font}
code,pre,kbd,samp,textarea{font-family:var(--mono)}
:focus-visible{outline:2px solid var(--acento);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition-duration:.01ms !important;animation-duration:.01ms !important;scroll-behavior:auto !important}}
"""

# JS del botón ☀/☾: dos estados (lo del sistema, o lo contrario fijado).
JS_TEMA = """
function esquemaSistema(){ return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; }
function esquemaGuardado(){ try { return localStorage.getItem('ccarf_esquema'); } catch (e) { return null; } }
function esquemaVisible(){ return esquemaGuardado() || esquemaSistema(); }
function ponerEsquema(doc){ const m = doc.querySelector('meta[name="color-scheme"]'); if (m) m.content = esquemaGuardado() || 'light dark'; }
function alternarEsquema(){
  const destino = esquemaVisible() === 'dark' ? 'light' : 'dark';
  try { destino === esquemaSistema() ? localStorage.removeItem('ccarf_esquema') : localStorage.setItem('ccarf_esquema', destino); } catch (e) {}
  ponerEsquema(document);
}
"""

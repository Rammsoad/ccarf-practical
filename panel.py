"""
panel.py · Panel web local para correr los labs del CCAR-F
==========================================================

Uso (desde la carpeta de los labs, con tu entorno virtual activado):

    python panel.py

Abre http://127.0.0.1:8765 en tu navegador. Ahí eliges dominio y demo, ajustas sus variables 🔧 con
controles (casillas, listas, campos) y le das Correr. La salida aparece en vivo y al terminar se muestra
la página de la corrida con su diagrama.

También tiene: casos rápidos, costo por corrida, comparar dos corridas,
grabaciones para ver sin API key (carpeta grabaciones/), buscador (Ctrl+K), página por dominio,
slides y guías de estudio de la carpeta material/, tamaño de letra e interfaz en español o inglés.
Los textos de casos, lo esperado de cada caso y el glosario están en extras.py.

- Corre en TU computadora (127.0.0.1): nadie más puede abrirlo. Usa tu API key del archivo .env.
- Los ajustes del panel aplican solo a esa corrida: no cambian los valores escritos en los labs.
- Cada corrida se guarda en salidas_html/dominioN/, igual que desde la terminal.
- Para cerrarlo: Ctrl+C en la terminal donde lo abriste.
- Si el puerto 8765 está ocupado:  python panel.py 8780
- Solo sirve archivos de salidas_html/, ejemplos_html/, grabaciones/ y material/, más el README, la guía y el
  código de los labs (solo lectura). Nunca el .env.
"""
from __future__ import annotations

import html
import importlib
import json
import os
import re
import importlib.util
import signal
import subprocess
import sys
import tempfile
import unicodedata
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import idioma
import paginas
import tema
from extras import CLASES, EXTRAS, GLOSARIO, GLOSARIO_BASICO, PRODUCTO, escenarios_de, marcar_glosario
from idioma import L, tr
from visual import ZOOM_HTML

CARPETA = Path(__file__).resolve().parent
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8765
MODELOS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]
TRABAJOS: dict[str, dict] = {}

# Material de estudio como ARCHIVOS dentro de la carpeta material/ (se comparten junto con los labs).
# El panel muestra el del idioma elegido con el botón ES / EN; si falta, el del otro idioma.
#   Español:  material/D1_slides.pdf      material/D1_guia_estudio.pdf
#   Inglés:   material/D1_slides_en.pdf   material/D1_study_guide_en.pdf
# (los slides también pueden ser .pptx). Un archivo en material/ tiene prioridad sobre el link de abajo.
MATERIAL = CARPETA / "material"
ARCHIVOS_MATERIAL = {
    "slides": {"es": ["slides.pdf", "slides.pptx"], "en": ["slides_en.pdf", "slides_en.pptx"]},
    "guia_estudio": {"es": ["guia_estudio.pdf"], "en": ["study_guide_en.pdf"]},
}
# Slides en línea: los decks en claude.ai. Solo se usan si falta el PDF en material/ (claude.ai no deja
# mostrarlos dentro del panel, así que se abren en otra pestaña). Son privados hasta que los compartes:
# para que los alumnos los abran, compártelos con link desde claude.ai (Share).
MATERIAL_EN_LINEA: dict[int, dict[str, dict[str, str]]] = {
    1: {"slides": {"es": "https://claude.ai/artifact/4DqCitr7oXYedTZrBPok8q",
                   "en": "https://claude.ai/artifact/JKYfpaUVcACUt8CnYVS2gb"}},
    2: {"slides": {"es": "https://claude.ai/artifact/AJ8AixyW2QP6aLWBpAx5x8",
                   "en": "https://claude.ai/artifact/8LqXBNkAtsVhsr5oYn7vTe"}},
    3: {"slides": {"es": "https://claude.ai/artifact/FXA4FDyzcFi7C9bstj8F4M",
                   "en": "https://claude.ai/artifact/LJ7gaSzfjhKZXiv4iLpLvr"}},
    4: {"slides": {"es": "https://claude.ai/artifact/6bp8R4gYqjsKKtkETrvm64",
                   "en": "https://claude.ai/artifact/Tp1QM7Uf1eLvFCyoN5Yuhm"}},
    5: {"slides": {"es": "https://claude.ai/artifact/GcL8xHhWqvUn3Tt7utpZeA",
                   "en": "https://claude.ai/artifact/NEsMeFGBbXhsqJmsL67kfZ"}},
}
ETIQUETAS_MATERIAL = {"slides": "Slides", "guia_estudio": "Guía de estudio"}   # se traducen con tr()


def material_dominio(n: int) -> dict[str, dict[str, str]]:
    """{"slides": {"es": url, "en": url}, "guia_estudio": {"es": url}}: solo lo que existe."""
    salida: dict[str, dict[str, str]] = {}
    for clave, idiomas in ARCHIVOS_MATERIAL.items():
        for lengua, sufijos in idiomas.items():
            for sufijo in sufijos:
                if (MATERIAL / f"D{n}_{sufijo}").exists():
                    salida.setdefault(clave, {})[lengua] = f"/archivos/material/D{n}_{sufijo}"
                    break
    for clave, idiomas in MATERIAL_EN_LINEA.get(n, {}).items():
        for lengua, url in idiomas.items():
            salida.setdefault(clave, {}).setdefault(lengua, url)
    return salida


def botones_material(n: int) -> str:
    """Botones de la página del dominio: uno por archivo y por idioma."""
    h = []
    for clave, idiomas in material_dominio(n).items():
        for lengua, url in sorted(idiomas.items(), key=lambda kv: kv[0] != idioma.actual()):
            h.append(f"<a class='boton' href='{url}' target='_blank'>{tr(ETIQUETAS_MATERIAL[clave])} ({lengua.upper()})"
                     f"{' ↗' if url.startswith('http') else ''}</a>")
    return "".join(h)


# Archivos de la carpeta que el panel puede MOSTRAR (solo lectura). Nunca el .env con tu API key.
DOCUMENTOS = {"README.md": "Cómo empezar: instalar, sacar tu key y estudiar con el panel",
              "GUIA_LABS.md": "Guía de todas las demos: qué hace cada una y qué esperar",
              "NOTAS_INSTRUCTOR.md": "Para quien da el curso (aparece solo si el archivo está en la carpeta)",
              "README_en.md": "README en inglés", "GUIA_LABS_en.md": "GUIA_LABS en inglés"}
EN_INGLES = {"README.md": "README_en.md", "GUIA_LABS.md": "GUIA_LABS_en.md"}   # con el panel en inglés se muestra este


def doc_idioma(nombre: str) -> str:
    """El documento en el idioma del panel, si existe esa versión."""
    otro = EN_INGLES.get(nombre)
    return otro if idioma.en() and otro and (CARPETA / otro).exists() else nombre
TEXTOS = {"comun.py": "Ayudantes que comparten los labs (llamar_claude, correr_agente, costos…), solo lectura",
          "requirements.txt": "Librerías que instala pip", ".env.example": "Plantilla del archivo .env (sin tu key)"}
CANDADO = threading.Lock()


# ---------------------------------------------------------------------
#  Leer los labs: demos, guías y variables 🔧 de cada demo
# ---------------------------------------------------------------------

def labs_disponibles() -> dict[int, Path]:
    """Labs que ya aceptan ajustes del panel (los que llaman a visual.aplicar_ajustes)."""
    labs = {}
    for n in range(1, 6):
        ruta = CARPETA / f"lab_dominio{n}.py"
        if ruta.exists() and "aplicar_ajustes" in ruta.read_text(encoding="utf-8"):
            labs[n] = ruta
    return labs


_CACHE: dict[int, dict] = {}


CANDADO_LABS = threading.RLock()


def info_lab(n: int) -> dict:
    """Importa el lab (sin correr nada) y arma la lista de demos, guías y variables.
    Si el archivo del lab cambió en disco (editaste una variable), lo vuelve a leer."""
    with CANDADO_LABS:
        return _info_lab(n)


def _info_lab(n: int) -> dict:
    version = (CARPETA / f"lab_dominio{n}.py").stat().st_mtime
    if n in _CACHE and _CACHE[n]["version"] == version:
        return _CACHE[n]
    argv = sys.argv[:]
    sys.argv = [f"lab_dominio{n}.py", "--sin-html"]
    if str(CARPETA) not in sys.path:
        sys.path.insert(0, str(CARPETA))
    try:
        nombre_modulo = f"lab_dominio{n}"
        if nombre_modulo in sys.modules:
            modulo = importlib.reload(sys.modules[nombre_modulo])
        else:
            modulo = importlib.import_module(nombre_modulo)
    finally:
        sys.argv = argv
    fuente = (CARPETA / f"lab_dominio{n}.py").read_text(encoding="utf-8").split("\n")
    demos = []
    for clave, (nombre, _) in modulo.DEMOS.items():
        prefijo = "D" + clave.replace(".", "") + "_"
        variables = []
        for var, valor in vars(modulo).items():
            if var.startswith(prefijo) and isinstance(valor, (str, int, float, bool, list)):
                variables.append(describir_variable(var, valor, fuente, getattr(modulo, "MODELO", "")))
        demos.append({"clave": clave, "nombre": nombre, "guia": guia_html(modulo.GUIAS.get(clave, "")),
                      "guia_md": modulo.GUIAS.get(clave, ""), "variables": variables})
    _CACHE[n] = {"dominio": n, "modelo": getattr(modulo, "MODELO", MODELOS[0]), "demos": demos, "version": version}
    return _CACHE[n]


def comentario_en_linea(linea: str) -> str:
    """El comentario al final de una línea de código, ignorando los # dentro de textos ("pedido #12345")."""
    comillas = None
    for i, c in enumerate(linea):
        if c in "\"'" and (comillas is None or comillas == c):
            comillas = None if comillas else c
        elif c == "#" and comillas is None:
            return linea[i + 1:].strip()
    return ""


def describir_variable(nombre: str, valor, fuente: list[str], modelo: str) -> dict:
    """Tipo de control y ayuda, a partir del valor y de los comentarios que la rodean en el lab."""
    linea = next((i for i, l in enumerate(fuente) if re.match(rf"{nombre}\s*=", l)), None)
    comentarios, candidatas = [], []
    if linea is not None:
        en_linea = comentario_en_linea(fuente[linea])
        if en_linea:
            comentarios.append(en_linea)
            candidatas += re.findall(r'"([^"\s]{1,40})"', en_linea)       # comentario en la misma línea
        i = linea - 1
        previos = []
        while i >= 0 and fuente[i].lstrip().startswith("#") and "CAMBIA AQUÍ" not in fuente[i] and "=====" not in fuente[i]:
            texto = fuente[i].lstrip("# ").rstrip()
            previos.insert(0, texto)
            m = re.match(r'^"([^"\s]{1,40})"\s*(->|:|\()', texto)          # líneas tipo  "amplia" -> ...
            if m:
                candidatas.insert(0, m.group(1))
            i -= 1
        comentarios = previos + comentarios
    ayuda = " · ".join(c for c in comentarios if c)
    if isinstance(valor, bool):
        tipo, opciones = "bool", []
    elif isinstance(valor, (int, float)):
        tipo, opciones = "numero", []
    elif isinstance(valor, list):
        tipo, opciones = "json", []
    else:
        opciones = []
        if " " not in valor and len(valor) <= 40:
            for o in candidatas:
                if o not in opciones:
                    opciones.append(o)
            if nombre.endswith("MODELO_B") or valor.startswith("claude-"):
                opciones += [m for m in MODELOS if m not in opciones]
            if valor not in opciones:
                opciones.insert(0, valor)
        tipo = "opciones" if len(opciones) >= 2 else ("texto_largo" if len(valor) > 60 else "texto")
    return {"nombre": nombre, "valor": valor, "tipo": tipo, "opciones": opciones, "ayuda": ayuda}


def es_cerca(linea: str) -> bool:
    """¿La línea abre o cierra un bloque de código? (``` solo, o con lenguaje: ```json). No cuenta ``` en línea."""
    return re.fullmatch(r"`{3,}[\w+-]*", linea.strip()) is not None


def guia_html(texto: str) -> str:
    """Convierte el markdown sencillo de las guías del lab a HTML."""
    salida, en_codigo, en_lista, previa = [], False, False, ""
    def linea_inline(t: str) -> str:
        t = html.escape(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", t)
        return t
    for l in texto.strip("\n").split("\n"):
        anterior, previa = previa, l
        if es_cerca(l):
            salida.append("</pre>" if en_codigo else "<pre>")
            en_codigo = not en_codigo
            continue
        if en_codigo:
            salida.append(html.escape(l))
            continue
        es_lista = re.match(r"^\s*(-|\d+\.)\s+", l)
        if en_lista and not es_lista and not l.startswith("   "):
            salida.append(f"</{en_lista}>")
            en_lista = False
        if l.startswith("####"):
            salida.append(f"<h4>{linea_inline(l.lstrip('# '))}</h4>")
        elif es_lista:
            if not en_lista:
                en_lista = "ol" if es_lista.group(1)[0].isdigit() else "ul"
                salida.append(f"<{en_lista}>")
            contenido = re.sub(r"^\s*(-|\d+\.)\s+", "", l)
            salida.append(f"<li>{linea_inline(contenido)}</li>")
        elif l.startswith("|"):
            salida.append(f"<div class='tabla'>{linea_inline(l)}</div>")
        elif l.strip() and en_lista and l.startswith("   ") and salida[-1].startswith("<li>"):
            salida[-1] = salida[-1][:-5] + " " + linea_inline(l.strip()) + "</li>"   # sigue el punto de la lista
        elif l.strip():
            if salida and salida[-1].startswith("<p>") and anterior.strip() and not en_lista:
                salida[-1] = salida[-1][:-4] + " " + linea_inline(l.strip()) + "</p>"   # mismo párrafo
            else:
                salida.append(f"<p>{linea_inline(l.strip())}</p>")
    if en_lista:
        salida.append(f"</{en_lista}>")
    return "\n".join(salida)


def ancla_de(titulo: str, demo: str | None = None) -> str:
    """El id que recibe un título de markdown (para enlazar directo a una sección).
    Dentro de una demo se antepone la demo, para que "De qué trata" no se repita en las 30."""
    base = re.sub(r"[^a-z0-9áéíóúñ]+", "-", titulo.lower()).strip("-")
    return f"demo-{demo.replace('.', '-')}--{base}" if demo else base


def demo_de_titulo(titulo: str) -> str | None:
    m = re.match(r"Demo (\d+\.\d+)\b", titulo)
    return m.group(1) if m else None


def md_a_html(texto: str) -> str:
    """Markdown sencillo (títulos, listas, tablas, código, enlaces) a HTML, para README y GUIA_LABS."""
    def inline(t: str) -> str:
        t = html.escape(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
        t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" target="_blank">\1</a>', t)
        return t
    salida, en_codigo, lista, tabla, parrafo = [], False, None, [], []
    demo_actual = None
    def cerrar_parrafo():
        if parrafo:
            salida.append(f"<p>{inline(' '.join(parrafo))}</p>")
            parrafo.clear()
    def cerrar_lista():
        nonlocal lista
        if lista:
            salida.append(f"</{lista}>")
            lista = None
    def cerrar_tabla():
        if not tabla:
            return
        filas = [f for f in tabla if not re.match(r"^\|?[\s:|-]+\|?$", f)]
        partes = ["<table>"]
        for i, f in enumerate(filas):
            celdas = [c.strip() for c in f.strip().strip("|").split("|")]
            etiqueta = "th" if i == 0 else "td"
            partes.append("<tr>" + "".join(f"<{etiqueta}>{inline(c)}</{etiqueta}>" for c in celdas) + "</tr>")
        partes.append("</table>")
        salida.append("".join(partes))
        tabla.clear()
    for linea in texto.split("\n"):
        if es_cerca(linea):
            cerrar_parrafo(); cerrar_lista(); cerrar_tabla()
            salida.append("</code></pre>" if en_codigo else "<pre><code>")
            en_codigo = not en_codigo
            continue
        if en_codigo:
            salida.append(html.escape(linea))
            continue
        if linea.startswith("|"):
            cerrar_parrafo(); cerrar_lista()
            tabla.append(linea)
            continue
        cerrar_tabla()
        m_titulo = re.match(r"^(#{1,6})\s+(.*)", linea)
        m_lista = re.match(r"^\s*([-*]|\d+\.)\s+(.*)", linea)
        if m_titulo:
            cerrar_parrafo(); cerrar_lista()
            nivel = len(m_titulo.group(1))
            if nivel <= 2:
                demo_actual = demo_de_titulo(m_titulo.group(2))
            ancla = ancla_de(m_titulo.group(2), demo_actual if nivel > 2 else None)
            salida.append(f'<h{nivel} id="{ancla}">{inline(m_titulo.group(2))}</h{nivel}>')
        elif m_lista:
            cerrar_parrafo()
            tipo = "ol" if m_lista.group(1)[0].isdigit() else "ul"
            if lista != tipo:
                cerrar_lista()
                salida.append(f"<{tipo}>")
                lista = tipo
            salida.append(f"<li>{inline(m_lista.group(2))}</li>")
        elif linea.strip():
            if lista and linea.startswith("  "):
                salida[-1] = salida[-1][:-5] + " " + inline(linea.strip()) + "</li>"
            else:
                cerrar_lista()
                parrafo.append(linea.strip())
        else:
            cerrar_parrafo(); cerrar_lista()
    cerrar_parrafo(); cerrar_lista(); cerrar_tabla()
    return "\n".join(salida)


ESTILO_DOC = """
*{box-sizing:border-box}
body{margin:0 auto;max-width:54rem;padding:2rem 1.75rem 5.5rem;background:var(--fondo);color:var(--texto);font-size:1.0625rem;line-height:1.65}
body.ancho{max-width:78rem}
a{color:var(--enlace)} p,li{max-width:74ch}
h1,h2,h3,h4{line-height:1.3;margin:1.8em 0 .5em} h1{font-size:1.85rem;margin-top:0}
h2{font-size:1.5rem;padding-bottom:.35rem;border-bottom:1px solid var(--borde)} h3{font-size:1.25rem} h4{font-size:1.1rem;color:var(--acento)}
li{margin:.3em 0} ul,ol{padding-left:1.5em}
code{background:var(--codigo-fondo);padding:.1em .35em;border-radius:.3em;font-size:.88em}
pre{background:var(--superficie);border:1px solid var(--borde);border-radius:.6rem;padding:.9rem 1rem;overflow-x:auto;font-size:.875rem;line-height:1.55}
pre code{background:none;padding:0;font-size:inherit}
table{border-collapse:collapse;margin:1rem 0;font-size:.94rem;display:block;overflow-x:auto;max-width:100%}
th,td{border:1px solid var(--borde);padding:.5rem .75rem;vertical-align:top;text-align:left}
th{background:var(--superficie-2);position:sticky;top:0} tr:nth-child(even) td{background:var(--superficie)}
.volver{font-size:.875rem;color:var(--texto-3);margin-bottom:1.25rem}
.linea{color:var(--texto-3);user-select:none;display:inline-block;width:4.5em;text-align:right;margin-right:1em}
.resaltada{background:var(--resaltado)}
abbr.termino{text-decoration:underline dotted var(--tinta);text-underline-offset:3px;cursor:help}
.boton{display:inline-block;padding:.4rem .8rem;border:1px solid var(--borde);border-radius:.5rem;text-decoration:none;color:var(--texto);
  font-size:.94rem;margin:.2rem .4rem .2rem 0;background:var(--superficie)}
.boton:hover{border-color:var(--acento)}
.tarjeta{background:var(--superficie);border:1px solid var(--borde);border-radius:.75rem;padding:1rem 1.25rem;margin:1rem 0}
.tarjeta h3{margin:0 0 .4rem}
.chip{font-size:.8rem;color:var(--producto);border:1px solid currentColor;border-radius:999px;padding:.05rem .55rem;margin-right:.4rem}
.ayuda{color:var(--texto-2);font-size:.95rem}
.mapa{overflow-x:auto;background:#1b1c18;border-radius:.6rem;padding:.6rem;margin-top:.6rem}
.mapa svg{min-width:40rem;width:100%;height:auto}
"""


def pagina_documento(titulo: str, cuerpo: str, ancho: bool = False, nota: str | None = None) -> str:
    nota = tr("(solo lectura)") if nota is None else nota
    return (f"<!DOCTYPE html><html lang='{idioma.actual()}'><head><meta charset='UTF-8'>{tema.CABEZA}<title>{html.escape(titulo)}</title>"
            f"<style>{tema.TOKENS}{ESTILO_DOC}</style></head><body{' class=ancho' if ancho else ''}><div class='volver'>CCAR-F · "
            f"{html.escape(titulo)} {nota}</div>" + cuerpo + ZOOM_HTML + "</body></html>")


def pagina_codigo(n: int, demo: str | None) -> str:
    """El código del lab con números de línea; si se pide una demo, abre en su bloque 🔧 CAMBIA AQUÍ."""
    lineas = (CARPETA / f"lab_dominio{n}.py").read_text(encoding="utf-8").split("\n")
    destino = None
    if demo:
        encabezado = re.compile(rf"^#\s+DEMO {re.escape(demo)}\b")
        destino = next((i for i, l in enumerate(lineas) if encabezado.match(l)), None)
    inicio_bloque = fin_bloque = -1
    if destino is not None:
        inicio_bloque = next((i for i in range(destino, min(destino + 8, len(lineas))) if "CAMBIA AQU" in lineas[i]), -1)
        if inicio_bloque >= 0:
            fin_bloque = next((i for i in range(inicio_bloque + 1, len(lineas)) if re.match(r"^# -{10,}", lineas[i])), inicio_bloque)
    partes = []
    for i, l in enumerate(lineas):
        clase = ' class="resaltada"' if inicio_bloque <= i <= fin_bloque and inicio_bloque >= 0 else ""
        ancla = ' id="aqui"' if i == destino else ""
        partes.append(f'<span{ancla}{clase}><span class="linea">{i + 1}</span>{html.escape(l)}</span>')
    nota = ("<p>" + tr("Abre en la demo {d}: el bloque resaltado es donde se cambian sus variables. "
            "Para cambiarlas sin editar el archivo, usa los controles del panel.").format(d=html.escape(demo)) + "</p>"
            if destino is not None else "")
    script = "<script>const a=document.getElementById('aqui'); if(a) a.scrollIntoView({block:'start'});</script>"
    return pagina_documento(f"lab_dominio{n}.py", nota + "<pre><code>" + "\n".join(partes) + "</code></pre>" + script, ancho=True)


def recursos() -> dict:
    """Todo lo que el menú 📚 Recursos enlaza (solo lo que existe en la carpeta)."""
    corridas = [n for n in range(1, 6) if (CARPETA / f"salidas_html/dominio{n}/index.html").exists()]
    ejemplos = [n for n in range(1, 6) if (CARPETA / f"{carpeta_ejemplos(n)}/dominio{n}/index.html").exists()]
    return {
        "documentos": [{"nombre": doc_idioma(k), "texto": tr(v)} for k, v in DOCUMENTOS.items()
                       if (CARPETA / k).exists() and k not in EN_INGLES.values()],
        "textos": [{"nombre": k, "texto": tr(v)} for k, v in TEXTOS.items() if (CARPETA / k).exists()],
        "ejemplos": ejemplos, "corridas": corridas, "carpeta_ejemplos": carpeta_ejemplos(),
        "labs": [n for n in range(1, 6) if (CARPETA / f"lab_dominio{n}.py").exists()],
        "material": {str(k): material_dominio(k) for k in range(1, 6) if material_dominio(k)},
    }



# ---------------------------------------------------------------------
#  Contexto de cada demo, estado de la key, grabaciones, búsqueda
# ---------------------------------------------------------------------
GRABACIONES = CARPETA / "grabaciones"
SESION = {"corridas": 0, "tokens": 0, "costo": 0.0}   # lo gastado desde que abriste el panel


def carpeta_ejemplos(n: int | None = None) -> str:
    """ejemplos_html/ o, con el panel en inglés, ejemplos_html/en/ (corridas reales en inglés) si existe."""
    en = "ejemplos_html/en"
    if idioma.en() and (CARPETA / en / (f"dominio{n}/index.html" if n else "index.html")).exists():
        return en
    return "ejemplos_html"


def ancla_guia_labs(demo: str) -> str | None:
    """Sección "## Demo X.Y · …" de GUIA_LABS.md, para enlazar directo a cómo correr esa demo."""
    nombre = doc_idioma("GUIA_LABS.md")
    ruta = CARPETA / nombre
    if not ruta.exists():
        return None
    for linea in ruta.read_text(encoding="utf-8").split("\n"):
        m = re.match(rf"^##\s+(Demo {re.escape(demo)}\b.*)", linea)
        if m:
            return f"/doc/{nombre}#" + ancla_de(m.group(1))
    return f"/doc/{nombre}"


def contexto_demo(n: int, demo: str) -> dict:
    """Los enlaces de la franja "Para esta demo"."""
    enlaces = {"material": material_dominio(n), "como": ancla_guia_labs(demo), "codigo": f"/codigo?n={n}&demo={demo}"}
    if (CARPETA / f"{carpeta_ejemplos(n)}/dominio{n}/index.html").exists():
        enlaces["ejemplo"] = f"/archivos/{carpeta_ejemplos(n)}/dominio{n}/index.html#demo-{demo}"
    if (CARPETA / f"salidas_html/dominio{n}/index.html").exists():
        enlaces["corridas"] = f"/archivos/salidas_html/dominio{n}/index.html#demo-{demo}"
    return enlaces


def extras_demo(demo: str) -> dict:
    """Casos rápidos y resultados esperados de la demo (de extras.py), con el glosario ya marcado."""
    extras = dict(L(EXTRAS).get(demo, {}))
    if extras.get("casos"):
        originales = EXTRAS[demo]["casos"]   # el nombre en español: con él se buscan y se guardan las grabaciones
        extras["casos"] = [{**c, "nombre_es": originales[i]["nombre"], "explica_html": marcar_glosario(html.escape(c["explica"])),
                            **({"clase_info": CLASES[c["clase"]]} if c.get("clase") in CLASES else {})}
                           for i, c in enumerate(extras["casos"])]
    return extras


def estimado(n: int, demo: str) -> dict | None:
    """Tokens de una corrida típica (de la primera grabación de la demo) y los precios del lab, para estimar el costo."""
    for g in grabaciones(demo):
        try:
            datos = json.loads((CARPETA / g["url"].replace("/archivos/", "", 1)).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        uso = (datos.get("resultado") or {}).get("uso") or {}
        modulo = sys.modules.get(f"lab_dominio{n}")
        if uso.get("llamadas") and modulo is not None:
            return {"entrada": uso.get("entrada", 0), "salida": uso.get("salida", 0), "llamadas": uso["llamadas"],
                    "precios": {k: list(v) for k, v in getattr(modulo, "PRECIOS", {}).items()}}
    return None


def grabaciones(demo: str) -> list[dict]:
    """Las grabaciones de la demo; con el panel en inglés, las de grabaciones/<demo>/en/ si las hay."""
    carpeta = GRABACIONES / demo
    if idioma.en() and any((carpeta / "en").glob("*.json")):
        carpeta, demo = carpeta / "en", f"{demo}/en"
    salida = []
    for ruta in sorted(carpeta.glob("*.json")) if carpeta.exists() else []:
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        titulo = datos.get("titulo", ruta.stem)
        salida.append({"url": f"/archivos/grabaciones/{demo}/{ruta.name}", "titulo": tr(titulo), "titulo_es": titulo,
                       "simulada": datos.get("simulada", False), "fecha": datos.get("fecha", "")})
    return salida


def valor_env(ruta: Path) -> str:
    """ANTHROPIC_API_KEY del .env, leído igual que lo leen los labs (python-dotenv: export, comillas, comentarios)."""
    if not ruta.exists():
        return ""
    try:
        from dotenv import dotenv_values
        return (dotenv_values(ruta).get("ANTHROPIC_API_KEY") or "").strip()
    except ImportError:
        for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = linea.strip().removeprefix("export ").strip()
            if linea.startswith("ANTHROPIC_API_KEY="):
                return linea.split("=", 1)[1].split(" #")[0].strip().strip('"').strip("'")
    return ""


def resolver_key() -> tuple[str, str]:
    """La key que usarán los labs: la del .env de la carpeta gana; si no hay, la de la terminal."""
    valor = valor_env(CARPETA / ".env")
    if valor:
        return valor, "archivo .env"
    return os.environ.get("ANTHROPIC_API_KEY", ""), "variable de entorno de la terminal"


def probar_key() -> dict:
    """Pregunta a Anthropic si la key sirve, con una consulta que no cuesta (lista de modelos). Nunca devuelve la key."""
    valor, fuente = resolver_key()
    if not valor or "pega-aqui" in valor:
        return {"ok": False, "motivo": "falta", "fuente": fuente}
    try:
        import anthropic
        anthropic.Anthropic(api_key=valor, max_retries=0, timeout=10).models.list(limit=1)
        return {"ok": True, "fuente": fuente}
    except Exception as e:  # noqa: BLE001
        motivo = {"AuthenticationError": "invalida", "PermissionDeniedError": "permiso"}.get(type(e).__name__, "red")
        return {"ok": motivo == "red", "motivo": motivo, "fuente": fuente}   # sin internet no la marcamos como mala


def estado_entorno() -> dict:
    """¿Hay API key y librerías? (nunca devuelve la key, solo si existe)."""
    valor, fuente = resolver_key()
    lista = bool(valor) and "pega-aqui" not in valor
    faltan = [paquete for modulo, paquete in (("anthropic", "anthropic"), ("rich", "rich"), ("dotenv", "python-dotenv"),
                                             ("claude_agent_sdk", "claude-agent-sdk"), ("mcp", "mcp"))
              if importlib.util.find_spec(modulo) is None]
    basicas = [p for p in faltan if p in ("anthropic", "rich", "python-dotenv")]
    return {"python": sys.executable, "faltan_basicas": basicas, "key": lista, "fuente": fuente if lista else None, "env_existe": (CARPETA / ".env").exists(),
            "env_txt": next((n for n in (".env.txt", "env.txt", ".env.rtf", "env") if (CARPETA / n).exists()), None),
            "faltan": faltan}


def guardar_grabacion(trabajo: dict, titulo: str) -> str:
    """Guarda una corrida terminada para reproducirla después sin API key."""
    demo = trabajo["demo"]
    en_ingles = trabajo.get("idioma") == "en"            # las corridas en inglés se guardan en grabaciones/<demo>/en/
    sub = f"{demo}/en" if en_ingles else demo
    carpeta = GRABACIONES / sub
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFKD", titulo.lower())
                    .encode("ascii", "ignore").decode()).strip("_") or "grabacion"
    nombre = f"{nombre}_{time.strftime('%Y%m%d_%H%M%S')}"
    pagina = None
    if trabajo.get("pagina") and Path(trabajo["pagina"]).exists():
        texto = Path(trabajo["pagina"]).read_text(encoding="utf-8")
        texto = texto.replace('href="index.html"', f'href="/archivos/salidas_html/dominio{trabajo["dominio"]}/index.html"')
        resultado = (trabajo.get("resultado") or {}).get("texto", "")
        nota = html.escape(f"📝 Recording «{idioma.tr(titulo)}». Result: {resultado}" if en_ingles
                           else f"📝 Grabación «{titulo}». Resultado: {resultado}") + "</div>"
        texto = re.sub(r"📝 .*?</div>", lambda _m: nota, texto, count=1)
        (carpeta / f"{nombre}.html").write_text(limpiar_rutas(texto), encoding="utf-8")
        pagina = f"/archivos/grabaciones/{sub}/{nombre}.html"
    datos = {"titulo": titulo, "demo": demo, "dominio": trabajo["dominio"], "simulada": False,
             "fecha": time.strftime("%Y-%m-%d %H:%M"), "ajustes": trabajo.get("ajustes", {}),
             "lineas": [limpiar_rutas(l) for l in trabajo["lineas"]], "tiempos": trabajo["tiempos"],
             "resultado": trabajo.get("resultado"), "pagina": pagina}
    (carpeta / f"{nombre}.json").write_text(limpiar_rutas(json.dumps(datos, ensure_ascii=False)), encoding="utf-8")
    return nombre


def entero(texto, defecto=None):
    """Número chico y solo con dígitos 0-9 ("²".isdigit() da True, pero int() truena)."""
    return int(texto) if isinstance(texto, str) and re.fullmatch(r"[0-9]{1,4}", texto) else defecto


def limpiar_rutas(texto: str) -> str:
    """Quita rutas de tu computadora (usuario, carpeta) antes de guardar algo que se comparte."""
    for ruta, cambio in ((str(CARPETA), "."), (str(Path(tempfile.gettempdir()).resolve()), "$TMP"),
                         (tempfile.gettempdir(), "$TMP"), (str(Path.home()), "~")):
        texto = texto.replace(ruta, cambio)
    # rutas temporales recortadas en los diagramas ("/private/var/folders/j0/cbhn0k…"): también fuera
    return re.sub(r"(/private)?/var/folders/[^\s\"'<>]*", "$TMP/…", texto)


def normalizar(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


ETIQUETAS_BUSQUEDA = {"GUIA_LABS.md": "Guía de las demos", "README.md": "Cómo empezar (README)"}


def texto_plano(md: str) -> str:
    """Texto para el buscador: sin marcas de markdown, separadores de tabla ni llaves de JSON."""
    t = re.sub(r"-{3,}|[{}\[\]`*#|>]", " ", md)
    return re.sub(r"\s+", " ", t).strip()


def indice_busqueda() -> list[dict]:
    items = []
    for nombre in (doc_idioma("GUIA_LABS.md"), doc_idioma("README.md")):
        ruta = CARPETA / nombre
        if not ruta.exists():
            continue
        titulo, cuerpo, ancla, demo_actual, en_codigo = nombre, [], "", None, False
        def cerrar():
            if cuerpo or titulo != nombre:
                items.append({"tipo": ETIQUETAS_BUSQUEDA.get(nombre, nombre), "titulo": titulo,
                              "texto": texto_plano(html.unescape(" ".join(cuerpo))), "url": f"/doc/{nombre}" + (f"#{ancla}" if ancla else "")})
        for linea in ruta.read_text(encoding="utf-8").split("\n"):
            if es_cerca(linea):
                en_codigo = not en_codigo
                continue
            m = None if en_codigo else re.match(r"^(#{1,4})\s+(.*)", linea)
            if m:
                cerrar()
                titulo, cuerpo, nivel = m.group(2).strip(), [], len(m.group(1))
                if nivel <= 2:
                    demo_actual = demo_de_titulo(titulo)
                ancla = ancla_de(titulo, demo_actual if nivel > 2 else None)
            elif not en_codigo:
                cuerpo.append(linea)
        cerrar()
    for termino, (en, definicion) in list(L(GLOSARIO_BASICO).items()) + list(L(GLOSARIO).items()):
        items.append({"tipo": tr("Glosario"), "titulo": f"{termino} · {en}" if termino.lower() != en.lower() else termino,
                      "texto": definicion, "url": None})
    for n in labs_disponibles():
        try:
            info = info_lab(n)
        except Exception:  # noqa: BLE001
            continue
        for d in info["demos"]:
            guia = guia_html(idioma.guia(d["clave"], d["guia_md"]))
            texto = " ".join([texto_plano(html.unescape(re.sub("<[^>]+>", " ", guia)))]
                             + [f"{v['nombre']} {tr(v.get('ayuda', ''))}" for v in d["variables"]])
            items.append({"tipo": tr("Demo del lab {n}").format(n=n), "titulo": f"Demo {d['clave']} · {tr(d['nombre'])}",
                          "texto": texto, "demo": [n, d["clave"]]})
    return items


def buscar(consulta: str) -> list[dict]:
    palabras = [p for p in normalizar(consulta).split() if p]
    if not palabras:
        return []
    resultados = []
    for item in indice_busqueda():
        titulo, texto = normalizar(item["titulo"]), normalizar(item["texto"])
        if not all(p in titulo or p in texto for p in palabras):
            continue
        puntos = sum(3 for p in palabras if p in titulo) + (2 if item.get("demo") else 0)
        pos = min((texto.find(p) for p in palabras if p in texto), default=0)
        fragmento = item["texto"][max(0, pos - 60): pos + 160]
        resultados.append((puntos, {**item, "texto": ("…" if pos > 60 else "") + fragmento + "…"}))
    resultados.sort(key=lambda x: -x[0])
    return [r for _, r in resultados[:14]]


# ---------------------------------------------------------------------
#  Páginas: dominio y comparar corridas
# ---------------------------------------------------------------------

def pagina_dominio(n: int) -> str:
    nombre = {1: "Agentic Architecture & Orchestration", 2: "Tool Design & MCP Integration",
              3: "Claude Code Configuration & Workflows", 4: "Prompt Engineering & Structured Output",
              5: "Context Management & Reliability"}.get(n, "")
    h = [f"<p class='volver'><a href='/'>{tr('← Volver al panel')}</a></p>", f"<h1>{tr('Dominio')} {n} · {html.escape(nombre)}</h1>",
         "<p class='ayuda'>" + tr("Todo lo del dominio en un solo lugar. Cada demo trae sus enlaces; "
         "<b>▶ Abrir en el panel</b> la deja lista para correr.") + "</p><p>"]
    h.append(botones_material(n))
    h.append(f"<a class='boton' href='/repaso?n={n}' target='_blank'>{tr('Hoja de repaso')}</a>"
             f"<a class='boton' href='/glosario?n={n}' target='_blank'>{tr('Glosario')}</a>"
             f"<a class='boton' href='/antipatrones' target='_blank'>{tr('Antipatrones')}</a>"
             f"<a class='boton' href='/escenarios' target='_blank'>{tr('Escenarios (lista no oficial)')}</a>")
    if (CARPETA / f"{carpeta_ejemplos(n)}/dominio{n}/index.html").exists():
        h.append(f"<a class='boton' href='/archivos/{carpeta_ejemplos(n)}/dominio{n}/index.html' target='_blank'>{tr('Todos los ejemplos')}</a>")
    if (CARPETA / f"salidas_html/dominio{n}/index.html").exists():
        h.append(f"<a class='boton' href='/archivos/salidas_html/dominio{n}/index.html' target='_blank'>{tr('Tus corridas')}</a>")
    h.append("</p>")
    h.append(paginas.mapa_svg(n, con_labs=n in labs_disponibles()))
    if n not in labs_disponibles():
        h.append("<p class='ayuda'>" + tr("Este lab todavía no se puede correr desde el panel; córrelo en la terminal "
                 "con <code>python lab_dominio{n}.py</code>.").format(n=n) + "</p>")
        return pagina_documento(f"{tr('Dominio')} {n}", "".join(h), nota="")
    for d in info_lab(n)["demos"]:
        ctx = contexto_demo(n, d["clave"])
        guia = guia_html(idioma.guia(d["clave"], d["guia_md"]))
        m = re.search(r"<h4>(De qué trata|What it is about)</h4>(.*?)(<h4>|$)", guia, re.S)
        resumen = marcar_glosario(m.group(2)) if m else ""
        extras = EXTRAS.get(d["clave"], {})
        chips = []
        if extras.get("casos"):
            chips.append(tr("Casos"))
        if grabaciones(d["clave"]):
            chips.append(tr("Grabación (sin API key)"))
        chips += [f"{tr('Escenario')} {e['n']}" for e in escenarios_de(d["clave"])]
        h.append(f"<div class='tarjeta'><h3>Demo {d['clave']} · {html.escape(tr(d['nombre']))}</h3>"
                 + "".join(f"<span class='chip'>{c}</span>" for c in chips) + resumen + "<p>"
                 f"<a class='boton' href='/?n={n}&demo={d['clave']}'>▶ {tr('Abrir en el panel')}</a>"
                 + (f"<a class='boton' href='{ctx['como']}' target='_blank'>{tr('Cómo correrla')}</a>" if ctx.get("como") else "")
                 + f"<a class='boton' href='{ctx['codigo']}' target='_blank'>&lt;/&gt; {tr('Código')}</a>"
                 + (f"<a class='boton' href='{ctx['ejemplo']}' target='_blank'>{tr('Ejemplo')}</a>" if ctx.get("ejemplo") else "")
                 + (f"<a class='boton' href='{ctx['corridas']}' target='_blank'>{tr('Tus corridas')}</a>" if ctx.get("corridas") else "")
                 + (f"<a class='boton' href='/comparar?n={n}&demo={d['clave']}' target='_blank'>{tr('Comparar')}</a>" if ctx.get("corridas") else "")
                 + "</p></div>")
    return pagina_documento(f"{tr('Dominio')} {n}", "".join(h), nota="")


def pagina_comparar(n: int, demo: str, a: str | None, b: str | None) -> str:
    """Dos corridas de la misma demo lado a lado: variables, resultado y diagramas."""
    try:
        todas = json.loads((CARPETA / f"salidas_html/dominio{n}/corridas.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        todas = []
    propias = [c for c in todas if c["demo"] == demo]
    cab = (f"<p class='volver'><a href='/' target='_top'>{tr('← Volver al panel')}</a></p>"
           f"<h1>{tr('Comparar corridas')} · demo {html.escape(demo)}</h1>"
           "<p class='ayuda'>" + tr("Elige dos corridas de la misma demo. Arriba ves qué variables cambiaron "
           "(en amarillo) y qué pasó en cada una; abajo, sus diagramas lado a lado.") + "</p>")
    if len(propias) < 2:
        cuerpo = cab + ("<div class='tarjeta'>" + tr("<b>Necesitas al menos 2 corridas de la demo {d}</b> "
                        "(llevas {k}).").format(d=html.escape(demo), k=len(propias)) + "<p class='ayuda'>" + tr("Sugerencia: en el panel usa los <b>Casos</b>, "
                        "corre <b>✅ Funciona bien</b> y luego un caso <b>❌</b>. Después vuelve a esta pestaña.") + "</p>"
                        "<p class='ayuda'>" + tr("Las grabaciones (▶ grabada) no cuentan aquí: Comparar usa tus corridas reales. "
                        "Sin key, compara los tickets de las dos grabaciones.") + "</p></div>")
        return pagina_comparar_html(cuerpo)
    ia, ib = entero(a, -1), entero(b, -1)
    ia = ia if 0 <= ia < len(propias) else len(propias) - 2
    ib = ib if 0 <= ib < len(propias) else len(propias) - 1
    def opciones(sel):
        return "".join(f"<option value='{i}' {'selected' if i == sel else ''}>#{i + 1} · {html.escape(str(c.get('fecha', '')).replace('T', ' '))}"
                       f"{' · ' + html.escape(c['resultado']['texto'][:60]) if c.get('resultado', {}).get('texto') else ''}</option>"
                       for i, c in enumerate(propias))
    ca, cb = propias[ia], propias[ib]
    filas = []
    for k in sorted(set(ca["config"]) | set(cb["config"])):
        va, vb = (json.dumps(c["config"].get(k), ensure_ascii=False) for c in (ca, cb))
        clase = " class='cambio'" if va != vb else ""
        filas.append(f"<tr{clase}><td>{html.escape(k)}</td><td>{html.escape(va)}</td><td>{html.escape(vb)}</td></tr>")
    for etiqueta, f in ((tr("Resultado"), lambda c: c.get("resultado", {}).get("texto", "—")),
                        (tr("Costo"), lambda c: costo_corto(c.get("resultado", {})))):
        filas.append(f"<tr class='res'><td>{etiqueta}</td><td>{html.escape(f(ca))}</td><td>{html.escape(f(cb))}</td></tr>")
    def columna(c, letra):
        archivo = quote(Path(str(c.get("archivo", ""))).name)
        return (f"<div class='col'><h3>{letra} · {html.escape(str(c.get('fecha', '')).replace('T', ' '))} "
                f"<a style='font-size:14px' href='/archivos/salidas_html/dominio{n}/{archivo}' target='_blank'>{tr('salida completa')} ↗</a></h3>"
                + "".join(c.get("diagramas", [])) + "</div>")
    cuerpo = (cab + "<form class='selector' method='get'>"
              f"<input type='hidden' name='n' value='{n}'><input type='hidden' name='demo' value='{html.escape(demo)}'>"
              f"<label>A <select name='a' onchange='this.form.submit()'>{opciones(ia)}</select></label>"
              f"<label>B <select name='b' onchange='this.form.submit()'>{opciones(ib)}</select></label></form>"
              f"<table class='comp'><tr><th>{tr('Variable')}</th><th>A</th><th>B</th></tr>" + "".join(filas) + "</table>"
              + diferencias_requests(ca.get("requests") or [], cb.get("requests") or [])
              + "<div class='lado'>" + columna(ca, "A") + columna(cb, "B") + "</div>")
    return pagina_comparar_html(cuerpo)


def diferencias_requests(ra: list, rb: list) -> str:
    """Llamada por llamada: qué cambió en lo que se le mandó a Claude (no solo en las variables)."""
    if not ra and not rb:
        return ""
    def campo(r, k):
        if r is None:
            return "—"
        if k == "tools":
            return ", ".join(r.get("tools") or []) or "—"
        if k == "messages":
            k_msgs = len(r.get('messages') or [])
            return f"{k_msgs} {tr('mensaje') if k_msgs == 1 else tr('mensajes')}"
        valor = r.get(k)
        return str(valor) if valor not in (None, "") else "—"
    filas = []
    for i in range(max(len(ra), len(rb))):
        a = ra[i] if i < len(ra) else None
        b = rb[i] if i < len(rb) else None
        filas.append(f"<tr class='res'><td colspan='3'><b>{tr('Llamada')} {i + 1}</b></td></tr>")
        for k, nombre in (("system", "system"), ("tools", "tools"), ("max_tokens", "max_tokens"), ("model", tr("modelo")),
                          ("messages", tr("historial"))):
            va, vb = campo(a, k), campo(b, k)
            clase = " class='cambio'" if va != vb else ""
            filas.append(f"<tr{clase}><td>{nombre}</td><td>{html.escape(va[:300])}</td><td>{html.escape(vb[:300])}</td></tr>")
    return ("<h3>" + tr("Lo que vio Claude: diferencias llamada por llamada") + "</h3>"
            "<p class='ayuda'>" + tr("En amarillo, lo que cambió en lo que se le mandó a la API. Aquí se ve la causa, no solo "
            "el efecto: un system distinto, menos tokens, otras tools o un historial más corto.") + "</p>"
            f"<table class='comp'><tr><th>{tr('Qué')}</th><th>A</th><th>B</th></tr>" + "".join(filas) + "</table>")


def costo_corto(resultado: dict) -> str:
    uso = resultado.get("uso") or {}
    if not uso.get("llamadas"):
        return "—"
    return f"{uso.get('entrada', 0) + uso.get('salida', 0):,} tokens · ≈ ${resultado.get('costo', 0):.4f}"


def pagina_comparar_html(cuerpo: str) -> str:
    extra = """<style>
body{max-width:1500px}
.selector{display:flex;gap:1.1rem;flex-wrap:wrap;margin:.6rem 0 1rem} .selector select{font:inherit;font-size:.94rem;padding:.4rem;
  background:var(--superficie);color:var(--texto);border:1px solid var(--borde);border-radius:.5rem;max-width:32rem}
table.comp{display:table} table.comp td:first-child{color:var(--texto-2);white-space:nowrap}
tr.cambio td{background:var(--resaltado) !important;color:var(--texto)} tr.res td{background:var(--bien-suave) !important}
.lado{display:grid;grid-template-columns:1fr 1fr;gap:18px} .col{min-width:0}
@media (max-width:760px){.lado{grid-template-columns:1fr}}
.col svg{max-width:100%;height:auto} .col .diagrama{max-width:100% !important;padding:12px !important}
</style>"""
    return pagina_documento(tr("Comparar corridas"), extra + cuerpo, ancho=True, nota="")


# ---------------------------------------------------------------------
#  Correr una demo
# ---------------------------------------------------------------------

HERRAMIENTAS_SEGURAS = {"Read", "Grep", "Glob", "Edit", "Write"}   # nunca Bash desde el panel


def validar_ajustes(dominio: int, demo: str, ajustes) -> dict:
    """Solo variables de esa demo, con el mismo tipo que en el lab; MODELO y DETALLE con valores conocidos."""
    demos = {d["clave"]: d for d in info_lab(dominio)["demos"]}
    if demo not in demos:
        raise ValueError("Esa demo no existe en el lab.")
    if not isinstance(ajustes, dict):
        raise ValueError("Ajustes inválidos.")
    originales = {v["nombre"]: v["valor"] for v in demos[demo]["variables"]}
    limpio = {}
    for k, v in ajustes.items():
        if k == "MODELO":
            if v not in MODELOS:
                raise ValueError(f"Modelo desconocido: {v}")
        elif k == "DETALLE":
            if v not in ("basico", "completo"):
                raise ValueError("DETALLE debe ser basico o completo.")
        elif k in originales:
            o = originales[k]
            mismo = (isinstance(v, bool) == isinstance(o, bool)) and (
                isinstance(v, type(o)) or (isinstance(o, (int, float)) and isinstance(v, (int, float)) and not isinstance(v, bool)))
            if not mismo:
                raise ValueError(f"{k} debe ser del mismo tipo que en el lab.")
            if re.search(r"_(TOOLS|HERRAMIENTAS)$", k) and not set(v) <= HERRAMIENTAS_SEGURAS | set(o):
                raise ValueError(f"{k} solo acepta: {', '.join(sorted(HERRAMIENTAS_SEGURAS))}.")
        else:
            raise ValueError(f"{k} no es una variable de la demo {demo}.")
        limpio[k] = v
    return limpio


def iniciar(dominio: int, demo: str, ajustes: dict) -> str:
    ajustes = validar_ajustes(dominio, demo, ajustes)
    with CANDADO:
        if any(not t["terminado"] for t in TRABAJOS.values()):
            raise RuntimeError("Ya hay una demo corriendo. Espera a que termine o detenla.")
        id_ = uuid.uuid4().hex[:8]
        # Colores: el lab escribe códigos ANSI (como en una terminal) y la página los convierte a colores.
        entorno = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
        ruta_resultado = Path(tempfile.gettempdir()) / f"ccarf_resultado_{id_}.json"
        entorno.update(CCARF_AJUSTES=json.dumps(ajustes, ensure_ascii=False), PYTHONUNBUFFERED="1",
                       CCARF_RESULTADO=str(ruta_resultado), CCARF_IDIOMA=idioma.actual(),
                       PYTHONIOENCODING="utf-8", FORCE_COLOR="1", COLORTERM="truecolor", TERM="xterm-256color",
                       COLUMNS="110")
        proceso = subprocess.Popen([sys.executable, f"lab_dominio{dominio}.py", demo, "--html"], cwd=CARPETA,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   env=entorno, text=True, encoding="utf-8", errors="replace", bufsize=1,
                                   start_new_session=(os.name == "posix"))
        trabajo = {"proceso": proceso, "lineas": [], "tiempos": [], "terminado": False, "pagina": None,
                   "codigo": None, "inicio": time.time(), "dominio": dominio, "demo": demo, "ajustes": ajustes,
                   "idioma": idioma.actual(),
                   "ruta_resultado": ruta_resultado, "resultado": None}
        TRABAJOS[id_] = trabajo
    threading.Thread(target=leer_salida, args=(trabajo,), daemon=True).start()
    vigilante = threading.Timer(MAX_SEGUNDOS_CORRIDA, detener, args=(trabajo, "tiempo"))
    vigilante.daemon = True
    vigilante.start()
    return id_


MAX_SEGUNDOS_CORRIDA = 20 * 60   # ninguna demo tarda tanto; si pasa, se detiene sola (y deja de gastar)


def detener(trabajo: dict, motivo: str = "boton") -> None:
    """Detiene la demo y todo lo que lanzó (Agent SDK, claude -p): sin esto seguirían corriendo y gastando."""
    proceso = trabajo["proceso"]
    if trabajo["terminado"] or proceso.poll() is not None:
        return
    if motivo == "tiempo":
        trabajo["lineas"].append(f"⏱ La demo pasó de {MAX_SEGUNDOS_CORRIDA // 60} minutos y se detuvo sola.")
        trabajo["tiempos"].append(round(time.time() - trabajo["inicio"], 2))
    def senal(sig):
        try:
            if os.name == "posix":
                os.killpg(proceso.pid, sig)
            else:
                proceso.send_signal(sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    senal(signal.SIGTERM)
    def rematar():
        time.sleep(5)
        if proceso.poll() is None:
            senal(signal.SIGKILL if os.name == "posix" else signal.SIGTERM)
    threading.Thread(target=rematar, daemon=True).start()


def leer_salida(trabajo: dict) -> None:
    try:
        for linea in trabajo["proceso"].stdout:
            linea = linea.rstrip("\n")
            trabajo["lineas"].append(linea)
            trabajo["tiempos"].append(round(time.time() - trabajo["inicio"], 2))
            m = re.search(r"Página de esta corrida: (.+\.html)", linea)
            if m:
                trabajo["pagina"] = m.group(1).strip()
        trabajo["codigo"] = trabajo["proceso"].wait()
        try:
            trabajo["resultado"] = json.loads(trabajo["ruta_resultado"].read_text(encoding="utf-8"))
            if not isinstance(trabajo["resultado"], dict):
                trabajo["resultado"] = None
        except (OSError, ValueError):
            trabajo["resultado"] = None
        res = trabajo["resultado"] or {}
        uso = res.get("uso") if isinstance(res.get("uso"), dict) else {}
        costo = res.get("costo") if isinstance(res.get("costo"), (int, float)) else 0
        SESION["corridas"] += 1
        SESION["tokens"] += (uso.get("entrada") or 0) + (uso.get("salida") or 0)
        SESION["costo"] += costo
    except Exception as e:  # noqa: BLE001
        trabajo["lineas"].append(f"⚠ El panel no pudo leer el final de la corrida: {type(e).__name__}")
        if trabajo["codigo"] is None:
            trabajo["codigo"] = trabajo["proceso"].poll()
    finally:
        try:
            trabajo["ruta_resultado"].unlink(missing_ok=True)
        except OSError:
            pass
        trabajo["terminado"] = True


def url_de_archivo(ruta: str | None) -> str | None:
    if not ruta:
        return None
    try:
        relativa = Path(ruta).resolve().relative_to(CARPETA)
    except ValueError:
        return None
    return "/archivos/" + relativa.as_posix()


# ---------------------------------------------------------------------
#  Servidor web
# ---------------------------------------------------------------------

class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *args):   # silencio en la terminal
        pass

    def _enviar(self, cuerpo: bytes | str, tipo="text/html; charset=utf-8", codigo=200):
        datos = cuerpo.encode("utf-8") if isinstance(cuerpo, str) else cuerpo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        # Que ninguna otra página pueda meter el panel en un iframe (clics escondidos que gasten tu saldo)
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Content-Security-Policy", "frame-ancestors 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(datos)

    def _json(self, obj, codigo=200):
        self._enviar(json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", codigo)

    def _host_ok(self) -> bool:
        """Solo atiende peticiones dirigidas a 127.0.0.1 o localhost en este puerto (evita DNS rebinding)."""
        return self.headers.get("Host", "") in {f"127.0.0.1:{PUERTO}", f"localhost:{PUERTO}"}

    def _origen_ok(self) -> bool:
        """Un POST solo puede venir del propio panel: otra página web no puede correr demos con tu key."""
        origen = self.headers.get("Origin")
        tipo = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        return tipo == "application/json" and origen in (None, f"http://127.0.0.1:{PUERTO}", f"http://localhost:{PUERTO}")

    def do_GET(self):
        if not self._host_ok():
            return self._enviar("No encontrado", "text/plain; charset=utf-8", 404)
        url = urlparse(self.path)
        q = parse_qs(url.query)
        self._idioma()
        if url.path == "/":
            return self._enviar(PAGINA)
        if url.path == "/api/labs":
            return self._json({"labs": sorted(labs_disponibles())})
        if url.path == "/api/lab":
            try:
                n = entero(q.get("n", ["1"])[0])
                if n not in labs_disponibles():
                    return self._json({"error": tr("Ese lab no existe.")}, 404)
                info = dict(info_lab(n))
                info["demos"] = [{**{k: v for k, v in d.items() if k != "guia_md"}, "nombre": tr(d["nombre"]),
                                  "guia": marcar_glosario(guia_html(idioma.guia(d["clave"], d["guia_md"])) if idioma.en() else d["guia"]),
                                  "contexto": contexto_demo(n, d["clave"]),
                                  "estudio_html": paginas.estudio_html(d["clave"]), "producto": L(PRODUCTO).get(d["clave"]),
                                  "examen_tema": paginas.examen_tema(d["clave"]),
                                  "escenarios": [{k: e[k] for k in ("n", "es", "en")} for e in escenarios_de(d["clave"])],
                                  "estimado": estimado(n, d["clave"]),
                                  "extras": extras_demo(d["clave"]), "grabaciones": grabaciones(d["clave"]),
                                  "variables": [{**v, "ayuda_html": marcar_glosario(html.escape(tr(v.get("ayuda") or "")))}
                                                for v in d["variables"]]}
                                 for d in info["demos"]]
                info["paginas"] = paginas.estudio().get("paginas", {})
                info["material_todo"] = {str(k): material_dominio(k) for k in range(1, 6) if material_dominio(k)}
                return self._json(info)
            except Exception as e:  # noqa: BLE001
                print(f"[panel] /api/lab: {type(e).__name__}: {e}", file=sys.stderr)
                return self._json({"error": tr("No se pudo leer el lab ({e}). Revisa la terminal del panel.").format(e=type(e).__name__)}, 500)
        if url.path == "/api/salida":
            t = TRABAJOS.get(q.get("id", [""])[0])
            if not t:
                return self._json({"error": "no existe"}, 404)
            desde = entero(q.get("desde", ["0"])[0], 0)
            return self._json({"lineas": t["lineas"][desde:], "total": len(t["lineas"]), "terminado": t["terminado"],
                               "codigo": t["codigo"], "pagina": url_de_archivo(t["pagina"]),
                               "indice": f"/archivos/salidas_html/dominio{t['dominio']}/index.html",
                               "segundos": round(time.time() - t["inicio"]),
                               "resultado": t["resultado"] if t["terminado"] else None, "sesion": SESION})
        if url.path.startswith("/archivos/"):
            return self._archivo(url.path[len("/archivos/"):])
        if url.path == "/api/recursos":
            return self._json(recursos())
        if url.path == "/api/probar_key":
            return self._json(probar_key())
        if url.path == "/api/estado":
            return self._json(estado_entorno())
        if url.path == "/api/buscar":
            return self._json({"resultados": buscar(q.get("q", [""])[0])})
        if url.path == "/dominio":
            n = entero(q.get("n", ["1"])[0])
            if n not in range(1, 6):
                return self._enviar("No encontrado", "text/plain; charset=utf-8", 404)
            return self._enviar(pagina_dominio(n))
        volver = f"<a href='/'>{tr('← Volver al panel')}</a>"
        if url.path == "/repaso":
            return self._enviar(paginas.pagina_repaso(volver))
        if url.path == "/glosario":
            return self._enviar(paginas.pagina_glosario(volver))
        if url.path == "/antipatrones":
            return self._enviar(paginas.pagina_antipatrones(True, volver))
        if url.path == "/escenarios":
            return self._enviar(paginas.pagina_escenarios(True, volver))
        if url.path == "/comparar":
            n = entero(q.get("n", [""])[0])
            if n not in range(1, 6):
                return self._enviar("No encontrado", "text/plain; charset=utf-8", 404)
            return self._enviar(pagina_comparar(n, q.get("demo", [""])[0], q.get("a", [None])[0], q.get("b", [None])[0]))
        if url.path.startswith("/doc/"):
            nombre = doc_idioma(url.path[len("/doc/"):])
            if nombre in DOCUMENTOS and (CARPETA / nombre).exists():
                return self._enviar(pagina_documento(nombre, md_a_html((CARPETA / nombre).read_text(encoding="utf-8"))))
            if nombre in TEXTOS and (CARPETA / nombre).exists():
                return self._enviar(pagina_documento(nombre, "<pre><code>" + html.escape((CARPETA / nombre).read_text(encoding="utf-8")) + "</code></pre>"))
            return self._enviar("No encontrado", "text/plain; charset=utf-8", 404)
        if url.path == "/codigo":
            n = entero(q.get("n", [""])[0])
            if n in range(1, 6) and (CARPETA / f"lab_dominio{n}.py").exists():
                return self._enviar(pagina_codigo(n, q.get("demo", [None])[0]))
            return self._enviar("No encontrado", "text/plain; charset=utf-8", 404)
        self._enviar("No encontrado", "text/plain; charset=utf-8", 404)

    def _archivo(self, relativa: str):
        """Solo sirve páginas de salidas_html/ y ejemplos_html/ (nada más de tu carpeta)."""
        ruta = (CARPETA / relativa).resolve()
        permitidas = [(CARPETA / "salidas_html").resolve(), (CARPETA / "ejemplos_html").resolve(), GRABACIONES.resolve(), MATERIAL.resolve()]
        if not any(ruta.is_relative_to(p) for p in permitidas) or not ruta.is_file():
            return self._enviar("No encontrado", "text/plain; charset=utf-8", 404)
        tipo = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
                ".pdf": "application/pdf", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}.get(
            ruta.suffix, "application/octet-stream")
        self._enviar(ruta.read_bytes(), tipo)

    def _idioma(self):
        """El idioma que eligió el botón ES / EN del panel (cookie idioma=en)."""
        cookies = dict(c.strip().split("=", 1) for c in (self.headers.get("Cookie") or "").split(";") if "=" in c)
        idioma.usar(cookies.get("idioma", "es"))

    def do_POST(self):
        self._idioma()
        if not (self._host_ok() and self._origen_ok()):
            return self._json({"error": "Petición rechazada: solo el panel puede pedir esto."}, 403)
        url = urlparse(self.path)
        try:
            largo = int(self.headers.get("Content-Length", 0))
            if not 0 <= largo <= 1_000_000:
                raise ValueError
            cuerpo = json.loads(self.rfile.read(largo) or b"{}")
            if not isinstance(cuerpo, dict):
                raise ValueError
        except ValueError:
            return self._json({"error": "Petición inválida."}, 400)
        if url.path == "/api/correr":
            try:
                dominio = int(cuerpo["dominio"])
                if dominio not in labs_disponibles():
                    raise ValueError("Ese lab todavía no se puede correr desde el panel.")
                id_ = iniciar(dominio, str(cuerpo["demo"]), cuerpo.get("ajustes", {}))
                return self._json({"id": id_})
            except (ValueError, RuntimeError, KeyError, TypeError) as e:
                return self._json({"error": str(e) if isinstance(e, (ValueError, RuntimeError)) else "Petición inválida."}, 400)
            except Exception as e:  # noqa: BLE001
                print(f"[panel] /api/correr: {type(e).__name__}: {e}", file=sys.stderr)
                return self._json({"error": f"No se pudo iniciar la demo ({type(e).__name__})."}, 500)
        if url.path == "/api/grabar":
            t = TRABAJOS.get(cuerpo.get("id", ""))
            if not t or not t["terminado"] or t["codigo"] != 0:
                return self._json({"error": "Solo se puede grabar una corrida que terminó bien."}, 400)
            return self._json({"nombre": guardar_grabacion(t, str(cuerpo.get("titulo") or "Corrida grabada")[:80])})
        if url.path == "/api/detener":
            t = TRABAJOS.get(cuerpo.get("id", ""))
            if t:
                detener(t)
            return self._json({"ok": True})
        self._json({"error": "no existe"}, 404)


WEB = CARPETA / "panel_web"   # la página del panel: index.html + panel.css + panel.js (se juntan al arrancar)


def leer_pagina() -> str:
    """Arma la página del panel con sus tres archivos y el tema compartido (tema.py)."""
    pagina = (WEB / "index.html").read_text(encoding="utf-8")
    return (pagina.replace("/*__CSS__*/", (WEB / "panel.css").read_text(encoding="utf-8"))
            .replace("/*__JS__*/", (WEB / "panel.js").read_text(encoding="utf-8")))


def paleta_monokai() -> list[str]:
    try:
        from rich.terminal_theme import MONOKAI
        return [MONOKAI.ansi_colors[i].hex for i in range(16)]
    except Exception:  # noqa: BLE001
        return ["#1a1a1a", "#f4005f", "#98e024", "#fd971f", "#9d65ff", "#f4005f", "#58d1eb", "#c4c5b5",
                "#625e4c", "#f4005f", "#98e024", "#e0d561", "#9d65ff", "#f4005f", "#58d1eb", "#f6f6ef"]


PAGINA = (leer_pagina().replace("__PALETA__", json.dumps(paleta_monokai()))
          .replace("__TEMA_CABEZA__", tema.CABEZA).replace("__TEMA_TOKENS__", tema.TOKENS)
          .replace("/*__JS_TEMA__*/", tema.JS_TEMA))


def main() -> None:
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    url = f"http://127.0.0.1:{PUERTO}"
    print(f"🎛  Panel de labs en {url}   (Ctrl+C para cerrarlo)")
    print(f"    Labs disponibles en el panel: {', '.join(f'dominio {n}' for n in labs_disponibles()) or 'ninguno'}")
    try:
        if not os.environ.get("CCARF_SIN_NAVEGADOR"):   # las pruebas (_dev/pruebas.py) no abren el navegador
            webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel cerrado.")


if __name__ == "__main__":
    main()

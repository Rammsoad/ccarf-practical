"""
paginas.py · Páginas de estudio del CCAR-F (las usa panel.py y también se guardan como archivos sueltos)

- Pestaña 📘 Estudiar del panel: la sección de la guía de estudio de cada tema.
- Hoja de repaso (como mini-escenarios), galería de antipatrones, glosario y los 6 escenarios del examen.
- Mapa conceptual de cada dominio.
- Reproductor de grabaciones y EMPIEZA_AQUI.html, que funcionan sin Python (doble clic).

Para volver a generar los archivos sueltos:  python paginas.py
Los textos salen de estudio.json (extraído de las guías de estudio) y de extras.py.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import idioma
import tema as estilos
import visual
from idioma import L, tr
from extras import CLASES, DISTRACTORES, ESCENARIOS, EXTRAS, GLOSARIO, GLOSARIO_BASICO, MAPAS, NO_SE_PRACTICA, REPASO_MINI, marcar_glosario

CARPETA = Path(__file__).resolve().parent
_CACHE: dict = {}


def estudio() -> dict:
    ruta = CARPETA / "estudio.json"
    if not ruta.exists():
        return {"temas": {}, "repaso": {}, "glosario": {}}
    version = ruta.stat().st_mtime
    if _CACHE.get("version") != version:
        _CACHE.update(version=version, datos=json.loads(ruta.read_text(encoding="utf-8")))
    return L(_CACHE["datos"])


def esc(t) -> str:
    return html.escape(str(t))


def celda(t: str) -> str:
    """Celda de una tabla de la guía: escapa, `código` → <code> y marca el glosario."""
    return marcar_glosario(re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(t)))


def tabla_guia(filas: list[list[str]]) -> str:
    """Tabla de la guía de estudio (la primera fila es el encabezado)."""
    if not filas:
        return ""
    cab = "".join(f"<th>{celda(c)}</th>" for c in filas[0])
    cuerpo = "".join("<tr>" + "".join(f"<td>{celda(c)}</td>" for c in f) + "</tr>" for f in filas[1:])
    return f"<div class='tabla'><table class='guia'><tr>{cab}</tr>{cuerpo}</table></div>"


def texto(t: str) -> str:
    """Texto de la guía a HTML: escapa, pone en <code> lo que va entre comillas rectas y marca el glosario."""
    h = esc(t)
    h = re.sub(r"&quot;([^&]{1,40})&quot;", r"<code>&quot;\1&quot;</code>", h)
    return marcar_glosario(h)


CSS = """
*{box-sizing:border-box}
body{margin:0 auto;max-width:62rem;padding:2rem 1.75rem 5.5rem;background:var(--fondo);color:var(--texto);font-size:1.0625rem;line-height:1.6}
a{color:var(--enlace)} h1{font-size:1.85rem;line-height:1.25;margin:0 0 .5rem} h2{font-size:1.45rem;margin:2.5rem 0 .6rem;
  padding-top:.9rem;border-top:3px solid var(--acento)} h3{font-size:1.2rem;margin:1.5rem 0 .4rem}
p,li{max-width:76ch} .ayuda{color:var(--texto-2);font-size:.95rem}
code{background:var(--codigo-fondo);padding:.05em .35em;border-radius:.3em;font-size:.88em}
table{border-collapse:collapse;width:100%;margin:.6rem 0;font-size:.95rem}
th,td{border:1px solid var(--borde);padding:.5rem .75rem;vertical-align:top;text-align:left}
th{background:var(--superficie-2);position:sticky;top:0} tr:nth-child(even) td{background:var(--superficie)}
.tarjeta{background:var(--superficie);border:1px solid var(--borde);border-radius:.75rem;padding:.9rem 1.1rem;margin:.9rem 0}
.boton{display:inline-block;padding:.35rem .75rem;border:1px solid var(--borde);border-radius:.5rem;text-decoration:none;color:var(--texto);
  font-size:.94rem;margin:.25rem .4rem .25rem 0;background:var(--superficie);cursor:pointer;font-family:inherit}
.boton:hover{border-color:var(--acento)} .boton.activo{border-color:var(--acento);background:var(--acento-suave)}
.chip{font-size:.8rem;font-weight:600;color:var(--trampa);background:var(--trampa-suave);border-radius:999px;padding:.05rem .55rem;margin-left:.3rem}
.idea{background:var(--acento-suave);border-left:4px solid var(--acento);border-radius:0 .5rem .5rem 0;padding:.75rem 1rem;font-size:1.15rem;margin:.6rem 0 1.1rem}
.mal{color:var(--trampa)} .bien{color:var(--bien)}
abbr.termino{text-decoration:underline dotted var(--tinta);text-underline-offset:3px;cursor:help}
details summary{cursor:pointer}
input.buscar{width:100%;font:inherit;font-size:1.0625rem;padding:.6rem .9rem;background:var(--superficie);color:var(--texto);
  border:1px solid var(--borde);border-radius:.6rem}
.tapado tr:not(.visto) td.resp{color:transparent;background:var(--codigo-fondo);cursor:pointer}
.tapado tr:not(.visto) td.resp *{color:transparent;background:transparent;text-decoration:none}
.tapado tr:not(.visto) .tit{color:transparent;background:var(--codigo-fondo);border-radius:.25em}
.tabla{overflow-x:auto}
.mapa{overflow-x:auto;background:#1b1c18;border-radius:.6rem;padding:.6rem;margin-top:.6rem}
.mapa svg{min-width:40rem;width:100%;height:auto}
.tarjeta.principal{border:2px solid var(--acento)}
.boton.principal{background:var(--acento);color:var(--sobre-acento);border-color:var(--acento);font-weight:700}
.terminal:empty::before{content:attr(data-vacio);color:#8a8f99;font-family:var(--letra)}
.terminal{color-scheme:dark;background:var(--terminal);color:var(--terminal-texto);border-radius:.6rem;padding:.9rem;min-height:12rem;
  overflow:auto;white-space:pre;font-family:var(--mono);font-size:.85rem;line-height:1.45}
@media print{:root{color-scheme:light !important} body{background:#fff;color:#000;max-width:none;padding:0 12px;font-size:12.5px}
  #ccZoom,.no-imprimir{display:none !important} th{background:#eee;position:static} td,th{border-color:#999}
  tr:nth-child(even) td{background:#f6f6f6} h2{border-color:#999;break-before:auto} a{color:#000}
  .tapado td.resp,.tapado .tit{color:#000 !important;background:none !important}}
"""


BASE_FUENTES = "/archivos/material/fuentes/"   # dónde quedan las letras vistas desde la página (main() la cambia)
SUFIJO = ""                                    # "" o "_en": las páginas sueltas en inglés terminan en _en.html
EJEMPLOS = "ejemplos_html"                      # en inglés: ejemplos_html/en (si existe)
REPRODUCTOR = "reproductor.html"


def pagina(titulo: str, cuerpo: str, volver: str = "") -> str:
    return (f"<!DOCTYPE html><html lang='{idioma.actual()}'><head><meta charset='UTF-8'>{estilos.cabeza(BASE_FUENTES)}<title>{esc(titulo)}</title>"
            f"<style>{estilos.TOKENS}{CSS}</style></head><body>"
            + (f"<p class='ayuda no-imprimir'>{volver}</p>" if volver else "")
            + cuerpo + visual.ZOOM_HTML + "</body></html>")


# ---------------------------------------------------------------------
#  Pestaña Estudiar
# ---------------------------------------------------------------------

def examen_tema(clave: str) -> str:
    """La primera idea de "Lo que pregunta el examen" del tema (para el ticket de los casos ✅)."""
    examen = (estudio()["temas"].get(clave) or {}).get("examen") or []
    return examen[0] if examen else ""


def estudio_html(clave: str) -> str:
    t = estudio()["temas"].get(clave)
    if not t:
        return ""
    h = [f"<h2 style='border:0;margin-top:0;padding-top:0'>{esc(clave)} · {esc(t['titulo'])}</h2>",
         f"<div class='idea'><b>{tr('La idea en una frase:')}</b> {texto(t.get('idea', ''))}</div>"]
    def seccion(icono, titulo, items, como_lista=False):
        if not items:
            return
        h.append(f"<h3>{icono + ' ' if icono else ''}{titulo}</h3>")
        if como_lista:
            h.append("<ul>" + "".join(f"<li>{texto(x)}</li>" for x in items if isinstance(x, str)) + "</ul>")
        else:
            h.extend(tabla_guia(x["tabla"]) if isinstance(x, dict) else f"<p>{texto(x)}</p>" for x in items)
    seccion("", tr("Explicación sencilla"), t.get("explicacion"))
    seccion("", tr("Analogía"), t.get("analogia"))
    seccion("", tr("En La Tiendita"), t.get("tiendita"))
    if t.get("confusiones"):
        h.append(f"<h3>{tr('Confusiones típicas')}</h3><table><tr><th>{tr('Lo que se cree')}</th><th>{tr('Por qué está mal')}</th></tr>"
                 + "".join(f"<tr><td class='mal'>{texto(a)}</td><td>{texto(b)}</td></tr>" for a, b in t["confusiones"])
                 + "</table>" + "".join(f"<p class='ayuda'>{texto(n)}</p>" for n in t.get("confusiones_nota", [])))
    seccion("🎓", tr("Lo que pregunta el examen"), t.get("examen"), como_lista=True)
    seccion("🔀", tr("Examen vs producto actual"), t.get("producto"))
    if t.get("autoevaluacion"):
        h.append(f"<h3>{tr('Autoevaluación')}</h3><p class='ayuda'>{tr('Contesta en voz alta antes de abrir la respuesta.')}</p>")
        for item in t["autoevaluacion"]:
            pregunta, _, respuesta = item.partition(" — ")
            h.append(f"<details class='tarjeta'><summary>{texto(pregunta)}</summary>"
                     f"<p class='bien'>{texto(respuesta) if respuesta else tr('(la respuesta está en la guía)')}</p></details>")
    dominio = clave.split(".")[0]
    no_se_practica = L(NO_SE_PRACTICA)
    if no_se_practica.get(clave):
        pagina_guia = (estudio().get("paginas", {}).get("guia_estudio") or {}).get(clave)
        donde = tr(" (guía del Dominio {d}, p. {p})").format(d=dominio, p=pagina_guia) if pagina_guia else ""
        h.append(f"<div class='no-practica'><b>{tr('No se practica en el lab, pero lo pregunta el examen')}</b>" + donde
                 + "<ul>" + "".join(f"<li>{texto(x)}</li>" for x in no_se_practica[clave]) + "</ul></div>")
    h.append("<p class='ayuda'>" + tr("Texto de la guía de estudio del Dominio {d}. La guía completa está en "
             "<code>material/D{d}_guia_estudio.pdf</code>.").format(d=dominio) + "</p>")
    return "<div class='estudio'>" + "".join(h) + "</div>"


# ---------------------------------------------------------------------
#  Hoja de repaso, glosario y antipatrones
# ---------------------------------------------------------------------

FILTRO_JS = """<script>
function filtrar(n){
  document.querySelectorAll('[data-dominio]').forEach(e => e.style.display = (!n || e.dataset.dominio == n) ? '' : 'none');
  document.querySelectorAll('.filtro .boton').forEach(b => b.classList.toggle('activo', b.dataset.n == (n || '')));
}
const q = new URLSearchParams(location.search).get('n'); filtrar(q);
</script>"""


DESTAPAR_JS = """<script>
document.querySelectorAll('td.resp').forEach(td => {
  const ver = () => td.closest('tr').classList.toggle('visto');
  td.addEventListener('click', ver);
  td.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ver(); } });
});
</script>"""


def botones_filtro() -> str:
    return (f"<div class='filtro no-imprimir'><button class='boton' data-n='' onclick=\"filtrar('')\">{tr('Todos')}</button>"
            + "".join(f"<button class='boton' data-n='{d}' onclick=\"filtrar('{d}')\">{tr('Dominio')} {d}</button>" for d in range(1, 6))
            + "</div>")


def pagina_repaso(volver: str = "") -> str:
    rep = estudio()["repaso"]
    repaso_mini, distractores = L(REPASO_MINI), L(DISTRACTORES)
    h = ["<h1>" + tr("Hoja de repaso: ¿qué harías?") + "</h1>",
         "<p class='ayuda'>" + tr("Las tablas de repaso de las cinco guías, escritas como pequeñas situaciones del examen. "
         "Lee la situación, contesta en voz alta y luego mira la respuesta. La columna <b>Distractor típico</b> es la "
         "opción que suena bien pero está mal. Para practicar, tapa las respuestas y da clic (o Enter) en una para verla. "
         "Se puede imprimir.") + "</p>",
         "<p class='no-imprimir'><label><input type='checkbox' onchange=\"document.body.classList.toggle('tapado', this.checked);"
         "document.querySelectorAll('tr.visto').forEach(r => r.classList.remove('visto'))\"> "
         + tr("Tapar las respuestas (y el título, que a veces la delata)") + "</label> · <button class='boton' onclick='window.print()'>"
         + tr("Imprimir") + "</button></p>",
         botones_filtro()]
    for d in range(1, 6):
        filas = rep.get(str(d), [])
        if not filas:
            continue
        h.append(f"<section data-dominio='{d}'><h2>{tr('Dominio')} {d} · {esc(visual.NOMBRES_DOMINIOS[d])}</h2>"
                 f"<div class='tabla'><table><tr><th style='width:45%'>{tr('Situación')}</th><th>{tr('Respuesta')}</th>"
                 f"<th style='width:22%'>{tr('Distractor típico')}</th><th style='width:70px'>{tr('Tema')}</th></tr>"
                 + "".join(f"<tr><td><b class='tit'>{texto(a)}{'' if a.rstrip().endswith('?') else '.'}</b> {texto(repaso_mini.get(a, ''))}</td>"
                           f"<td class='resp' tabindex='0' role='button' aria-label='{tr('Ver la respuesta')}'>{texto(b)}</td>"
                           f"<td class='mal'>✘ {esc(distractores.get(a, '—'))}</td><td>{esc(c)}</td></tr>" for a, b, c in filas)
                 + "</table></div></section>")
    return pagina(tr("CCAR-F · Hoja de repaso"), "".join(h) + FILTRO_JS + DESTAPAR_JS, volver)


def pagina_glosario(volver: str = "") -> str:
    glo = estudio()["glosario"]
    glosario = L(GLOSARIO)
    en = {k.lower(): v[0] for k, v in glosario.items()}
    filas, vistos = [], set()
    for d in range(1, 6):
        for termino, significado, tema in glo.get(str(d), []):
            ingles = en.get(termino.lower(), "")
            vistos.add(termino.lower())
            filas.append((d, termino, significado, tema, ingles))
    for termino, (ingles, definicion) in glosario.items():
        if termino.lower() not in vistos:
            vistos.add(termino.lower())
            filas.append(("", termino, definicion, "", ingles))
    h = ["<h1>" + tr("Glosario") + "</h1>",
         "<p class='ayuda'>" + tr("Los términos de las cinco guías de estudio. Escribe para filtrar; la columna “En el examen” "
         "da el nombre en inglés cuando difiere o conviene reconocerlo.") + "</p>",
         "<input class='buscar no-imprimir' placeholder='" + tr("Busca un término o una palabra de la definición…") + "' "
         "oninput=\"const v=this.value.toLowerCase();document.querySelectorAll('tr[data-t]').forEach(r=>r.style.display=r.dataset.t.includes(v)?'':'none')\">",
         "<details class='tarjeta' open><summary>" + tr("<b>Palabras básicas</b> (si es tu primera vez)") + "</summary><div class='tabla'><table>"
         + "".join(f"<tr data-t='{esc((t + ' ' + d).lower())}' data-dominio=''><td style='width:24%'><b>{esc(t)}</b></td><td>{esc(d)}</td></tr>"
                   for t, (_, d) in L(GLOSARIO_BASICO).items()) + "</table></div></details>",
         botones_filtro(),
         f"<div class='tabla'><table><tr><th style='width:24%'>{tr('Término')}</th><th>{tr('Qué significa')}</th>"
         f"<th style='width:16%'>{tr('En el examen')}</th><th style='width:70px'>{tr('Tema')}</th></tr>"]
    for d, termino, significado, tema, ingles in filas:
        clave = esc(f"{termino} {significado} {ingles}".lower())
        h.append(f"<tr data-t='{clave}' data-dominio='{d}'><td><b>{esc(termino)}</b></td><td>{esc(significado)}</td>"
                 f"<td>{esc(ingles)}</td><td>{esc(tema)}</td></tr>")
    h.append("</table></div>")
    return pagina(tr("CCAR-F · Glosario"), "".join(h) + FILTRO_JS, volver)


def sin_prefijo(t: str) -> str:
    """Quita un "Antipatrón:" inicial (la página ya dice que es un antipatrón)."""
    return re.sub(r"^(Antipatrón|Anti-pattern):\s*", "", t)


def pagina_antipatrones(en_panel: bool, volver: str = "") -> str:
    li = idioma.actual()
    h = ["<h1>" + tr("Galería de antipatrones") + "</h1>",
         "<p class='ayuda'>" + tr("El examen vive de respuestas que suenan bien pero están mal. Aquí están juntas: primero las que "
         "puedes ver fallar en los labs, y luego las confusiones típicas de las cinco guías.") + "</p>",
         "<p class='ayuda'>" + tr("Cada caso dice si es <b>{a}</b> ({b}) o <b>{c}</b> ({d})").format(
             a=CLASES['trampa'][li], b=esc(CLASES['trampa']['ayuda_' + li]), c=CLASES['producto'][li],
             d=esc(CLASES['producto']['ayuda_' + li])) + "</p>",
         "<h2>" + tr("En los labs: velos fallar") + "</h2>"]
    producto = []
    for demo, extras in L(EXTRAS).items():
        for i, caso in enumerate(extras.get("casos", [])):
            if caso.get("tipo") != "falla":
                continue
            destino = producto if caso.get("clase") == "producto" else h
            dominio = demo.split(".")[0]
            botones = []
            if en_panel:
                botones.append(f"<a class='boton' href='/?n={dominio}&demo={demo}&caso={i}'>▶ {tr('Correrlo en el panel')}</a>")
                if caso.get("grabacion"):
                    botones.append(f"<a class='boton' href='/?n={dominio}&demo={demo}&grab={esc(caso['grabacion'])}'>{tr('Ver grabación')}</a>")
            elif caso.get("grabacion"):
                botones.append(f"<a class='boton' href='../grabaciones/{REPRODUCTOR}#{demo}/{esc(caso['grabacion'])}'>{tr('Ver grabación')}</a>")
            clase = CLASES.get(caso.get("clase", "trampa"), CLASES["trampa"])
            destino.append(f"<div class='tarjeta' data-dominio='{dominio}'><b>Demo {esc(demo)} · {esc(caso['nombre'])}</b> "
                           f"<span class='chip'>{clase[li]}</span>"
                           f"<p><span class='mal'>{tr('Parece correcto:')}</span> {texto(caso.get('parece', ''))}</p>"
                           f"<p><b>{tr('Por qué falla:')}</b> {texto(sin_prefijo(caso['explica']))}</p>"
                           + (f"<p>🎓 <b>{tr('En el examen:')}</b> {texto(caso['examen'])}</p>" if caso.get("examen") else "")
                           + "".join(botones) + "</div>")
    if producto:
        h.append(f"<h2>{CLASES['producto'][li]}: {tr('fallan hoy, pero no son error en el examen')}</h2>"
                 f"<p class='ayuda'>{esc(CLASES['producto']['ayuda_' + li])}</p>" + "".join(producto))
    h.append("<p class='ayuda'>" + tr("Varias demos tienen grabaciones para verlas sin key; lo demás se corre en el panel "
             "(o se graba con “Guardar como grabación”).") + "</p>")
    h.append("<h2>" + tr("Confusiones típicas de las guías") + "</h2>" + botones_filtro())
    temas = estudio()["temas"]
    for clave in sorted(temas, key=lambda c: [int(x) for x in c.split(".")]):
        t = temas[clave]
        if not t.get("confusiones"):
            continue
        h.append(f"<div data-dominio='{clave.split('.')[0]}'><h3>{esc(clave)} · {esc(t['titulo'])}</h3>"
                 f"<table><tr><th style='width:42%'>{tr('Lo que se cree')}</th><th>{tr('Por qué está mal')}</th></tr>"
                 + "".join(f"<tr><td class='mal'>{texto(a)}</td><td>{texto(b)}</td></tr>" for a, b in t["confusiones"])
                 + "</table></div>")
    return pagina(tr("CCAR-F · Antipatrones"), "".join(h) + FILTRO_JS, volver)


def pagina_escenarios(en_panel: bool, volver: str = "") -> str:
    """Los 6 escenarios del examen y qué demos los practican."""
    def enlace(demo):
        d = demo.split(".")[0]
        href = f"/?n={d}&demo={demo}" if en_panel else f"../{EJEMPLOS}/dominio{d}/index.html"
        return f"<a class='boton' href='{href}'>{esc(demo)}</a>"
    li = idioma.actual()
    h = ["<h1>" + tr("Los 6 escenarios del examen") + "</h1>",
         "<p class='ayuda'>" + tr("Según los sitios de preparación, las preguntas del examen se basan en estos escenarios y en cada "
         "examen salen 4 de los 6, al azar. Los nombres no vienen de la guía oficial; qué demos van con cada uno lo "
         "decidimos nosotros. Las demos van en el orden sugerido para practicar.") + " "
         + (tr("Clic en una demo para abrirla en el panel.") if en_panel else tr("Clic en una demo para ver su ejemplo.")) + "</p>",
         f"<table><tr><th style='width:26%'>{tr('Escenario')}</th><th>{tr('Qué se pregunta')}</th><th style='width:30%'>Demos</th></tr>"]
    for e in ESCENARIOS:
        h.append(f"<tr><td><b>{e['n']}. {esc(e[li])}</b>" + (f"<br><small>{esc(e['en'])}</small>" if li == "es" else "") + "</td>"
                 f"<td>{esc(e['prueba_' + li])}</td><td>{''.join(enlace(d) for d in e['demos'])}</td></tr>")
    h.append("</table>")
    # Práctica: situaciones del repaso que caen en las demos de cada escenario, con la respuesta tapada
    repaso = [f for filas in estudio()["repaso"].values() for f in filas]
    repaso_mini = L(REPASO_MINI)
    h.append("<h2>" + tr("Practica cada escenario") + "</h2><p class='ayuda'>" + tr("Situaciones cortas como las del examen. Contesta en voz "
             "alta y da clic (o Enter) en la respuesta para verla.") + "</p>")
    usadas = set()
    for e in ESCENARIOS:
        # Una situación por demo, en el orden de la lista del escenario (y sin repetir las de otro escenario si se puede)
        propias = []
        for demo in e["demos"]:
            de_demo = [f for f in repaso if demo in [t.strip() for t in str(f[2]).split(",")] and f not in propias]
            nuevas = [f for f in de_demo if f[0] not in usadas] or de_demo
            if nuevas:
                propias.append(nuevas[0])
            if len(propias) == 4:
                break
        usadas.update(f[0] for f in propias)
        if not propias:
            continue
        h.append(f"<h3>{e['n']}. {esc(e[li])}</h3><div class='tabla'><table><tr><th style='width:55%'>{tr('Situación')}</th>"
                 f"<th>{tr('Respuesta')}</th><th style='width:70px'>{tr('Tema')}</th></tr>"
                 + "".join(f"<tr><td>{texto(repaso_mini.get(a, a))}</td><td class='resp' tabindex='0' role='button' "
                           f"aria-label='{tr('Ver la respuesta')}'>{texto(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in propias)
                 + "</table></div>")
    return pagina(tr("CCAR-F · Escenarios del examen"), "<div class='tapado'>" + "".join(h) + "</div>" + DESTAPAR_JS, volver)


# ---------------------------------------------------------------------
#  Mapa conceptual de un dominio
# ---------------------------------------------------------------------

def mapa_svg(n: int, con_labs: bool) -> str:
    filas = L(MAPAS).get(n, [])
    if not filas:
        return ""
    nodos, aristas = [], []
    for i, (tema, idea) in enumerate(filas):
        etiqueta = tema + ("\n" + tr("ver lab") + " " + tema.split()[0] if con_labs else "")
        nodos.append({"id": f"t{i}", "fila": i, "col": 0, "tipo": "claude", "texto": etiqueta})
        nodos.append({"id": f"i{i}", "fila": i, "col": 1, "tipo": "nota", "texto": idea})
        aristas.append((f"t{i}", f"i{i}", tr("idea clave")))
    svg = visual.svg_grafo(nodos, aristas, columnas=2)
    svg = re.sub(r"<!--tipos:[^>]*-->", "", svg)
    return ("<div class='tarjeta'><b>" + tr("Mapa del dominio") + "</b><p class='ayuda'>" + tr("Cada tema con la idea que más pregunta el "
            "examen. Úsalo para ubicarte antes de estudiar un tema y para repasar al final.") + "</p><div class='mapa'>" + svg + "</div></div>")


# ---------------------------------------------------------------------
#  Sin Python: reproductor de grabaciones y EMPIEZA_AQUI.html
# ---------------------------------------------------------------------

def pagina_reproductor(js_ansi: str) -> str:
    grabaciones = []
    carpeta = CARPETA / "grabaciones"
    for demo_dir in sorted(p for p in carpeta.iterdir() if p.is_dir()) if carpeta.exists() else []:
        nombre_demo, rel = demo_dir.name, demo_dir.name
        if idioma.en() and any((demo_dir / "en").glob("*.json")):      # en inglés, las grabaciones en inglés
            demo_dir, rel = demo_dir / "en", f"{demo_dir.name}/en"
        for f in sorted(demo_dir.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            pagina_rel = f"{rel}/{f.stem}.html" if (demo_dir / f"{f.stem}.html").exists() else ""
            grabaciones.append({"id": f"{nombre_demo}/{f.name}", "demo": nombre_demo, "titulo": tr(d.get("titulo", f.stem)),
                                "simulada": d.get("simulada", False), "lineas": d.get("lineas", []),
                                "tiempos": d.get("tiempos", []), "pagina": pagina_rel,
                                "resultado": (d.get("resultado") or {}).get("texto", "")})
    datos = json.dumps(grabaciones, ensure_ascii=False).replace("</", "<\\/")
    textos = json.dumps({k: tr(k) for k in ("(ejemplo simulado)", "Reproduciendo…", "✔ Terminó.", "Resultado:",
                                             "Ver el diagrama de esta corrida")}, ensure_ascii=False).replace("</", "<\\/")
    cuerpo = "<h1>" + tr("Grabaciones de los labs") + "</h1><p class='ayuda'>" + tr(
        "Corridas guardadas que puedes ver sin Python y sin API key. Elige una y dale ▶. Las que dicen "
        "“ejemplo simulado” usan respuestas armadas, no del modelo real.") + "</p>" + f"""
<div id='lista'></div>
<p id='estado' class='ayuda'></p>
<pre id='salida' class='terminal' data-vacio='{tr("Elige una grabación arriba y dale ▶.")}'></pre>
<p id='final'></p>
<script>
const GRAB = {datos};
const TX = {textos};
{js_ansi}
function esc(t){{ return String(t).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}
const dormir = ms => new Promise(r => setTimeout(r, ms));
let ACTUAL = null;
document.getElementById('lista').innerHTML = GRAB.map((g, i) => `<button class='boton' onclick='reproducir(${{i}})'>▶ Demo ${{esc(g.demo)}} · ${{esc(g.titulo)}}${{g.simulada ? ' <small>' + TX['(ejemplo simulado)'] + '</small>' : ''}}</button>`).join('');
async function reproducir(i){{
  const g = GRAB[i], yo = ACTUAL = {{}};
  const out = document.getElementById('salida'); out.replaceChildren(); ESTILO = {{}};
  document.getElementById('final').replaceChildren();
  let previo = 0;
  for (let k = 0; k < g.lineas.length; k++) {{
    if (ACTUAL !== yo) return;
    const espera = Math.min(900, Math.max(0, ((g.tiempos[k] || 0) - previo) * 1000)); previo = g.tiempos[k] || previo;
    if (espera > 25) await dormir(espera);
    out.insertAdjacentHTML('beforeend', ansiAHtml(g.lineas[k]) + '\\n'); out.scrollTop = out.scrollHeight;
    document.getElementById('estado').textContent = `${{TX['Reproduciendo…']}} ${{k + 1}}/${{g.lineas.length}}`;
  }}
  document.getElementById('estado').textContent = TX['✔ Terminó.'];
  document.getElementById('final').innerHTML = (g.resultado ? `<b>${{TX['Resultado:']}}</b> ${{esc(g.resultado)}} ` : '')
    + (typeof g.pagina === 'string' && /^[\\w.\\-\\/]+\\.html$/.test(g.pagina) && !g.pagina.includes('..') ? `<a class='boton' href='${{esc(g.pagina)}}'>${{TX['Ver el diagrama de esta corrida']}}</a>` : '');
}}
const h = decodeURIComponent(location.hash.slice(1)); const k = GRAB.findIndex(g => g.id === h); if (k >= 0) reproducir(k);
</script>"""
    return pagina(tr("CCAR-F · Grabaciones"), cuerpo, f"<a href='../EMPIEZA_AQUI{SUFIJO}.html'>{tr('← Empieza aquí')}</a>")


def pagina_empieza(slides: dict) -> str:
    guias = "".join(f"<a class='boton' href='material/D{d}_guia_estudio.pdf'>D{d}</a>"
                    for d in range(1, 6) if (CARPETA / f"material/D{d}_guia_estudio.pdf").exists())
    def deck_url(d, idioma):
        local = CARPETA / f"material/D{d}_slides{'' if idioma == 'es' else '_en'}.pdf"
        return f"material/{local.name}" if local.exists() else slides.get(d, {}).get(idioma)
    deck = "".join(f"<a class='boton' href='{deck_url(d, 'es')}'>D{d}</a>" for d in range(1, 6) if deck_url(d, "es"))
    deck_en = "".join(f"<a class='boton' href='{deck_url(d, 'en')}'>D{d} (EN)</a>" for d in range(1, 6) if deck_url(d, "en"))
    otro = (tr("<p class='ayuda'><a href='EMPIEZA_AQUI_en.html'>English version</a></p>") if not idioma.en()
            else "<p class='ayuda'><a href='EMPIEZA_AQUI.html'>Versión en español</a></p>")
    return pagina(tr("CCAR-F · Empieza aquí"), otro + tr(EMPIEZA).format(guias=guias, deck=deck, deck_en=deck_en, s=SUFIJO, ej=EJEMPLOS))


EMPIEZA = """
<h1>CCAR-F · Empieza aquí</h1>
<p class='ayuda'>Todo lo de esta carpeta, en un solo lugar. Lo de la primera parte se abre con doble clic, sin instalar nada.</p>
<h2>Sin instalar nada</h2>
<div class='tarjeta principal'><b>Empieza aquí: grabaciones</b><p class='ayuda'>Corridas guardadas de los labs, como si las corrieras tú. No necesitas Python ni API key.</p>
<a class='boton principal' href='grabaciones/reproductor{s}.html'>Abrir grabaciones</a></div>
<div class='tarjeta'><b>Ejemplos de los labs</b><p class='ayuda'>Qué muestra cada demo, con diagramas y su explicación.</p>
<a class='boton' href='{ej}/index.html'>Abrir ejemplos</a></div>
<div class='tarjeta'><b>Los 6 escenarios del examen</b><p class='ayuda'>En qué situaciones pregunta el examen y qué demos practican cada una.</p>
<a class='boton' href='material/escenarios{s}.html'>Abrir escenarios</a></div>
<div class='tarjeta'><b>Hoja de repaso</b><p class='ayuda'>Pequeñas situaciones del examen y qué responder, de los cinco dominios. Imprimible.</p>
<a class='boton' href='material/repaso{s}.html'>Abrir hoja de repaso</a></div>
<div class='tarjeta'><b>Galería de antipatrones</b><p class='ayuda'>Lo que suena bien pero está mal, tema por tema.</p>
<a class='boton' href='material/antipatrones{s}.html'>Abrir galería</a></div>
<div class='tarjeta'><b>Glosario</b><p class='ayuda'>Los términos de las guías, con buscador.</p>
<a class='boton' href='material/glosario{s}.html'>Abrir glosario</a></div>
<div class='tarjeta'><b>Guías de estudio (PDF)</b><br>{guias}</div>
<div class='tarjeta'><b>Slides (PDF)</b><p class='ayuda'>Las presentaciones de cada dominio, en español y en inglés.</p>{deck}<br>{deck_en}</div>
<h2>Con Python: el panel</h2>
<div class='tarjeta'><p>El panel corre las demos con controles, muestra la guía de cada tema junto al lab y compara corridas.</p>
<ol><li>Instala Python 3.10 o más reciente.</li>
<li>Abre una terminal en esta carpeta (Mac: clic derecho en la carpeta → <b>Nuevo terminal en la carpeta</b>; Windows: escribe <code>powershell</code> en la barra de dirección de la carpeta).</li>
<li>Crea el entorno: <code>python3 -m venv .venv</code> (en Windows, <code>python -m venv .venv</code>), actívalo y corre <code>pip install -r requirements.txt</code>.</li>
<li>Copia <code>.env.example</code> como <code>.env</code> (<code>cp .env.example .env</code>; en Windows, <code>copy</code>) y pega tu API key. Ojo: el archivo empieza con punto, está oculto, y no debe terminar en <code>.txt</code>.</li>
<li>Corre <code>python panel.py</code>: se abre en tu navegador.</li></ol>
<p class='ayuda'>Los pasos con más detalle (y qué hacer si algo falla) están en el archivo <code>README.md</code> de esta carpeta.</p></div>
<h2>Cómo sacar tu API key</h2>
<div class='tarjeta'><ol>
<li>Entra a <a href='https://platform.claude.com/settings/keys'>platform.claude.com → Settings → API keys</a> (crea tu cuenta si no tienes).</li>
<li>Pon primero un <b>límite de gasto</b> bajo (por ejemplo 5 USD al mes) en la sección de límites o de facturación.
Correr todas las demos una vez cuesta centavos.</li>
<li>Da clic en <b>Create key</b>, ponle un nombre (por ejemplo <i>labs-ccarf</i>) y, si te deja, una fecha de vencimiento corta.</li>
<li>Copia la key en ese momento: <b>solo se muestra una vez</b>.</li>
<li>Pégala en tu archivo <code>.env</code> después de <code>ANTHROPIC_API_KEY=</code>. No la pegues en chats, código ni capturas.</li>
<li>Cuando termines de estudiar, bórrala en la misma página.</li></ol>
<p class='ayuda'>¿Sin key? Usa las grabaciones: no gastan nada.</p></div>"""


def escribir_estaticas() -> None:
    import panel   # aquí, para no importar el panel al cargar este módulo
    js = panel.PAGINA
    js_ansi = js[js.index("// ---- Colores:"):js.index("async function api(")]
    (CARPETA / "material").mkdir(exist_ok=True)
    slides = {d: m.get("slides", {}) for d, m in panel.MATERIAL_EN_LINEA.items()}
    global BASE_FUENTES, SUFIJO, REPRODUCTOR, EJEMPLOS
    for lengua, sufijo in (("es", ""), ("en", "_en")):
        idioma.usar(lengua)
        SUFIJO, REPRODUCTOR = sufijo, f"reproductor{sufijo}.html"
        EJEMPLOS = "ejemplos_html/en" if sufijo and (CARPETA / "ejemplos_html/en/index.html").exists() else "ejemplos_html"
        volver = f"<a href='../EMPIEZA_AQUI{sufijo}.html'>{tr('← Empieza aquí')}</a>"
        BASE_FUENTES = "fuentes/"            # material/*.html
        for nombre, hacer in (("repaso", lambda: pagina_repaso(volver)), ("glosario", lambda: pagina_glosario(volver)),
                              ("antipatrones", lambda: pagina_antipatrones(False, volver)),
                              ("escenarios", lambda: pagina_escenarios(False, volver))):
            (CARPETA / f"material/{nombre}{sufijo}.html").write_text(hacer(), encoding="utf-8")
        BASE_FUENTES = "../material/fuentes/"   # grabaciones/reproductor.html
        if (CARPETA / "grabaciones").exists():
            (CARPETA / f"grabaciones/{REPRODUCTOR}").write_text(pagina_reproductor(js_ansi), encoding="utf-8")
        BASE_FUENTES = "material/fuentes/"      # EMPIEZA_AQUI.html (en la raíz)
        (CARPETA / f"EMPIEZA_AQUI{sufijo}.html").write_text(pagina_empieza(slides), encoding="utf-8")
    idioma.usar("es")
    SUFIJO, REPRODUCTOR, BASE_FUENTES, EJEMPLOS = "", "reproductor.html", "/archivos/material/fuentes/", "ejemplos_html"
    print("Listo (en español y, con _en, en inglés): EMPIEZA_AQUI.html, material/repaso.html, material/glosario.html, "
          "material/antipatrones.html, material/escenarios.html, grabaciones/reproductor.html")


if __name__ == "__main__":
    escribir_estaticas()

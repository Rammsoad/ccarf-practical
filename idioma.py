"""
idioma.py · Español / inglés para el panel y las páginas.

El botón ES / EN del panel guarda la cookie `idioma`; panel.py la lee en cada petición y llama a `usar()`.
Los textos se escriben en español (en extras.py, estudio.json, los labs) y su traducción vive en `idiomas/`:

- idiomas/en.json         {"texto en español": "English text"}: casos, glosario, Estudiar, títulos, plantillas…
- idiomas/guias_en.json   {"1.1": "guía de la demo en markdown"}: las guías GUIA_N_M en inglés.

Si un texto no tiene traducción, sale en español (nada se rompe). Si cambias un texto en español, su traducción
deja de aplicar hasta que la actualices: `python _dev/traduccion.py reporte` dice cuántos faltan.
"""
from __future__ import annotations

import contextvars
import json
import re
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "idiomas"
IDIOMAS = ("es", "en")
_ACTUAL: contextvars.ContextVar[str] = contextvars.ContextVar("idioma", default="es")
_CACHE: dict = {}

# Campos que nunca se traducen: valores que se le mandan al lab, identificadores y nombres de archivo.
NO_TRADUCIR = frozenset({"valores", "tipo", "clase", "final", "grabacion", "demos", "n", "url", "valor",
                         "clave", "paginas", "nombre_es", "esperado"})


_FIJO: list = [None]     # en un lab (un proceso, varios hilos) el idioma es uno solo: fijar()


def usar(idioma: str) -> None:
    """Fija el idioma de la petición actual (cada hilo del servidor tiene el suyo)."""
    _ACTUAL.set(idioma if idioma in IDIOMAS else "es")


def fijar(idioma: str) -> None:
    """Fija el idioma para todo el proceso, incluidos sus hilos (lo usan los labs)."""
    _FIJO[0] = idioma if idioma in IDIOMAS else "es"


def actual() -> str:
    return _FIJO[0] or _ACTUAL.get()


def en() -> bool:
    return actual() == "en"


def _leer(nombre: str) -> dict:
    ruta = CARPETA / nombre
    try:
        version = ruta.stat().st_mtime
    except OSError:
        return {}
    if _CACHE.get(nombre, (None,))[0] != version:
        try:
            _CACHE[nombre] = (version, json.loads(ruta.read_text(encoding="utf-8")))
        except ValueError:
            _CACHE[nombre] = (version, {})
        _CACHE.pop(("datos", nombre), None)
    return _CACHE[nombre][1]


def tabla() -> dict:
    return _leer("en.json")


def guia(clave: str, texto_es: str) -> str:
    """La guía de una demo en el idioma actual (la de español si no hay traducción)."""
    return (_leer("guias_en.json").get(clave) or texto_es) if en() else texto_es


def tr(texto: str) -> str:
    """Un texto fijo (de una plantilla) en el idioma actual."""
    return tabla().get(texto, texto) if en() else texto


def traducir(obj, tab: dict | None = None):
    """Copia de obj (dict, lista, tupla, texto) con cada texto traducido; las llaves también (así las búsquedas
    por texto siguen cuadrando). No toca los campos de NO_TRADUCIR."""
    tab = tabla() if tab is None else tab
    if isinstance(obj, str):
        return tab.get(obj, obj)
    if isinstance(obj, dict):
        return {(tab.get(k, k) if isinstance(k, str) else k): (v if k in NO_TRADUCIR else traducir(v, tab))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(traducir(x, tab) for x in obj)
    return obj


_DATOS: dict = {}


def L(obj):
    """obj en el idioma actual. Para datos fijos (los de extras.py, estudio.json): guarda la copia traducida."""
    if not en():
        return obj
    tab = tabla()
    clave = (id(obj), id(tab))
    if clave not in _DATOS:
        if len(_DATOS) > 400:
            _DATOS.clear()
        _DATOS[clave] = (obj, traducir(obj, tab))     # guarda obj para que su id no se reutilice
    return _DATOS[clave][1]


# ---------------------------------------------------------------------
#  Lo que imprimen los labs al correr (idiomas/salida_en.json): textos exactos y plantillas con huecos ⟦0⟧
# ---------------------------------------------------------------------
_PLANTILLAS: dict = {}


def _compiladas(tab: dict) -> list:
    if _PLANTILLAS.get("tab") is not tab:
        lista = []
        for clave, ingles in tab.get("plantillas", {}).items():
            trozos = re.split(r"⟦(\d+)⟧", clave)
            literales = trozos[0::2]
            patron = "".join(re.escape(lit) + ("(.*?)" if i < len(literales) - 1 else "") for i, lit in enumerate(literales))
            lista.append((len("".join(literales)), literales[0], literales[-1], re.compile(patron, re.S), ingles))
        lista.sort(key=lambda x: -x[0])     # primero las más específicas
        _PLANTILLAS.update(tab=tab, lista=lista)
    return _PLANTILLAS["lista"]


def _salida_una(texto: str, tab: dict):
    exactos = tab.get("exactos", {})
    if texto in exactos:
        return exactos[texto]
    for _, inicio, fin, patron, ingles in _compiladas(tab):
        if not (texto.startswith(inicio) and texto.endswith(fin)):
            continue
        m = patron.fullmatch(texto)
        if m and not any(" · " in (g or "") for g in m.groups()):     # un hueco no se traga varias piezas " · "
            def hueco(h):          # lo que llenó cada hueco también se traduce (texto exacto o plantilla más corta)
                g = m.group(int(h.group(1)) + 1)
                return exactos.get(g) or (_salida_una(g, tab) if g and len(g) < len(texto) else None) or g
            return re.sub(r"⟦(\d+)⟧", hueco, ingles)
    return None


def salida(texto):
    """Un texto que imprime un lab, en el idioma actual (si no hay traducción, tal cual)."""
    if not en() or not isinstance(texto, str) or not texto.strip():
        return texto
    tab = _leer("salida_en.json")
    r = _salida_una(texto, tab)
    if r is not None:
        return r
    if " · " in texto and "\n" not in texto:     # piezas unidas con " · " (p. ej. una comparación): una por una
        piezas = texto.split(" · ")
        nuevas = [_salida_una(x, tab) for x in piezas]
        if any(n is not None for n in nuevas):
            return " · ".join(n if n is not None else x for n, x in zip(nuevas, piezas))
    if "\n" in texto:          # varias líneas: se intenta línea por línea
        lineas = texto.split("\n")
        nuevas = [(_salida_una(l, tab) if l.strip() else None) for l in lineas]
        if any(n is not None for n in nuevas):
            return "\n".join(n if n is not None else l for n, l in zip(nuevas, lineas))
    return texto


def parchar_rich() -> None:
    """Con CCARF_IDIOMA=en: traduce lo que los labs imprimen con rich (print, Panel, Table, Rule), sin tocar cada línea."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.table import Table
    if getattr(Console, "_ccarf_parchado", False):
        return
    Console._ccarf_parchado = True
    print_original, input_original = Console.print, Console.input

    def imprimir(self, *objetos, **kw):
        return print_original(self, *[salida(o) if isinstance(o, str) else o for o in objetos], **kw)

    def preguntar(self, prompt="", **kw):
        return input_original(self, salida(prompt) if isinstance(prompt, str) else prompt, **kw)
    Console.print, Console.input = imprimir, preguntar

    panel_init = Panel.__init__

    def panel(self, renderable="", *a, **kw):
        for k in ("title", "subtitle"):
            if isinstance(kw.get(k), str):
                kw[k] = salida(kw[k])
        return panel_init(self, salida(renderable) if isinstance(renderable, str) else renderable, *a, **kw)
    Panel.__init__ = panel

    tabla_init, columna, fila = Table.__init__, Table.add_column, Table.add_row

    def tabla(self, *columnas, **kw):
        for k in ("title", "caption"):
            if isinstance(kw.get(k), str):
                kw[k] = salida(kw[k])
        return tabla_init(self, *[salida(c) if isinstance(c, str) else c for c in columnas], **kw)

    def agregar_columna(self, header="", *a, **kw):
        return columna(self, salida(header) if isinstance(header, str) else header, *a, **kw)

    def agregar_fila(self, *celdas, **kw):
        return fila(self, *[salida(c) if isinstance(c, str) else c for c in celdas], **kw)
    Table.__init__, Table.add_column, Table.add_row = tabla, agregar_columna, agregar_fila

    regla_init = Rule.__init__

    def regla(self, title="", *a, **kw):
        return regla_init(self, salida(title) if isinstance(title, str) else title, *a, **kw)
    Rule.__init__ = regla

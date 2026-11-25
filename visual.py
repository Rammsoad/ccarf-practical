"""
visual.py · Modo HTML compartido por los labs del CCAR-F
========================================================

Lo usan todos los lab_dominioN.py. No se corre solo.

Qué hace:
  - Decide si el modo HTML está encendido (MODO_HTML del lab, o --html / --sin-html en el comando).
  - Dibuja los diagramas de cada corrida como SVG (cajas y flechas, barras).
  - Guarda cada corrida como página nueva en salidas_html/dominioN/ y arma el índice
    con Anterior / Siguiente para comparar corridas.
  - Mantiene salidas_html/index.html (portada con los 5 dominios).
  - Escribe la nota automática y el costo de cada corrida, y el "paso a paso" de los diagramas que lo traen.
  - En el índice pone arriba de cada demo "¿De qué va esta demo?", sacado de su guía.
  - Guarda el resultado de la corrida (registrar_resultado) para que el panel lo muestre.

Colores (los mismos en todos los labs):
  azul = Claude · gris = tu código · verde = salió bien · rojo = bloqueado o falló
  morado = hook, gate o fork · amarillo = datos de entrada
"""
from __future__ import annotations

import atexit
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import time
import uuid

import idioma
from pathlib import Path

CARPETA_LABS = Path(__file__).resolve().parent

# Estado del modo HTML (lo llena configurar())
ESTADO = {"activo": False, "dominio": 0, "script": "lab_dominioN.py", "consola": None}
DIAGRAMAS: list[str] = []
TRAZA: list[dict] = []          # tool_use / tool_result que registran las demos del Agent SDK

COLORES = {
    #  tipo        relleno     borde      significado (para la leyenda)
    "claude":   ("#1f3b57", "#58a6ff", "Claude: lo que responde o pide"),
    "codigo":   ("#2d2d2d", "#9e9e9e", "Tu código o una tool"),
    "ok":       ("#1e3d2a", "#3fb950", "Salió bien / permitido / cubierto"),
    "bloqueo":  ("#4a1f1f", "#f85149", "Bloqueado / falló / faltó"),
    "hook":     ("#3b2453", "#bc8cff", "Hook, gate, fork o control"),
    "nota":     ("#3a3420", "#d29922", "Datos de entrada"),
}

PRE_HTML = ("<pre style=\"font-family:Menlo,'DejaVu Sans Mono',consolas,'Courier New',monospace\">"
            "<code style=\"font-family:inherit\">")


# ---------------------------------------------------------------------
#  Configuración
# ---------------------------------------------------------------------

def configurar(dominio: int, modo_html: bool) -> bool:
    """Lee --html / --sin-html (y los quita de sys.argv). Devuelve si el modo HTML queda encendido."""
    activo = ("--html" in sys.argv) or (modo_html and "--sin-html" not in sys.argv)
    sys.argv[:] = [a for a in sys.argv if a not in ("--html", "--sin-html")]
    ESTADO.update(activo=activo, dominio=dominio, script=Path(sys.argv[0]).name or f"lab_dominio{dominio}.py")
    return activo


def usar_consola(consola) -> None:
    ESTADO["consola"] = consola


def carpeta_relativa() -> str:
    return f"salidas_html/dominio{ESTADO['dominio']}"


def activo() -> bool:
    return ESTADO["activo"]


def panel_estado():
    """Texto del panel '🌐 Modo HTML' del menú (el lab lo imprime con su Panel)."""
    script = ESTADO["script"]
    if ESTADO["activo"]:
        texto = (f"[bold green]ENCENDIDO[/]: cada corrida se guarda como página nueva en [bold]{carpeta_relativa()}/[/], "
                 "con un diagrama de lo que pasó.\n"
                 f"Para recorrer y comparar corridas abre [bold]{carpeta_relativa()}/index.html[/].\n"
                 f"¿Todavía no corres nada? En [bold]ejemplos_html/dominio{ESTADO['dominio']}/index.html[/] ves lo que "
                 "posiblemente vas a ver.\n\n"
                 "¿Prefieres ajustar las variables con botones y ver todo en el navegador?  python panel.py\n\n"
                 "Apagar siempre:      MODO_HTML = False   (en la configuración general, arriba en el lab)\n"
                 f"Apagar una vez:      python {script} <demo> --sin-html")
        return texto, "green"
    texto = ("[bold yellow]APAGADO[/]: la salida solo se ve en la terminal.\n\n"
             "Encender siempre:    MODO_HTML = True    (en la configuración general, arriba en el lab)\n"
             f"Encender una vez:    python {script} <demo> --html")
    return texto, "yellow"


def aplicar_ajustes(variables: dict) -> None:
    """Ajustes que manda el panel web (panel.py) para UNA corrida, sin tocar los valores escritos en el lab.
    Llegan en la variable de entorno CCARF_AJUSTES como JSON: {"D12_DESCOMPOSICION": "estrecha", ...}."""
    import os
    datos = os.environ.get("CCARF_AJUSTES")
    if not datos:
        return
    try:
        ajustes = json.loads(datos)
    except ValueError:
        return
    aplicados = []
    for nombre, valor in ajustes.items():
        if nombre in variables and (nombre in ("MODELO", "DETALLE") or (nombre[:1] == "D" and nombre[1:3].isdigit())):
            if variables[nombre] != valor:
                aplicados.append(f"{nombre} = {json.dumps(valor, ensure_ascii=False)}")
            variables[nombre] = valor
    consola = ESTADO["consola"]
    if consola is not None and aplicados:
        consola.print("🎛  Ajustes del panel para esta corrida: " + " · ".join(aplicados), markup=False, highlight=False)


# ---------------------------------------------------------------------
#  Utilidades de texto
# ---------------------------------------------------------------------

def xml(texto) -> str:
    return str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def corto(texto, n: int = 60) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def _partir(texto: str, ancho_px: float, px_por_letra: float = 7.4) -> list[str]:
    maximo = max(8, int((ancho_px - 16) / px_por_letra))
    lineas = []
    for parrafo in str(texto).split("\n"):
        actual = ""
        for palabra in parrafo.split(" "):
            if len(actual) + len(palabra) + 1 > maximo and actual:
                lineas.append(actual)
                actual = palabra
            else:
                actual = f"{actual} {palabra}".strip()
        lineas.append(actual)
    return lineas


def _marca_tipos(tipos) -> str:
    return f"<!--tipos:{','.join(sorted(set(tipos)))}-->"


# ---------------------------------------------------------------------
#  Dibujos
# ---------------------------------------------------------------------

def svg_grafo(nodos: list[dict], aristas: list[tuple], columnas: int | None = None) -> str:
    """Cajas por filas y flechas entre ellas.
    nodos:   {"id", "fila", "texto", "tipo", opcional "col" (si se pasa `columnas`), opcional "completo": True}
    aristas: (id_origen, id_destino, etiqueta)
    La primera línea del texto de cada caja sale en negritas.
    """
    ancho, margen = 1000, 20
    filas = sorted({n["fila"] for n in nodos})
    pos = {}
    y = margen
    for fila in filas:
        en_fila = [n for n in nodos if n["fila"] == fila]
        alto_fila = 0
        for i, n in enumerate(en_fila):
            ancho_col = (ancho - 2 * margen) / (columnas or len(en_fila))
            col = n.get("col", i) if columnas else i
            hueco = 80 if (columnas or len(en_fila)) > 1 else 40
            w = ancho_col - hueco
            x = margen + col * ancho_col + hueco / 2
            if n.get("completo"):
                w, x = ancho - 2 * margen - hueco, margen + hueco / 2
            lineas = _partir(idioma.salida(n["texto"]), w)
            h = 16 + 17 * len(lineas)
            pos[n["id"]] = [x, y, w, h, lineas, n.get("tipo", "codigo"), n.get("paso", 0)]
            alto_fila = max(alto_fila, h)
        for n in en_fila:
            pos[n["id"]][1] = y + (alto_fila - pos[n["id"]][3]) / 2
        y += alto_fila + 46
    alto = y - 46 + margen

    punta = "punta_" + uuid.uuid4().hex[:8]   # id único: el índice junta diagramas de muchas corridas
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" '
              'font-family="Atkinson Hyperlegible Next, Inter, Segoe UI, Helvetica, Arial, sans-serif" font-size="13">',
              f'<defs><marker id="{punta}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
              'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#bbbbbb"/></marker></defs>']
    for origen, destino, etiqueta in aristas:
        if origen not in pos or destino not in pos:
            continue
        etiqueta = idioma.salida(etiqueta)
        paso = pos[destino][6]          # la flecha aparece junto con la caja a la que llega
        partes.append(f'<g data-paso="{paso}">' if paso else "<g>")
        xa, ya, wa, ha, *_ = pos[origen]
        xb, yb, wb, hb, *_ = pos[destino]
        if abs((ya + ha / 2) - (yb + hb / 2)) < 2:          # misma fila → flecha horizontal
            if xb > xa:
                x1, y1, x2, y2 = xa + wa, ya + ha / 2, xb, yb + hb / 2
            else:
                x1, y1, x2, y2 = xa, ya + ha / 2, xb + wb, yb + hb / 2
        else:                                              # otra fila → de abajo hacia arriba
            x1, y1, x2, y2 = xa + wa / 2, ya + ha, xb + wb / 2, yb
        partes.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="#bbbbbb" '
                      f'stroke-width="1.6" marker-end="url(#{punta})"/>')
        if etiqueta:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if abs(y1 - y2) < 2:
                my -= 13
            ancho_et = 7 * len(etiqueta) + 10
            partes.append(f'<rect x="{mx - ancho_et / 2:.0f}" y="{my - 10:.0f}" width="{ancho_et:.0f}" height="18" '
                          'rx="4" fill="#1b1c18"/>')
            partes.append(f'<text x="{mx:.0f}" y="{my + 3:.0f}" fill="#d0d0d0" font-size="11.5" '
                          f'text-anchor="middle">{xml(etiqueta)}</text>')
        partes.append("</g>")
    for x, y0, w, h, lineas, tipo, paso in pos.values():
        partes.append(f'<g data-paso="{paso}">' if paso else "<g>")
        relleno, borde, _ = COLORES.get(tipo, COLORES["codigo"])
        partes.append(f'<rect x="{x:.0f}" y="{y0:.0f}" width="{w:.0f}" height="{h:.0f}" rx="9" fill="{relleno}" '
                      f'stroke="{borde}" stroke-width="1.6"/>')
        for i, linea in enumerate(lineas):
            peso = ' font-weight="600"' if i == 0 else ""
            partes.append(f'<text x="{x + w / 2:.0f}" y="{y0 + 21 + 17 * i:.0f}" fill="#f0f0f0" '
                          f'text-anchor="middle"{peso}>{xml(linea)}</text>')
        partes.append("</g>")
    partes.append("</svg>")
    return _marca_tipos(v[5] for v in pos.values()) + "".join(partes)


def svg_barras(filas: list[tuple], maximo: float | None = None, unidad: str = "") -> str:
    """Barras horizontales: (etiqueta, valor, tipo) o (etiqueta, valor, tipo, texto_del_valor)."""
    ancho, izq, margen = 1000, 260, 16
    maximo = maximo or max([f[1] for f in filas] + [1])
    ancho_util = ancho - izq - margen - 120
    alto = margen * 2 + 34 * len(filas)
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" '
              'font-family="Atkinson Hyperlegible Next, Inter, Segoe UI, Helvetica, Arial, sans-serif" font-size="13">']
    for k, fila in enumerate(filas):
        etiqueta, valor, tipo = fila[:3]
        etiqueta = idioma.salida(etiqueta)
        texto_valor = fila[3] if len(fila) > 3 else f"{valor:,.0f}{unidad}"
        y = margen + 34 * k
        relleno, borde, _ = COLORES.get(tipo, COLORES["codigo"])
        w = max(3, valor / maximo * ancho_util) if maximo else 3
        partes.append(f'<text x="{izq - 12}" y="{y + 17}" fill="#f0f0f0" text-anchor="end">{xml(corto(etiqueta, 34))}</text>')
        partes.append(f'<rect x="{izq}" y="{y}" width="{w:.0f}" height="24" rx="6" fill="{relleno}" stroke="{borde}" stroke-width="1.6"/>')
        partes.append(f'<text x="{izq + w + 8:.0f}" y="{y + 17}" fill="#d0d0d0" font-size="12.5">{xml(texto_valor)}</text>')
    partes.append("</svg>")
    return _marca_tipos(f[2] for f in filas) + "".join(partes)


def svg_barras_tiempo(barras: list[tuple], total: float) -> str:
    """Barras tipo Gantt: (nombre, inicio_s, duracion_s, tipo). Escala común en segundos."""
    ancho, izq, margen = 1000, 230, 20
    escala_max = max([total] + [i + d for _, i, d, _ in barras]) or 1
    ancho_util = ancho - izq - margen - 60
    alto = margen * 2 + 34 * len(barras) + 26
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="{ancho}" height="{alto}" '
              'font-family="Atkinson Hyperlegible Next, Inter, Segoe UI, Helvetica, Arial, sans-serif" font-size="13">']
    for k, (nombre, inicio, dur, tipo) in enumerate(barras):
        y = margen + 34 * k
        relleno, borde, _ = COLORES.get(tipo, COLORES["codigo"])
        x = izq + inicio / escala_max * ancho_util
        w = max(3, dur / escala_max * ancho_util)
        partes.append(f'<text x="{izq - 12}" y="{y + 17}" fill="#f0f0f0" text-anchor="end">{xml(corto(nombre, 30))}</text>')
        partes.append(f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="24" rx="6" fill="{relleno}" stroke="{borde}" stroke-width="1.6"/>')
        partes.append(f'<text x="{x + w + 8:.0f}" y="{y + 17}" fill="#d0d0d0" font-size="12">{dur:.1f} s</text>')
    y = margen + 34 * len(barras) + 8
    partes.append(f'<line x1="{izq}" y1="{y}" x2="{izq + ancho_util}" y2="{y}" stroke="#777"/>')
    partes.append(f'<text x="{izq}" y="{y + 16}" fill="#aaa" font-size="11.5">0 s</text>')
    partes.append(f'<text x="{izq + ancho_util}" y="{y + 16}" fill="#aaa" font-size="11.5" text-anchor="end">{escala_max:.1f} s</text>')
    partes.append("</svg>")
    return _marca_tipos(b[3] for b in barras) + "".join(partes)


def subtitulo(texto: str, svg: str) -> str:
    """Para juntar varios dibujos en un mismo diagrama, cada uno con su subtítulo."""
    tipos = svg[: svg.find("-->") + 3] if svg.startswith("<!--tipos:") else ""
    return (tipos + f'<div style="font-size:13.5px;font-weight:600;color:#e0e0e0;margin:10px 0 2px">{xml(texto)}</div>'
            + svg)


def _leyenda(svg: str) -> str:
    tipos = set()
    resto = svg
    while "<!--tipos:" in resto:
        i = resto.index("<!--tipos:") + len("<!--tipos:")
        j = resto.index("-->", i)
        tipos |= {t for t in resto[i:j].split(",") if t}
        resto = resto[j:]
    chips = []
    for tipo in COLORES:
        if tipo in tipos:
            relleno, borde, significado = COLORES[tipo]
            chips.append(f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px">'
                         f'<span style="width:14px;height:14px;border-radius:4px;background:{relleno};border:1.5px solid {borde};'
                         f'display:inline-block"></span>{xml(significado)}</span>')
    return (f'<div style="font-size:12px;color:#c8c8c8;margin-top:8px">{"".join(chips)}</div>' if chips else "")


FUENTE = "'Atkinson Hyperlegible Next',Inter,'Segoe UI',system-ui,-apple-system,Helvetica,Arial,sans-serif"

SCRIPT_PASOS = """<script>
window.ccPaso = window.ccPaso || function (boton, d) {
  const caja = boton.closest('.diagrama'), pp = caja.querySelector('.pasoapaso');
  const datos = JSON.parse(pp.querySelector('.pp-datos').textContent), n = datos.length;
  let k = +pp.dataset.k || 0;
  if (d === 0) k = 0; else if (k === 0) k = d > 0 ? 1 : n; else k = Math.max(1, Math.min(n, k + d));
  pp.dataset.k = k;
  caja.querySelectorAll('svg g[data-paso]').forEach(g => {
    const p = +g.dataset.paso;
    g.style.transition = 'opacity .25s';
    g.style.opacity = (k === 0 || p <= k) ? 1 : 0.07;
    g.style.filter = (k && p === k) ? 'drop-shadow(0 0 7px #ffd479)' : '';
  });
  pp.querySelector('.pp-pos').textContent = k ? 'Paso ' + k + ' de ' + n : 'Viendo todo';
  pp.querySelector('.pp-ant').disabled = k === 1;
  pp.querySelector('.pp-sig').disabled = k === n;
  pp.querySelector('.pp-texto').innerHTML = k ? datos[k - 1].texto : pp.dataset.intro;
  const salida = pp.querySelector('.pp-salida');
  salida.innerHTML = '';
  if (!k || !datos[k - 1].busca) return;
  // Busca en la salida de la consola (si esta página la trae) la línea que corresponde a este paso
  const lineas = [];
  document.querySelectorAll('pre').forEach(pre => lineas.push(...pre.textContent.split('\\n')));
  let vez = datos[k - 1].vez || 1;
  for (const l of lineas) {
    if (l.includes(datos[k - 1].busca) && --vez === 0) {
      const t = document.createElement('code'); t.textContent = l.trim();
      salida.append('📟 En la salida de la consola: ', t);
      break;
    }
  }
};
</script>"""


def _bloque_pasos(pasos: list[dict]) -> str:
    """Controles del paso a paso: el diagrama se va revelando caja por caja con su explicación."""
    from extras import marcar_glosario
    datos = [{"texto": marcar_glosario(xml(idioma.salida(p["texto"]))), "busca": idioma.salida(p.get("busca", "")), "vez": p.get("vez", 1)}
             for p in pasos]
    intro = idioma.salida("Dale <b>Paso siguiente ▶</b> para ver el diagrama caja por caja, con lo que pasa en cada momento "
                          "y la línea de la salida que le corresponde.")
    boton = ("background:#2d2d2d;color:#f0f0f0;border:1px solid #666;border-radius:7px;padding:5px 12px;"
             "font:inherit;font-size:14px;cursor:pointer")
    return (f'<div class="pasoapaso" data-k="0" data-intro="{xml(intro)}" style="background:#22231f;border:1px solid #3d3d3d;'
            'border-radius:8px;padding:10px 14px;margin:0 0 12px">'
            '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
            f'<b style="font-size:15px">{idioma.salida("👣 Paso a paso")}</b>'
            f'<button class="pp-ant" style="{boton}" onclick="ccPaso(this,-1)">{idioma.salida("◀ Paso anterior")}</button>'
            f'<span class="pp-pos" style="min-width:96px;text-align:center;color:#ddd">{idioma.salida("Viendo todo")}</span>'
            f'<button class="pp-sig" style="{boton}" onclick="ccPaso(this,1)">{idioma.salida("Paso siguiente ▶")}</button>'
            f'<button style="{boton}" onclick="ccPaso(this,0)">{idioma.salida("Ver todo")}</button></div>'
            f'<div class="pp-texto" style="margin-top:8px;font-size:15px;line-height:1.55;color:#e6e6e6">{intro}</div>'
            '<div class="pp-salida" style="margin-top:6px;font-size:13.5px;color:#bdbdbd"></div>'
            '<script type="application/json" class="pp-datos">'
            + json.dumps(datos, ensure_ascii=False).replace("</", "<\\/") + "</script></div>" + script_pasos())


def script_pasos() -> str:
    """El script del paso a paso con sus textos en el idioma de la corrida."""
    s = SCRIPT_PASOS
    for es in ("Viendo todo", "📟 En la salida de la consola: "):
        s = s.replace(f"'{es}'", json.dumps(idioma.salida(es), ensure_ascii=False))
    return s.replace("'Paso ' + k + ' de ' + n", json.dumps(idioma.salida("Paso")) + " + ' ' + k + ' ' + "
                     + json.dumps(idioma.salida("de")) + " + ' ' + n")


def agregar_diagrama(titulo: str, svg: str, explicacion: str = "", conclusion: str = "",
                     pasos: list[dict] | None = None) -> None:
    """Guarda el diagrama (con leyenda y conclusión) y deja en la salida la línea que en el HTML
    se reemplaza por el dibujo.
    pasos (opcional): [{"texto", "busca", "vez"}] para el paso a paso; las cajas llevan "paso": k."""
    if not ESTADO["activo"]:
        return
    titulo, explicacion, conclusion = idioma.salida(titulo), idioma.salida(explicacion), idioma.salida(conclusion)
    try:
        from extras import marcar_glosario
    except ImportError:          # sin extras.py: el texto sale tal cual
        def marcar_glosario(t):
            return t
    DIAGRAMAS.append(
        f'<div class="diagrama" style="font-family:{FUENTE};background:#1b1c18;color:#f0f0f0;'
        'border:1px solid #444;border-radius:10px;padding:16px 20px;margin:16px 0;max-width:1000px;white-space:normal">'
        f'<div style="font-size:18px;font-weight:600;color:#f0f0f0;margin-bottom:6px">📊 {xml(titulo)}</div>'
        + (f'<div style="font-size:15px;line-height:1.55;color:#d0d0d0;margin-bottom:12px;max-width:80ch">'
           f'{marcar_glosario(xml(explicacion))}</div>' if explicacion else "")
        + (_bloque_pasos(pasos) if pasos else "")
        + svg + _leyenda(svg)
        + (f'<div style="font-size:15.5px;line-height:1.55;color:#f3f3f3;background:#26331f;border-left:4px solid #3fb950;'
           f'border-radius:6px;padding:10px 14px;margin-top:12px">👉 {marcar_glosario(xml(conclusion))}</div>'
           if conclusion else "")
        + "</div>")
    consola = ESTADO["consola"]
    if consola is not None:
        consola.print(f"📊 Diagrama {len(DIAGRAMAS)} de esta corrida: ábrelo en el HTML", markup=False, highlight=False)


# ---------------------------------------------------------------------
#  Resultado de la corrida (lo lee el panel: predicción, costo y nota automática)
# ---------------------------------------------------------------------
RESULTADO: dict = {}
REQUESTS: list = []
RESPUESTAS: list = []


def registrar_respuesta(resp) -> None:
    """Lo esencial de cada respuesta de la API: stop_reason, tools pedidas y tokens (para el diagrama automático)."""
    try:
        RESPUESTAS.append({"stop": resp.stop_reason,
                           "tools": [b.name for b in resp.content if getattr(b, "type", "") == "tool_use"],
                           "entrada": resp.usage.input_tokens, "salida": resp.usage.output_tokens})
    except Exception:  # noqa: BLE001
        pass


def diagrama_generico() -> None:
    """Si la demo no dibujó su propio diagrama: el flujo de la corrida (llamadas a la API o tools del Agent SDK)."""
    nodos, aristas, fila = [], [], 0
    if REQUESTS:
        for i, r in enumerate(REQUESTS[:10], 1):
            resp = RESPUESTAS[i - 1] if i - 1 < len(RESPUESTAS) else None
            nodos.append({"id": f"q{i}", "fila": fila, "col": 0, "tipo": "codigo",
                          "texto": f"Llamada {i} · {corto(r['etiqueta'], 40)}\n{len(r['messages'])} mensaje{'s' if len(r['messages']) != 1 else ''} · max_tokens {r['max_tokens']}"})
            if resp:
                tipo = {"end_turn": "ok", "tool_use": "claude", "max_tokens": "bloqueo"}.get(resp["stop"], "claude")
                nodos.append({"id": f"r{i}", "fila": fila, "col": 1, "tipo": tipo,
                              "texto": f"Claude · stop_reason = {resp['stop']}\n"
                                       + (f"pide: {', '.join(resp['tools'])}" if resp["tools"] else "responde con texto")})
                aristas.append((f"q{i}", f"r{i}", "respuesta"))
            fila += 1
        if len(REQUESTS) > 10:
            nodos.append({"id": "mas", "fila": fila, "col": 0, "completo": True, "tipo": "nota",
                          "texto": f"… y {len(REQUESTS) - 10} llamadas más (todas en “Lo que se le mandó a Claude”)"})
            fila += 1
    if TRAZA:
        for j, t in enumerate(TRAZA[:12], 1):
            nodos.append({"id": f"t{j}", "fila": fila, "col": 0, "tipo": "claude",
                          "texto": f"Claude pide {t['nombre']}\n{corto(json.dumps(t['entrada'], ensure_ascii=False), 60)}"})
            estado = "bloqueo" if t.get("error") else "ok"
            nodos.append({"id": f"u{j}", "fila": fila, "col": 1, "tipo": estado,
                          "texto": ("Falló o se bloqueó\n" if t.get("error") else "Resultado\n") + corto(t.get("resultado", ""), 60)})
            aristas.append((f"t{j}", f"u{j}", "tool_result"))
            fila += 1
    if not nodos:
        return
    conclusion = RESULTADO.get("texto") or (
        f"{len(REQUESTS)} llamadas a la API" if REQUESTS else f"{len(TRAZA)} tools ejecutadas por el Agent SDK")
    agregar_diagrama("El flujo de esta corrida", svg_grafo(nodos, aristas, columnas=2),
                     "Izquierda: lo que mandó tu código (o lo que pidió Claude). Derecha: cómo respondió. "
                     "Diagrama automático: muestra el flujo de llamadas, no el concepto de la demo.", conclusion)


def _bloque_corto(b) -> dict:
    """Un bloque de mensaje (dict o del SDK) en forma corta y legible."""
    get = (lambda k, d=None: b.get(k, d)) if isinstance(b, dict) else (lambda k, d=None: getattr(b, k, d))
    tipo = get("type", "text")
    if tipo == "text":
        return {"type": "text", "text": corto(get("text", ""), 400)}
    if tipo == "tool_use":
        return {"type": "tool_use", "name": get("name"), "input": get("input")}
    if tipo == "tool_result":
        contenido = get("content", "")
        return {"type": "tool_result", "is_error": bool(get("is_error", False)),
                "content": corto(contenido if isinstance(contenido, str) else json.dumps(contenido, ensure_ascii=False, default=str), 300)}
    return {"type": tipo}


def registrar_request(etiqueta: str, kw: dict) -> None:
    """Guarda, en forma corta, lo que se le mandó a Claude en cada llamada (para el inspector y para comparar)."""
    mensajes = []
    for m in kw.get("messages", []):
        c = m.get("content") if isinstance(m, dict) else None
        bloques = [{"type": "text", "text": corto(c, 400)}] if isinstance(c, str) else [_bloque_corto(b) for b in (c or [])]
        mensajes.append({"role": m.get("role") if isinstance(m, dict) else "?", "content": bloques})
    sistema = kw.get("system")
    REQUESTS.append({"etiqueta": etiqueta, "model": kw.get("model"), "max_tokens": kw.get("max_tokens"),
                     "system": sistema if isinstance(sistema, str) else json.dumps(sistema, ensure_ascii=False, default=str) if sistema else "",
                     "tools": [t.get("name") for t in kw.get("tools", []) if isinstance(t, dict)],
                     "tool_choice": kw.get("tool_choice"), "messages": mensajes})


def html_requests(requests: list) -> str:
    """Sección plegable de la página: lo que viajó a la API en cada llamada."""
    if not requests:
        return ""
    partes = []
    for i, r in enumerate(requests, 1):
        resumen = idioma.salida(f"Llamada {i} · {xml(r['etiqueta'])} · {len(r['messages'])} mensajes · max_tokens {r['max_tokens']}")
        partes.append(f"<details style='margin:6px 0'><summary style='cursor:pointer'>{resumen}</summary>"
                      f"<pre style='white-space:pre-wrap;background:#121311;border:1px solid #333;border-radius:8px;"
                      f"padding:10px;font-size:13px'>{xml(json.dumps(r, ensure_ascii=False, indent=2, default=str))}</pre></details>")
    return (f'<div style="font-family:{FUENTE};color:#e8e8e8;background:#1b1c18;border:1px solid #444;border-radius:10px;'
            'padding:14px 20px;margin:16px 0;max-width:1000px;line-height:1.5">'
            f'<div style="font-size:18px;font-weight:600">{idioma.salida("🔍 Lo que se le mandó a Claude")}</div>'
            '<div style="font-size:14.5px;color:#c8c8c8;margin:4px 0 8px">' + idioma.salida("Cada llamada lleva el historial completo: "
            "la API no recuerda nada entre llamadas. Abre una para ver system, tools y mensajes tal como viajaron.") + '</div>'
            + "".join(partes) + "</div>")


def registrar_resultado(parte: str | None = None, **datos) -> None:
    """Guarda datos del resultado (p. ej. final="end_turn", texto="…", uso={…}, costo=0.001).
    parte="A" / "B"…: en demos con varias partes guarda el resultado de cada una (el ticket las junta).
    Si la corrida la lanzó el panel, también los escribe en el archivo que el panel indica."""
    datos = json.loads(json.dumps(datos, ensure_ascii=False, default=str))
    if "texto" in datos:
        datos["texto"] = idioma.salida(datos["texto"])
    if parte:
        partes = RESULTADO.setdefault("partes", {})
        partes[parte] = {k: datos[k] for k in ("final", "texto") if k in datos}
        if len(partes) > 1:
            datos["texto"] = " · ".join(f"Parte {p}: {v['texto']}" for p, v in partes.items() if v.get("texto"))
    RESULTADO.update(datos)
    ruta = os.environ.get("CCARF_RESULTADO")
    if ruta:
        try:
            Path(ruta).write_text(json.dumps(RESULTADO, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def texto_costo(resultado: dict) -> str:
    uso = resultado.get("uso") or {}
    if not uso.get("llamadas"):
        return ""
    tokens = uso.get("entrada", 0) + uso.get("salida", 0)
    cache = idioma.salida(f" + {uso['cache']:,} de caché") if uso.get("cache") else ""
    llamadas = idioma.salida(f"{uso['llamadas']} llamadas a la API") if uso["llamadas"] != 1 else idioma.salida("1 llamada a la API")
    return (llamadas + idioma.salida(f" · {tokens:,} tokens ({uso.get('entrada', 0):,} entrada + {uso.get('salida', 0):,} salida")
            + f"{cache}) · ≈ ${resultado.get('costo', 0):.4f} USD")


def nota_automatica(config: dict, anterior: dict | None, resultado: dict) -> str:
    """Nota que se escribe sola: qué cambió respecto a la corrida anterior de la misma demo y qué pasó."""
    if anterior is None:
        partes = [idioma.salida("Primera corrida de esta demo.")]
    else:
        cambios = [f"{k}: {corto(json.dumps(anterior.get(k), ensure_ascii=False), 30)} → "
                   f"{corto(json.dumps(v, ensure_ascii=False), 30)}"
                   for k, v in config.items() if json.dumps(anterior.get(k)) != json.dumps(v)]
        partes = [idioma.salida("Cambió ") + "; ".join(cambios) + "." if cambios
                  else idioma.salida("Mismas variables que la corrida anterior (la diferencia es solo la respuesta del modelo).")]
    if resultado.get("texto"):
        partes.append(idioma.salida("Resultado: ") + resultado["texto"])
    return " ".join(partes)


LIBRERIAS_OPCIONALES = ("claude_agent_sdk", "mcp")


# ---------------------------------------------------------------------
#  Carpetas temporales de la corrida y Claude Code aislado
# ---------------------------------------------------------------------
_BASE_TEMPORAL: Path | None = None


def carpeta_temporal(prefijo: str) -> Path:
    """Carpeta temporal dentro de la carpeta de esta corrida. Todo se borra al terminar la corrida
    (y lo que quedó de corridas detenidas a la mitad se borra en la siguiente)."""
    global _BASE_TEMPORAL
    if _BASE_TEMPORAL is None:
        for vieja in Path(tempfile.gettempdir()).glob("ccarf_corrida_*"):
            try:
                if time.time() - vieja.stat().st_mtime > 3600:
                    shutil.rmtree(vieja, ignore_errors=True)
            except OSError:
                pass
        _BASE_TEMPORAL = Path(tempfile.mkdtemp(prefix="ccarf_corrida_")).resolve()
        atexit.register(shutil.rmtree, _BASE_TEMPORAL, True)
    return Path(tempfile.mkdtemp(prefix=prefijo, dir=_BASE_TEMPORAL)).resolve()


def aislar_claude_code() -> Path:
    """Claude Code (Agent SDK y claude -p) guarda cada sesión en su carpeta de configuración.
    Para no tocar tu ~/.claude, la corrida usa una carpeta temporal (CLAUDE_CONFIG_DIR) que se borra al final."""
    if os.environ.get("CCARF_CLAUDE_AISLADO") != "1":
        os.environ["CLAUDE_CONFIG_DIR"] = str(carpeta_temporal("claude_config_"))
        os.environ["CCARF_CLAUDE_AISLADO"] = "1"
    return Path(os.environ["CLAUDE_CONFIG_DIR"])


def _fuente_key() -> str:
    """De dónde salió la key (nunca la muestra)."""
    try:
        principal = Path(sys.modules["__main__"].__file__).resolve().parent / ".env"
        from dotenv import dotenv_values
        if principal.exists() and (dotenv_values(principal).get("ANTHROPIC_API_KEY") or "").strip():
            return "el archivo .env de la carpeta de los labs"
    except (OSError, AttributeError, KeyError, ImportError):
        pass
    return "una variable de entorno de tu terminal (ANTHROPIC_API_KEY), porque el .env de la carpeta no tiene key"


def _aviso(titulo: str, texto: str, resumen: str) -> None:
    registrar_resultado(texto=resumen)
    consola = ESTADO["consola"]
    if consola is not None:
        from rich.panel import Panel
        consola.print(Panel(texto, title=titulo, border_style="yellow"))
    else:
        print(f"{titulo}\n{texto}")


def correr_demo(funcion) -> None:
    """Corre una demo. Si falta una librería, la key no sirve o no hay saldo, lo explica en vez de un Traceback."""
    try:
        funcion()
    except Exception as e:  # noqa: BLE001
        clase, mensaje = type(e).__name__, str(e)
        if clase == "AuthenticationError":
            return _aviso("🔑 Anthropic rechazó tu API key (error 401)",
                          "La key llegó, pero Anthropic dice que no es válida. Pasa cuando está mal copiada, ya la borraste "
                          "o la cambiaste por otra.\n\n"
                          f"La key que se usó salió de: {_fuente_key()}.\n\n"
                          "Qué hacer:\n"
                          "  1. En platform.claude.com → Settings → API keys, revisa que siga activa (o crea otra).\n"
                          "  2. Pégala completa en .env, después de ANTHROPIC_API_KEY=, sin espacios de más.\n"
                          "  3. Si alguna vez la pusiste con export (o setx en Windows), quita esa variable vieja:\n"
                          "       macOS/Linux: unset ANTHROPIC_API_KEY  y bórrala de ~/.zshrc o ~/.bashrc\n"
                          "       Windows: quítala de las variables de entorno y abre otra terminal\n"
                          "  4. Cierra el panel (Ctrl+C) y vuelve a abrirlo.",
                          "no se pudo correr: Anthropic rechazó la API key (401).")
        if clase == "PermissionDeniedError":
            return _aviso("🔑 Tu key no tiene permiso para esto (error 403)",
                          f"Anthropic respondió: {mensaje[:300]}\n\nRevisa en platform.claude.com que la key y tu "
                          "organización tengan acceso a este modelo, o prueba con el modelo que viene puesto en el lab.",
                          "no se pudo correr: la key no tiene permiso (403).")
        if clase == "BadRequestError" and "credit balance" in mensaje.lower():
            return _aviso("💳 Tu cuenta no tiene saldo",
                          "Anthropic dice que el saldo de créditos es muy bajo. Agrega créditos en platform.claude.com "
                          "→ Billing y vuelve a correr. Mientras tanto, usa 🎬 Ver sin API key en el panel.",
                          "no se pudo correr: la cuenta no tiene saldo.")
        if not isinstance(e, ModuleNotFoundError):
            raise
        _falta_libreria(e)


def _falta_libreria(e: ModuleNotFoundError) -> None:
    """Falta claude-agent-sdk o mcp: explica cómo instalarlo."""
    nombre = (e.name or "").split(".")[0]
    if nombre not in LIBRERIAS_OPCIONALES:
        raise e
    paquete = {"claude_agent_sdk": "claude-agent-sdk", "mcp": "mcp"}[nombre]
    texto = (f"Esta demo necesita la librería {paquete} y no está instalada en el Python que estás usando:\n"
             f"  {sys.executable}\n\n"
             "Solución: en la carpeta de los labs, con tu entorno virtual activado, corre\n"
             "  python -m pip install -r requirements.txt\n\n"
             "Si ya lo hiciste, seguramente se instaló en otro Python: activa el entorno virtual (.venv) "
             "antes de correr el lab o el panel, y vuelve a intentar.")
    registrar_resultado(texto=f"no se pudo correr: falta la librería {paquete}.")
    consola = ESTADO["consola"]
    if consola is not None:
        from rich.panel import Panel
        consola.print(Panel(texto, title=f"⚠ Falta instalar {paquete}", border_style="yellow"))
    else:
        print(texto)


def tarjeta_tal_cual(titulo: str, columnas: list[tuple[str, str]], filas: list[tuple[str | None, list[str]]],
                     explicacion: str = "", conclusion: str = "") -> None:
    """Tarjeta «tal cual»: el texto EXACTO que recibe Claude, lado a lado (prompts, descripciones, errores).
    columnas: [(etiqueta, color)]; filas: [(subtítulo o None, [texto de cada columna])]."""
    caja = ("background:#24251f;border:1px solid #444;border-radius:8px;padding:10px 12px;vertical-align:top;"
            "white-space:pre-wrap;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13.5px;line-height:1.5")
    ancho = f"{100 // max(1, len(columnas))}%"
    cab = "".join(f'<th style="text-align:left;color:{c};width:{ancho}">{xml(idioma.salida(e))}</th>' for e, c in columnas)
    cuerpo = []
    for subtitulo, textos in filas:
        if subtitulo:
            cuerpo.append(f'<tr><td colspan="{len(columnas)}" style="padding:14px 0 4px;font-family:monospace;'
                          f'font-size:15px;color:#ffd27a">{xml(idioma.salida(subtitulo))}</td></tr>')
        cuerpo.append("<tr>" + "".join(f'<td style="{caja}">{xml(t)}</td>' for t in textos) + "</tr>")
    html = ('<table style="width:100%;border-collapse:separate;border-spacing:8px 4px;table-layout:fixed">'
            f"<tr>{cab}</tr>" + "".join(cuerpo) + "</table>")
    agregar_diagrama(titulo, html, explicacion, conclusion)


def diagrama_seguro(funcion, *args) -> None:
    """Un error al dibujar nunca debe tumbar la demo. Corre aunque no haya HTML: algunos diagramas también
    registran el resultado para el ticket (agregar_diagrama no hace nada si el HTML está apagado)."""
    try:
        funcion(*args)
    except Exception as e:  # noqa: BLE001
        consola = ESTADO["consola"]
        if consola is not None and ESTADO["activo"]:
            consola.print(f"   (no se pudo dibujar el diagrama: {e})", markup=False, highlight=False, style="dim")


# ---------------------------------------------------------------------
#  Traza de las corridas del Agent SDK (qué tools pidió y qué regresaron)
# ---------------------------------------------------------------------

def limpiar_traza() -> None:
    TRAZA.clear()


def registrar_tool_use(id_: str, nombre: str, entrada: dict) -> None:
    TRAZA.append({"id": id_, "nombre": nombre, "entrada": entrada, "error": None, "resultado": ""})


def registrar_tool_result(id_: str, es_error: bool, texto: str) -> None:
    for t in reversed(TRAZA):
        if t["id"] == id_:
            t["error"], t["resultado"] = bool(es_error), texto
            return


# ---------------------------------------------------------------------
#  Guardar la corrida y el índice
# ---------------------------------------------------------------------

def config_de_demo(clave: str, variables: dict, demos: dict, modelo: str) -> dict:
    """Las variables 🔧 de la demo (D21_…, D22_…) con su valor en esta corrida."""
    claves = list(demos) if clave == "todas" else [clave]
    config = {"MODELO": modelo}
    for c in claves:
        prefijo = "D" + c.replace(".", "") + "_"
        for nombre, valor in variables.items():
            if nombre.startswith(prefijo) and isinstance(valor, (str, int, float, bool, list)):
                config[nombre] = valor
    return config


def guardar_html(eleccion: str, config: dict, demos: dict, guias: dict | None = None) -> None:
    """Guarda la corrida como página nueva y actualiza el índice del dominio y la portada."""
    from rich.terminal_theme import MONOKAI
    consola = ESTADO["consola"]
    if consola is None or (eleccion not in demos and eleccion != "todas"):
        return
    if not DIAGRAMAS:
        diagrama_seguro(diagrama_generico)
    carpeta = CARPETA_LABS / carpeta_relativa()
    carpeta.mkdir(parents=True, exist_ok=True)
    ahora = dt.datetime.now()
    nombre = f"{eleccion}_{ahora:%Y-%m-%d_%H-%M-%S}.html"

    registro = carpeta / "corridas.json"
    try:
        corridas = json.loads(registro.read_text(encoding="utf-8")) if registro.exists() else []
    except (OSError, ValueError):
        # Archivo dañado (p. ej. la corrida anterior se detuvo a medio escribir): se guarda aparte, no se pierde
        try:
            registro.replace(registro.with_name(f"corridas_dañado_{dt.datetime.now():%Y%m%d_%H%M%S}.json"))
        except OSError:
            pass
        corridas = []
    previas = [c for c in corridas if c["demo"] == eleccion]
    nota = nota_automatica(config, previas[-1]["config"] if previas else None, RESULTADO)
    costo = texto_costo(RESULTADO)

    filas = "".join(f'<tr><td style="padding:3px 16px 3px 0;color:#bbb">{xml(k)}</td>'
                    f'<td>{xml(corto(json.dumps(v, ensure_ascii=False), 90))}</td></tr>' for k, v in config.items())
    encabezado = (f'<div style="font-family:{FUENTE};color:#e8e8e8;background:#1b1c18;line-height:1.5;'
                  'border:1px solid #444;border-radius:10px;padding:14px 20px;margin:14px 0;max-width:1000px">'
                  f'<div style="font-size:19px;font-weight:600">{idioma.salida("Dominio")} {ESTADO["dominio"]} · demo {xml(eleccion)} · '
                  f'{ahora:%d/%m/%Y %H:%M:%S}</div>'
                  f'<div style="font-size:15px;color:#e6e6e6;margin:6px 0">📝 {xml(nota)}</div>'
                  + (f'<div style="font-size:14px;color:#bbb;margin:0 0 6px">💲 {xml(costo)}</div>' if costo else "")
                  + '<div style="font-size:14px;color:#bbb;margin:8px 0 6px">' + idioma.salida("Variables de esta corrida")
                  + ' (<a style="color:#58a6ff" href="index.html">' + idioma.salida("recorrer todas las corridas") + '</a>)</div>'
                  f'<table style="font-size:14px;border-collapse:collapse">{filas}</table></div>')
    html = consola.export_html(theme=MONOKAI)
    for n, bloque in enumerate(DIAGRAMAS, start=1):
        marcador = idioma.salida(f"📊 Diagrama {n} de esta corrida: ábrelo en el HTML")
        html = html.replace(marcador, "</code></pre>" + bloque + PRE_HTML, 1)
    html = html.replace("<body>", "<body>" + encabezado, 1)
    html = html.replace("</head>", f"<style>{CSS_PAGINA}</style></head>", 1)
    html = html.replace("</body>", html_requests(REQUESTS) + ZOOM_HTML + "</body>", 1)
    (carpeta / nombre).write_text(html, encoding="utf-8")

    corridas.append({"archivo": nombre, "demo": eleccion, "fecha": ahora.isoformat(timespec="seconds"), "idioma": idioma.actual(),
                     "config": json.loads(json.dumps(config, ensure_ascii=False, default=str)),
                     "nota": nota, "resultado": dict(RESULTADO), "diagramas": list(DIAGRAMAS),
                     "requests": json.loads(json.dumps(REQUESTS, ensure_ascii=False, default=str))})
    temporal = registro.with_suffix(".json.tmp")     # escribir aparte y luego reemplazar: nunca queda a medias
    temporal.write_text(json.dumps(corridas, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporal, registro)
    guias = {k: idioma.guia(k, v) for k, v in (guias or {}).items()}
    (carpeta / "index.html").write_text(html_indice(corridas, demos, ESTADO["dominio"], guias=guias), encoding="utf-8")
    escribir_portada(CARPETA_LABS / "salidas_html", ejemplo=False)
    registrar_resultado(nota=nota)
    print(f"\n🌐 Página de esta corrida: {carpeta / nombre}")
    print(f"🌐 Recorrer corridas:      {carpeta / 'index.html'}")


ZOOM_HTML = """<div id="ccZoom" title="Tamaño de letra (se recuerda)">
<button onclick="ccZoom(-1)">A−</button><button onclick="ccZoom(1)">A+</button>
<button id="ccTemaBtn" onclick="ccTema()" title="Tema claro / oscuro (por defecto, el de tu sistema)" hidden>☀</button></div>
<style>#ccZoom{position:fixed;top:10px;right:14px;z-index:50;display:flex;gap:4px;font-family:var(--letra,system-ui,sans-serif)}
#ccZoom button{background:var(--superficie-2,#2d2d2d);color:var(--texto,#f0f0f0);border:1px solid var(--borde,#666);border-radius:7px;
  padding:4px 10px;font-size:14px;cursor:pointer}
@media print{#ccZoom{display:none}}</style>
<script>(function(){
  if (window.top !== window.self) { document.getElementById('ccZoom').style.display = 'none'; }
  // Tema: solo en páginas con los colores de tema.py (las corridas HTML son siempre oscuras, como una terminal)
  var meta = document.querySelector('meta[name="color-scheme"]');
  var conTema = !!meta && getComputedStyle(document.documentElement).getPropertyValue('--fondo').trim() !== '';
  function sistema(){ return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; }
  function guardado(){ try { return localStorage.getItem('ccarf_esquema'); } catch (e) { return null; } }
  function pintar(){ document.getElementById('ccTemaBtn').textContent = (guardado() || sistema()) === 'dark' ? '\u2600' : '\u263e'; }
  window.ccTema = function(){
    if (window.top !== window.self) {   // dentro del panel: el tema es del panel completo
      try { var b = window.top.document.getElementById('tema'); if (b) { b.click(); return; } } catch (e) {}
    }
    var destino = (guardado() || sistema()) === 'dark' ? 'light' : 'dark';
    try { destino === sistema() ? localStorage.removeItem('ccarf_esquema') : localStorage.setItem('ccarf_esquema', destino); } catch (e) {}
    meta.content = guardado() || 'light dark'; pintar();
  };
  if (conTema) { document.getElementById('ccTemaBtn').hidden = false; pintar(); matchMedia('(prefers-color-scheme: dark)').addEventListener('change', pintar); }
  function leer(){ try { return +(localStorage.getItem('ccarf_escala') || 1); } catch (e) { return 1; } }
  function guardar(v){ try { localStorage.setItem('ccarf_escala', v); } catch (e) {} }
  window.ccZoom = function(d){ var v = Math.min(1.6, Math.max(0.8, +(leer() + 0.1 * d).toFixed(2))); guardar(v); document.body.style.zoom = v; };
  document.body.style.zoom = leer();
})();</script>"""

try:   # letras locales: las páginas de corridas están a dos carpetas de la raíz (salidas_html/dominioN/, grabaciones/N.M/)
    from tema import fuentes_css as _fuentes_css
    _FUENTES = _fuentes_css("../../material/fuentes/")
except ImportError:
    _FUENTES = ""

CSS_PAGINA = _FUENTES + """
body{max-width:1100px;margin:0 auto !important;padding:8px 24px 48px;font-family:'Atkinson Hyperlegible Next',Inter,system-ui,sans-serif !important}
pre,code{font-family:'Recursive',Menlo,'DejaVu Sans Mono',monospace !important}
.diagrama svg{max-width:100%;height:auto}
.diagrama{max-width:100% !important;box-sizing:border-box;overflow-x:auto}
pre{font-size:14px !important;line-height:1.5 !important}
abbr.termino{text-decoration:underline dotted #8ab4f8;text-underline-offset:3px;cursor:help}
"""

ESTILOS_INDICE = """
body{background:#202120;color:#e8e8e8;font-family:Inter,'Segoe UI',system-ui,-apple-system,Helvetica,Arial,sans-serif;
  margin:0 auto;padding:28px 28px 60px;max-width:1120px;font-size:16px;line-height:1.55}
h1{font-size:27px;line-height:1.25;margin:0 0 8px} h2{font-size:21px;margin:40px 0 10px} a{color:#58a6ff}
section.demo{margin-top:56px;padding-top:6px;border-top:3px solid #4b6b8c;position:relative}
section.demo::before{content:"";position:absolute;left:0;right:0;top:6px;border-top:1px dashed #4b6b8c;opacity:.6}
section.demo h2{margin-top:22px;display:flex;align-items:center;gap:10px}
section.demo h2::before{content:"";width:10px;height:22px;background:#58a6ff;border-radius:3px;flex:none}
.nota{color:#c4c4c4;font-size:15px;margin:0 0 12px;max-width:80ch}
.resultado{color:#e6e6e6;font-size:15px;margin:0 0 10px}
abbr.termino{text-decoration:underline dotted #8ab4f8;text-underline-offset:3px;cursor:help}
.aviso{background:#fff3cd;color:#664d03;border:1px solid #ffda6a;border-radius:8px;padding:10px 16px;margin:0 0 16px;font-size:14px}
.nav{display:flex;align-items:center;gap:14px;margin-bottom:10px}
.nav button{background:#2d2d2d;color:#f0f0f0;border:1px solid #666;border-radius:8px;padding:6px 14px;font-size:14px;cursor:pointer}
.nav button:hover:not(:disabled){border-color:#58a6ff}
.nav button:disabled{opacity:.35;cursor:default}
.pos{font-size:14px;color:#ddd;min-width:190px;text-align:center}
.reciente{background:#1e3d2a;color:#7ee28f;border:1px solid #3fb950;border-radius:999px;padding:1px 8px;font-size:12px;margin-left:6px}
.tarjeta{display:none;max-width:1040px;background:#2a2b28;border:1px solid #444;border-radius:10px;padding:14px}
.tarjeta.activa{display:block}
.cab{font-size:14px;margin-bottom:4px}
table{font-size:14px;border-collapse:collapse;margin-bottom:10px}
td{padding:4px 16px 4px 0;vertical-align:top} td:first-child{color:#bbb;white-space:nowrap}
tr.cambio td{background:#5a4a00;color:#fff3b0} .antes{color:#e0d39a;font-size:12px}
.tarjeta svg{max-width:100%;height:auto}
details.intro{max-width:1040px;background:#1f2a33;border:1px solid #35506a;border-radius:10px;padding:12px 18px;margin:0 0 14px}
details.intro summary{cursor:pointer;font-weight:600;font-size:16px;color:#cfe3ff}
details.intro summary span{font-weight:400;font-size:13px;color:#9fb6cc}
details.intro h3{font-size:16px;color:#ffd479;margin:16px 0 4px}
details.intro p,details.intro li{max-width:80ch;line-height:1.6;color:#e2e2e2}
details.intro code{background:#2f3a44;padding:1px 5px;border-radius:4px;font-size:.9em}
details.intro .como-leer{color:#bcd;font-size:14.5px;border-top:1px solid #35506a;padding-top:10px;margin-top:14px}
.tarjeta .diagrama{max-width:100% !important;box-sizing:border-box}
"""

SCRIPT_INDICE = """
function mostrar(sec, k){
  const total = +sec.dataset.total;
  k = Math.max(1, Math.min(total, k));
  sec.dataset.k = k;
  sec.querySelectorAll('.tarjeta').forEach(t => t.classList.toggle('activa', +t.dataset.k === k));
  sec.querySelector('.pos').innerHTML = (sec.dataset.etiqueta || 'Corrida') + ' ' + k + ' de ' + total
      + (k === total && !sec.dataset.etiqueta ? '<span class="reciente">más reciente</span>' : '');
  sec.querySelector('.ant').disabled = k === 1;
  sec.querySelector('.sig').disabled = k === total;
}
function mover(boton, paso){ const sec = boton.closest('section'); mostrar(sec, +sec.dataset.k + paso); }
document.querySelectorAll('section.demo').forEach(sec => mostrar(sec, sec.dataset.etiqueta ? 1 : +sec.dataset.total));
"""


def _md_corto(texto: str) -> str:
    """Markdown sencillo de las guías (párrafos, listas, `código`, **negritas**) a HTML."""
    import html as _html
    import re
    def inline(t):
        t = _html.escape(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        return re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
    salida, lista, en_codigo = [], None, False
    for linea in texto.strip("\n").split("\n"):
        if linea.strip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        m = re.match(r"^\s*(-|\d+\.)\s+(.*)", linea)
        if m:
            tipo = "ol" if m.group(1)[0].isdigit() else "ul"
            if lista != tipo:
                if lista:
                    salida.append(f"</{lista}>")
                salida.append(f"<{tipo}>")
                lista = tipo
            salida.append(f"<li>{inline(m.group(2))}</li>")
        elif linea.strip().startswith(">"):
            if lista:
                salida.append(f"</{lista}>")
                lista = None
            salida.append(f"<p style='border-left:3px solid #6b7f93;padding-left:10px;color:#cfd8e0'>"
                          f"{inline(linea.strip().lstrip('>').strip())}<!--fin--></p>")
        elif linea.strip() and lista and linea.startswith("  "):
            salida[-1] = salida[-1][:-5] + " " + inline(linea.strip()) + "</li>"
        elif linea.strip():
            if lista:
                salida.append(f"</{lista}>")
                lista = None
            if salida and salida[-1].startswith("<p>") and not salida[-1].endswith("<!--fin--></p>"):
                salida[-1] = salida[-1][:-4] + " " + inline(linea.strip()) + "</p>"
            else:
                salida.append(f"<p>{inline(linea.strip())}</p>")
        elif salida and salida[-1].startswith("<p>"):
            salida[-1] = salida[-1][:-4] + "<!--fin--></p>"
    if lista:
        salida.append(f"</{lista}>")
    return "\n".join(salida)


def _secciones_guia(guia: str) -> dict:
    import re
    partes = re.split(r"^####\s+(.*)$", guia or "", flags=re.M)
    return {partes[i].strip(): partes[i + 1] for i in range(1, len(partes) - 1, 2)}


def intro_demo(guia: str, abierta: bool) -> str:
    """Caja "de qué trata esta demo" para el índice: la saca de la guía de la demo."""
    secciones = _secciones_guia(guia)
    if not secciones:
        return ""
    try:
        from extras import marcar_glosario
    except ImportError:
        def marcar_glosario(t):
            return t
    trata = next((v for k, v in secciones.items() if k.startswith(("De qué trata", "What it is about"))), "")
    cambia_titulo = next((k for k in secciones if k.startswith(("Qué esperar", "What to expect"))), None) or \
        next((k for k in secciones if k.startswith(("Experimento", "Experiment"))), None) or \
        next((k for k in secciones if k.startswith(("Por qué", "Why"))), None)
    examen = next((v for k, v in secciones.items() if k.startswith(("Lo que pregunta el examen", "What the exam asks"))), "")
    h = ""
    if trata:
        h += f"<h3>{idioma.salida('📖 De qué trata esta demo')}</h3>{marcar_glosario(_md_corto(trata))}"
    if cambia_titulo:
        nombre = (idioma.salida("Qué esperar") if cambia_titulo.startswith(("Qué esperar", "What to expect"))
                  else idioma.salida("Qué cambia entre una corrida y otra"))
        h += f"<h3>🧪 {nombre}</h3>{marcar_glosario(_md_corto(secciones[cambia_titulo]))}"
    if examen:
        h += f"<h3>{idioma.salida('🎓 Lo que pregunta el examen')}</h3>{marcar_glosario(_md_corto(examen))}"
    h += ("<p class='como-leer'>" + idioma.salida("<b>Cómo leer cada tarjeta:</b> arriba, las variables de esa corrida (en amarillo lo que "
          "cambió respecto a la anterior). Luego el diagrama, con su leyenda de colores. Al final, en verde, "
          "👉 la conclusión: lo que tienes que llevarte.") + "</p>")
    return (f"<details class='intro'{' open' if abierta else ''}><summary>{idioma.salida('¿De qué va esta demo?')} "
            f"<span>({idioma.salida('clic para ocultar') if abierta else idioma.salida('clic para ver')})</span></summary>{h}</details>")


def html_indice(corridas: list[dict], demos: dict, dominio: int, ejemplo: bool = False,
                guias: dict | None = None, reales: bool = False) -> str:
    """Índice del dominio: por demo, UNA corrida a la vez con Anterior / Siguiente.
    En amarillo, las variables que cambiaron respecto a la corrida anterior.
    Con ejemplo=True es la versión de ejemplos_html/ (corridas simuladas, abre en la primera)."""
    secciones = []
    for n_sec, demo in enumerate(list(demos) + ["todas"]):
        propias = [c for c in corridas if c["demo"] == demo]
        if not propias:
            continue
        claves = sorted({k for c in propias for k in c["config"]})
        tarjetas = []
        for k_corrida, c in enumerate(propias, start=1):
            anterior = propias[k_corrida - 2]["config"] if k_corrida > 1 else None
            filas, cambiaron = [], []
            for k in claves:
                valor = json.dumps(c["config"].get(k), ensure_ascii=False)
                antes = json.dumps(anterior.get(k), ensure_ascii=False) if anterior is not None else valor
                if valor != antes:
                    cambiaron.append(k)
                    filas.append(f'<tr class="cambio"><td>{xml(k)}</td><td>{xml(corto(valor, 60))} '
                                 f'<span class="antes">(antes: {xml(corto(antes, 40))})</span></td></tr>')
                else:
                    filas.append(f"<tr><td>{xml(k)}</td><td>{xml(corto(valor, 60))}</td></tr>")
            if c.get("titulo"):
                resumen = idioma.salida(c["titulo"])
            elif k_corrida == 1:
                resumen = idioma.salida("Primera corrida de esta demo.")
            elif cambiaron:
                resumen = idioma.salida("Cambió respecto a la corrida anterior: ") + ", ".join(cambiaron)
            else:
                resumen = idioma.salida("Mismas variables que la corrida anterior (la diferencia es solo la respuesta del modelo).")
            enlace = (f' · <a href="{xml(c["archivo"])}">{idioma.salida("ver salida completa")}</a>' if c.get("archivo") else "")
            fecha = idioma.salida("Ejemplo") if ejemplo else c["fecha"].replace("T", " ")
            extra = ""
            if c.get("resultado", {}).get("texto"):
                extra += f'<p class="resultado">🏁 {xml(c["resultado"]["texto"])}</p>'
            if texto_costo(c.get("resultado", {})):
                extra += f'<p class="nota">💲 {xml(texto_costo(c["resultado"]))}</p>'
            tarjetas.append(
                f'<div class="tarjeta" data-k="{k_corrida}">'
                f'<div class="cab"><b>{xml(fecha)}</b>{enlace}</div>'
                f'<p class="nota">{xml(resumen)}</p>' + extra +
                f'<table>{"".join(filas)}</table>' + "".join(c.get("diagramas", [])) + "</div>")
        titulo_demo = idioma.salida("Todas las demos") if demo == "todas" else f"Demo {demo} · {idioma.tr(demos[demo][0])}"
        etiqueta = f' data-etiqueta="{idioma.salida("Ejemplo")}"' if ejemplo else ""
        secciones.append(
            f'<section class="demo" id="demo-{xml(demo)}" data-total="{len(propias)}"{etiqueta}>'
            f'<h2>{xml(titulo_demo)}</h2>' + intro_demo((guias or {}).get(demo, ""), abierta=ejemplo) +
            f'<div class="nav"><button class="ant" onclick="mover(this, -1)">{idioma.salida("◀ Anterior")}</button>'
            f'<span class="pos"></span><button class="sig" onclick="mover(this, 1)">{idioma.salida("Siguiente ▶")}</button></div>'
            + "".join(tarjetas) + "</section>")
    if ejemplo and reales:      # ejemplos hechos con corridas reales (los de ejemplos_html/en/)
        cabeza = (f"<h1>{idioma.salida(f'Lab del Dominio {dominio} · lo que posiblemente vas a ver')}</h1>"
                  "<div class='aviso'>" + idioma.salida("<b>Ejemplos de corridas reales.</b> Cada caso de cada demo se corrió una vez "
                  "con Haiku 5.5 (noviembre de 2026) y aquí está lo que salió. Tus corridas pueden variar: el modelo no responde "
                  "igual cada vez.") + " " + idioma.salida(f"Las tuyas se guardan en <code>salidas_html/dominio{dominio}/</code>.") + "</div>"
                  "<p class='nota'>" + idioma.salida("Usa <b>◀ Anterior</b> y <b>Siguiente ▶</b> para ver los ejemplos de cada demo. "
                  "En amarillo, la variable que cambia respecto al ejemplo anterior.") + "</p>")
    elif ejemplo:
        cabeza = (f"<h1>{idioma.salida(f'Lab del Dominio {dominio} · lo que posiblemente vas a ver')}</h1>"
                  "<div class='aviso'>" + idioma.salida("<b>Ejemplos, no corridas reales.</b> Cada demo trae uno o más ejemplos armados "
                  "con resultados típicos (los que describe la guía de cada demo), para que veas qué muestra cada diagrama "
                  "antes de correr el lab. Tus corridas reales pueden variar: el modelo no responde igual cada vez.")
                  + " " + idioma.salida(f"Las tuyas se guardan en <code>salidas_html/dominio{dominio}/</code>.") + "</div>"
                  "<p class='nota'>" + idioma.salida("Usa <b>◀ Anterior</b> y <b>Siguiente ▶</b> para ver los ejemplos de cada demo. "
                  "En amarillo, la variable que cambia respecto al ejemplo anterior.") + "</p>")
    else:
        cabeza = (f"<h1>{idioma.salida(f'Lab del Dominio {dominio} · corridas guardadas')}</h1>"
                  "<p class='nota'>" + idioma.salida("Cada demo muestra una corrida a la vez y abre en la <b>más reciente</b>. Usa "
                  "<b>◀ Anterior</b> y <b>Siguiente ▶</b> para recorrerlas en orden de tiempo. En amarillo, las variables "
                  "que cambiaron respecto a la corrida anterior (con su valor de antes): compara cómo cambia el diagrama.") + "</p>")
    return (f"<!DOCTYPE html><html lang='{idioma.actual()}'><head><meta charset='UTF-8'><title>Lab · {idioma.salida('Dominio')} {dominio}</title>"
            f"<style>{ESTILOS_INDICE}</style></head><body>"
            f"<p class='nota'><a href='../index.html'>{idioma.salida('← todos los dominios')}</a></p>" + cabeza
            + ("".join(secciones) or f"<p>{idioma.salida('Todavía no hay corridas.')}</p>")
            + f"<script>{script_indice()}</script>{ZOOM_HTML}</body></html>")


def script_indice() -> str:
    """El script del índice con sus textos en el idioma de la página."""
    return (SCRIPT_INDICE.replace("'Corrida'", json.dumps(idioma.salida("Corrida"), ensure_ascii=False))
            .replace("' de '", json.dumps(" " + idioma.salida("de") + " ", ensure_ascii=False))
            .replace("'<span class=\"reciente\">más reciente</span>'",
                     json.dumps('<span class="reciente">' + idioma.salida("más reciente") + "</span>", ensure_ascii=False)))


NOMBRES_DOMINIOS = {
    1: "Agentic Architecture & Orchestration",
    2: "Tool Design & MCP Integration",
    3: "Claude Code Configuration & Workflows",
    4: "Prompt Engineering & Structured Output",
    5: "Context Management & Reliability",
}


def escribir_portada(carpeta: Path, ejemplo: bool) -> None:
    """index.html de salidas_html/ (o ejemplos_html/) con un enlace por dominio."""
    carpeta.mkdir(parents=True, exist_ok=True)
    filas = []
    for d, nombre in NOMBRES_DOMINIOS.items():
        indice = carpeta / f"dominio{d}" / "index.html"
        if indice.exists():
            filas.append(f"<li><a href='dominio{d}/index.html'>{idioma.salida('Dominio')} {d} · {xml(nombre)}</a></li>")
        else:
            falta = idioma.salida("ejemplos próximamente") if ejemplo else idioma.salida("todavía sin corridas")
            filas.append(f"<li style='color:#888'>{idioma.salida('Dominio')} {d} · {xml(nombre)} ({falta})</li>")
    titulo = idioma.salida("Ejemplos de lo que vas a ver") if ejemplo else idioma.salida("Tus corridas guardadas")
    nota = (idioma.salida("Ejemplos con resultados típicos, para ver los diagramas antes de correr los labs.")
            if ejemplo else idioma.salida("Cada dominio guarda sus corridas aquí cuando el modo HTML está encendido."))
    (carpeta / "index.html").write_text(
        f"<!DOCTYPE html><html lang='{idioma.actual()}'><head><meta charset='UTF-8'><title>CCAR-F · labs</title>"
        f"<style>{ESTILOS_INDICE} li{{margin:8px 0;font-size:16px}}</style></head><body>"
        f"<h1>CCAR-F · Labs · {titulo}</h1><p class='nota'>{nota}</p><ul>{''.join(filas)}</ul>{ZOOM_HTML}</body></html>",
        encoding="utf-8")

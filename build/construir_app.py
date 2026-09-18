#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
construir_app.py — Convierte el documento de Claude Design en una app autonoma.

El .dc.html que exporta Claude Design NO es una pagina normal: necesita
support.js, que a su vez se descarga React, ReactDOM y Babel de unpkg y compila
la plantilla en el navegador en cada carga. En un movil eso son varios megas y
un par de segundos de pantalla en blanco.

Este script se queda con lo que importa del diseno -el CSS, la plantilla y la
clase de logica, que es JavaScript normal- y lo ensambla con runtime.js, un
interprete de plantillas de unos 5 KB. Resultado: un index.html autonomo, sin
dependencias externas salvo las fuentes.

Uso:
    python construir_app.py
    python construir_app.py --diseno ..\\design_src\\diseno.html --datos ..\\fondeadoras.json

Genera:
    ../docs/index.html              la app para GitHub Pages
    ../docs/manifest.webmanifest    para anadirla a la pantalla de inicio
    ../artifact.html                la misma app para publicar como artifact
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VACIOS = {"input", "br", "img", "hr", "meta", "link", "source", "area", "col"}
EVENTOS = {"onclick": "click", "onchange": "input", "oninput": "input"}
IGNORAR = re.compile(r"^(hint-|data-dc-)")


# --------------------------------------------------------------------------
# Compilador de plantilla -> arbol de instrucciones
# --------------------------------------------------------------------------
class Compilador(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = []
        self.pila = [self.raiz]
        self.hovers = {}          # css -> nombre de clase

    # --- utilidades ---
    def _partes(self, texto):
        """'a {{ x }} b' -> ['a ', {'e': 'x'}, ' b']"""
        partes, pos = [], 0
        for m in re.finditer(r"\{\{(.*?)\}\}", texto, re.S):
            if m.start() > pos:
                partes.append(texto[pos:m.start()])
            partes.append({"e": m.group(1).strip()})
            pos = m.end()
        if pos < len(texto):
            partes.append(texto[pos:])
        return partes or [""]

    def _clase_hover(self, css):
        css = css.strip().rstrip(";")
        if css not in self.hovers:
            self.hovers[css] = "dh%d" % (len(self.hovers) + 1)
        return self.hovers[css]

    def _dict_attrs(self, attrs):
        d = {}
        for k, v in attrs:
            d[k] = v if v is not None else ""
        return d

    # --- ganchos del parser ---
    def handle_starttag(self, tag, attrs):
        a = self._dict_attrs(attrs)

        if tag == "sc-if":
            nodo = {"t": "if", "e": self._expr(a.get("value", "")), "k": []}
            self.pila[-1].append(nodo)
            self.pila.append(nodo["k"])
            return

        if tag == "sc-for":
            nodo = {"t": "for", "e": self._expr(a.get("list", "")),
                    "as": a.get("as", "it"), "k": []}
            self.pila[-1].append(nodo)
            self.pila.append(nodo["k"])
            return

        nodo = {"t": "el", "g": tag, "a": {}, "k": []}
        clases = []

        for nombre, valor in a.items():
            if IGNORAR.match(nombre):
                continue
            if nombre in EVENTOS:
                nodo.setdefault("ev", {})[EVENTOS[nombre]] = self._expr(valor)
                continue
            if nombre == "style-hover":
                clases.append(self._clase_hover(valor))
                continue
            if nombre == "value" and tag == "input":
                nodo["v"] = self._partes(valor)      # se asigna como propiedad
                continue
            if nombre == "class":
                clases.append(valor)
                continue
            nodo["a"][nombre] = self._partes(valor)

        if clases:
            nodo["a"]["class"] = [" ".join(clases)]

        self.pila[-1].append(nodo)
        if tag not in VACIOS:
            self.pila.append(nodo["k"])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VACIOS and len(self.pila) > 1:
            self.pila.pop()

    def handle_endtag(self, tag):
        if tag in VACIOS:
            return
        if len(self.pila) > 1:
            self.pila.pop()

    def handle_data(self, texto):
        if not texto:
            return
        if not texto.strip() and "\n" in texto:
            return                                   # sangrado entre etiquetas
        self.pila[-1].append({"t": "tx", "p": self._partes(texto)})

    def _expr(self, v):
        m = re.search(r"\{\{(.*?)\}\}", v, re.S)
        return m.group(1).strip() if m else v.strip()


def limpiar_arbol(nodos):
    """Quita las listas de hijos vacias para que el JSON pese menos."""
    for n in nodos:
        if "k" in n:
            if n["k"]:
                limpiar_arbol(n["k"])
            else:
                del n["k"]
    return nodos


# --------------------------------------------------------------------------
# Troceado del documento de Claude Design
# --------------------------------------------------------------------------
def trocear(html):
    css = ""
    m = re.search(r"<helmet[^>]*>(.*?)</helmet>", html, re.S)
    if m:
        for s in re.findall(r"<style[^>]*>(.*?)</style>", m.group(1), re.S):
            css += s
        html_sin_helmet = html.replace(m.group(0), "")
    else:
        html_sin_helmet = html

    m = re.search(r"<x-dc[^>]*>(.*?)</x-dc>", html_sin_helmet, re.S)
    if not m:
        sys.exit("No encuentro el bloque <x-dc> en el documento de diseno.")
    plantilla = m.group(1)

    m = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        sys.exit("No encuentro el bloque de logica <script type=\"text/x-dc\">.")
    logica = m.group(1)

    props = {}
    mp = re.search(r'data-props="([^"]*)"', html)
    if mp:
        crudo = (mp.group(1).replace("&quot;", '"').replace("&amp;", "&")
                 .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))
        try:
            for k, v in json.loads(crudo).items():
                if isinstance(v, dict) and "default" in v:
                    props[k] = v["default"]
        except Exception:
            pass

    return css, plantilla, logica, props


# --------------------------------------------------------------------------
# Ensamblado
# --------------------------------------------------------------------------
CARGADOR = """
/* Datos: primero la copia incrustada para pintar ya, despues el JSON de la red. */
window.DATA = SNAPSHOT;
(function () {
  var url = 'fondeadoras.json?v=' + Date.now();
  if (location.protocol === 'file:') return;          // abierto en local: solo snapshot
  if (typeof fetch !== 'function') return;
  fetch(url, { cache: 'no-store' })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      if (!d || !d.campos || !d.planes) throw new Error('JSON incompleto');
      window.DATA = d;
      if (window.__app) { window.__app.setState({ listo: true }); window.__app.pintar(); }
    })
    .catch(function () { /* sin red: se queda la copia incrustada */ });
})();
"""

ARRANQUE = """
var PROPS = %(props)s;
var app = new Component(document.getElementById('root'), PLANTILLA, PROPS);
window.__app = app;
app.montar();
"""

SHELL = """<!DOCTYPE html>
<html lang="es" data-tema="oscuro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%(titulo)s</title>
<meta name="description" content="Comparador de fondeadoras de futuros: filtros, orden, comparador y coste real.">
<meta name="theme-color" content="#0a0c0e" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f3f2ef" media="(prefers-color-scheme: light)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="%(icono)s">
<link rel="apple-touch-icon" href="%(icono)s">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
%(css)s
</style>
</head>
<body>
<div id="root"></div>
<script>%(runtime)s</script>
<script>var SNAPSHOT = %(snapshot)s;</script>
<script>%(cargador)s</script>
<script>var PLANTILLA = %(plantilla)s;</script>
<script>
%(logica)s
%(arranque)s
</script>
</body>
</html>
"""

SHELL_ARTIFACT = """<style>
%(css)s
</style>
<div id="root"></div>
<script>%(runtime)s</script>
<script>var SNAPSHOT = %(snapshot)s;</script>
<script>var PLANTILLA = %(plantilla)s;</script>
<script>
window.DATA = SNAPSHOT;
%(logica)s
%(arranque)s
</script>
"""

ICONO = ("data:image/svg+xml,"
         "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
         "%3Crect width='64' height='64' rx='14' fill='%230a0c0e'/%3E"
         "%3Crect x='14' y='30' width='8' height='20' rx='2' fill='%2359b8c8'/%3E"
         "%3Crect x='28' y='22' width='8' height='28' rx='2' fill='%2359b8c8'/%3E"
         "%3Crect x='42' y='14' width='8' height='36' rx='2' fill='%2359b8c8'/%3E"
         "%3C/svg%3E")

MANIFEST = {
    "name": "Comparador de fondeadoras",
    "short_name": "Fondeadoras",
    "start_url": ".",
    "scope": ".",
    "display": "standalone",
    "orientation": "any",
    "background_color": "#0a0c0e",
    "theme_color": "#0a0c0e",
    "icons": [{"src": ICONO, "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
}


def main():
    aqui = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Claude Design -> app autonoma")
    ap.add_argument("--diseno", default=str(aqui.parent / "design_src" / "diseno.html"))
    ap.add_argument("--runtime", default=str(aqui / "runtime.js"))
    ap.add_argument("--datos", default=str(aqui.parent / "fondeadoras.json"))
    ap.add_argument("--salida", default=str(aqui.parent / "docs"))
    ap.add_argument("--artifact", default=str(aqui.parent / "artifact.html"))
    args = ap.parse_args()

    for r in (args.diseno, args.runtime, args.datos):
        if not Path(r).exists():
            sys.exit("No encuentro: " + r)

    html = Path(args.diseno).read_text(encoding="utf-8")
    css, plantilla, logica, props = trocear(html)

    c = Compilador()
    c.feed(plantilla)
    c.close()
    arbol = limpiar_arbol(c.raiz)

    # CSS de los estados :hover, que en la plantilla vienen como style-hover
    reglas = []
    for decl, clase in c.hovers.items():
        trozos = [d.strip() for d in decl.split(";") if d.strip()]
        reglas.append(".%s:hover{%s}" % (clase, "".join(t + " !important;" for t in trozos)))
    css_final = css.strip() + "\n" + "\n".join(reglas) + "\n"

    datos = json.loads(Path(args.datos).read_text(encoding="utf-8"))
    snapshot = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    arbol_json = json.dumps(arbol, ensure_ascii=False, separators=(",", ":"))
    runtime = Path(args.runtime).read_text(encoding="utf-8")
    logica = logica.replace("extends DCLogic", "extends Logic")
    arranque = ARRANQUE % {"props": json.dumps(props, ensure_ascii=False)}
    titulo = datos.get("meta", {}).get("titulo") or "Comparador de fondeadoras"

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    (salida / "index.html").write_text(SHELL % {
        "titulo": titulo, "css": css_final, "runtime": runtime,
        "snapshot": snapshot, "cargador": CARGADOR, "plantilla": arbol_json,
        "logica": logica, "arranque": arranque, "icono": ICONO,
    }, encoding="utf-8")

    (salida / "manifest.webmanifest").write_text(
        json.dumps(MANIFEST, ensure_ascii=False, indent=2), encoding="utf-8")

    (salida / "fondeadoras.json").write_text(
        json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    Path(args.artifact).write_text(SHELL_ARTIFACT % {
        "css": css_final, "runtime": runtime, "snapshot": snapshot,
        "plantilla": arbol_json, "logica": logica, "arranque": arranque,
    }, encoding="utf-8")

    def kb(p):
        return "%.0f KB" % (Path(p).stat().st_size / 1024)

    def contar(nodos):
        n = 0
        for x in nodos:
            n += 1
            n += contar(x.get("k", []))
        return n

    print("OK")
    print("   %-34s %s" % (salida / "index.html", kb(salida / "index.html")))
    print("   %-34s %s" % (salida / "fondeadoras.json", kb(salida / "fondeadoras.json")))
    print("   %-34s %s" % (salida / "manifest.webmanifest", kb(salida / "manifest.webmanifest")))
    print("   %-34s %s" % (args.artifact, kb(args.artifact)))
    print("   plantilla: %d nodos · %d estilos :hover · %d planes"
          % (contar(arbol), len(c.hovers), len(datos.get("planes", []))))


if __name__ == "__main__":
    main()

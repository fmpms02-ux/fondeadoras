#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar.py — Lleva los datos del dia del Excel a la web de GitHub Pages.

    1. git pull            por si se ha tocado algo desde github.com
    2. exportar_json.py    comparativa_fondeadoras.xlsx (OneDrive) -> fondeadoras.json
    3. construir_app.py    fondeadoras.json + diseno -> docs/
    4. probar_app.js       comprobaciones sobre la app construida
    5. commit y push       SOLO de docs/ (los datos y la app construida)

Lo lanza cada manana el Programador de tareas de Windows a traves de
"Publicar web fondeadoras.bat /auto" (raiz del proyecto en OneDrive), despues
del refresco de las 08:15. Si no hay cambios no hace nada, asi que se puede
ejecutar tantas veces como se quiera.

Los cambios de codigo (exportar_json.py, build/, design_src/, este fichero...)
NO se suben solos. El 30/09/2026 una ejecucion rutinaria publico unas ediciones
que otra sesion tenia a medias, porque entonces se hacia "git add -A". Ahora se
avisa de que estan ahi y se dejan sin subir. Para subirlos a proposito:

    python publicar.py --todo "Que cambia y por que"

Ojo: la app de docs/ se construye con el codigo que haya en disco, este
confirmado o no. Por eso el aviso: lo publicado puede llevar ya ese cambio.

Si el Excel no se puede leer o salen muchos menos planes que en la ultima
publicacion, exportar_json.py falla, aqui se para todo y la web sigue con los
datos del dia anterior: mejor datos de ayer que una pantalla rota.
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EXCEL = (Path.home() / "OneDrive" / "Claude_Asesor_Plan_Trading" / "Control fondeadoras"
         / "Registro central" / "comparativa_fondeadoras.xlsx")


def ejecutar(*cmd, callado=False):
    r = subprocess.run(cmd, cwd=AQUI, capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = (r.stdout + r.stderr).strip()
    if salida and (not callado or r.returncode != 0):
        print(salida)
    if r.returncode != 0:
        sys.exit(f"ERROR ({r.returncode}) en: {' '.join(map(str, cmd))}. No se publica nada.")
    return r


def main():
    ap = argparse.ArgumentParser(description="Publica la web de fondeadoras en GitHub Pages")
    ap.add_argument("--todo", metavar="MENSAJE",
                    help="sube tambien los cambios de codigo, con este mensaje de commit")
    args = ap.parse_args()

    print(f"\n--- {datetime.now():%d/%m/%Y %H:%M} ---")
    ejecutar("git", "pull", "--ff-only", "--quiet")
    ejecutar(sys.executable, "exportar_json.py", "--excel", str(EXCEL), "--salida", "fondeadoras.json")
    ejecutar(sys.executable, str(Path("build") / "construir_app.py"))
    # Las comprobaciones de la app ya construida. Necesitan node y jsdom
    # (npm install --no-save jsdom); si faltan se avisa, pero no se bloquea.
    if (AQUI / "node_modules" / "jsdom").exists():
        r = subprocess.run(["node", str(Path("build") / "probar_app.js")], cwd=AQUI,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(r.stdout[-3000:] + r.stderr[-2000:])
            sys.exit("ERROR: la app construida no pasa las pruebas. No se publica nada.")
        print("Pruebas de la app: OK")
    else:
        print("AVISO: sin jsdom, la app se publica sin pasar las pruebas.")

    if args.todo:
        ejecutar("git", "add", "-A")
        mensaje = args.todo
    else:
        ejecutar("git", "add", "docs")
        mensaje = f"Datos del {datetime.now():%d/%m/%Y}"
        # Lo que queda fuera: codigo tocado y sin confirmar (segunda columna
        # de --porcelain distinta de espacio, o ficheros nuevos "??").
        estado = ejecutar("git", "status", "--porcelain", callado=True).stdout.splitlines()
        resto = [l[3:] for l in estado if l[1:2] != " "]
        if resto:
            print("AVISO: hay cambios de codigo SIN SUBIR: " + ", ".join(resto))
            print("       La app publicada se ha construido con ellos. Para subirlos:")
            print('       python publicar.py --todo "Que cambia y por que"')
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=AQUI).returncode != 0:
        ejecutar("git", "commit", "--quiet", "-m", mensaje)
    # Se sube todo lo pendiente, no solo lo de hoy: si ayer fallo el push
    # (sin red, sesion caducada), su commit se quedo en local esperando.
    pendientes = int(ejecutar("git", "rev-list", "--count", "@{u}..HEAD", callado=True).stdout.strip() or 0)
    if not pendientes:
        print("Sin cambios: la web ya tiene estos datos.")
        return
    ejecutar("git", "push", "--quiet")
    print("Publicado. GitHub Pages sirve la version nueva en uno o dos minutos.")


if __name__ == "__main__":
    main()

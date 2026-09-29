#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar.py — Lleva los datos del dia del Excel a la web de GitHub Pages.

    1. git pull            por si se ha tocado algo desde github.com
    2. exportar_json.py    comparativa_fondeadoras.xlsx (OneDrive) -> fondeadoras.json
    3. construir_app.py    fondeadoras.json + diseno -> docs/
    4. probar_app.js       36 comprobaciones sobre la app construida
    5. commit y push       solo si docs/ ha cambiado

Lo lanza cada manana el Programador de tareas de Windows a traves de
"Publicar web fondeadoras.bat /auto" (raiz del proyecto en OneDrive), despues
del refresco de las 08:15. Si no hay cambios no hace nada, asi que se puede
ejecutar tantas veces como se quiera.

Si el Excel ha perdido una columna o no se puede leer, exportar_json.py falla,
aqui se para todo y la web sigue con los datos del dia anterior: mejor datos de
ayer que una pantalla rota.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EXCEL = (Path.home() / "OneDrive" / "Claude_Asesor_Plan_Trading" / "Control fondeadoras"
         / "Registro central" / "comparativa_fondeadoras.xlsx")


def ejecutar(*cmd):
    r = subprocess.run(cmd, cwd=AQUI, capture_output=True, text=True, encoding="utf-8", errors="replace")
    salida = (r.stdout + r.stderr).strip()
    if salida:
        print(salida)
    if r.returncode != 0:
        sys.exit(f"ERROR ({r.returncode}) en: {' '.join(map(str, cmd))}. No se publica nada.")
    return r


def main():
    print(f"\n--- {datetime.now():%d/%m/%Y %H:%M} ---")
    ejecutar("git", "pull", "--ff-only", "--quiet")
    ejecutar(sys.executable, "exportar_json.py", "--excel", str(EXCEL), "--salida", "fondeadoras.json")
    ejecutar(sys.executable, str(Path("build") / "construir_app.py"))
    # Las 36 comprobaciones de la app ya construida. Necesitan node y jsdom
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

    ejecutar("git", "add", "-A")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=AQUI).returncode == 0:
        print("Sin cambios: la web ya tiene estos datos.")
        return
    ejecutar("git", "commit", "--quiet", "-m", f"Datos del {datetime.now():%d/%m/%Y}")
    ejecutar("git", "push", "--quiet")
    print("Publicado. GitHub Pages sirve la version nueva en uno o dos minutos.")


if __name__ == "__main__":
    main()

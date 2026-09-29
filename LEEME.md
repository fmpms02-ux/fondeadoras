# Claude_Fondeadoras-Web

Repositorio de la **web del comparador de fondeadoras**, publicada en
**https://fmpms02-ux.github.io/fondeadoras/** (GitHub: `fmpms02-ux/fondeadoras`).

Es una **vista** del registro de fondeadoras, igual que el Excel: no calcula
nada, solo pinta lo que hay en `comparativa_fondeadoras.xlsx`. El dato vive en
OneDrive (`Claude_Asesor_Plan_Trading/Control fondeadoras/Registro central/`),
no aquí.

---

## Qué hay en esta carpeta

| Ruta | Qué es | ¿Se sube a GitHub? |
|---|---|---|
| `docs/` | **La web publicada**: `index.html`, `fondeadoras.json` y `manifest.webmanifest`. GitHub Pages sirve esta carpeta. Se regenera sola: no se edita a mano. | Sí |
| `exportar_json.py` | Excel → `fondeadoras.json`. Avisa de columnas nuevas, planes sin precio y promociones a punto de caducar. | Sí |
| `build/construir_app.py` | Une el diseño de Claude Design con los datos y genera `docs/`. | Sí |
| `build/runtime.js` | Intérprete de plantillas de ~5 KB que sustituye al runtime de Claude Design (sin React ni Babel). | Sí |
| `build/probar_app.js` | 36 comprobaciones automáticas sobre la app ya construida. | Sí |
| `design_src/diseno.html` | El diseño de Claude Design. Desde el 29/09/2026 es **el del artefacto** (lista ordenada por precio con promo, sin puesto a la vista, tabla en pantalla ancha); el del 18/09 queda en el historial de Git. Si cambias el diseño, se sustituye este archivo. | Sí |
| `publicar.py` | La cadena completa de cada día (ver abajo). | Sí |
| `README.md` | Documentación técnica original del 18/09 (cómo se construyó la app). | Sí |
| `LEEME.md` | Este archivo. | Sí |
| `fondeadoras.json`, `artifact.html` | Intermedios que genera `publicar.py`. | No (`.gitignore`) |
| `node_modules/` | `jsdom`, que usan las pruebas. Se reinstala con `npm install --no-save --no-package-lock jsdom`. | No |

---

## Cómo se actualiza

Automático, todos los días:

```
08:15  Tarea de Claude "refresco-diario-fondeadoras"
         re-verifica las firmas → fondeadoras.csv → comparativa_fondeadoras.xlsx
10:00  Programador de tareas de Windows → "Publicar web fondeadoras.bat /auto"
         → publicar.py:
             1. git pull
             2. exportar_json.py    (Excel de OneDrive → fondeadoras.json)
             3. construir_app.py    (→ docs/)
             4. probar_app.js       (si falla, no se publica nada)
             5. commit y push       (solo si docs/ ha cambiado)
         → GitHub Pages sirve la versión nueva en uno o dos minutos
```

Para publicar a mano, doble clic en **`Publicar web fondeadoras.bat`**, en la
raíz de `Claude_Asesor_Plan_Trading`. Si no hay cambios no hace nada, así que
se puede lanzar las veces que haga falta.

Registro de cada ejecución: `Control fondeadoras/Registro central/publicar_web.log`
(en OneDrive).

**Por qué la subida no va dentro de la tarea de las 08:15:** esa tarea corre en
una máquina Linux aislada que no tiene las credenciales de GitHub de Windows.

**Por qué no es un artefacto de claude.ai:** un artefacto solo puede pedir datos
a su propio dominio, así que no puede leer este repositorio al abrirse. Además,
su enlace compartido apunta a una versión fija.

---

## Cómo carga la app los datos

1. Pinta al instante con la copia de los datos incrustada en `index.html`.
2. En segundo plano pide `fondeadoras.json?v=<marca de tiempo>` y repinta con lo
   más reciente. El `?v=` evita la caché de GitHub Pages.
3. Sin red, se queda con la copia incrustada.

Filtros, orden, favoritos, comparador y tema se guardan en el navegador de cada
uno (`localStorage`).

---

## Cosas a saber

- **El repositorio es público.** GitHub Pages gratuito lo exige, así que todo lo
  que hay en `docs/fondeadoras.json` lo puede ver cualquiera.
- **Esta carpeta está fuera de OneDrive a propósito.** Git crea y borra ficheros
  de bloqueo constantemente, y en la carpeta sincronizada no se puede borrar
  desde el shell.
- **Si el Excel pierde una columna** o no se puede leer, `exportar_json.py` falla,
  `publicar.py` se para y la web sigue con los datos del día anterior.
- **Cambiar el diseño.** Vale tanto el `.dc.html` exportado de Claude Design
  como el HTML sacado de un artefacto publicado. El segundo viene ya pasado por
  el navegador, y Claude Design escribe `onClick` como `sc-camel-on-click` y las
  tablas como `<sc-raw-table>`. `construir_app.py` entiende las dos formas.
  Tras cambiarlo: `python build/construir_app.py`, y luego
  `node build/probar_app.js`. Si el diseño cambia el orden inicial o las
  métricas por defecto, hay que ajustar esas pruebas, que las comprueban.
- **Columna nueva en el Excel:** se exporta como texto y se avisa. Para darle
  tipo, grupo o filtro, se declara en `MAPA_COLUMNAS` de `exportar_json.py`.
- **La fecha «generado»** es la de la última regeneración del Excel, no la de la
  publicación.
- **La web mide y ordena. No recomienda.** Cada fila lleva su fecha de consulta:
  antes de pagar, se vuelve a mirar el precio en el carrito de la firma.

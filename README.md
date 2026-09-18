# Comparador de fondeadoras — del Excel al móvil

## La cadena completa

```
comparativa_fondeadoras.xlsx        tu PC — fuente de verdad (skill gestionar-fondeadoras)
      │  python exportar_json.py
      ▼
fondeadoras.json                    78 KB · datos + esquema de campos
      │  python build\construir_app.py        (une el diseño con el runtime)
      ▼
docs\index.html                     139 KB · la app, sin dependencias externas
      │  git push
      ▼
https://fmpms02-ux.github.io/fondeadoras/
      ▼
El móvil, añadida a la pantalla de inicio
```

## Qué hay en cada carpeta

| Ruta | Qué es |
|---|---|
| `exportar_json.py` | Excel → `fondeadoras.json`. Lo ejecutas tú cuando cambian los datos. |
| `fondeadoras.json` | Los datos con su esquema de campos. |
| `docs\` | **Lo que se sube a GitHub**: `index.html`, `fondeadoras.json`, `manifest.webmanifest`. |
| `build\construir_app.py` | Convierte el documento de Claude Design en la app autónoma. |
| `build\runtime.js` | El micro-runtime de plantillas (~5 KB) que sustituye al de Design. |
| `build\probar_app.js` | 36 comprobaciones automáticas sobre la app ya construida. |
| `design_src\` | El diseño original exportado de Claude Design. Fuente, no se publica. |
| `artifact.html` | La misma app empaquetada para publicarla como artifact. |

## Por qué no se sube el .dc.html tal cual

El documento que exporta Claude Design no es una página normal: necesita `support.js`,
que a su vez descarga React, ReactDOM y **Babel** de un CDN y compila la plantilla en el
navegador **en cada carga**. En un móvil son unos 2,5 MB y un par de segundos de pantalla
en blanco, y depende de que unpkg esté disponible.

`construir_app.py` se queda con lo que importa del diseño —el CSS, la plantilla y la clase
de lógica, que es JavaScript normal— y lo ensambla con `runtime.js`, un intérprete de
plantillas de unos 5 KB que entiende el mismo lenguaje (`{{ }}`, `<sc-if>`, `<sc-for>`,
`style-hover`). El resultado es un `index.html` de 139 KB que **no descarga nada** salvo
las dos fuentes de Google, y que funciona aunque te quedes sin cobertura.

**Consecuencia importante:** el diseño manda. Si retocas algo en Claude Design, vuelves a
exportar, sustituyes `design_src\diseno.html` y ejecutas `construir_app.py` otra vez. No
hay que tocar el HTML generado a mano: se sobrescribe en cada compilación.

## Uso

```powershell
pip install openpyxl          # solo la primera vez

# 1. Datos nuevos en el Excel
python exportar_json.py

# 2. Reconstruir la app
python build\construir_app.py

# 3. (opcional) Comprobar que todo sigue funcionando
npm install jsdom
node build\probar_app.js
```

`exportar_json.py` avisa de columnas nuevas que no reconoce, planes sin precio y
promociones caducadas o a menos de siete días de caducar.

## El JSON

```
meta      título, fechas, grupos, textos del método y del simulador, avisos
campos    esquema de los 32 campos: key, label, tipo, unidad, grupo, filtrable, ordenable
planes    35 registros
```

La app monta los filtros, el orden, el selector de métricas, la ficha, el comparador y el
CSV **leyendo `campos`**. Para que una columna nueva del Excel aparezca en la app, basta
con declararla en el diccionario `MAPA_COLUMNAS` de `exportar_json.py`; el HTML no se toca.

Dos detalles del exportador que conviene conocer:

- **`fiabilidad_nota`** no está en el Excel: se extrae del `73/100 — …` de la columna de
  fiabilidad para poder **ordenar y filtrar por la nota**, cosa que con el texto no se
  puede. Es el único campo añadido sobre el esquema del diseño.
- **El `id` de cada plan** es `firma--plan` en lugar del número de fila. Así, cuando el
  ranking cambie de orden, tus favoritos y el comparador seguirán apuntando al plan
  correcto en vez de al que ocupe ahora esa posición.

## El repositorio

Ya está montado y publicado en **https://fmpms02-ux.github.io/fondeadoras/**. Es público
porque si fuera privado el `fetch` del JSON necesitaría un token, y eso no se pone en una web.

Estructura:

```
fondeadoras/
├─ docs/
│  ├─ index.html
│  ├─ fondeadoras.json
│  └─ manifest.webmanifest
├─ build/
├─ design_src/
├─ exportar_json.py
└─ comparativa_fondeadoras.xlsx   (tu fuente de verdad; súbela cuando quieras)
```

Pages está configurado en **Settings → Pages → Deploy from a branch → `main` / `/docs`**.
Abre la URL en el móvil y *Añadir a pantalla de inicio*: el `manifest.webmanifest` hace que
se abra a pantalla completa, sin barra de navegador.

## Cómo se comporta al arrancar

1. Pinta **al instante** con la copia de los datos incrustada en el propio `index.html`.
2. En segundo plano pide `fondeadoras.json?v=<marca de tiempo>` y, si llega, repinta con
   los datos frescos. El `?v=` evita que GitHub Pages te sirva el JSON antiguo.
3. Si no hay red, se queda con la copia incrustada y no falla.

Es decir: para **actualizar** los datos basta con subir el JSON, pero conviene reconstruir
el `index.html` de vez en cuando para que la copia de respaldo tampoco envejezca.

## Actualizar

```powershell
python exportar_json.py
python build\construir_app.py
git add -A
git commit -m "Datos al 2026-XX-XX"
git push
```

Refrescas en el móvil y listo. El ordenador solo hace falta para actualizar, no para
consultar.

## Notas sueltas

- El estado (filtros, orden, métricas, favoritos, comparador, tema, meses del simulador)
  se guarda en `localStorage`, dentro de un `try/catch`: en modo incógnito la app funciona
  igual, simplemente no recuerda nada.
- Por debajo de 780 px se ven tarjetas; por encima, la tabla completa con las métricas que
  hayas elegido. Añadiendo `#movil` a la URL se fuerzan las tarjetas en cualquier pantalla.
- El botón **CSV** funciona en GitHub Pages, pero no dentro de la vista previa del artifact:
  ahí el visor no permite descargas.

## Aviso

Las condiciones de las prop firms cambian sin publicar cambios. Cada fila lleva su fecha de
consulta. Antes de pagar nada, vuelve a mirar en la web oficial el precio vigente, el tipo
exacto de drawdown en las **dos** fases, la cuota de activación, la regla de consistencia y
si TradingView permite **ejecutar** o solo ver gráficos.

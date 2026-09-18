/* Prueba headless de docs/index.html con jsdom.
   Comprueba que la app pinta, filtra, ordena, compara y abre la ficha
   sin errores de consola.  Uso:  node build/probar_app.js            */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const ruta = path.join(__dirname, '..', 'docs', 'index.html');
const html = fs.readFileSync(ruta, 'utf8');

const errores = [];
const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  url: 'https://ejemplo.github.io/fondeadoras/',
  pretendToBeVisual: true,
  virtualConsole: new (require('jsdom').VirtualConsole)()
    .on('jsdomError', e => errores.push('jsdomError: ' + e.message))
    .on('error', (...a) => errores.push('console.error: ' + a.join(' ')))
});

const { window } = dom;
const doc = window.document;
const $ = s => doc.querySelectorAll(s);

let fallos = 0, pasos = 0;
function ok(nombre, cond, extra) {
  pasos++;
  if (cond) console.log('  ok   ' + nombre + (extra ? '  [' + extra + ']' : ''));
  else { fallos++; console.log('  FALLA ' + nombre + (extra ? '  [' + extra + ']' : '')); }
}

// El runtime pinta en requestAnimationFrame: se espera a que se vacie la cola
const esperar = () => new Promise(r => setTimeout(r, 60));

(async () => {
  await esperar(); await esperar();

  const app = window.__app;
  console.log('\n— arranque —');
  ok('la app se ha instanciado', !!app);
  ok('los datos estan cargados', !!(window.DATA && window.DATA.planes.length === 35),
     window.DATA ? window.DATA.planes.length + ' planes' : 'sin DATA');
  ok('state.listo', app && app.state.listo === true);

  // jsdom simula una ventana de 1024 px, asi que arranca en modo tabla.
  // Para probar la vista de movil hay que forzar el ancho estrecho.
  console.log('\n— lista (movil) —');
  app.setState({ ancho: false }); await esperar();
  let tarjetas = $('article');
  ok('pinta una tarjeta por plan', tarjetas.length === 35, tarjetas.length + ' tarjetas');
  ok('la primera tarjeta es el puesto 1',
     /#1/.test(tarjetas[0].textContent) && /Tradeify/.test(tarjetas[0].textContent));
  ok('muestra precio con promo y tarifa tachada', /123/.test(tarjetas[0].textContent));
  ok('muestra las 3 metricas por defecto',
     tarjetas[0].textContent.includes('Precio tarifa') &&
     tarjetas[0].textContent.includes('Drawdown') &&
     tarjetas[0].textContent.includes('Dias min.'));
  ok('badge de TradingView', /TRADINGVIEW/.test(tarjetas[0].textContent));
  ok('contador de la promo', /PROMO/.test(tarjetas[0].textContent));
  ok('nav con 4 pestanas', $('nav button').length === 4);

  console.log('\n— buscador —');
  const input = doc.querySelector('input[placeholder="Buscar firma o plan"]');
  ok('existe el buscador', !!input);
  input.value = 'apex';
  input.dispatchEvent(new window.Event('input', { bubbles: true }));
  await esperar();
  tarjetas = $('article');
  const soloApex = [...tarjetas].every(t => /Apex/i.test(t.textContent));
  ok('filtra por texto', tarjetas.length > 0 && tarjetas.length < 35 && soloApex,
     tarjetas.length + ' resultados, todos Apex: ' + soloApex);
  ok('el foco del buscador sobrevive al repintado',
     doc.querySelector('input[placeholder="Buscar firma o plan"]') === input);
  ok('el valor del input se conserva', input.value === 'apex');

  input.value = '';
  input.dispatchEvent(new window.Event('input', { bubbles: true }));
  await esperar();
  ok('al vaciar vuelven los 35', $('article').length === 35);

  console.log('\n— filtros —');
  app.setState({ hoja: 'filtros' }); await esperar();
  const facetas = [...$('button')].filter(b => /Trailing intradia/.test(b.textContent));
  ok('la hoja de filtros lista las facetas', facetas.length > 0, facetas.length + ' coincidencias');
  facetas[0].dispatchEvent(new window.Event('click', { bubbles: true }));
  await esperar();
  const nIntradia = window.DATA.planes.filter(p => p.dd_evaluacion === 'Trailing intradia').length;
  ok('al marcar una faceta se filtra', app.state.enums.dd_evaluacion &&
     app.filtrados().length === nIntradia, app.filtrados().length + ' de ' + nIntradia);
  app.setState({ enums: {}, hoja: null }); await esperar();
  ok('limpiar filtros restaura', $('article').length === 35);

  console.log('\n— orden —');
  app.ordenarPor('precio_promo'); await esperar();
  let precios = app.visibles().map(p => p.precio_promo).filter(v => typeof v === 'number');
  ok('ordena ascendente por precio', precios.every((v, i) => i === 0 || precios[i - 1] <= v),
     precios[0] + ' … ' + precios[precios.length - 1]);
  app.ordenarPor('precio_promo'); await esperar();
  precios = app.visibles().map(p => p.precio_promo).filter(v => typeof v === 'number');
  ok('el segundo clic invierte el sentido',
     precios.every((v, i) => i === 0 || precios[i - 1] >= v));
  app.ordenarPor('fiabilidad_nota'); await esperar();
  ok('se puede ordenar por la nota de fiabilidad derivada',
     app.state.ordenKey === 'fiabilidad_nota' && $('article').length === 35);
  app.setState({ ordenKey: 'puesto', ordenDir: 'asc' }); await esperar();

  console.log('\n— ficha —');
  const verFicha = [...$('button')].find(b => b.textContent.trim() === 'Ver ficha');
  verFicha.dispatchEvent(new window.Event('click', { bubbles: true }));
  await esperar();
  ok('se abre la ficha', !!app.state.ficha, app.state.ficha);
  const cuerpo = doc.body.textContent;
  ok('la ficha trae los grupos de campos',
     cuerpo.includes('IDENTIDAD') || cuerpo.includes('Identidad'));
  ok('la ficha trae el aviso de verificacion', /antes de pagar/i.test(cuerpo));
  app.setState({ ficha: null }); await esperar();

  console.log('\n— comparador —');
  const ids = window.DATA.planes.slice(0, 2).map(p => p.id);
  app.toggleComparar(ids[0]); app.toggleComparar(ids[1]);
  app.setState({ vista: 'comparar' }); await esperar();
  const filasCmp = $('tbody tr').length;
  ok('el comparador enfrenta 2 planes', filasCmp > 0, filasCmp + ' filas de diferencias');
  app.setState({ soloDif: false }); await esperar();
  ok('sin "solo diferencias" salen mas filas', $('tbody tr').length >= filasCmp,
     $('tbody tr').length + ' filas');

  console.log('\n— coste real —');
  app.setState({ vista: 'coste', meses: 1 }); await esperar();
  const topstep = window.DATA.planes.find(p => p.firma === 'Topstep');
  const c1 = app.costeTarifa(topstep, 1), c6 = app.costeTarifa(topstep, 6);
  ok('un plan mensual escala con los meses', c6 === c1 * 6, c1 + ' -> ' + c6);
  const tradeify = window.DATA.planes[0];
  ok('un plan de pago unico no escala',
     app.costeTarifa(tradeify, 1) === app.costeTarifa(tradeify, 6));
  app.setState({ meses: 6 }); await esperar();
  ok('la vista de coste pinta', doc.body.textContent.includes('Coste real hasta el primer cobro'));

  console.log('\n— metodo —');
  app.setState({ vista: 'metodo' }); await esperar();
  ok('el metodo trae los 10 bloques del Excel', $('section').length >= 10, $('section').length);
  ok('incluye la leyenda', /Verde: compatible/.test(doc.body.textContent));

  console.log('\n— tabla en pantalla ancha —');
  app.setState({ vista: 'lista', ancho: true }); await esperar();
  ok('pinta la tabla', $('table thead th').length > 0, $('table thead th').length + ' columnas');
  ok('una fila por plan', $('table tbody tr').length === 35, $('table tbody tr').length);
  app.setState({ ancho: false }); await esperar();

  console.log('\n— persistencia —');
  ok('guarda en localStorage', !!window.localStorage.getItem('ff.comparador.v1'));
  const guardado = JSON.parse(window.localStorage.getItem('ff.comparador.v1'));
  ok('guarda el comparador y las metricas',
     Array.isArray(guardado.cols) && guardado.cols.length === 3);

  console.log('\n— consola —');
  ok('sin errores de JavaScript', errores.length === 0, errores.slice(0, 3).join(' | '));

  console.log('\n' + (fallos === 0 ? 'TODO OK' : fallos + ' FALLOS') + ' — ' + pasos + ' comprobaciones\n');
  process.exit(fallos === 0 ? 0 : 1);
})().catch(e => { console.error('EXCEPCION', e); process.exit(1); });

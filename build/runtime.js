/* ---------------------------------------------------------------------------
   Micro-runtime de plantillas — sustituye a dc-runtime.
   Sin React, sin Babel, sin CDN: ~5 KB y todo local.

   Interpreta el mismo lenguaje de plantilla que usa Claude Design:
     {{ expresion }}            en texto y dentro de atributos
     <sc-if value="{{ x }}">    condicional
     <sc-for list="{{ l }}" as="p">  repeticion
     onClick / onChange="{{ h }}"    manejadores
     style-hover="..."               estilos al pasar el raton

   La plantilla llega ya compilada a arbol de instrucciones (JSON) desde
   construir_app.py, asi que aqui no se parsea HTML: los nodos se crean con
   createElement, lo que evita que el parser del navegador reubique un
   <sc-for> que este dentro de una <table>.

   El render construye un arbol nuevo y despues lo fusiona (morphing) contra
   el vivo, emparejando por clave. Asi no se pierde el foco del buscador ni
   la posicion del scroll al teclear.
--------------------------------------------------------------------------- */
(function (global) {
  'use strict';

  var VACIOS = { input: 1, br: 1, img: 1, hr: 1, meta: 1, link: 1, source: 1 };

  // ---- evaluacion de expresiones (solo rutas y literales) ----
  function evaluar(scope, expr) {
    if (expr === 'true') return true;
    if (expr === 'false') return false;
    if (expr === 'null') return null;
    var partes = expr.split('.');
    var v = scope[partes[0]];
    for (var i = 1; i < partes.length && v !== null && v !== undefined; i++) v = v[partes[i]];
    return v;
  }

  // Une los trozos de un atributo o de un texto: ["px ", {e:"x"}, ";"]
  function unir(partes, scope) {
    if (partes.length === 1 && typeof partes[0] === 'object') {
      var u = evaluar(scope, partes[0].e);
      return u === null || u === undefined ? '' : u;
    }
    var s = '';
    for (var i = 0; i < partes.length; i++) {
      var p = partes[i];
      if (typeof p === 'string') s += p;
      else {
        var v = evaluar(scope, p.e);
        s += (v === null || v === undefined) ? '' : v;
      }
    }
    return s;
  }

  // ---- construccion del arbol nuevo ----
  function construir(inst, scope, salida, clave) {
    for (var i = 0; i < inst.length; i++) {
      var n = inst[i];
      var k = clave + '/' + i;

      if (n.t === 'tx') {
        var txt = String(unir(n.p, scope));
        var nodo = document.createTextNode(txt);
        nodo.__k = k;
        salida.push(nodo);

      } else if (n.t === 'if') {
        if (evaluar(scope, n.e)) construir(n.k, scope, salida, k + ':si');

      } else if (n.t === 'for') {
        var lista = evaluar(scope, n.e);
        if (lista && lista.length) {
          for (var j = 0; j < lista.length; j++) {
            var hijo = Object.create(scope);
            hijo[n.as] = lista[j];
            // la clave usa el id del elemento si lo tiene: asi reordenar no recrea
            var idj = (lista[j] && (lista[j].id || lista[j].key || lista[j].valor || lista[j].label));
            construir(n.k, hijo, salida, k + '#' + (idj !== undefined ? idj : j));
          }
        }

      } else if (n.t === 'el') {
        var el = document.createElement(n.g);
        el.__k = k;
        for (var a in n.a) el.setAttribute(a, unir(n.a[a], scope));
        if (n.v !== undefined) {
          var val = unir(n.v, scope);
          if (el.value !== val) el.value = val;
        }
        if (n.ev) {
          el.__on = {};
          for (var ev in n.ev) {
            var h = evaluar(scope, n.ev[ev]);
            if (typeof h === 'function') el.__on[ev] = h;
          }
        }
        if (n.k && n.k.length) {
          var hijos = [];
          construir(n.k, scope, hijos, k);
          for (var m = 0; m < hijos.length; m++) el.appendChild(hijos[m]);
        }
        salida.push(el);
      }
    }
  }

  // ---- fusion contra el DOM vivo ----
  function sincronizarAtributos(viejo, nuevo) {
    var na = nuevo.attributes, i, at;
    for (i = 0; i < na.length; i++) {
      at = na[i];
      if (viejo.getAttribute(at.name) !== at.value) viejo.setAttribute(at.name, at.value);
    }
    var va = viejo.attributes;
    for (i = va.length - 1; i >= 0; i--) {
      at = va[i];
      if (!nuevo.hasAttribute(at.name)) viejo.removeAttribute(at.name);
    }
    if ('value' in nuevo && nuevo.tagName === 'INPUT') {
      if (viejo.value !== nuevo.value) viejo.value = nuevo.value;
    }
  }

  function fusionar(viejo, nuevo) {
    if (nuevo.nodeType === 3) {
      if (viejo.nodeValue !== nuevo.nodeValue) viejo.nodeValue = nuevo.nodeValue;
      return viejo;
    }
    sincronizarAtributos(viejo, nuevo);
    viejo.__on = nuevo.__on;
    fusionarHijos(viejo, nuevo.childNodes);
    return viejo;
  }

  function fusionarHijos(padre, nuevos) {
    var viejos = [], i;
    for (i = 0; i < padre.childNodes.length; i++) viejos.push(padre.childNodes[i]);

    var porClave = {};
    for (i = 0; i < viejos.length; i++) {
      if (viejos[i].__k !== undefined) porClave[viejos[i].__k] = viejos[i];
    }

    var resultado = [], usados = [];
    for (i = 0; i < nuevos.length; i++) {
      var n = nuevos[i];
      var v = porClave[n.__k];
      if (v && v.nodeName === n.nodeName && !v.__usado) {
        v.__usado = true;
        usados.push(v);
        resultado.push(fusionar(v, n));
      } else {
        resultado.push(n);
      }
    }
    for (i = 0; i < usados.length; i++) usados[i].__usado = false;

    // fuera los que ya no estan
    var vivos = {};
    for (i = 0; i < resultado.length; i++) vivos[i] = resultado[i];
    for (i = 0; i < viejos.length; i++) {
      var q = viejos[i], sigue = false;
      for (var j = 0; j < resultado.length; j++) if (resultado[j] === q) { sigue = true; break; }
      if (!sigue && q.parentNode === padre) padre.removeChild(q);
    }

    // coloca en orden (insertBefore mueve si ya estaba)
    var ref = null;
    for (i = resultado.length - 1; i >= 0; i--) {
      var nodo = resultado[i];
      if (nodo.parentNode !== padre || nodo.nextSibling !== ref) padre.insertBefore(nodo, ref);
      ref = nodo;
    }
  }

  // ---- delegacion de eventos ----
  function delegar(raiz, tipo) {
    raiz.addEventListener(tipo, function (e) {
      var n = e.target;
      while (n && n !== raiz.parentNode) {
        if (n.__on && n.__on[tipo]) {
          n.__on[tipo](e);
          if (e.cancelBubble) return;   // el manejador llamo a stopPropagation()
        }
        n = n.parentNode;
      }
    }, false);
  }

  // ---- clase base ----
  function Logic(raiz, inst, props) {
    this.base = raiz;
    this._inst = inst;
    this.props = props || {};
    this._pendiente = false;
    if (!this.state) this.state = {};
  }

  Logic.prototype.setState = function (o) {
    for (var k in o) this.state[k] = o[k];
    this.programar();
  };

  // Se repinta en una microtarea, no en requestAnimationFrame: rAF se congela
  // cuando la pestana no esta en primer plano y la app se quedaria muerta.
  var aplazar = (typeof queueMicrotask === 'function')
    ? queueMicrotask
    : function (f) { Promise.resolve().then(f); };

  Logic.prototype.programar = function () {
    if (this._pendiente) return;
    this._pendiente = true;
    var self = this;
    aplazar(function () {
      self._pendiente = false;
      try { self.pintar(); } catch (e) { console.error('Error al pintar:', e); }
    });
  };

  Logic.prototype.pintar = function () {
    var scope = this.renderVals();
    var hijos = [];
    construir(this._inst, scope, hijos, '');
    var contenedor = document.createDocumentFragment();
    for (var i = 0; i < hijos.length; i++) contenedor.appendChild(hijos[i]);
    fusionarHijos(this.base, contenedor.childNodes);
    if (this.componentDidUpdate) this.componentDidUpdate();
  };

  Logic.prototype.montar = function () {
    delegar(this.base, 'click');
    delegar(this.base, 'input');
    this.pintar();
    if (this.componentDidMount) this.componentDidMount();
    this.programar();
  };

  global.Logic = Logic;
  global.DCRuntime = { evaluar: evaluar, construir: construir, fusionar: fusionar };

})(typeof window !== 'undefined' ? window : this);

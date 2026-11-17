// ===== Gráficas de línea en SVG propio (sin librerías) =====
// - null = sin datos: la línea se corta y el día se sombrea. Nunca se dibuja como 0.
// - Ratón: tooltip. Teclado: ←/→ (Inicio/Fin) para moverse, Intro para abrir el detalle. Toque: abre el detalle.
const Grafica = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  let W = 800, H = 230;
  const P = {l: 48, r: 12, t: 12, b: 28};
  // se dibuja al ancho real disponible: así 1 unidad del dibujo ≈ 1 píxel y los textos se leen también en el móvil
  function medir() {
    const ancho = ((document.querySelector('#contenido') || {}).clientWidth || 830) - 32;
    W = Math.max(300, Math.min(1400, ancho));
    H = W < 560 ? 190 : 230;
  }
  const svgEl = (tag, a) => { const n = document.createElementNS(NS, tag); for (const k in a) n.setAttribute(k, a[k]); return n; };
  const fechaCorta = f => new Date(f + 'T12:00:00').toLocaleDateString('es-ES', {day: 'numeric', month: 'short'});
  const fechaLarga = f => new Date(f + 'T12:00:00').toLocaleDateString('es-ES', {weekday: 'long', day: 'numeric', month: 'long'});

  function escala(max) {
    if (!(max > 0)) return {max: 1, paso: 1};
    const bruto = max / 4, mag = 10 ** Math.floor(Math.log10(bruto));
    const paso = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= bruto);
    return {max: paso * Math.ceil(max / paso), paso};
  }

  // cfg: {fechas, series:[{id,nombre,color,valores,discontinua}], formato(v), etiqueta, onDia(i)}
  function crear(cont, cfg) {
    medir();
    const n = cfg.fechas.length, vis = cfg.series;
    const vals = vis.flatMap(s => s.valores).filter(v => v != null && isFinite(v));
    const {max, paso} = escala(Math.max(0, ...vals));
    const iw = W - P.l - P.r, ih = H - P.t - P.b;
    const x = i => P.l + (n === 1 ? iw / 2 : i * iw / (n - 1));
    const y = v => P.t + ih - (v / max) * ih;
    const svg = svgEl('svg', {viewBox: `0 0 ${W} ${H}`, tabindex: '0', role: 'group', 'aria-label': cfg.etiqueta + '. Usa las flechas para recorrer los días e Intro para ver el detalle.'});
    // días sin datos en ninguna serie visible: banda sombreada
    const ancho = n > 1 ? iw / (n - 1) : iw;
    cfg.fechas.forEach((f, i) => {
      if (vis.length && vis.every(s => s.valores[i] == null)) svg.append(svgEl('rect', {class: 'hueco', x: x(i) - ancho / 2, y: P.t, width: ancho, height: ih}));
    });
    for (let v = 0; v <= max + 1e-9; v += paso) {
      svg.append(svgEl('line', {class: 'eje', x1: P.l, x2: W - P.r, y1: y(v), y2: y(v)}));
      const t = svgEl('text', {x: P.l - 6, y: y(v) + 4, 'text-anchor': 'end'}); t.textContent = cfg.formato(v); svg.append(t);
    }
    const cada = n <= 7 ? (W < 420 ? 2 : 1) : n <= 30 ? (W < 560 ? 10 : 5) : (W < 560 ? 30 : 15);
    cfg.fechas.forEach((f, i) => {
      if ((n - 1 - i) % cada === 0) { const t = svgEl('text', {x: x(i), y: H - 8, 'text-anchor': i === n - 1 ? 'end' : i === 0 ? 'start' : 'middle'}); t.textContent = fechaCorta(f); svg.append(t); }
    });
    // degradado suave bajo cada línea (solo en tramos con datos: los huecos siguen vacíos, nunca se rellenan)
    const defs = svgEl('defs', {}); svg.append(defs);
    vis.forEach((s, k) => {
      const gid = `g-${Math.random().toString(36).slice(2, 8)}-${k}`; s._grad = gid;
      const g = svgEl('linearGradient', {id: gid, x1: 0, y1: 0, x2: 0, y2: 1});
      g.append(svgEl('stop', {offset: '0%', 'stop-color': s.color, 'stop-opacity': vis.length > 1 ? .14 : .28}),
        svgEl('stop', {offset: '100%', 'stop-color': s.color, 'stop-opacity': 0}));
      defs.append(g);
      let tramo = [];
      const cerrar = () => { if (tramo.length > 1) svg.append(svgEl('path', {class: 'area', fill: `url(#${gid})`,
        d: `M${x(tramo[0][0]).toFixed(1)},${y(0).toFixed(1)}` + tramo.map(([i, v]) => `L${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('') + `L${x(tramo[tramo.length - 1][0]).toFixed(1)},${y(0).toFixed(1)}Z`})); tramo = []; };
      s.valores.forEach((v, i) => { if (v == null || !isFinite(v)) cerrar(); else tramo.push([i, v]); });
      cerrar();
    });
    for (const s of vis) {
      let d = '', abierto = false;
      s.valores.forEach((v, i) => {
        if (v == null) { abierto = false; return; }
        d += (abierto ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1);
        abierto = true;
        const aislado = (i === 0 || s.valores[i - 1] == null) && (i === n - 1 || s.valores[i + 1] == null);
        if (aislado || (n <= 31 && W >= 420)) svg.append(svgEl('circle', {class: 'punto', cx: x(i), cy: y(v), r: aislado ? 3.5 : 2.6, fill: s.color}));
      });
      if (d) svg.append(svgEl('path', {class: 'linea', d, stroke: s.color, 'stroke-dasharray': s.discontinua ? '6 4' : 'none'}));
    }
    const cursor = svgEl('line', {class: 'cursor', y1: P.t, y2: P.t + ih, x1: -10, x2: -10});
    svg.append(cursor);
    const vivo = el('div', {class: 'am', 'aria-live': 'polite', style: 'min-height:1.2em'});
    let sel = n - 1;

    const texto = i => `${fechaLarga(cfg.fechas[i])}: ` + vis.map(s => `${s.nombre} ${s.valores[i] == null ? 'sin datos' : cfg.formato(s.valores[i])}`).join(' · ');
    const indice = ev => { const r = svg.getBoundingClientRect(); const px = (ev.clientX - r.left) * W / r.width;
      return Math.max(0, Math.min(n - 1, Math.round((px - P.l) / (n > 1 ? iw / (n - 1) : 1)))); };
    const marcar = i => { sel = i; cursor.setAttribute('x1', x(i)); cursor.setAttribute('x2', x(i)); };
    svg.addEventListener('pointermove', ev => { if (ev.pointerType !== 'mouse') return; const i = indice(ev); marcar(i);
      showTip(ev, fechaLarga(cfg.fechas[i]), vis.map(s => `${s.nombre}: ${s.valores[i] == null ? 'sin datos' : cfg.formato(s.valores[i])}`).join(' · ')); });
    svg.addEventListener('pointerleave', () => { hideTip(); });
    svg.addEventListener('click', ev => { const i = indice(ev); marcar(i); vivo.textContent = texto(i); cfg.onDia(i); });
    svg.addEventListener('keydown', ev => {
      const mov = {ArrowLeft: -1, ArrowRight: 1}[ev.key];
      if (mov) { ev.preventDefault(); marcar(Math.max(0, Math.min(n - 1, sel + mov))); vivo.textContent = texto(sel); }
      else if (ev.key === 'Home' || ev.key === 'End') { ev.preventDefault(); marcar(ev.key === 'Home' ? 0 : n - 1); vivo.textContent = texto(sel); }
      else if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); cfg.onDia(sel); }
    });
    svg.addEventListener('focus', () => { marcar(sel); vivo.textContent = texto(sel); });
    cont.replaceChildren(svg, vivo);
  }

  // Valor de hoy y diferencia con ayer, sin porcentajes engañosos.
  function comparar(hoy, ayer, formato) {
    if (hoy == null) return {hoy: 'sin datos', dif: 'Hoy todavía sin datos'};
    if (ayer == null) return {hoy: formato(hoy), dif: 'Sin comparación (ayer sin datos)'};
    const d = hoy - ayer, signo = d > 0 ? '+' : d < 0 ? '−' : '±';
    if (ayer === 0) return {hoy: formato(hoy), dif: `${signo}${formato(Math.abs(d))} vs ayer (ayer: 0)`};
    const pct = Math.round(d / ayer * 100);
    return {hoy: formato(hoy), dif: `${signo}${formato(Math.abs(d))} (${signo}${Math.abs(pct)} %) vs ayer`};
  }
  return {crear, comparar, fechaLarga};
})();

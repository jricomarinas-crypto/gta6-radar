// ===== INICIO › Hoy: tres gráficas diarias + resumen operativo =====
// Cada gráfica lleva su etiqueta DEMO o REAL: nunca se mezclan datos demo y reales en una misma gráfica.
const Hoy = (() => {
  const st = {periodo: guardado.leer('hoy.periodo', 30), metrica: guardado.leer('hoy.metrica', 'publicados'),
    ocultas: guardado.leer('hoy.ocultas', {}), dia: null, produccion: null, piezas: null};
  const nf0 = v => fmt(v);
  const METRICAS = {
    publicados: {nombre: 'Vídeos publicados', unidad: 'vídeos/día',
      def: 'Vídeos de GTA 6 cuya fecha de publicación cae ese día, entre los que ha visto el Radar.'},
    detectados: {nombre: 'Vídeos detectados', unidad: 'vídeos/día',
      def: 'Vídeos que el Radar vio por primera vez ese día (aunque se publicaran antes).'},
    max_vistas_hora: {nombre: 'Máx. vistas/hora', unidad: 'vistas/hora',
      def: 'Mayor velocidad medida ese día entre los vídeos que se actualizaron. Solo existe desde que se guarda el resumen diario.'},
  };
  const zona = () => (DATA.series || {}).zona || 'Europe/Madrid';
  const diaLocal = iso => iso ? new Intl.DateTimeFormat('en-CA', {timeZone: zona()}).format(new Date(iso)) : null;

  function fechasPeriodo() {
    const hoy = (DATA.series || {}).hoy || new Date().toISOString().slice(0, 10);
    const out = [];
    for (let i = st.periodo - 1; i >= 0; i--) { const d = new Date(hoy + 'T12:00:00'); d.setDate(d.getDate() - i); out.push(d.toISOString().slice(0, 10)); }
    return out;
  }
  const alinear = (fechas, filas, clave) => { const m = new Map((filas || []).map(f => [f.fecha, f[clave]])); return fechas.map(f => m.has(f) ? m.get(f) : null); };

  function bloque(id, titulo, def, etq) {
    const caja = el('section', {class: 'graf', 'aria-labelledby': 'g-' + id});
    caja.append(el('div', {class: 'graf-cab'},
      el('div', {}, el('h3', {id: 'g-' + id}, titulo, etq ? el('span', {class: 'etq ' + etq.toLowerCase(), text: etq}) : null),
        el('div', {class: 'def', text: def})),
      el('div', {class: 'graf-hoy', id: 'hoy-' + id})));
    return caja;
  }
  function leyenda(id, series, alCambiar) {
    const ocultas = new Set(st.ocultas[id] || []);
    return el('div', {class: 'leyenda', role: 'group', 'aria-label': 'Series'}, ...series.map(s => {
      const b = el('button', {type: 'button', 'aria-pressed': ocultas.has(s.id) ? 'false' : 'true'},
        el('i', {class: s.discontinua ? 'discont' : '', style: `background:${s.color};border-color:${s.color}`}), s.nombre);
      b.addEventListener('click', () => { ocultas.has(s.id) ? ocultas.delete(s.id) : ocultas.add(s.id);
        st.ocultas[id] = [...ocultas]; guardado.poner('hoy.ocultas', st.ocultas); alCambiar(); });
      return b;
    }));
  }
  function resumenHoy(caja, series, formato) {
    caja.replaceChildren(...series.map(s => { const n = s.valores.length, c = Grafica.comparar(s.valores[n - 1], s.valores[n - 2], formato);
      return el('div', {}, el('div', {class: 'n', text: c.hoy}), el('div', {class: 'd', text: (series.length > 1 ? s.nombre + ': ' : 'Hoy · ') + c.dif})); }));
  }
  function vacio(titulo, falta, porque, accion) {
    return el('div', {class: 'graf-vacio', role: 'status'}, el('b', {text: titulo}), el('br'),
      el('span', {}, el('b', {text: 'Falta: '}), falta), el('br'), el('span', {}, el('b', {text: 'Por qué: '}), porque), el('br'),
      el('span', {}, el('b', {text: 'Qué hacer: '}), accion));
  }

  // ---------- detalle de un día (conserva periodo, métrica y series elegidas)
  async function detalle(id, fecha, series, formato, caja) {
    st.dia = {id, fecha};
    const i = fechasPeriodo().indexOf(fecha);
    const partes = [el('b', {text: Grafica.fechaLarga(fecha)}),
      el('div', {class: 'vals'}, ...series.map(s => el('span', {}, `${s.nombre}: `, el('b', {text: s.valores[i] == null ? 'sin datos' : formato(s.valores[i])}))))];
    if (id === 'radar') {
      const vids = (DATA.videos || []).filter(v => diaLocal(v.published_at) === fecha).slice(0, 8);
      partes.push(vids.length ? el('ul', {}, ...vids.map(v => el('li', {}, safeUrl(v.url) ? el('a', {href: safeUrl(v.url), target: '_blank', rel: 'noopener', text: v.title}) : v.title,
        el('span', {class: 'am', text: ` · ${v.channel || '—'} · ${fmt(v.velocity)} vistas/h`}))))
        : el('div', {class: 'am', text: 'La lista de vídeos solo está disponible para las últimas 48 h del Radar.'}),
        el('a', {href: '#/investigar/videos', text: 'Abrir Investigar › Vídeos →'}));
    }
    if (id === 'produccion' && window.PC_ESTUDIO) {
      try {
        const d = await api('/api/series/dia?fecha=' + encodeURIComponent(fecha));
        const NOMBRE = {pieza_creada: 'pieza creada', idea_aprobado: 'idea aprobada', guion_aprobado: 'guion aprobado', video_fabricado: 'vídeo fabricado',
          video_aprobado: 'vídeo aprobado', exportado: 'exportado', publicado: 'publicado'};
        partes.push(d.eventos.length ? el('ul', {}, ...d.eventos.map(e => el('li', {}, `${new Date(e.hora).toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit'})} · ${NOMBRE[e.tipo] || e.tipo}`
          + (e.plataforma ? ` (${e.plataforma})` : '') + ` · ${e.titulo || e.pieza}` + (e.origen === 'reconstruido' ? ' · reconstruido' : ''))))
          : el('div', {class: 'am', text: 'Ningún evento ese día.'}), el('a', {href: '#/crear/produccion', text: 'Abrir Crear › En producción →'}));
      } catch (e) { partes.push(el('div', {class: 'bad', text: 'No se pudo cargar el detalle: ' + e.message})); }
    }
    const cerrar = el('button', {class: 'btn', type: 'button', text: 'Cerrar detalle'});
    cerrar.addEventListener('click', () => { st.dia = null; caja.replaceChildren(); });
    caja.replaceChildren(el('div', {class: 'detalle-dia'}, ...partes, el('div', {style: 'margin-top:6px'}, cerrar)));
  }

  function grafica(id, caja, series, formato, etiqueta) {
    const ocultas = new Set(st.ocultas[id] || []);
    const vis = series.filter(s => !ocultas.has(s.id));
    const g = el('div'); const det = el('div', {id: 'det-' + id});
    caja.append(g, det);
    Grafica.crear(g, {fechas: fechasPeriodo(), series: vis, formato, etiqueta, onDia: i => detalle(id, fechasPeriodo()[i], vis, formato, det)});
    resumenHoy(caja.querySelector('.graf-hoy'), vis.length ? vis : series.slice(0, 1), formato);
    if (st.dia && st.dia.id === id && fechasPeriodo().includes(st.dia.fecha)) detalle(id, st.dia.fecha, vis, formato, det);
  }

  // ---------- 1. Radar
  function radar() {
    const caja = bloque('radar', 'Radar · actividad sobre GTA 6', METRICAS[st.metrica].def, DATA.demo ? 'DEMO' : 'REAL');
    const sel = el('div', {class: 'seg', role: 'group', 'aria-label': 'Métrica del Radar'}, ...Object.entries(METRICAS).map(([k, m]) => {
      const b = el('button', {type: 'button', 'aria-pressed': k === st.metrica ? 'true' : 'false', text: m.nombre});
      b.addEventListener('click', () => { st.metrica = k; guardado.poner('hoy.metrica', k); pintar(); });
      return b;
    }));
    caja.append(el('div', {class: 'leyenda'}, sel, el('span', {class: 'am', text: 'Unidad: ' + METRICAS[st.metrica].unidad})));
    const fechas = fechasPeriodo();
    const valores = alinear(fechas, (DATA.series || {}).radar, st.metrica);
    if (valores.every(v => v == null)) {
      caja.append(vacio('Todavía no hay datos diarios del Radar en este periodo.', 'resúmenes diarios guardados por el Radar.',
        'el resumen diario empezó a guardarse el 16-nov-2026 y en estos datos no hay ejecuciones con vídeos (sin clave de YouTube el Radar no trae vídeos).',
        'pon YOUTUBE_API_KEY en GitHub Secrets y espera a las próximas ejecuciones horarias.'));
      return caja;
    }
    grafica('radar', caja, [{id: st.metrica, nombre: METRICAS[st.metrica].nombre, color: '#F97316', valores}], nf0, 'Radar: ' + METRICAS[st.metrica].nombre);
    return caja;
  }

  // ---------- 2. Mi canal
  function canal() {
    // En el Estudio: tus mediciones reales (privadas). En la web pública: la demo, etiquetada. Nunca se mezclan.
    const demo = window.PC_ESTUDIO ? null : (DATA.series || {}).canal_demo;
    const real = window.PC_ESTUDIO ? st.canal : null;
    const datos = real || demo;
    const caja = bloque('canal', 'Mi canal · vistas diarias', 'Vistas nuevas de cada día por plataforma (diferencia entre mediciones; nunca la suma de acumulados). Si entre dos mediciones pasan varios días, todo cuenta el día de la segunda («acumula N días»).', real ? 'REAL' : demo ? 'DEMO' : null);
    if (!datos) {
      caja.append(vacio('Sin datos de tus vídeos todavía.', 'mediciones de vistas de TikTok, YouTube Shorts y YouTube largo.',
        window.PC_ESTUDIO ? 'aún no has registrado ninguna medición.' : 'tus métricas son privadas y solo se ven en el Estudio de tu Mac.',
        window.PC_ESTUDIO ? 'regístralas en Mi canal › Estadísticas (TikTok a mano). YouTube Analytics queda pendiente de aprobar.' : 'abre el Estudio (python -m estudio).'));
      return caja;
    }
    if (real) { const notas = real.filter(d => d.notas && d.notas.length && fechasPeriodo().includes(d.fecha));
      if (notas.length) caja.append(el('div', {class: 'am', text: 'Ojo: ' + notas.map(d => `${d.fecha}: ${d.notas.join('; ')}`).join(' · ')})); }
    const fechas = fechasPeriodo();
    const series = [{id: 'tiktok', nombre: 'TikTok', color: '#22D3EE'}, {id: 'shorts', nombre: 'YouTube Shorts', color: '#F472B6'},
      {id: 'largo', nombre: 'YouTube largo', color: '#FACC15', discontinua: true}].map(s => ({...s, valores: alinear(fechas, datos, s.id)}));
    caja.append(leyenda('canal', series, pintar));
    grafica('canal', caja, series, nf0, 'Mi canal: vistas diarias por plataforma');
    return caja;
  }

  // ---------- 3. Producción
  function produccion() {
    const demoDatos = (DATA.series || {}).produccion_demo;
    const real = window.PC_ESTUDIO ? st.produccion : null;
    const filas = real ? real.dias : (!window.PC_ESTUDIO ? demoDatos : null);
    const etq = real ? 'REAL' : (filas ? 'DEMO' : null);
    const caja = bloque('produccion', 'Producción · mis piezas',
      'Fabricados: versiones de vídeo terminadas (regrabar y volver a fabricar suma otra). Aprobados: vídeos aprobados por ti. Publicados: subidas que marcas como hechas, una por plataforma.', etq);
    if (!filas) {
      caja.append(window.PC_ESTUDIO
        ? el('div', {class: 'am', role: 'status', text: 'Cargando los eventos del Estudio…'})
        : vacio('La producción solo se ve en el Estudio de tu Mac.', 'los eventos de producción (son privados).',
          'esta es la web pública o un archivo; los eventos viven en data/estudio.db y no se publican.', 'abre el Estudio: python -m estudio.'));
      return caja;
    }
    const fechas = fechasPeriodo();
    const series = [{id: 'fabricados', nombre: 'Fabricados', color: '#60A5FA'}, {id: 'aprobados', nombre: 'Aprobados', color: '#34D399'},
      {id: 'publicados', nombre: 'Publicados', color: '#F97316'}].map(s => ({...s, valores: alinear(fechas, filas, s.id)}));
    if (series.every(s => s.valores.every(v => v == null))) {
      caja.append(vacio('Sin eventos de producción en este periodo.', 'eventos del Estudio.', 'el registro empezó con la primera pieza; antes no hay datos.', 'crea una pieza en Crear › Fábrica de ideas.'));
      return caja;
    }
    caja.append(leyenda('produccion', series, pintar));
    if (real && real.hay_reconstruidos) caja.append(el('div', {class: 'am', text: 'Incluye eventos reconstruidos a partir de fechas guardadas antes del 16-nov (marcados en el detalle).'}));
    grafica('produccion', caja, series, nf0, 'Producción: vídeos fabricados, aprobados y publicados');
    return caja;
  }

  // ---------- resumen operativo (cada tarjeta lleva a su detalle)
  function resumen() {
    const k = DATA.kpis || {}, c24 = Date.now() - 864e5;
    const alertas = (DATA.alerts || []).filter(a => new Date(a.created_at) >= c24 && ['critical', 'high'].includes(a.severity)).length;
    const noticias = (DATA.news || []).filter(n => new Date(n.published_at) >= c24).length;
    const tarjeta = (href, tipo, v, l) => el(href ? 'a' : 'div', {class: 'res', href}, el('div', {class: 'tipo', text: tipo}), el('div', {class: 'v', text: v}), el('div', {class: 'l', text: l}));
    const t = [tarjeta('#/investigar/videos', 'Radar · últimas 24 h', fmt(k.videos_24h), `vídeos de GTA 6 · ${noticias} noticias`),
      tarjeta('#/investigar/videos', 'Velocidad · ahora', fmt(k.max_velocity), 'vistas/hora del vídeo que más crece'),
      tarjeta('#/inicio/alertas', 'Alertas · últimas 24 h', fmt(alertas), 'altas o críticas')];
    if (window.PC_ESTUDIO && st.piezas) {
      const p = st.piezas, n = e => p.filter(x => x.etapa === e).length;
      t.push(tarjeta('#/crear/produccion', 'Producción · ahora', fmt(n('Guion') + n('Montaje') + n('Brief')), 'piezas en curso (brief, guion o montaje)'),
        tarjeta('#/crear/produccion', 'Revisión · ahora', fmt(n('Revisión')), 'vídeos esperando tu aprobación'));
    }
    t.push(tarjeta(null, 'Mis vídeos', '—', 'sin métricas todavía (registro manual en la fase 2)'));
    return el('div', {class: 'resumen', 'aria-label': 'Resumen'}, ...t);
  }

  function pintar() {
    const periodo = el('div', {class: 'seg', role: 'group', 'aria-label': 'Periodo'}, ...[7, 30, 90].map(d => {
      const b = el('button', {type: 'button', 'aria-pressed': d === st.periodo ? 'true' : 'false', text: d + ' días'});
      b.addEventListener('click', () => { st.periodo = d; guardado.poner('hoy.periodo', d); pintar(); });
      return b;
    }));
    $('#hoy').replaceChildren(el('div', {class: 'hoy-cab'}, el('h2', {text: 'Últimos días'}), periodo,
      el('span', {class: 'am', text: `Días en hora de ${zona()}`})), radar(), canal(), produccion(), el('h2', {text: 'Resumen'}), resumen());
  }

  async function cargarEstudio() {
    try { st.produccion = await api('/api/series?dias=90'); st.piezas = (await api('/api/piezas')).piezas; }
    catch (e) { st.produccion = null; }
    try { st.canal = (await api('/api/canal/serie')).serie; } catch (e) { st.canal = null; }
    pintar();
  }

  function iniciar() {
    pintar();
    let ancho = innerWidth, espera;
    window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => {
      if (Math.abs(innerWidth - ancho) > 40 && !document.querySelector('[data-vista="inicio/hoy"]').hidden) { ancho = innerWidth; pintar(); } }, 200); });
    window.addEventListener('estudio-listo', cargarEstudio);
    window.addEventListener('vista', e => { if (e.detail === 'inicio/hoy' && window.PC_ESTUDIO) cargarEstudio(); });
  }
  return {iniciar, comparar: Grafica.comparar};
})();

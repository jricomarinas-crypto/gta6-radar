// ===== Crear (fase 3): Revisión y Calendario · Sistema › Automatizaciones · «Crear vídeo de esto» en Temas =====
// Solo en el Estudio. El Calendario es tu planificación: no publica nada automáticamente.
const Crear = (() => {
  const st = {mes: null};
  const vacio = t => el('div', {class: 'empty', text: t});
  const isoDia = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

  async function pintarRevision() {
    const d = await api('/api/piezas');
    const pend = d.piezas.filter(p => p.espera_a_javier);
    const grupos = [['Brief', 'Ideas por aprobar'], ['Guion', 'Guiones listos para aprobar'], ['Revisión', 'Vídeos por revisar']];
    $('#revision').replaceChildren(el('div', {class: 'card'},
      el('p', {class: 'am', text: 'Solo lo que espera una decisión tuya. Los botones son los mismos que en En producción: nada se aprueba ni se publica sin que lo pulses.'}),
      pend.length ? null : vacio('Nada pendiente. 🎉')),
      ...grupos.filter(([e]) => pend.some(p => p.etapa === e)).map(([e, t]) => el('div', {class: 'card'}, el('h2', {text: `${t} (${pend.filter(p => p.etapa === e).length})`}),
        el('div', {class: 'op'}, ...pend.filter(p => p.etapa === e).map(piezaCard)))));
  }

  async function pintarCalendario() {
    const [d] = await Promise.all([api('/api/piezas')]);
    const hoy = new Date(); st.mes = st.mes || new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    const m = st.mes, ini = new Date(m.getFullYear(), m.getMonth(), 1), fin = new Date(m.getFullYear(), m.getMonth() + 1, 0);
    const porDia = {};
    const add = (f, x) => { (porDia[f] = porDia[f] || []).push(x); };
    d.piezas.forEach(p => {
      if (p.fecha_prevista) add(p.fecha_prevista, {tipo: 'prevista', p});
      Object.entries(p.exportacion || {}).forEach(([pl, e]) => { if (e.subida_en) add(isoDia(new Date(e.subida_en)), {tipo: 'publicada', p, pl, url: e.url}); });
    });
    if (DATA.release_date) add(DATA.release_date, {tipo: 'lanzamiento'});
    const item = x => x.tipo === 'lanzamiento' ? el('div', {class: 'cal-it lanz', text: '🚀 Lanzamiento de GTA 6'})
      : el('div', {class: 'cal-it ' + x.tipo}, x.tipo === 'publicada' ? '✓ ' : '📅 ',
        el('a', {href: '#/crear/produccion', text: x.p.idea.titulo || x.p.id, title: `${x.p.etapa} · encargo ${x.p.id}`}),
        el('span', {class: 'am', text: x.tipo === 'publicada' ? ` · publicada en ${FAB.plataformas[x.pl] || x.pl}` : ` · prevista · ${x.p.etapa}`}));
    const dias = [];
    for (let i = 1; i <= fin.getDate(); i++) dias.push(new Date(m.getFullYear(), m.getMonth(), i));
    const hueco = (ini.getDay() + 6) % 7;  // la semana empieza el lunes
    const rejilla = el('div', {class: 'cal', role: 'grid', 'aria-label': 'Calendario del mes'},
      ...['L', 'M', 'X', 'J', 'V', 'S', 'D'].map(x => el('div', {class: 'cal-cab', role: 'columnheader', text: x})),
      ...Array.from({length: hueco}, () => el('div', {class: 'cal-dia vacio', 'aria-hidden': 'true'})),
      ...dias.map(dd => { const f = isoDia(dd), xs = porDia[f] || [];
        return el('div', {class: 'cal-dia' + (f === isoDia(hoy) ? ' hoy' : '') + (xs.length ? ' con' : ''), role: 'gridcell'},
          el('div', {class: 'cal-n', text: dd.toLocaleDateString('es-ES', {weekday: 'short', day: 'numeric'})}), ...xs.map(item)); }));
    const sinFecha = d.piezas.filter(p => !p.fecha_prevista && !['Publicado', 'Descartada'].includes(p.etapa));
    const cambiar = n => { st.mes = new Date(m.getFullYear(), m.getMonth() + n, 1); pintarCalendario(); };
    $('#calendario').replaceChildren(el('div', {class: 'card'},
      el('div', {class: 'toolbar'}, el('button', {class: 'btn', type: 'button', text: '‹ Anterior', onclick: () => cambiar(-1)}),
        el('h2', {style: 'margin:0 12px', text: m.toLocaleDateString('es-ES', {month: 'long', year: 'numeric'})}),
        el('button', {class: 'btn', type: 'button', text: 'Siguiente ›', onclick: () => cambiar(1)}),
        el('button', {class: 'btn', type: 'button', text: 'Hoy', onclick: () => { st.mes = null; pintarCalendario(); }})),
      el('div', {class: 'aviso', text: 'Es tu planificación: no publica nada automáticamente. Las publicadas salen el día en que las marcaste como subidas.'}),
      rejilla),
      el('div', {class: 'card'}, el('h2', {text: `Sin fecha prevista (${sinFecha.length})`}),
        ...(sinFecha.length ? sinFecha.map(p => el('div', {class: 'res-item'}, el('div', {class: 'vt', text: p.idea.titulo || p.id}),
          el('div', {class: 'meta'}, el('span', {text: `${p.etapa} · encargo ${p.id}`}),
            boton('Programar…', async () => { const f = prompt('Fecha prevista (AAAA-MM-DD). Es solo tu planificación.', isoDia(new Date(Date.now() + 864e5)));
              if (f) { await api(`/api/piezas/${p.id}/programar`, {fecha: f.trim()}); pintarCalendario(); } }))))
          : [vacio('Todas tus piezas en curso tienen fecha.')])));
  }

  async function pintarAutomatizaciones() {
    const caja = $('#automatizaciones');
    if (!caja) return;
    const d = await api('/api/seguimientos');
    caja.replaceChildren(el('h2', {text: 'Seguimientos de investigaciones (en tu Mac)'}),
      el('p', {class: 'am', text: 'Se calculan al abrir el Estudio con los datos del Radar que hay en tu Mac. Las ejecuciones de GitHub Actions están debajo.'}),
      ...(d.seguimientos.length ? d.seguimientos.map(s => el('div', {class: 'res-item'}, el('a', {href: '#/investigar/investigaciones/' + s.inv_id, text: s.titulo}),
        el('span', {class: 'am', text: ` · ${s.consultas.join(' · ')} · ${s.n_novedades} novedad(es) · revisado ${new Date(s.revisado_en).toLocaleString('es-ES')}`})))
        : [vacio('No sigues ninguna investigación. Actívalo en su pestaña «Seguimiento».')]));
  }

  // «Crear vídeo de esto» en Temas y tendencias (ideas del día y temas con hueco)
  function decorarTemas() {
    document.querySelectorAll('#oportunidades [data-titulo]').forEach(n => {
      if (n.querySelector('.crear-esto')) return;
      const b = el('button', {type: 'button', class: 'btn crear-esto', text: 'Crear vídeo de esto'});
      b.addEventListener('click', () => Investigar.crearVideoDeEsto({titulo: n.dataset.titulo, url: n.dataset.url || '', origen: 'Temas y tendencias'}));
      n.append(b);
    });
  }

  function alCambiarVista(ruta) {
    if (!window.PC_ESTUDIO) return;
    const fn = {'crear/revision': pintarRevision, 'crear/calendario': pintarCalendario, 'sistema/ejecuciones': pintarAutomatizaciones, 'investigar/temas': decorarTemas}[ruta];
    if (fn) Promise.resolve(fn()).catch(e => console.warn(e));
  }
  function iniciar() {
    window.addEventListener('vista', e => alCambiarVista(e.detail));
    window.addEventListener('estudio-listo', () => alCambiarVista(rutaActual()));
  }
  return {iniciar};
})();

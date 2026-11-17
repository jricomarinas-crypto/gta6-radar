// ===== Mi canal (fase 2B): Estadísticas y registro manual, Lo que más rinde, Mis vídeos, Colaboradores =====
// Privado: solo funciona en el Estudio (data/estudio.db). Fuentes vigiladas (Sistema) es pública: se pinta siempre.
const Canal = (() => {
  const st = {plataforma: '', filtro: null, rinde: {agrupar: 'formato', plataforma: '', dias: '', orden: 'n'}, orden: {k: 'medido_en', asc: false}, colab: 'destacados'};
  const PLAT = {tiktok: 'TikTok', shorts: 'YouTube Shorts', youtube: 'YouTube largo'};
  const COLOR = {tiktok: '#22D3EE', shorts: '#F472B6', youtube: '#FACC15'};
  const n0 = v => v == null ? '—' : fmt(v);
  const cuando = iso => iso ? new Date(iso).toLocaleString('es-ES', {day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'}) : '—';
  const vacio = t => el('div', {class: 'empty', text: t});
  const localAhora = () => { const d = new Date(); d.setSeconds(0, 0); return new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 16); };
  const aLocal = iso => { if (!iso) return ''; const d = new Date(iso); return new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 16); };
  // POST que devuelve también los errores por campo (api() de radar.js solo da el mensaje)
  async function enviar(path, body) {
    const r = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    const data = await r.json().catch(() => ({}));
    return {ok: r.ok, data};
  }
  function accion(texto, fn, clase = '') {
    const b = el('button', {type: 'button', class: 'btn ' + clase, text: texto});
    b.addEventListener('click', async () => { if (b.disabled) return; b.disabled = true; try { await fn(b); } catch (e) { alert(e.message); } finally { b.disabled = false; } });
    return b;
  }
  // campo con su hueco de error justo debajo
  function campo(nombre, etiqueta, input, ayuda) {
    const err = el('span', {class: 'err-campo', id: 'err-' + nombre, 'aria-live': 'polite'});
    input.setAttribute('aria-describedby', 'err-' + nombre);
    return el('label', {class: 'campo-m', 'data-campo': nombre}, etiqueta, input, ayuda ? el('small', {class: 'am', text: ayuda}) : null, err);
  }
  function pintarErrores(form, errores) {
    form.querySelectorAll('.err-campo').forEach(e => { e.textContent = ''; });
    Object.entries(errores || {}).forEach(([k, m]) => { const e = form.querySelector('#err-' + k); if (e) e.textContent = m; });
  }

  // ---------------- Estadísticas
  async function pintarEstadisticas() {
    const caja = $('#estadisticas');
    caja.replaceChildren(el('div', {class: 'card am', role: 'status', text: 'Cargando…'}));
    const [e, vs, ms] = await Promise.all([api('/api/canal/estadisticas'), api('/api/canal/videos'), api('/api/canal/mediciones?plataforma=' + st.plataforma)]);
    caja.replaceChildren(formulario(vs.videos, ms.metricas), periodos(e), grafica(e), desgloses(e.desgloses), tabla(ms.mediciones));
  }
  function periodos(e) {
    if (!e.hay_datos) return el('div', {class: 'card'}, vacio('Aún no hay mediciones. Registra la primera con el formulario: las gráficas y comparaciones salen de ahí.'));
    return el('div', {class: 'card'}, el('h2', {text: 'Comparación de periodos'}),
      el('p', {class: 'am', text: 'Vistas nuevas (diferencias entre mediciones). «Días con datos» = días en los que registraste alguna medición.'}),
      el('div', {class: 'kpis'}, ...e.periodos.map(p => el('div', {class: 'kpi'},
        el('div', {class: 't', text: `Últimos ${p.dias} días frente a los ${p.dias} anteriores`}),
        el('div', {class: 'n', text: n0(p.actual.vistas)}),
        el('div', {class: 'am', text: `antes: ${n0(p.anterior.vistas)} · días con datos ${p.actual.dias_con_datos}/${p.dias} frente a ${p.anterior.dias_con_datos}/${p.dias}`}),
        p.cambio_pct != null ? el('div', {class: p.cambio_pct >= 0 ? 'ok' : 'bad', text: (p.cambio_pct >= 0 ? '+' : '') + p.cambio_pct + ' %'}) : null,
        p.aviso ? el('div', {class: 'aviso', text: p.aviso}) : null))));
  }
  function grafica(e) {
    const caja = el('div', {class: 'card'}, el('h2', {text: 'Vistas nuevas por día y plataforma (90 días)'}));
    if (!e.hay_datos) return caja.appendChild(vacio('Sin datos todavía.')) && caja;
    const fechas = e.diario.map(d => d.fecha);
    const series = Object.keys(PLAT).map(p => ({id: p, nombre: PLAT[p], color: COLOR[p], discontinua: p === 'youtube', valores: e.diario.map(d => d[p])}))
      .filter(s => s.valores.some(v => v != null));
    const det = el('div', {class: 'am', 'aria-live': 'polite'});
    const g = el('div');
    caja.append(el('div', {class: 'leyenda'}, ...series.map(s => el('span', {class: 'am'}, el('i', {style: `display:inline-block;width:10px;height:10px;border-radius:50%;background:${s.color};margin-right:4px`}), s.nombre + '  '))), g, det);
    Grafica.crear(g, {fechas, series, formato: v => fmt(v), etiqueta: 'Vistas nuevas por día', onDia: i => {
      const d = e.diario[i];
      det.textContent = `${d.fecha}: ` + series.map(s => `${s.nombre} ${d[s.id] == null ? 'sin medición' : fmt(d[s.id])}`).join(' · ') + (d.notas.length ? ' — ' + d.notas.join('; ') : ''); }});
    return caja;
  }
  function desgloses(d) {
    const lista = (obj, nombres) => Object.keys(obj).length ? el('ul', {class: 'hist'}, ...Object.entries(obj).sort((a, b) => b[1] - a[1]).map(([k, v]) => el('li', {}, el('b', {text: fmt(v)}), ' · ' + (nombres[k] || k))))
      : vacio('Sin datos.');
    return el('div', {class: 'card'}, el('h2', {text: `Desglose de los últimos ${d.dias} días (vistas nuevas)`}),
      el('div', {class: 'grid2'}, el('div', {}, el('h3', {text: 'Por plataforma'}), lista(d.plataforma, PLAT)), el('div', {}, el('h3', {text: 'Por formato'}), lista(d.formato, {}))));
  }
  function formulario(videos, unidades) {
    const pre = window.PC_MEDIR; window.PC_MEDIR = null;
    const sel = el('select', {name: 'video_id'}, el('option', {value: '', text: 'Elige el vídeo…'}),
      ...videos.map(v => el('option', {value: v.id, text: `${PLAT[v.plataforma]} · ${v.titulo}`})), el('option', {value: 'nuevo', text: '+ Vídeo nuevo (pegar URL)…'}));
    const plat = el('select', {name: 'plataforma'}, ...Object.entries(PLAT).map(([k, t]) => el('option', {value: k, text: t})));
    const url = el('input', {type: 'url', name: 'url', placeholder: 'https://www.tiktok.com/@…/video/…'});
    const tit = el('input', {type: 'text', name: 'titulo', placeholder: 'para reconocerlo'});
    const pub = el('input', {type: 'datetime-local', name: 'publicado_en'});
    const nuevo = el('div', {class: 'inv-form', hidden: true}, campo('plataforma', 'Plataforma', plat), campo('url', 'URL del vídeo', url),
      campo('titulo', 'Título', tit), campo('publicado_en', 'Publicado (fecha y hora)', pub));
    sel.addEventListener('change', () => { nuevo.hidden = sel.value !== 'nuevo'; });
    if (pre) { const v = videos.find(x => x.url === pre.url); if (v) sel.value = v.id; else { sel.value = 'nuevo'; nuevo.hidden = false; plat.value = pre.plataforma === 'shorts' ? 'shorts' : pre.plataforma; url.value = pre.url || ''; } }
    const med = el('input', {type: 'datetime-local', name: 'medido_en', value: localAhora(), required: ''});
    const ETQ = {vistas: 'Visualizaciones', tiempo_medio_s: 'Tiempo medio visto (s)', pct_completo: '% que lo ve entero', compartidos: 'Compartidos',
      seguidores_ganados: 'Seguidores ganados', likes: 'Me gusta', comentarios: 'Comentarios'};
    const metr = Object.keys(ETQ).map(k => [k, el('input', {type: 'text', inputmode: 'decimal', name: k, autocomplete: 'off', placeholder: 'vacío = no lo sé'})]);
    const nota = el('input', {type: 'text', name: 'nota', placeholder: 'opcional'});
    const idEdit = el('input', {type: 'hidden', name: 'id'});
    const titulo = el('h2', {text: 'Registrar métricas'});
    const ok = el('div', {'aria-live': 'polite'});
    const form = el('form', {class: 'medir', novalidate: ''}, idEdit, el('div', {class: 'inv-form'}, campo('video_id', 'Vídeo', sel)), nuevo,
      el('div', {class: 'inv-form'}, campo('medido_en', 'Medido (fecha y hora)', med, 'hora de tu Mac (Madrid)')),
      el('div', {class: 'metricas'}, ...metr.map(([k, i]) => campo(k, ETQ[k], i, unidades[k]))),
      el('div', {class: 'inv-form'}, campo('nota', 'Nota', nota)),
      el('div', {class: 'acciones'}, el('button', {class: 'btn pri', type: 'submit', text: 'Guardar medición'}),
        el('button', {class: 'btn', type: 'button', text: 'Limpiar', onclick: () => { form.reset(); idEdit.value = ''; med.value = localAhora(); titulo.textContent = 'Registrar métricas'; nuevo.hidden = true; pintarErrores(form, {}); }})), ok);
    const mandar = async confirmar => {
      const body = {medido_en: med.value, nota: nota.value, confirmar, id: idEdit.value || null, ...Object.fromEntries(metr.map(([k, i]) => [k, i.value]))};
      if (sel.value === 'nuevo') Object.assign(body, {plataforma: plat.value, url: url.value, titulo: tit.value, publicado_en: pub.value}); else body.video_id = sel.value;
      if (!sel.value) return pintarErrores(form, {video_id: 'Elige el vídeo (o «Vídeo nuevo»).'});
      const r = await enviar('/api/canal/mediciones', body);
      if (r.ok) { ok.replaceChildren(el('span', {class: 'guardado-ok', text: 'Guardada ✓'})); pintarEstadisticas(); return; }
      pintarErrores(form, r.data.errores || {});
      if (r.data.confirmar && confirm(r.data.error + '\n\n¿Guardarla igualmente?')) return mandar(true);
      if (!r.data.errores) alert(r.data.error || 'No se pudo guardar.');
    };
    form.addEventListener('submit', async ev => { ev.preventDefault(); const b = form.querySelector('button[type=submit]'); if (b.disabled) return; b.disabled = true;
      try { await mandar(false); } finally { b.disabled = false; } });
    form.cargar = m => { idEdit.value = m.id; sel.value = m.video_id; nuevo.hidden = true; med.value = aLocal(m.medido_en); nota.value = m.nota || '';
      metr.forEach(([k, i]) => { i.value = m[k] == null ? '' : m[k]; }); titulo.textContent = 'Corregir medición'; form.scrollIntoView({behavior: 'smooth'}); };
    st.form = form;
    return el('div', {class: 'card'}, titulo,
      el('p', {class: 'am', text: 'Copia los números de la app (TikTok Studio, YouTube Studio). Todo es opcional salvo el vídeo y la hora: deja vacío lo que no tengas (vacío no es cero). Los valores son ACUMULADOS desde la publicación: el panel calcula lo nuevo de cada día.'}), form);
  }
  function tabla(ms) {
    const cols = [['medido_en', 'Medido'], ['titulo', 'Vídeo'], ['plataforma', 'Plataforma'], ['vistas', 'Vistas'], ['tiempo_medio_s', 'T. medio (s)'],
      ['pct_completo', '% entero'], ['compartidos', 'Compart.'], ['seguidores_ganados', 'Seguid.'], ['likes', 'Me gusta'], ['comentarios', 'Coment.']];
    const o = st.orden, ord = [...ms].sort((a, b) => { const x = a[o.k], y = b[o.k]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * (o.asc ? 1 : -1); });
    const filtro = el('select', {'aria-label': 'Plataforma'}, el('option', {value: '', text: 'Todas las plataformas'}), ...Object.entries(PLAT).map(([k, t]) => el('option', {value: k, text: t})));
    filtro.value = st.plataforma; filtro.addEventListener('change', () => { st.plataforma = filtro.value; pintarEstadisticas(); });
    return el('div', {class: 'card'}, el('div', {class: 'toolbar'}, el('h2', {text: `Mediciones (${ms.length})`}), el('span', {style: 'flex:1'}), filtro),
      ms.length ? el('div', {class: 'tblwrap'}, el('table', {class: 'tbl'},
        el('tr', {}, ...cols.map(([k, t]) => el('th', {class: ['titulo', 'plataforma', 'medido_en'].includes(k) ? '' : 'num'},
          el('button', {type: 'button', class: 'th-ord', 'aria-sort': o.k === k ? (o.asc ? 'ascending' : 'descending') : null, text: t + (o.k === k ? (o.asc ? ' ▲' : ' ▼') : ''),
            onclick: () => { st.orden = {k, asc: o.k === k ? !o.asc : false}; pintarEstadisticas(); }}))), el('th', {text: ''})),
        ...ord.map(m => el('tr', {}, ...cols.map(([k]) => el('td', {class: ['titulo', 'plataforma', 'medido_en'].includes(k) ? '' : 'num',
          text: k === 'medido_en' ? cuando(m[k]) : k === 'plataforma' ? PLAT[m[k]] : ['titulo'].includes(k) ? m[k] : n0(m[k])})),
          el('td', {}, accion('Corregir', async () => st.form.cargar(m)), accion('Borrar…', async () => {
            if (!confirm(`¿Borrar la medición de «${m.titulo}» del ${cuando(m.medido_en)}? Queda anotado en el registro de cambios.`)) return;
            await api(`/api/canal/mediciones/${m.id}/borrar`, {}); pintarEstadisticas(); }))))))
        : vacio('Sin mediciones.'));
  }

  // ---------------- Lo que más rinde
  async function pintarRinde() {
    const f = st.rinde, caja = $('#rinde');
    const d = await api('/api/canal/rinde?' + new URLSearchParams(f));
    const agr = el('div', {class: 'seg', role: 'group', 'aria-label': 'Agrupar por'}, ...Object.entries(d.agrupaciones).map(([k, t]) => {
      const b = el('button', {type: 'button', 'aria-pressed': f.agrupar === k ? 'true' : 'false', text: t}); b.addEventListener('click', () => { f.agrupar = k; pintarRinde(); }); return b; }));
    const plat = el('select', {'aria-label': 'Plataforma'}, el('option', {value: '', text: 'Todas las plataformas'}), ...Object.entries(d.plataformas).map(([k, t]) => el('option', {value: k, text: t}))); plat.value = f.plataforma;
    const dias = el('select', {'aria-label': 'Periodo'}, ...[['', 'Todo'], ['30', 'Publicados en 30 días'], ['90', 'Publicados en 90 días']].map(([v, t]) => el('option', {value: v, text: t}))); dias.value = f.dias;
    const orden = el('select', {'aria-label': 'Ordenar por'}, ...[['n', 'Nº de vídeos'], ['mediana_48', 'Mediana de vistas a 48 h'], ['mediana_vistas', 'Mediana de vistas actuales'],
      ['vistas_total', 'Vistas totales'], ['seguidores_total', 'Seguidores ganados'], ['compartidos_total', 'Compartidos']].map(([v, t]) => el('option', {value: v, text: t}))); orden.value = f.orden;
    [plat, dias, orden].forEach((s, i) => s.addEventListener('change', () => { f[['plataforma', 'dias', 'orden'][i]] = s.value; pintarRinde(); }));
    const ficha = g => el('article', {class: 'res-item'},
      el('div', {class: 'vt'}, g.clave, ' ', g.pocos_datos ? el('span', {class: 'b s-warn', text: `pocos datos (${g.n} < ${d.min_grupo})`}) : null),
      el('div', {class: 'rinde-m'},
        el('span', {}, el('b', {text: g.n}), ' vídeo(s)'),
        el('span', {}, el('b', {text: n0(g.mediana_48)}), ` mediana a 48 h (${g.n_48} de ${g.n} con dato)`),
        el('span', {}, el('b', {text: n0(g.mediana_vistas)}), ` mediana por vídeo · ${n0(g.vistas_total)} en total (${g.n_vistas} con dato)`),
        el('span', {}, el('b', {text: n0(g.seguidores_total)}), ` seguidores (${g.n_seguidores} con dato)`),
        el('span', {}, el('b', {text: n0(g.compartidos_total)}), ` compartidos (${g.n_compartidos} con dato)`),
        el('span', {}, 'Retención: ', g.retencion.estado === 'ok' ? el('b', {text: g.retencion.valor + ' %'}) : '', ' ' + g.retencion.texto)),
      el('div', {class: 'acciones'}, el('a', {class: 'btn', href: '#/canal/mis-videos', text: 'Ver vídeos', onclick: () => { st.filtro = {campo: f.agrupar, valor: g.clave, ids: g.videos}; }}),
        accion('Crear idea…', async () => { const t = prompt('Título de la idea (se crea en el Estudio, etapa Idea; no se aprueba nada):', `${g.clave}: nueva pieza`); if (!t) return;
          await api('/api/enviar', {a_mano: true, titulo: t, por_que: `Rinde en Mi canal (${d.agrupaciones[f.agrupar]}: ${g.clave}, ${g.n} vídeo(s))`, variante: 'ultima_hora', plataformas: ['tiktok', 'shorts']});
          alert('Idea creada. La tienes en Crear › En producción.'); })));
    caja.replaceChildren(el('div', {class: 'card'}, el('div', {class: 'inv-form'}, agr, plat, dias, orden),
      el('p', {class: 'am', text: 'Para comparar con justicia se usa la mediana de vistas a 48 h (la misma ventana para todos). Los totales dependen de cuánto tiempo lleva publicado cada vídeo. No hay «ganador»: con menos de 5 vídeos, cualquier diferencia puede ser casualidad.' + (d.multi ? ' Un vídeo con varios temas cuenta en cada uno.' : '')}),
      el('p', {class: 'am', text: d.ingresos})),
      el('div', {class: 'card'}, ...(d.grupos.length ? d.grupos.map(ficha) : [vacio('Aún no hay vídeos tuyos. Aparecen al marcar una pieza como subida o al registrar un vídeo en Estadísticas.')])));
  }

  // ---------------- Mis vídeos
  async function pintarMisVideos() {
    const caja = $('#mis-videos');
    const d = await api('/api/canal/videos');
    const f = st.filtro;
    const vids = f ? d.videos.filter(v => f.ids.includes(v.id)) : d.videos;
    const ficha = v => {
      const u = v.ultimos, serie = el('input', {type: 'text', value: v.serie || '', 'aria-label': 'Serie', placeholder: 'serie'});
      const colab = el('input', {type: 'text', value: v.colaboracion || '', 'aria-label': 'Colaboración', placeholder: 'con quién'});
      const temas = el('input', {type: 'text', value: v.temas.join(', '), 'aria-label': 'Temas', placeholder: 'temas, separados por comas'});
      const dur = el('input', {type: 'text', inputmode: 'decimal', value: v.duracion_s ?? '', 'aria-label': 'Duración en segundos', placeholder: 'segundos'});
      const okm = el('span', {class: 'guardado-ok', 'aria-live': 'polite'});
      const val = k => u[k] ? `${n0(u[k].valor)}` : '—';
      return el('article', {class: 'res-item'},
        el('div', {class: 'meta'}, el('span', {class: 'b', text: v.plataforma_nombre}), v.formato ? el('span', {text: `formato ${v.formato}${v.variante ? ' · ' + v.variante : ''}`}) : null,
          el('span', {text: 'publicado ' + cuando(v.publicado_en)}), el('span', {text: `${v.n_mediciones} medición(es) · última ${cuando(v.ultima_medicion)}`}),
          v.pieza_id ? el('span', {class: 'am', text: 'pieza ' + v.pieza_id}) : null),
        el('div', {class: 'vt'}, safeUrl(v.url) ? el('a', {href: safeUrl(v.url), target: '_blank', rel: 'noopener', text: v.titulo}) : v.titulo),
        el('div', {class: 'rinde-m'}, el('span', {}, el('b', {text: val('vistas')}), ' vistas'), el('span', {}, el('b', {text: val('seguidores_ganados')}), ' seguidores'),
          el('span', {}, el('b', {text: val('compartidos')}), ' compartidos'),
          el('span', {}, 'retención: ', el('b', {text: u.pct_completo ? n0(u.pct_completo.valor) + ' % entero' : '—'}), u.tiempo_medio_s ? ` · ${u.tiempo_medio_s.valor} s de media` : '')),
        el('div', {class: 'am'}, el('b', {text: '48 h: '}), v.v48.estado === 'ok' ? `${n0(v.v48.vistas)} vistas (${v.v48.texto})` : v.v48.texto,
          ' · ', el('b', {text: 'Índice: '}), v.indice48.estado === 'ok' ? el('span', {text: v.indice48.texto}) : v.indice48.texto),
        el('details', {}, el('summary', {text: 'Editar serie, colaboración, temas y duración'}),
          el('div', {class: 'inv-form'}, el('label', {}, 'Serie', serie), el('label', {}, 'Colaboración', colab), el('label', {class: 'ancho'}, 'Temas', temas), el('label', {}, 'Duración (s)', dur)),
          el('div', {class: 'acciones'}, accion('Guardar', async () => { await api('/api/canal/videos/' + v.id, {serie: serie.value, colaboracion: colab.value, temas: temas.value, duracion_s: dur.value}); okm.textContent = 'Guardado ✓'; }, 'pri'),
            el('a', {class: 'btn', href: '#/canal/estadisticas', text: 'Registrar métricas', onclick: () => { window.PC_MEDIR = {plataforma: v.plataforma, url: v.url}; }}), okm)));
    };
    caja.replaceChildren(el('div', {class: 'card'},
      el('p', {class: 'am', text: `Vistas a 48 h = la medición más cercana a 48 h, solo si está entre las ${d.ventana[0]} y las ${d.ventana[1]} h (no se interpola). Índice a 48 h = tus vistas a 48 h ÷ la mediana de tus ${d.historial} piezas anteriores de la misma plataforma; con menos de ${d.historial}, «historial insuficiente». Este índice NO es comparable con las vistas/hora de los vídeos del Radar: para esos, ve a `},
        el('a', {href: '#/investigar/videos', text: 'Investigar › Vídeos'}), '.'),
      f ? el('div', {class: 'chips'}, el('span', {class: 'chip'}, `${f.campo}: ${f.valor}`, el('button', {type: 'button', 'aria-label': 'Quitar filtro', text: '✕', onclick: () => { st.filtro = null; pintarMisVideos(); }}))) : null),
      el('div', {class: 'card'}, ...(vids.length ? vids.map(ficha) : [vacio('Aún no hay vídeos tuyos. Aparecen solos al marcar una pieza como subida (En producción) o al registrar uno nuevo en Estadísticas.')])));
  }

  // ---------------- Colaboradores
  async function pintarColaboradores() {
    const caja = $('#colaboradores');
    const d = await api('/api/colaboradores');
    const vistas = [['destacados', 'Destacados'], ['emergentes', 'Emergentes'], ['posibles', 'Posibles colaboradores'], ['guardados', `Guardados (${d.guardados.length})`]];
    const seg = el('div', {class: 'seg', role: 'group', 'aria-label': 'Vista'}, ...vistas.map(([k, t]) => {
      const b = el('button', {type: 'button', 'aria-pressed': st.colab === k ? 'true' : 'false', text: t}); b.addEventListener('click', () => { st.colab = k; pintarColaboradores(); }); return b; }));
    const delRadar = c => { const g = d.por_creador[c.id];
      return el('article', {class: 'res-item'},
        el('div', {class: 'vt'}, safeUrl(c.url) ? el('a', {href: c.url, target: '_blank', rel: 'noopener', text: c.name}) : c.name),
        el('div', {class: 'meta'}, el('span', {text: 'YouTube'}), el('span', {text: `${n0(c.subscribers)} suscriptores`}), el('span', {text: `${c.n_videos} vídeo(s) de GTA 6 · ${n0(c.views)} vistas`}),
          c.language ? el('span', {text: c.language.toUpperCase()}) : null, ...c.temas.map(t => el('span', {class: 'b', text: TOPIC[t] || t})), el('span', {class: 'am', text: 'medido ' + cuando(c.medido_en)})),
        c.mejores.length ? el('div', {class: 'am'}, 'Mejores: ', ...c.mejores.flatMap((m, i) => [i ? ' · ' : '', safeUrl(m.url) ? el('a', {href: m.url, target: '_blank', rel: 'noopener', text: m.title}) : m.title])) : null,
        el('div', {class: 'acciones'}, g ? el('span', {class: 'b s-info', text: 'guardado · ' + d.estados[g.estado]})
          : accion('Guardar como colaborador', async () => { await api('/api/colaboradores', {creador_radar: c.id}); pintarColaboradores(); }, 'pri'))); };
    const guardado = c => { const est = el('select', {'aria-label': 'Estado'}, ...Object.entries(d.estados).map(([k, t]) => el('option', {value: k, text: t}))); est.value = c.estado;
      const nota = el('textarea', {class: 'campo', 'aria-label': 'Nota'}); nota.value = c.nota || '';
      const okm = el('span', {class: 'guardado-ok', 'aria-live': 'polite'});
      return el('article', {class: 'res-item'}, el('div', {class: 'vt'}, safeUrl(c.url) ? el('a', {href: c.url, target: '_blank', rel: 'noopener', text: c.nombre}) : c.nombre),
        el('div', {class: 'meta'}, el('span', {text: c.plataforma || '—'}), c.idioma ? el('span', {text: c.idioma.toUpperCase()}) : null, ...c.temas.map(t => el('span', {class: 'b', text: TOPIC[t] || t})),
          el('span', {class: 'am', text: 'actualizado ' + cuando(c.actualizado_en)})),
        el('div', {class: 'inv-form'}, el('label', {}, 'Estado', est), el('label', {class: 'ancho'}, 'Nota (privada)', nota)),
        el('div', {class: 'acciones'}, accion('Guardar', async () => { await api('/api/colaboradores/' + c.id, {estado: est.value, nota: nota.value}); okm.textContent = 'Guardado ✓'; }, 'pri'),
          accion('Quitar…', async () => { if (!confirm(`¿Quitar a ${c.nombre} de tus colaboradores?`)) return; await api(`/api/colaboradores/${c.id}/borrar`, {}); pintarColaboradores(); }), okm)); };
    const manual = el('form', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Añadir a mano', el('input', {type: 'text', name: 'nombre', placeholder: 'nombre del creador', required: ''})),
      el('label', {class: 'ancho'}, 'Enlace', el('input', {type: 'url', name: 'url', placeholder: 'https://…'})), el('button', {class: 'btn', type: 'submit', text: 'Guardar'}));
    manual.addEventListener('submit', async e => { e.preventDefault(); const fd = new FormData(manual);
      try { await api('/api/colaboradores', {nombre: fd.get('nombre'), url: fd.get('url')}); st.colab = 'guardados'; pintarColaboradores(); } catch (err) { alert(err.message); } });
    let cuerpo;
    if (st.colab === 'destacados' || st.colab === 'emergentes') {
      const l = d[st.colab];
      cuerpo = [el('p', {class: 'am', text: 'Criterio: ' + d.criterios[st.colab] + (d.demo ? ' · Datos del Radar de DEMOSTRACIÓN.' : '')}),
        ...(l.length ? l.map(delRadar) : [vacio('Ningún creador cumple el criterio con los datos actuales del Radar.')])];
    } else {
      const l = st.colab === 'posibles' ? d.guardados.filter(c => ['por_revisar', 'interesante'].includes(c.estado)) : d.guardados;
      cuerpo = [st.colab === 'guardados' ? manual : el('p', {class: 'am', text: 'Los que tienes en «Por revisar» o «Interesante».'}),
        ...(l.length ? l.map(guardado) : [vacio('Nada todavía. Guarda creadores desde Destacados, Emergentes o Investigar › Creadores.')])];
    }
    caja.replaceChildren(el('div', {class: 'card'}, seg, el('p', {class: 'am', text: 'Guardar o cambiar el estado NO envía ningún mensaje: es tu lista privada. No se muestran contactos ni puntuaciones inventadas.'})),
      el('div', {class: 'card'}, ...cuerpo));
  }
  // «Guardar como colaborador» en la tabla de Investigar › Creadores (solo en el Estudio)
  async function decorarCreadores() {
    const filas = [...document.querySelectorAll('#creators tr[data-id]')];
    if (!filas.length || document.querySelector('#creators th.th-colab')) return;
    let g = {}; try { g = (await api('/api/colaboradores')).por_creador; } catch { return; }
    document.querySelector('#creators tr').append(el('th', {class: 'th-colab', text: 'Colaborador'}));
    filas.forEach(tr => tr.append(el('td', {}, tr.dataset.oficial ? '—' : g[tr.dataset.id] ? el('span', {class: 'b s-info', text: 'guardado'})
      : accion('Guardar', async b => { await api('/api/colaboradores', {creador_radar: tr.dataset.id}); b.replaceWith(el('span', {class: 'b s-info', text: 'guardado'})); }))));
  }

  // ---------------- Fuentes vigiladas (público)
  function pintarFuentes() {
    const f = DATA.fuentes;
    if (!f) { $('#fuentes').replaceChildren(vacio('Sin información de fuentes en este panel.')); return; }
    const c = x => x ? `${fmt(x.h24)} en 24 h · ${fmt(x.d7)} en 7 días` : null;
    $('#fuentes').replaceChildren(
      el('p', {class: 'am', text: 'Lo que vigila el Radar según config.yaml. Para añadir o quitar fuentes, edita config.yaml (o pídemelo en el chat): el panel no cambia la configuración. Los números cuentan lo que el Radar vio por primera vez.'}),
      el('h3', {text: `Medios (RSS) · noticias: ${c(f.noticias_total)}`}),
      el('div', {class: 'tblwrap'}, el('table', {class: 'tbl'}, el('tr', {}, el('th', {text: 'Medio'}), el('th', {text: 'Idioma'}), el('th', {text: 'Traído'})),
        ...f.rss.map(r => el('tr', {}, el('td', {text: r.nombre}), el('td', {text: (r.idioma || '—').toUpperCase()}),
          el('td', {text: r.google_news ? 'no atribuible: Google News guarda el medio original como fuente' : c(r.cuenta)}))))),
      el('h3', {text: `YouTube · vídeos: ${c(f.videos_total)}`}),
      el('ul', {class: 'hist'}, ...f.youtube_vias.map(v => el('li', {}, el('b', {text: v.via}), ': ' + c(v.cuenta)))),
      el('p', {class: 'am', text: `Búsquedas (${f.busquedas_por_ejecucion} por ejecución, rotando): ${f.palabras_clave.join(' · ')}`}),
      el('p', {class: 'am', text: `Tendencias de Gaming en: ${f.regiones_tendencias.join(', ') || '—'} · Canales oficiales: ${f.canales_oficiales.join(', ') || '—'} · Prioritarios: ${f.creadores_prioritarios.join(', ') || 'ninguno'}`}),
      el('p', {class: 'am', text: `Vigilancia por RSS de canales: ${f.vigilancia.activar ? 'activa' : 'desactivada'} · ${f.vigilancia.vigilados} canal(es) vigilado(s) ahora (máximo ${f.vigilancia.max_canales}; entran con ≥ ${f.vigilancia.min_videos_14d} vídeos de GTA 6 en 14 días).`}));
  }

  function alCambiarVista(ruta) {
    if (ruta === 'sistema/fuentes') return pintarFuentes();
    if (!window.PC_ESTUDIO) return;
    const fn = {'canal/estadisticas': pintarEstadisticas, 'canal/rinde': pintarRinde, 'canal/mis-videos': pintarMisVideos,
      'canal/colaboradores': pintarColaboradores, 'investigar/creadores': decorarCreadores}[ruta];
    if (fn) Promise.resolve(fn()).catch(e => { console.warn(e); const id = {'canal/estadisticas': 'estadisticas', 'canal/rinde': 'rinde', 'canal/mis-videos': 'mis-videos', 'canal/colaboradores': 'colaboradores'}[ruta];
      if (id) $('#' + id).replaceChildren(el('div', {class: 'card bad', text: 'No se pudo cargar: ' + e.message})); });
  }
  function iniciar() {
    window.addEventListener('vista', e => alCambiarVista(e.detail));
    window.addEventListener('estudio-listo', () => alCambiarVista(rutaActual()));
  }
  return {iniciar};
})();

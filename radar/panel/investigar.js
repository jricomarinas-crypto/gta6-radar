// ===== Investigar (fase 1B): Buscador, Noticias, Vídeos con acciones, Biblioteca, Mis investigaciones, Continuar =====
// Solo funciona en el Estudio (todo es privado y se guarda en data/estudio.db). En la web pública, cada sección
// muestra el aviso «funciona en el Estudio de tu Mac» y no hay controles que aparenten guardar.
const Investigar = (() => {
  const st = {invs: [], busq: {q: '', tipos: [], dias: '', fuente: '', idioma: '', tema: '', verificacion: ''},
    noticias: {vista: 'ultimas', fuente: '', tema: ''}, bib: {q: '', tipo: '', etiqueta: '', archivadas: false}, pestana: 'resumen'};
  const TIPO_REF = {noticia: 'Noticia', video: 'Vídeo', creador: 'Creador', enlace: 'Enlace'};
  const ESTADO_INV = {abierta: 'Abierta', recopilando: 'Recopilando fuentes', contrastando: 'Contrastando',
    lista: 'Lista para convertir en contenido', archivada: 'Archivada'};
  const TIPO_NOTA = {apunte: 'Apunte', pregunta: 'Pregunta pendiente', idea: 'Idea', enfoque: 'Posible enfoque'};
  const fecha = iso => iso ? new Date(iso).toLocaleString('es-ES', {day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'}) : 'fecha desconocida';
  const vacio = t => el('div', {class: 'empty', text: t});
  const enlace = (url, texto) => safeUrl(url) ? el('a', {href: safeUrl(url), target: '_blank', rel: 'noopener', text: texto}) : texto;

  // botón que se desactiva mientras trabaja (evita duplicados por doble clic) y muestra el error si falla
  function accion(texto, fn, clase = '') {
    const b = el('button', {type: 'button', class: 'btn ' + clase, text: texto});
    b.addEventListener('click', async () => { if (b.disabled) return; b.disabled = true;
      try { await fn(b); } catch (e) { alert(e.message); } finally { b.disabled = false; } });
    return b;
  }
  // extracto con las coincidencias marcadas (marcas \u0001…\u0002 del buscador), sin insertar HTML
  function resaltado(txt) {
    const out = []; let resto = String(txt || '');
    while (resto) { const a = resto.indexOf('\u0001'); if (a < 0) { out.push(resto); break; }
      const b = resto.indexOf('\u0002', a); out.push(resto.slice(0, a)); out.push(el('mark', {text: resto.slice(a + 1, b < 0 ? undefined : b)}));
      resto = b < 0 ? '' : resto.slice(b + 1); }
    return out;
  }
  async function cargarInvs() { st.invs = (await api('/api/investigaciones')).investigaciones; return st.invs; }

  // ---------- acciones sobre un elemento (noticia, vídeo, creador)
  function accionesRef(tipo, origen, url, estado = {}, conLeida = false) {
    const caja = el('div', {class: 'acciones'});
    const pintar = e => {
      const btnG = accion(e.guardada ? '★ Guardada' : '☆ Guardar', async () => {
        const r = await api('/api/referencias', {tipo, origen, guardada: !e.guardada}); pintar({...e, ...r, guardada: !!r.guardada}); });
      const btnL = conLeida ? accion(e.leida ? '✓ Leída' : 'Marcar leída', async () => {
        const r = await api('/api/referencias', {tipo, origen, leida: !e.leida}); pintar({...e, ...r, leida: !!r.leida}); }) : null;
      const btnN = accion(e.nota ? '✎ Nota' : 'Añadir nota', async () => {
        const n = prompt('Tu nota sobre este elemento (privada):', e.nota || ''); if (n === null) return;
        const r = await api('/api/referencias', {tipo, origen, nota: n}); pintar({...e, ...r, nota: r.nota || ''}); });
      const sel = el('select', {'aria-label': 'Añadir a una investigación'}, el('option', {value: '', text: 'Añadir a investigación…'}),
        ...st.invs.map(i => el('option', {value: i.id, text: i.titulo})), el('option', {value: '__nueva', text: '+ Nueva investigación…'}));
      sel.addEventListener('change', async () => {
        let iid = sel.value; if (!iid) return; sel.disabled = true;
        try {
          if (iid === '__nueva') { const t = prompt('Título de la nueva investigación:'); if (!t) { sel.value = ''; return; }
            iid = (await api('/api/investigaciones', {titulo: t})).id; await cargarInvs(); }
          const aporte = prompt('¿Qué aporta esta fuente a la investigación? (opcional)') || '';
          await api(`/api/investigaciones/${iid}/fuentes`, {tipo, origen, aporte});
          pintar({...e, en_investigaciones: (e.en_investigaciones || 0) + 1, guardada: e.guardada});
        } catch (err) { alert(err.message); } finally { sel.disabled = false; }
      });
      caja.replaceChildren(...[url && safeUrl(url) ? el('a', {class: 'btn', href: safeUrl(url), target: '_blank', rel: 'noopener', text: 'Abrir original ↗'}) : null,
        btnG, btnL, btnN, sel, e.en_investigaciones ? el('span', {class: 'marca', text: `en ${e.en_investigaciones} investigación(es)`}) : null].filter(Boolean));
      if (e.nota) caja.append(el('div', {class: 'am', style: 'flex-basis:100%', text: 'Tu nota: ' + e.nota}));
    };
    pintar(estado);
    return caja;
  }

  // ---------- Buscador
  function pintarBuscador() {
    const b = st.busq;
    const inp = el('input', {type: 'search', class: 'ancho', value: b.q, placeholder: 'tema, medio, creador, palabra…', 'aria-label': 'Buscar'});
    const tipos = Object.entries({noticia: 'Noticias', video: 'Vídeos', creador: 'Creadores', briefing: 'Briefings', referencia: 'Guardados', nota: 'Mis notas', investigacion: 'Investigaciones', afirmacion: 'Afirmaciones', dossier: 'Dossiers'})
      .map(([k, t]) => { const c = el('input', {type: 'checkbox', value: k}); c.checked = !b.tipos.length || b.tipos.includes(k); return [c, el('label', {class: 'chk'}, c, t)]; });
    const dias = el('select', {'aria-label': 'Periodo'}, ...[['', 'Cualquier fecha'], ['1', 'Último día'], ['7', 'Últimos 7 días'], ['30', 'Últimos 30 días']]
      .map(([v, t]) => el('option', {value: v, text: t}))); dias.value = b.dias;
    const fuente = el('select', {'aria-label': 'Fuente', id: 'bq-fuente'}, el('option', {value: '', text: 'Cualquier fuente'}));
    const idioma = el('select', {'aria-label': 'Idioma'}, ...[['', 'Cualquier idioma'], ['es', 'Español'], ['en', 'Inglés']].map(([v, t]) => el('option', {value: v, text: t}))); idioma.value = b.idioma;
    const tema = el('select', {'aria-label': 'Tema', id: 'bq-tema'}, el('option', {value: '', text: 'Cualquier tema'}));
    const verif = el('select', {'aria-label': 'Verificación'}, ...[['', 'Cualquier verificación'], ['official', 'Oficial'], ['reported', 'Reportado'], ['unverified', 'Sin verificar'], ['opinion', 'Opinión']]
      .map(([v, t]) => el('option', {value: v, text: t}))); verif.value = b.verificacion;
    const res = el('div', {id: 'bq-res', 'aria-live': 'polite'});
    const form = el('form', {class: 'inv-form', role: 'search'},
      el('label', {class: 'ancho'}, 'Buscar en lo ya recopilado', inp), el('button', {class: 'btn pri', type: 'submit', text: 'Buscar'}));
    const lanzar = async () => {
      b.q = inp.value.trim(); b.tipos = tipos.filter(([c]) => c.checked).map(([c]) => c.value);
      if (b.tipos.length === tipos.length) b.tipos = [];
      Object.assign(b, {dias: dias.value, fuente: fuente.value, idioma: idioma.value, tema: tema.value, verificacion: verif.value});
      await buscar(res, {fuente, tema});
    };
    form.addEventListener('submit', e => { e.preventDefault(); lanzar(); });
    const ext = q => [el('span', {class: 'am', text: 'Buscar fuera (abre otra pestaña, no se guarda nada aquí):'}),
      el('a', {class: 'btn', target: '_blank', rel: 'noopener', href: 'https://www.google.com/search?q=' + encodeURIComponent(q || 'GTA 6'), text: 'Google ↗'}),
      el('a', {class: 'btn', target: '_blank', rel: 'noopener', href: 'https://www.youtube.com/results?search_query=' + encodeURIComponent(q || 'GTA 6'), text: 'YouTube ↗'})];
    const externa = el('div', {class: 'chips'}, ...ext(b.q));
    inp.addEventListener('input', () => externa.replaceChildren(...ext(inp.value)));
    $('#buscador').replaceChildren(el('div', {class: 'card'}, form,
      el('div', {class: 'chips'}, ...tipos.map(([, l]) => l)),
      el('div', {class: 'inv-form'}, dias, fuente, idioma, tema, verif),
      el('p', {class: 'am', text: 'Busca en las noticias, vídeos, creadores y briefings que ya ha recopilado el Radar y en tu trabajo guardado. No consulta internet en tiempo real.'}),
      externa), el('div', {class: 'card'}, res));
    if (b.q) buscar(res, {fuente, tema}); else res.replaceChildren(vacio('Escribe algo y pulsa Buscar.'));
  }
  async function buscar(res, selects) {
    const b = st.busq;
    if (!b.q) { res.replaceChildren(vacio('Escribe algo y pulsa Buscar.')); return; }
    res.replaceChildren(el('div', {class: 'am', role: 'status', text: 'Buscando…'}));
    const p = new URLSearchParams({q: b.q, tipos: b.tipos.join(','), dias: b.dias, fuente: b.fuente, idioma: b.idioma, tema: b.tema, verificacion: b.verificacion});
    let d; try { d = await api('/api/buscar?' + p); } catch (e) { res.replaceChildren(el('div', {class: 'bad', text: 'No se pudo buscar: ' + e.message})); return; }
    if (selects.fuente.options.length === 1) d.fuentes.forEach(f => selects.fuente.append(el('option', {value: f, text: f})));
    if (selects.tema.options.length === 1) Object.entries(d.temas).forEach(([k, t]) => selects.tema.append(el('option', {value: k, text: t})));
    selects.fuente.value = b.fuente; selects.tema.value = b.tema;
    const chips = [['dias', b.dias && `Últimos ${b.dias} días`], ['fuente', b.fuente], ['idioma', b.idioma && b.idioma.toUpperCase()],
      ['tema', b.tema && (d.temas[b.tema] || b.tema)], ['verificacion', b.verificacion], ['tipos', b.tipos.length && b.tipos.map(t => d.tipos[t]).join(', ')]].filter(([, v]) => v);
    const quitar = k => { b[k] = k === 'tipos' ? [] : ''; pintarBuscador(); };
    const est = await api('/api/estados', {claves: d.resultados.filter(r => ['noticia', 'video', 'creador'].includes(r.tipo)).map(r => `${r.tipo}:${r.clave}`)});
    res.replaceChildren(...[
      el('div', {class: 'toolbar'}, el('span', {text: `${d.total} resultado(s)` + (d.total > d.resultados.length ? ` · mostrando ${d.resultados.length}` : '') + (d.demo ? ' · datos del Radar de DEMOSTRACIÓN' : '')})),
      chips.length ? el('div', {class: 'chips'}, ...chips.map(([k, v]) => el('span', {class: 'chip'}, v, el('button', {type: 'button', 'aria-label': 'Quitar filtro ' + v, text: '✕', onclick: () => quitar(k)}))),
        el('button', {type: 'button', class: 'btn', text: 'Limpiar filtros', onclick: () => { Object.assign(b, {tipos: [], dias: '', fuente: '', idioma: '', tema: '', verificacion: ''}); pintarBuscador(); }})) : null,
      ...(d.resultados.length ? d.resultados.map(r => el('article', {class: 'res-item'},
        el('div', {class: 'meta'}, el('span', {class: 'b', text: r.tipo_nombre}), r.privado ? el('span', {class: 'b s-info', text: 'privado'}) : null,
          r.demo ? el('span', {class: 'b s-warn', text: 'demo'}) : null, el('span', {text: r.fuente || '—'}),
          el('span', {text: r.fecha ? 'publicado ' + fecha(r.fecha) : 'fecha de publicación desconocida'}),
          r.detectado ? el('span', {text: 'detectado ' + fecha(r.detectado)}) : null,
          r.verificacion && VER[r.verificacion] ? el('span', {class: 'b ' + VER[r.verificacion][0], text: VER[r.verificacion][1]}) : null),
        el('div', {class: 'vt'}, ['investigacion', 'dossier'].includes(r.tipo) ? el('a', {href: '#/investigar/investigaciones/' + r.clave}, ...resaltado(r.titulo_marcado))
          : r.tipo === 'afirmacion' ? el('a', {href: '#/investigar/rumores'}, ...resaltado(r.titulo_marcado))
          : safeUrl(r.url) ? el('a', {href: safeUrl(r.url), target: '_blank', rel: 'noopener'}, ...resaltado(r.titulo_marcado)) : resaltado(r.titulo_marcado)),
        el('div', {class: 'sum ext'}, ...resaltado(r.extracto)),
        ['noticia', 'video', 'creador'].includes(r.tipo) ? accionesRef(r.tipo, r.clave, r.url, est.estados[`${r.tipo}:${r.clave}`] || {}, r.tipo === 'noticia') : null))
        : [vacio('Sin coincidencias en lo recopilado. Prueba otras palabras, quita filtros o busca fuera con los botones de arriba.')])].filter(Boolean));
  }

  // ---------- Noticias y fuentes
  async function pintarNoticias() {
    const n = st.noticias, caja = $('#noticias-estudio');
    caja.replaceChildren(el('div', {class: 'card'}, el('div', {class: 'am', role: 'status', text: 'Cargando…'})));
    let d; try { d = await api('/api/noticias?' + new URLSearchParams(n)); } catch (e) { caja.replaceChildren(el('div', {class: 'card bad', text: e.message})); return; }
    const vistas = el('div', {class: 'seg', role: 'group', 'aria-label': 'Vista'}, ...[['ultimas', 'Últimas'], ['sin_leer', 'Sin leer'], ['guardadas', 'Guardadas']].map(([k, t]) => {
      const b = el('button', {type: 'button', 'aria-pressed': n.vista === k ? 'true' : 'false', text: t}); b.addEventListener('click', () => { n.vista = k; pintarNoticias(); }); return b; }));
    const fuente = el('select', {'aria-label': 'Fuente'}, el('option', {value: '', text: 'Todas las fuentes'}), ...d.fuentes.map(f => el('option', {value: f, text: f}))); fuente.value = n.fuente;
    const tema = el('select', {'aria-label': 'Tema'}, el('option', {value: '', text: 'Todos los temas'}), ...Object.entries(d.temas).map(([k, t]) => el('option', {value: k, text: t}))); tema.value = n.tema;
    fuente.addEventListener('change', () => { n.fuente = fuente.value; pintarNoticias(); });
    tema.addEventListener('change', () => { n.tema = tema.value; pintarNoticias(); });
    caja.replaceChildren(el('div', {class: 'card'},
      el('div', {class: 'inv-form'}, vistas, fuente, tema, el('span', {class: 'am', text: `${d.total} noticia(s)` + (d.demo ? ' · DEMOSTRACIÓN' : '')})),
      el('p', {class: 'am', text: 'Del medio solo tenemos titular y extracto: abre el original para leer el artículo completo. La agrupación de coberturas de una misma noticia llega en la fase 2.'}),
      ...(d.noticias.length ? d.noticias.map(x => el('article', {class: 'res-item'},
        el('div', {class: 'meta'}, el('span', {text: x.fuente || '—'}), el('span', {text: 'publicado ' + fecha(x.publicado_en)}),
          x.detectado_en ? el('span', {text: 'detectado ' + fecha(x.detectado_en)}) : null,
          x.oficial ? el('span', {class: 'b s-info', text: 'Oficial'}) : null,
          x.verificacion && VER[x.verificacion] ? el('span', {class: 'b ' + VER[x.verificacion][0], text: VER[x.verificacion][1]}) : null,
          ...(x.temas || []).map(t => el('span', {class: 'b', text: TOPIC[t] || t}))),
        el('div', {class: 'vt', style: x.estado.leida ? 'opacity:.7' : ''}, enlace(x.url, x.titulo)),
        x.resumen ? el('div', {class: 'sum'}, el('span', {class: 'marca', text: x.resumen_es_ia ? 'Resumen (generado) · ' : 'Extracto del medio · '}), x.resumen) : null,
        accionesRef('noticia', x.id, x.url, x.estado, true)))
        : [vacio(n.vista === 'sin_leer' ? 'No te queda nada sin leer con estos filtros.' : n.vista === 'guardadas' ? 'Aún no has guardado ninguna noticia.' : 'Sin noticias con estos filtros.')])));
  }

  // ---------- Vídeos: acciones en cada vídeo del explorador (solo en el Estudio)
  async function decorarVideos() {
    if (!window.PC_ESTUDIO) return;
    const arts = [...document.querySelectorAll('#videos article.vid[data-id]')];
    if (!arts.length) return;
    let est = {}; try { est = (await api('/api/estados', {claves: arts.map(a => 'video:' + a.dataset.id)})).estados; } catch { return; }
    arts.forEach(a => { if (a.querySelector('.acciones')) return;
      a.children[1].append(accionesRef('video', a.dataset.id, a.dataset.url, est['video:' + a.dataset.id] || {})); });
  }

  // ---------- Biblioteca
  async function pintarBiblioteca() {
    const b = st.bib, caja = $('#biblioteca');
    const p = new URLSearchParams({q: b.q, tipo: b.tipo, etiqueta: b.etiqueta, archivadas: b.archivadas ? '1' : ''});
    let d; try { d = await api('/api/biblioteca?' + p); } catch (e) { caja.replaceChildren(el('div', {class: 'card bad', text: e.message})); return; }
    const q = el('input', {type: 'search', value: b.q, placeholder: 'título, nota, fuente…', 'aria-label': 'Buscar en la biblioteca'});
    const tipo = el('select', {'aria-label': 'Tipo'}, el('option', {value: '', text: 'Todos los tipos'}), ...Object.entries(TIPO_REF).map(([k, t]) => el('option', {value: k, text: t}))); tipo.value = b.tipo;
    const et = el('input', {type: 'text', value: b.etiqueta, placeholder: 'etiqueta', 'aria-label': 'Etiqueta'});
    const arch = el('input', {type: 'checkbox'}); arch.checked = b.archivadas;
    const form = el('form', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Buscar', q), el('label', {}, 'Tipo', tipo), el('label', {}, 'Etiqueta', et),
      el('label', {class: 'chk'}, arch, 'Ver archivadas'), el('button', {class: 'btn pri', type: 'submit', text: 'Filtrar'}));
    form.addEventListener('submit', e => { e.preventDefault(); Object.assign(b, {q: q.value.trim(), tipo: tipo.value, etiqueta: et.value.trim(), archivadas: arch.checked}); pintarBiblioteca(); });
    const manual = el('form', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Guardar un enlace manual', el('input', {type: 'url', name: 'url', placeholder: 'https://…', required: ''})),
      el('label', {class: 'ancho'}, 'Título', el('input', {type: 'text', name: 'titulo', placeholder: 'de qué trata'})), el('button', {class: 'btn', type: 'submit', text: 'Guardar enlace'}));
    manual.addEventListener('submit', async e => { e.preventDefault(); const f = new FormData(manual);
      try { await api('/api/referencias', {tipo: 'enlace', url: f.get('url'), titulo: f.get('titulo'), guardada: true}); manual.reset(); pintarBiblioteca(); } catch (err) { alert(err.message); } });
    caja.replaceChildren(el('div', {class: 'card'}, form, manual), el('div', {class: 'card'},
      el('div', {class: 'toolbar'}, el('span', {text: `${d.referencias.length} referencia(s)`})),
      ...(d.referencias.length ? d.referencias.map(fichaRef) : [vacio(b.q || b.tipo || b.etiqueta ? 'Nada con estos filtros.' : 'Tu biblioteca está vacía. Guarda noticias, vídeos o enlaces con ☆ Guardar.')])));
  }
  function fichaRef(r) {
    const nota = el('textarea', {class: 'campo', 'aria-label': 'Nota', placeholder: 'Tu nota (privada)'}); nota.value = r.nota || '';
    const etiq = el('input', {type: 'text', value: r.etiquetas.join(', '), placeholder: 'etiquetas separadas por comas', 'aria-label': 'Etiquetas'});
    const ok = el('span', {class: 'guardado-ok', 'aria-live': 'polite'});
    return el('article', {class: 'res-item'},
      el('div', {class: 'meta'}, el('span', {class: 'b', text: TIPO_REF[r.tipo] || r.tipo}), el('span', {text: r.fuente || '—'}),
        el('span', {text: r.publicado_en ? 'publicado ' + fecha(r.publicado_en) : 'fecha de publicación desconocida'}), el('span', {text: 'guardado ' + fecha(r.creada_en)}),
        r.archivada ? el('span', {class: 'b', text: 'archivada'}) : null),
      el('div', {class: 'vt'}, enlace(r.url, r.titulo)),
      r.extracto ? el('div', {class: 'sum', text: r.extracto.slice(0, 280)}) : null,
      r.investigaciones.length ? el('div', {class: 'am'}, 'En: ', ...r.investigaciones.flatMap((i, k) => [k ? ', ' : '', el('a', {href: '#/investigar/investigaciones/' + i.id, text: i.titulo})])) : null,
      el('div', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Nota', nota), el('label', {class: 'ancho'}, 'Etiquetas', etiq)),
      el('div', {class: 'acciones'},
        accion('Guardar cambios', async () => { await api(`/api/referencias/${r.id}`, {nota: nota.value, etiquetas: etiq.value}); ok.textContent = 'Guardado ✓'; }, 'pri'),
        accion(r.archivada ? 'Desarchivar' : 'Archivar', async () => { await api(`/api/referencias/${r.id}`, {archivada: !r.archivada}); pintarBiblioteca(); }),
        accion('Eliminar…', async () => {
          if (!confirm(`¿Eliminar «${r.titulo}» de tu biblioteca?` + (r.investigaciones.length ? ` También se quitará de ${r.investigaciones.length} investigación(es).` : '') + ' No se puede deshacer.')) return;
          await api(`/api/referencias/${r.id}/eliminar`, {}); pintarBiblioteca(); }), ok));
  }

  // ---------- Mis investigaciones
  async function pintarInvestigaciones() {
    const caja = $('#investigaciones');
    if (window.PC_SUB) return pintarDetalle(window.PC_SUB);
    await cargarInvs();
    const todas = (await api('/api/investigaciones?todas=1')).investigaciones;
    const form = el('form', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Título', el('input', {type: 'text', name: 'titulo', required: '', minlength: '3', placeholder: 'p. ej. ¿Saldrá en PC en 2027?'})),
      el('label', {class: 'ancho'}, 'Pregunta que quieres resolver', el('input', {type: 'text', name: 'pregunta', placeholder: 'opcional'})),
      el('button', {class: 'btn pri', type: 'submit', text: 'Crear investigación'}));
    form.addEventListener('submit', async e => { e.preventDefault(); const btn = form.querySelector('button'); if (btn.disabled) return; btn.disabled = true;
      try { const f = new FormData(form); const i = await api('/api/investigaciones', {titulo: f.get('titulo'), pregunta: f.get('pregunta')});
        location.hash = '#/investigar/investigaciones/' + i.id; } catch (err) { alert(err.message); } finally { btn.disabled = false; } });
    caja.replaceChildren(el('div', {class: 'card'}, el('h2', {text: 'Nueva investigación'}), form),
      el('div', {class: 'card'}, el('h2', {text: 'Tus investigaciones'}), ...(todas.length ? todas.map(i => el('article', {class: 'res-item'},
        el('div', {class: 'vt'}, el('a', {href: '#/investigar/investigaciones/' + i.id, text: i.titulo})),
        i.pregunta ? el('div', {class: 'sum', text: i.pregunta}) : null,
        el('div', {class: 'meta'}, el('span', {class: 'b' + (i.estado === 'lista' ? ' s-good' : i.estado === 'archivada' ? '' : ' s-info'), text: ESTADO_INV[i.estado]}),
          el('span', {text: `${i.n_fuentes} fuente(s) · ${i.n_notas} nota(s)`}), el('span', {text: 'última actividad ' + fecha(i.actividad_en)}))))
        : [vacio('Aún no tienes investigaciones. Crea la primera arriba.')])));
  }
  async function pintarDetalle(iid) {
    const caja = $('#investigaciones');
    let i; try { i = await api('/api/investigaciones/' + iid); } catch (e) { caja.replaceChildren(el('div', {class: 'card bad', text: e.message}), el('a', {href: '#/investigar/investigaciones', text: '← Volver a Mis investigaciones'})); return; }
    const estado = el('select', {'aria-label': 'Estado'}, ...Object.entries(ESTADO_INV).map(([k, t]) => el('option', {value: k, text: t}))); estado.value = i.estado;
    estado.addEventListener('change', async () => { await api('/api/investigaciones/' + iid, {estado: estado.value}); });
    const pest = [['resumen', 'Resumen'], ['fuentes', `Fuentes (${i.fuentes.length})`], ['afirmaciones', `Afirmaciones (${i.n_afirmaciones})`],
      ['notas', `Notas (${i.notas.length})`], ['cronologia', 'Cronología'], ['dossier', 'Dossier']];
    const tabs = el('div', {class: 'inv-tabs', role: 'tablist'}, ...pest.map(([k, t]) => { const b = el('button', {type: 'button', role: 'tab', 'aria-selected': st.pestana === k ? 'true' : 'false', text: t});
      b.addEventListener('click', () => { st.pestana = k; pintarDetalle(iid); }); return b; }));
    const fn = {fuentes: pestanaFuentes, notas: pestanaNotas, afirmaciones: pestanaAfirmaciones, cronologia: pestanaCronologia, dossier: pestanaDossier}[st.pestana] || pestanaResumen;
    const cuerpo = el('div', {}, el('div', {class: 'am', role: 'status', text: 'Cargando…'}));
    Promise.resolve(fn(i)).then(n => cuerpo.replaceChildren(n)).catch(e => cuerpo.replaceChildren(el('div', {class: 'bad', text: e.message})));
    const piezas = (i.piezas || []).length ? el('div', {class: 'am'}, 'Piezas creadas desde aquí: ', ...i.piezas.flatMap((p, k) =>
      [k ? ', ' : '', el('a', {href: '#/crear/produccion', text: `${p.titulo || p.id} (encargo ${p.id})`})])) : null;
    caja.replaceChildren(el('div', {class: 'card'}, el('a', {href: '#/investigar/investigaciones', text: '← Mis investigaciones'}),
      el('h2', {style: 'margin-top:8px', text: i.titulo}), el('div', {class: 'inv-form'}, el('label', {}, 'Estado', estado),
        el('span', {class: 'am', text: `creada ${fecha(i.creada_en)} · última actividad ${fecha(i.actividad_en)}`})), piezas, tabs, cuerpo));
    $('#migas').querySelector('b').textContent = i.titulo;
  }
  function pestanaResumen(i) {
    const campos = [['pregunta', 'Qué estoy investigando (la pregunta)'], ['descripcion', 'Descripción'], ['que_se', 'Qué sé'],
      ['que_falta', 'Qué falta por comprobar'], ['conclusion', 'Conclusión provisional']];
    const areas = campos.map(([k, t]) => { const a = el('textarea', {class: 'campo', name: k}); a.value = i[k] || ''; return [k, el('label', {class: 'ancho'}, t, a), a]; });
    const ok = el('span', {class: 'guardado-ok', 'aria-live': 'polite'});
    return el('div', {}, ...areas.map(([, l]) => l), el('div', {class: 'acciones'},
      accion('Guardar resumen', async () => { await api('/api/investigaciones/' + i.id, Object.fromEntries(areas.map(([k, , a]) => [k, a.value]))); ok.textContent = 'Guardado ✓ (en tu Mac)'; }, 'pri'), ok));
  }
  function pestanaFuentes(i) {
    const manual = el('form', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Añadir un enlace', el('input', {type: 'url', name: 'url', required: '', placeholder: 'https://…'})),
      el('label', {class: 'ancho'}, 'Título', el('input', {type: 'text', name: 'titulo'})), el('label', {class: 'ancho'}, 'Qué aporta', el('input', {type: 'text', name: 'aporte'})),
      el('button', {class: 'btn pri', type: 'submit', text: 'Añadir fuente'}));
    manual.addEventListener('submit', async e => { e.preventDefault(); const f = new FormData(manual);
      try { await api(`/api/investigaciones/${i.id}/fuentes`, {tipo: 'enlace', url: f.get('url'), titulo: f.get('titulo'), aporte: f.get('aporte')}); pintarDetalle(i.id); } catch (err) { alert(err.message); } });
    return el('div', {}, el('p', {class: 'am', text: 'Añade noticias y vídeos desde el Buscador, Noticias o Vídeos con «Añadir a investigación…», o pega aquí un enlace.'}), manual,
      ...(i.fuentes.length ? i.fuentes.map(r => { const ap = el('textarea', {class: 'campo', 'aria-label': 'Qué aporta'}); ap.value = r.aporte || '';
        return el('article', {class: 'res-item'},
          el('div', {class: 'meta'}, el('span', {class: 'b', text: TIPO_REF[r.tipo] || r.tipo}), el('span', {text: r.fuente || '—'}),
            el('span', {text: r.publicado_en ? 'publicado ' + fecha(r.publicado_en) : 'fecha de publicación desconocida'}), el('span', {text: 'consultada ' + fecha(r.consultada_en)})),
          el('div', {class: 'vt'}, enlace(r.url, r.titulo)),
          el('label', {class: 'ancho am'}, 'Qué aporta esta fuente', ap),
          el('div', {class: 'acciones'}, accion('Guardar', async () => { await api(`/api/investigaciones/${i.id}/fuentes/${r.id}`, {aporte: ap.value}); }, 'pri'),
            accion('Quitar de la investigación', async () => { if (!confirm('¿Quitarla de esta investigación? Seguirá en tu biblioteca.')) return;
              await api(`/api/investigaciones/${i.id}/fuentes/${r.id}/quitar`, {}); pintarDetalle(i.id); })));
      }) : [vacio('Todavía no hay fuentes en esta investigación.')]));
  }
  function pestanaNotas(i) {
    const tipo = el('select', {name: 'tipo', 'aria-label': 'Tipo de nota'}, ...Object.entries(TIPO_NOTA).map(([k, t]) => el('option', {value: k, text: t})));
    const txt = el('textarea', {class: 'campo', name: 'texto', required: '', placeholder: 'Escribe tu nota…'});
    const form = el('form', {class: 'inv-form'}, el('label', {}, 'Tipo', tipo), el('label', {class: 'ancho'}, 'Nota', txt), el('button', {class: 'btn pri', type: 'submit', text: 'Añadir nota'}));
    form.addEventListener('submit', async e => { e.preventDefault(); const btn = form.querySelector('button'); if (btn.disabled) return; btn.disabled = true;
      try { await api(`/api/investigaciones/${i.id}/notas`, {texto: txt.value, tipo: tipo.value}); pintarDetalle(i.id); } catch (err) { alert(err.message); btn.disabled = false; } });
    return el('div', {}, form, ...(i.notas.length ? i.notas.map(n => { const a = el('textarea', {class: 'campo', 'aria-label': 'Editar nota'}); a.value = n.texto;
      return el('article', {class: 'res-item'}, el('div', {class: 'meta'}, el('span', {class: 'b', text: TIPO_NOTA[n.tipo] || n.tipo}), el('span', {text: fecha(n.actualizada_en || n.creada_en)})), a,
        el('div', {class: 'acciones'}, accion('Guardar', async () => { await api(`/api/investigaciones/${i.id}/notas/${n.id}`, {texto: a.value, tipo: n.tipo}); }, 'pri'),
          accion('Borrar…', async () => { if (!confirm('¿Borrar esta nota? No se puede deshacer.')) return; await api(`/api/investigaciones/${i.id}/notas/${n.id}/borrar`, {}); pintarDetalle(i.id); })));
    }) : [vacio('Sin notas todavía.')]));
  }

  // ---------- Continuar investigando
  async function pintarContinuar() {
    const caja = $('#continuar');
    const [invs, bib] = await Promise.all([cargarInvs(), api('/api/biblioteca').then(d => d.referencias)]);
    caja.replaceChildren(el('div', {class: 'card'}, el('h2', {text: 'Investigaciones activas'}),
      ...(invs.length ? invs.slice(0, 6).map(i => el('div', {class: 'res-item'}, el('div', {class: 'vt'}, el('a', {href: '#/investigar/investigaciones/' + i.id, text: i.titulo})),
        el('div', {class: 'meta'}, el('span', {class: 'b s-info', text: ESTADO_INV[i.estado]}), el('span', {text: `${i.n_fuentes} fuente(s) · ${i.n_notas} nota(s) · ${fecha(i.actividad_en)}`}))))
        : [vacio('No hay investigaciones abiertas.'), el('a', {class: 'btn', href: '#/investigar/investigaciones', text: 'Crear una investigación'})])),
      el('div', {class: 'card'}, el('h2', {text: 'Guardado recientemente'}),
        ...(bib.length ? bib.slice(0, 6).map(r => el('div', {class: 'res-item'}, el('div', {class: 'vt'}, enlace(r.url, r.titulo)),
          el('div', {class: 'meta'}, el('span', {class: 'b', text: TIPO_REF[r.tipo]}), el('span', {text: r.fuente || '—'}), el('span', {text: 'guardado ' + fecha(r.creada_en)}))))
          : [vacio('Aún no has guardado nada.')]), el('a', {href: '#/investigar/biblioteca', text: 'Abrir la biblioteca →'})));
  }

  // ===================== Fase 2A: afirmaciones, cronología y dossier =====================
  const EST_AF = {pendiente: ['', 'Pendiente de revisar'], sin_evidencia: ['s-warn', 'Sin evidencia suficiente'],
    atribuida: ['s-info', 'Información atribuida'], confirmado: ['s-good', 'Confirmado por fuente primaria'],
    contradicho: ['s-bad', 'Contradicho por evidencia'], no_verificable: ['s-warn', 'No verificable con los datos disponibles']};
  const REL = {a_favor: 'A favor', en_contra: 'En contra', repite: 'Solo repite'};
  const TIPO_EV = {anuncio: 'Anuncio', publicacion: 'Publicación relevante', rumor: 'Aparece un rumor', confirmacion: 'Confirmación',
    desmentido: 'Desmentido o contradicción', actualizacion: 'Actualización de la investigación'};
  const dia = iso => iso ? new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('es-ES', {day: 'numeric', month: 'short', year: 'numeric'}) : null;
  const opciones = (obj, vacia) => [...(vacia ? [el('option', {value: '', text: vacia})] : []), ...Object.entries(obj).map(([k, v]) => el('option', {value: k, text: Array.isArray(v) ? v[1] : v}))];

  // Ficha de una afirmación. «refs» son las referencias que se pueden usar como evidencia; «alCambiar» repinta.
  function fichaAfirm(a, refs, alCambiar, invId) {
    const c = a.cuentas, est = EST_AF[a.estado] || ['', a.estado];
    const caja = el('article', {class: 'res-item afirm'});
    const evid = a.evidencias.map(e => el('li', {},
      el('span', {class: 'b' + (e.relacion === 'a_favor' ? ' s-good' : e.relacion === 'en_contra' ? ' s-bad' : ''), text: REL[e.relacion]}),
      e.independiente ? el('span', {class: 'b s-info', text: 'independiente'}) : null, ' ', enlace(e.url, e.titulo),
      el('span', {class: 'am', text: ` · ${e.fuente || '—'} · ${dia(e.publicado_en) || 'fecha desconocida'}`}), e.nota ? el('span', {class: 'am', text: ' · ' + e.nota}) : null, ' ',
      accion('Quitar', async () => { await api(`/api/afirmaciones/${a.id}/evidencias/${e.ref_id}/quitar`, {}); alCambiar(); })));
    // añadir evidencia
    const refSel = el('select', {'aria-label': 'Referencia'}, el('option', {value: '', text: refs.length ? 'Elige una fuente…' : 'No hay fuentes: añádelas antes'}),
      ...refs.map(r => el('option', {value: r.id, text: `${r.titulo} (${r.fuente || '—'})`})));
    const relSel = el('select', {'aria-label': 'Relación'}, ...opciones(REL));
    const indep = el('input', {type: 'checkbox'});
    const evNota = el('input', {type: 'text', placeholder: 'qué dice exactamente (opcional)', 'aria-label': 'Nota de la evidencia'});
    relSel.addEventListener('change', () => { indep.disabled = relSel.value === 'repite'; if (indep.disabled) indep.checked = false; });
    const fEv = el('form', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Evidencia', refSel), el('label', {}, 'Relación', relSel),
      el('label', {class: 'chk', title: 'Oficial o primaria: la fuente original, no alguien que lo repite'}, indep, 'Fuente independiente / primaria'),
      el('label', {class: 'ancho'}, 'Nota', evNota), el('button', {class: 'btn', type: 'submit', text: 'Añadir evidencia'}));
    fEv.addEventListener('submit', async e => { e.preventDefault(); if (!refSel.value) return alert('Elige una fuente.');
      try { await api(`/api/afirmaciones/${a.id}/evidencias`, {ref_id: +refSel.value, relacion: relSel.value, independiente: indep.checked, nota: evNota.value}); alCambiar(); } catch (err) { alert(err.message); } });
    // cambiar estado
    const estSel = el('select', {'aria-label': 'Nuevo estado'}, ...opciones(EST_AF)); estSel.value = a.estado;
    const estNota = el('input', {type: 'text', placeholder: 'por qué (obligatorio para Confirmado y Contradicho)', 'aria-label': 'Motivo'});
    const fEst = el('form', {class: 'inv-form'}, el('label', {}, 'Valoración', estSel), el('label', {class: 'ancho'}, 'Motivo', estNota),
      el('button', {class: 'btn pri', type: 'submit', text: 'Guardar valoración'}));
    fEst.addEventListener('submit', async e => { e.preventDefault();
      try { await api(`/api/afirmaciones/${a.id}/estado`, {estado: estSel.value, nota: estNota.value}); alCambiar(); } catch (err) { alert(err.message); } });
    const hist = el('details', {}, el('summary', {text: `Historial (${a.historial.length})`}), el('ul', {class: 'hist'}, ...a.historial.map(h => el('li', {},
      el('span', {class: 'am', text: fecha(h.cuando) + ' · ' + h.autor + ' · '}),
      h.campo === 'estado' ? `estado: ${EST_AF[h.antes]?.[1] || h.antes} → ${EST_AF[h.despues]?.[1] || h.despues}` : h.campo === 'creada' ? 'creada' : `${h.campo}: ${h.antes ?? '—'} → ${h.despues ?? '—'}`,
      h.nota ? el('span', {class: 'am', text: ' · «' + h.nota + '»'}) : null))));
    caja.append(...[
      el('div', {class: 'meta'}, el('span', {class: 'b ' + est[0], text: est[1]}), el('span', {class: 'b', text: 'en el guion: ' + a.etiqueta}),
        a.revision_antigua ? el('span', {class: 'b s-warn', text: 'revisión antigua'}) : null,
        el('span', {text: a.revisada_en ? 'revisada ' + fecha(a.revisada_en) : 'sin revisar'})),
      el('div', {class: 'vt', text: '«' + a.texto + '»'}),
      el('div', {class: 'am', text: `Quién lo dijo primero: ${a.quien_primero || 'desconocido'} · fecha de origen: ${dia(a.fecha_origen) || 'desconocida'}`}),
      a.investigaciones.length ? el('div', {class: 'am'}, 'En: ', ...a.investigaciones.flatMap((x, k) => [k ? ', ' : '', el('a', {href: '#/investigar/investigaciones/' + x.id, text: x.titulo})])) : null,
      el('div', {class: 'cuentas', text: `${c.independientes} fuente(s) independiente(s) · ${c.a_favor} a favor · ${c.en_contra} en contra · ${c.repite} que solo repiten (no suman credibilidad)`}),
      evid.length ? el('ul', {class: 'evid'}, ...evid) : el('div', {class: 'am', text: 'Sin evidencias todavía.'}),
      el('details', {}, el('summary', {text: 'Añadir evidencia o cambiar la valoración'}), fEv, fEst),
      hist,
      invId ? el('div', {class: 'acciones'}, accion('Quitar de esta investigación', async () => {
        if (!confirm('¿Quitarla de esta investigación? Seguirá en Rumores y verificación con su historial.')) return;
        await api(`/api/investigaciones/${invId}/afirmaciones/${a.id}/quitar`, {}); alCambiar(); })) : null].filter(Boolean));
    return caja;
  }

  async function pestanaAfirmaciones(i) {
    const [d, todas] = await Promise.all([api('/api/afirmaciones?inv=' + i.id), api('/api/afirmaciones')]);
    const repintar = () => pintarDetalle(i.id);
    const texto = el('input', {type: 'text', name: 'texto', required: '', minlength: '8', placeholder: 'p. ej. «GTA 6 costará 80 dólares en México»'});
    const quien = el('input', {type: 'text', name: 'quien', placeholder: 'medio, persona o cuenta (opcional)'});
    const fo = el('input', {type: 'date', name: 'fecha'});
    const origen = el('select', {'aria-label': 'Referencia de origen'}, el('option', {value: '', text: 'Sin referencia de origen'}), ...i.fuentes.map(r => el('option', {value: r.id, text: r.titulo})));
    const form = el('form', {class: 'inv-form'}, el('label', {class: 'ancho'}, 'Qué se afirma (una sola afirmación concreta)', texto),
      el('label', {class: 'ancho'}, 'Quién lo dijo primero', quien), el('label', {}, 'Fecha de origen (si se conoce)', fo),
      el('label', {class: 'ancho'}, 'Dónde lo viste', origen), el('button', {class: 'btn pri', type: 'submit', text: 'Añadir afirmación'}));
    form.addEventListener('submit', async e => { e.preventDefault();
      try { await api('/api/afirmaciones', {texto: texto.value, inv_id: i.id, quien_primero: quien.value, fecha_origen: fo.value, ref_origen: origen.value || null}); repintar(); } catch (err) { alert(err.message); } });
    const ajenas = todas.afirmaciones.filter(a => !a.investigaciones.some(x => x.id === i.id));
    const enl = el('select', {'aria-label': 'Afirmación existente'}, el('option', {value: '', text: ajenas.length ? 'Enlazar una afirmación que ya existe…' : 'No hay otras afirmaciones'}), ...ajenas.map(a => el('option', {value: a.id, text: a.texto})));
    enl.addEventListener('change', async () => { if (!enl.value) return; try { await api(`/api/investigaciones/${i.id}/afirmaciones/${enl.value}`, {}); repintar(); } catch (err) { alert(err.message); } });
    return el('div', {}, el('p', {class: 'am', text: 'La unidad es la afirmación, no el artículo. Las fuentes que solo repiten no suben su credibilidad. «Confirmado» exige una evidencia a favor de una fuente independiente.'}),
      form, el('div', {class: 'inv-form'}, enl),
      ...(d.afirmaciones.length ? d.afirmaciones.map(a => fichaAfirm(a, i.fuentes, repintar, i.id)) : [vacio('Aún no hay afirmaciones en esta investigación.')]));
  }

  async function pintarRumores() {
    const caja = $('#rumores'), f = st.rumores || (st.rumores = {estado: '', q: '', inv: ''});
    const [d, bib, invs] = await Promise.all([api('/api/afirmaciones?' + new URLSearchParams(f)), api('/api/biblioteca'), cargarInvs()]);
    const estado = el('select', {'aria-label': 'Estado'}, ...opciones(EST_AF, 'Todos los estados')); estado.value = f.estado;
    const inv = el('select', {'aria-label': 'Investigación'}, el('option', {value: '', text: 'Todas las investigaciones'}), ...invs.map(x => el('option', {value: x.id, text: x.titulo}))); inv.value = f.inv;
    const q = el('input', {type: 'search', value: f.q, placeholder: 'texto, quién lo dijo…', 'aria-label': 'Buscar afirmación'});
    const form = el('form', {class: 'inv-form'}, el('label', {}, 'Estado', estado), el('label', {}, 'Investigación', inv), el('label', {class: 'ancho'}, 'Buscar', q),
      el('button', {class: 'btn pri', type: 'submit', text: 'Filtrar'}));
    form.addEventListener('submit', e => { e.preventDefault(); Object.assign(f, {estado: estado.value, inv: inv.value, q: q.value.trim()}); pintarRumores(); });
    const antiguas = d.afirmaciones.filter(a => a.revision_antigua).length;
    caja.replaceChildren(el('div', {class: 'card'}, form,
      el('p', {class: 'am', text: `Sin puntuación de «verdad»: el estado lo decides tú y cada cambio queda en el historial. ${antiguas ? antiguas + ` sin revisar desde hace más de ${d.dias_revision} días.` : ''}`})),
      el('div', {class: 'card'}, el('div', {class: 'toolbar'}, el('span', {text: `${d.afirmaciones.length} afirmación(es)`})),
        ...(d.afirmaciones.length ? d.afirmaciones.map(a => fichaAfirm(a, bib.referencias, pintarRumores))
          : [vacio('No hay afirmaciones con estos filtros. Se crean desde la pestaña Afirmaciones de una investigación.')])));
  }

  // ---------- Cronología
  function lineaTiempo(eventos, alCambiar) {
    if (!eventos.length) return vacio('Sin eventos todavía.');
    const QUE = {ocurrio: 'ocurrió', publicado: 'publicado', detectado: 'detectado por el Radar', registrado: 'registrado aquí'};
    return el('ol', {class: 'timeline'}, ...eventos.map(e => el('li', {class: 'ev ev-' + e.tipo + (e.oculto ? ' ev-oculto' : '')},
      el('div', {class: 'meta'}, el('b', {text: dia(e.ocurrio_en || e.publicado_en || e.detectado_en || e.creado_en)}),
        el('span', {class: 'am', text: 'fecha: ' + QUE[e.fecha_usada]}), el('span', {class: 'b', text: e.tipo_nombre}),
        e.automatico ? el('span', {class: 'am', text: 'automático'}) : null, e.inv_titulo ? el('a', {href: '#/investigar/investigaciones/' + e.inv_id, text: e.inv_titulo}) : null),
      el('div', {class: 'vt'}, e.url ? enlace(e.url, e.titulo) : e.titulo),
      el('div', {class: 'am', text: `ocurrió: ${dia(e.ocurrio_en) || 'desconocido'} · publicado: ${dia(e.publicado_en) || 'desconocido'} · detectado: ${dia(e.detectado_en) || '—'}${e.fuente ? ' · ' + e.fuente : ''}`}),
      e.nota ? el('div', {class: 'sum', text: e.nota}) : null,
      el('div', {class: 'acciones'}, accion(e.oculto ? 'Mostrar' : 'Ocultar', async () => { await api('/api/cronologia/' + e.id, {oculto: !e.oculto}); alCambiar(); }),
        e.automatico ? null : accion('Borrar…', async () => { if (!confirm('¿Borrar este evento? No se puede deshacer.')) return; await api(`/api/cronologia/${e.id}/borrar`, {}); alCambiar(); })))));
  }
  function formEvento(invId, fuentes, alCambiar) {
    const tipo = el('select', {'aria-label': 'Tipo'}, ...opciones(TIPO_EV)), titulo = el('input', {type: 'text', required: '', placeholder: 'qué pasó'});
    const ocu = el('input', {type: 'date'}), ref = el('select', {'aria-label': 'Referencia'}, el('option', {value: '', text: 'Sin referencia'}), ...fuentes.map(r => el('option', {value: r.id, text: r.titulo})));
    const nota = el('input', {type: 'text', placeholder: 'opcional'});
    const f = el('form', {class: 'inv-form'}, el('label', {}, 'Tipo', tipo), el('label', {class: 'ancho'}, 'Evento', titulo),
      el('label', {}, 'Cuándo ocurrió (si se sabe)', ocu), el('label', {class: 'ancho'}, 'Referencia', ref), el('label', {class: 'ancho'}, 'Nota', nota),
      el('button', {class: 'btn pri', type: 'submit', text: 'Añadir evento'}));
    f.addEventListener('submit', async e => { e.preventDefault();
      try { await api('/api/cronologia', {tipo: tipo.value, titulo: titulo.value, inv_id: invId || null, ref_id: ref.value || null, ocurrio_en: ocu.value, nota: nota.value}); alCambiar(); } catch (err) { alert(err.message); } });
    return el('details', {}, el('summary', {text: 'Añadir un evento a mano'}), f);
  }
  async function pestanaCronologia(i) {
    const d = await api('/api/cronologia?inv=' + i.id);
    return el('div', {}, el('p', {class: 'am', text: 'Ordenada por cuándo ocurrió; si no se sabe, por cuándo se publicó. Ninguna fecha se inventa.'}),
      formEvento(i.id, i.fuentes, () => pintarDetalle(i.id)), lineaTiempo(d.eventos, () => pintarDetalle(i.id)));
  }
  async function pintarCronologia() {
    const caja = $('#cronologia'), f = st.crono || (st.crono = {tipo: '', tema: '', inv: '', desde: '', hasta: '', ocultos: ''});
    const [d, invs] = await Promise.all([api('/api/cronologia?' + new URLSearchParams(f)), cargarInvs()]);
    const tipo = el('select', {'aria-label': 'Tipo'}, ...opciones(TIPO_EV, 'Todos los tipos')); tipo.value = f.tipo;
    const tema = el('select', {'aria-label': 'Tema'}, ...opciones(d.temas, 'Todos los temas')); tema.value = f.tema;
    const inv = el('select', {'aria-label': 'Investigación'}, el('option', {value: '', text: 'Todas'}), ...invs.map(x => el('option', {value: x.id, text: x.titulo}))); inv.value = f.inv;
    const desde = el('input', {type: 'date', value: f.desde, 'aria-label': 'Desde'}), hasta = el('input', {type: 'date', value: f.hasta, 'aria-label': 'Hasta'});
    const ocultos = el('input', {type: 'checkbox'}); ocultos.checked = !!f.ocultos;
    const form = el('form', {class: 'inv-form'}, el('label', {}, 'Tipo', tipo), el('label', {}, 'Tema', tema), el('label', {}, 'Investigación', inv),
      el('label', {}, 'Desde', desde), el('label', {}, 'Hasta', hasta), el('label', {class: 'chk'}, ocultos, 'Ver ocultos'), el('button', {class: 'btn pri', type: 'submit', text: 'Filtrar'}));
    form.addEventListener('submit', e => { e.preventDefault(); Object.assign(f, {tipo: tipo.value, tema: tema.value, inv: inv.value, desde: desde.value, hasta: hasta.value, ocultos: ocultos.checked ? '1' : ''}); pintarCronologia(); });
    caja.replaceChildren(el('div', {class: 'card'}, form, el('p', {class: 'am', text: 'Reúne los eventos de tus investigaciones: fuentes añadidas, rumores, confirmaciones, desmentidos y los que añadas a mano.'})),
      el('div', {class: 'card'}, formEvento(f.inv, [], pintarCronologia), lineaTiempo(d.eventos, pintarCronologia)));
  }

  // ---------- Dossier y paso a la Fábrica
  function vistaDossier(c) {
    const grupos = [['confirmadas', 'Confirmado'], ['atribuidas', 'Atribuido (REPORTADO)'], ['incertidumbres', 'Incertidumbres (RUMOR)'], ['contradichas', 'Contradicho (no se afirma)']];
    return el('div', {class: 'dossier'},
      c.avisos.length ? el('div', {class: 'aviso'}, ...c.avisos.map(a => el('div', {text: '⚠ ' + a}))) : null,
      ...grupos.filter(([k]) => c.afirmaciones[k].length).map(([k, t]) => el('div', {}, el('h3', {text: `${t} (${c.afirmaciones[k].length})`}),
        el('ul', {}, ...c.afirmaciones[k].map(a => el('li', {}, el('span', {class: 'b', text: a.etiqueta}), ' ' + a.texto,
          el('span', {class: 'am', text: ` · ${a.cuentas.independientes} independiente(s), ${a.cuentas.repite} solo repiten`})))))),
      el('div', {class: 'am', text: `${c.fuentes.length} fuente(s) · ${c.cronologia.length} evento(s) en la cronología`}));
  }
  async function pestanaDossier(i) {
    const d = await api(`/api/investigaciones/${i.id}/dossier`);
    const descargar = (md, n) => { const a = el('a', {href: URL.createObjectURL(new Blob([md], {type: 'text/markdown'})), download: `dossier-${i.id}-v${n}.md`}); a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); };
    const versiones = d.versiones.map(v => el('li', {}, el('b', {text: `v${v.n}`}), ` · ${fecha(v.creado_en)}`,
      v.piezas.length ? el('span', {class: 'am', text: ' · piezas: ' + v.piezas.map(p => p.id).join(', ')}) : null, ' ',
      accion('Crear idea de vídeo…', async () => { const dv = await api('/api/dossiers/' + v.id); caja.replaceChildren(pasoFabrica(dv, d, i)); }, 'pri'),
      accion('Descargar .md', async () => { const dv = await api('/api/dossiers/' + v.id); descargar(dv.markdown, v.n); })));
    const caja = el('div', {},
      el('p', {class: 'am', text: 'Vista previa con lo que hay ahora en la investigación. «Guardar versión» la congela: la pieza que salga de ella sabrá exactamente con qué datos se hizo.'}),
      el('div', {class: 'acciones'}, accion('Guardar versión del dossier', async () => { await api(`/api/investigaciones/${i.id}/dossier`, {}); pintarDetalle(i.id); }, 'pri'),
        accion('Copiar Markdown', async b => { await navigator.clipboard.writeText(d.markdown); b.textContent = 'Copiado ✓'; })),
      vistaDossier(d.contenido),
      el('details', {}, el('summary', {text: 'Ver el dossier completo (Markdown)'}), el('pre', {class: 'md-pre', text: d.markdown})),
      el('h3', {text: 'Versiones guardadas'}),
      versiones.length ? el('ul', {class: 'hist'}, ...versiones) : vacio('Aún no has guardado ninguna versión. Guarda una para poder crear la idea de vídeo.'));
    return caja;
  }
  function pasoFabrica(dv, d, i) {
    const c = dv.contenido;
    const variante = el('select', {'aria-label': 'Formato'}, ...opciones(d.variantes));
    const plats = Object.entries(d.plataformas).map(([k, t]) => { const x = el('input', {type: 'checkbox', value: k}); x.checked = true; return [x, el('label', {class: 'chk'}, x, t)]; });
    const resumen = el('div', {});
    const pintar = () => { const bulo = variante.value === 'verdad_bulo';
      resumen.replaceChildren(...[el('h3', {text: 'Lo que recibirá el guion'}),
        el('ul', {}, ...['confirmadas', 'atribuidas', 'incertidumbres', ...(bulo ? ['contradichas'] : [])].flatMap(k => c.afirmaciones[k]).map(a =>
          el('li', {}, el('span', {class: 'b', text: a.etiqueta}), ' ' + a.texto))),
        !bulo && c.afirmaciones.contradichas.length ? el('div', {class: 'aviso', text: 'No se afirmará (contradicho): ' + c.afirmaciones.contradichas.map(a => a.texto).join(' · ')}) : null,
        el('div', {class: 'am', text: 'Fuentes: ' + (c.fuentes.map(f => f.titulo).join(' · ') || 'ninguna')}),
        ...c.avisos.map(a => el('div', {class: 'aviso', text: '⚠ ' + a}))].filter(Boolean)); };
    variante.addEventListener('change', pintar); pintar();
    const ok = el('div', {'aria-live': 'polite'});
    return el('div', {}, el('h3', {text: `Crear idea de vídeo desde el dossier v${dv.n}`}),
      el('p', {class: 'am', text: 'Se crea la pieza en el Estudio en la etapa Idea. No se aprueba, no se fabrica y no se publica nada: eso lo decides tú en En producción.'}),
      el('div', {class: 'inv-form'}, el('label', {}, 'Formato', variante), ...plats.map(([, l]) => l)), resumen,
      el('div', {class: 'acciones'}, accion('Crear idea en el Estudio', async () => {
        const p = await api(`/api/dossiers/${dv.id}/idea`, {variante: variante.value, plataformas: plats.filter(([x]) => x.checked).map(([x]) => x.value)});
        ok.replaceChildren(el('div', {class: 'guardado-ok', text: `Pieza ${p.id} en el Estudio (etapa Idea). `}), el('a', {href: '#/crear/produccion', text: 'Ir a En producción →'})); }, 'pri'),
        accion('Volver al dossier', async () => pintarDetalle(i.id))), ok);
  }
  async function pintarDossiers() {
    const d = await api('/api/dossiers');
    $('#dossiers').replaceChildren(el('div', {class: 'card'}, el('h2', {text: 'Dossiers guardados'}),
      el('p', {class: 'am', text: 'Cada dossier es una versión congelada de una investigación. Los guiones de las piezas que salen de un dossier usan sus afirmaciones y etiquetas.'}),
      ...(d.dossiers.length ? d.dossiers.map(x => el('article', {class: 'res-item'},
        el('div', {class: 'vt'}, el('a', {href: '#/investigar/investigaciones/' + x.inv_id, text: `${x.inv_titulo} · dossier v${x.n}`})),
        el('div', {class: 'meta'}, el('span', {text: 'guardado ' + fecha(x.creado_en)}),
          el('span', {text: x.piezas.length ? 'piezas: ' + x.piezas.map(p => `${p.id} (${p.titulo || ''})`).join(', ') : 'sin piezas todavía'}))))
        : [vacio('Aún no hay dossiers. Se preparan en la pestaña Dossier de una investigación.')])));
  }

  function alCambiarVista(ruta) {
    if (!window.PC_ESTUDIO) return;
    const fn = {'investigar/buscador': pintarBuscador, 'investigar/noticias': pintarNoticias, 'investigar/biblioteca': pintarBiblioteca,
      'investigar/investigaciones': pintarInvestigaciones, 'inicio/continuar': pintarContinuar, 'investigar/videos': decorarVideos,
      'investigar/rumores': pintarRumores, 'investigar/cronologia': pintarCronologia, 'crear/guiones': pintarDossiers}[ruta];
    if (fn) Promise.resolve(fn()).catch(e => console.warn(e));
  }
  function iniciar() {
    window.addEventListener('vista', e => alCambiarVista(e.detail));
    window.addEventListener('estudio-listo', async () => { await cargarInvs().catch(() => {}); alCambiarVista(rutaActual()); });
    // el explorador de vídeos se vuelve a pintar al filtrar: se añaden las acciones después de cada repintado
    const original = render;
    render = function () { original(); decorarVideos(); };  // eslint-disable-line no-global-assign
  }
  return {iniciar};
})();

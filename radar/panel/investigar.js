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
    const tipos = Object.entries({noticia: 'Noticias', video: 'Vídeos', creador: 'Creadores', briefing: 'Briefings', referencia: 'Guardados', nota: 'Mis notas', investigacion: 'Investigaciones'})
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
        el('div', {class: 'vt'}, r.tipo === 'investigacion' ? el('a', {href: '#/investigar/investigaciones/' + r.clave}, ...resaltado(r.titulo_marcado))
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
    const pest = [['resumen', 'Resumen'], ['fuentes', `Fuentes (${i.fuentes.length})`], ['notas', `Notas (${i.notas.length})`]];
    const tabs = el('div', {class: 'inv-tabs', role: 'tablist'}, ...pest.map(([k, t]) => { const b = el('button', {type: 'button', role: 'tab', 'aria-selected': st.pestana === k ? 'true' : 'false', text: t});
      b.addEventListener('click', () => { st.pestana = k; pintarDetalle(iid); }); return b; }),
      ...['Afirmaciones', 'Cronología', 'Dossier'].map(t => el('span', {class: 'pronto', title: 'Llega en la fase 2', text: t + ' · fase 2'})));
    let cuerpo;
    if (st.pestana === 'fuentes') cuerpo = pestanaFuentes(i); else if (st.pestana === 'notas') cuerpo = pestanaNotas(i); else cuerpo = pestanaResumen(i);
    caja.replaceChildren(el('div', {class: 'card'}, el('a', {href: '#/investigar/investigaciones', text: '← Mis investigaciones'}),
      el('h2', {style: 'margin-top:8px', text: i.titulo}), el('div', {class: 'inv-form'}, el('label', {}, 'Estado', estado),
        el('span', {class: 'am', text: `creada ${fecha(i.creada_en)} · última actividad ${fecha(i.actividad_en)}`})), tabs, cuerpo));
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

  function alCambiarVista(ruta) {
    if (!window.PC_ESTUDIO) return;
    const fn = {'investigar/buscador': pintarBuscador, 'investigar/noticias': pintarNoticias, 'investigar/biblioteca': pintarBiblioteca,
      'investigar/investigaciones': pintarInvestigaciones, 'inicio/continuar': pintarContinuar, 'investigar/videos': decorarVideos}[ruta];
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

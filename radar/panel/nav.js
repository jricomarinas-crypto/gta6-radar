// ===== Navegación lateral, rutas (#/grupo/seccion), estado de los datos y vistas de Sistema =====
// Las secciones aún no construidas se muestran como «pronto» (no son enlaces): ningún control aparenta funcionar.
const MENU = [
  {id: 'inicio', ico: '⌂', t: 'Inicio', items: [['hoy', 'Hoy'], ['alertas', 'Alertas'], ['continuar', 'Continuar investigando']]},
  {id: 'investigar', ico: '⌕', t: 'Investigar', items: [['buscador', 'Buscador'], ['noticias', 'Noticias y fuentes'],
    ['videos', 'Vídeos'], ['temas', 'Temas y tendencias'], ['rumores', 'Rumores y verificación'], ['creadores', 'Creadores y canales'],
    ['cronologia', 'Cronología'], ['investigaciones', 'Mis investigaciones'], ['biblioteca', 'Biblioteca de referencias']]},
  {id: 'canal', ico: '▤', t: 'Mi canal', items: [['estadisticas', 'Estadísticas'], ['rinde', 'Lo que más rinde'],
    ['mis-videos', 'Mis vídeos'], ['colaboradores', 'Colaboradores']]},
  {id: 'crear', ico: '✚', t: 'Crear', items: [['ideas', 'Fábrica de ideas'], ['guiones', 'Guiones y dossiers'],
    ['produccion', 'En producción'], ['revision', 'Revisión', '3'], ['calendario', 'Calendario', '3'], ['episodios', 'Episodios y archivos']]},
  {id: 'sistema', ico: '⚙', t: 'Sistema', items: [['fuentes', 'Fuentes vigiladas'], ['ejecuciones', 'Automatizaciones y ejecuciones'],
    ['configuracion', 'Configuración']]},
];
const RUTA_INICIAL = 'inicio/hoy';

function rutaValida(r) {
  const [g, s] = (r || '').split('/');
  const grupo = MENU.find(x => x.id === g);
  const item = grupo && grupo.items.find(i => i[0] === s);
  return item && !item[2] && document.querySelector(`[data-vista="${g}/${s}"]`) ? `${g}/${s}` : null;
}
function rutaActual() { return rutaValida(location.hash.replace(/^#\/?/, '')) || RUTA_INICIAL; }
// subruta: una investigación concreta (#/investigar/investigaciones/<id>)
function subRuta() {
  const p = location.hash.replace(/^#\/?/, '').split('/');
  return p[0] === 'investigar' && p[1] === 'investigaciones' && /^[0-9a-f]{6}$/.test(p[2] || '') ? p[2] : null;
}

function construirMenu() {
  const abiertos = guardado.leer('nav.abiertos', ['inicio', 'investigar', 'crear']);
  const nav = $('#nav-menu');
  nav.replaceChildren(...MENU.map(g => {
    const abierto = abiertos.includes(g.id);
    const lista = el('ul', {id: 'grupo-' + g.id, hidden: !abierto}, ...g.items.map(([id, t, fase]) => el('li', {},
      fase ? el('span', {class: 'pronto', title: `Llega en la fase ${fase}`}, t, el('small', {text: 'fase ' + fase}))
           : el('a', {href: `#/${g.id}/${id}`, 'data-ruta': `${g.id}/${id}`, text: t}))));
    const boton = el('button', {type: 'button', 'aria-expanded': abierto ? 'true' : 'false', 'aria-controls': 'grupo-' + g.id, title: g.t},
      el('span', {class: 'ico', 'aria-hidden': 'true', text: g.ico}), el('span', {class: 'txt', text: g.t}), el('span', {class: 'fl', 'aria-hidden': 'true', text: '›'}));
    boton.addEventListener('click', () => {
      if (document.body.classList.contains('nav-contraida')) { contraer(false); abrirGrupo(g.id, true); return; }
      abrirGrupo(g.id, boton.getAttribute('aria-expanded') !== 'true');
    });
    return el('div', {class: 'grupo'}, boton, lista);
  }));
  nav.addEventListener('click', e => { if (e.target.closest('a[data-ruta]') && document.body.classList.contains('nav-abierta')) menuMovil(false); });
}
function abrirGrupo(id, abrir) {
  const b = document.querySelector(`[aria-controls="grupo-${id}"]`);
  b.setAttribute('aria-expanded', abrir ? 'true' : 'false');
  $('#grupo-' + id).hidden = !abrir;
  const abiertos = new Set(guardado.leer('nav.abiertos', ['inicio', 'investigar', 'crear']));
  abrir ? abiertos.add(id) : abiertos.delete(id);
  guardado.poner('nav.abiertos', [...abiertos]);
}
function contraer(si) {
  document.body.classList.toggle('nav-contraida', si);
  $('#nav-contraer').setAttribute('aria-expanded', si ? 'false' : 'true');
  $('#nav-contraer').setAttribute('aria-label', si ? 'Expandir el menú' : 'Contraer el menú');
  $('#nav-contraer').textContent = si ? '»' : '«';
  guardado.poner('nav.contraida', si);
}

// menú en móvil: se abre por encima, se cierra con Esc, el velo o al elegir; el foco vuelve al botón ☰
function menuMovil(abrir) {
  document.body.classList.toggle('nav-abierta', abrir);
  $('#nav-velo').hidden = !abrir;
  $('#nav-abrir').setAttribute('aria-expanded', abrir ? 'true' : 'false');
  if (abrir) (document.querySelector('#nav-menu a[aria-current=page]') || $('#nav-cerrar')).focus();
  else $('#nav-abrir').focus();
}
document.addEventListener('keydown', e => {
  if (!document.body.classList.contains('nav-abierta')) return;
  if (e.key === 'Escape') { e.preventDefault(); menuMovil(false); return; }
  if (e.key === 'Tab') {  // el foco no se escapa del menú mientras está abierto
    const f = [...$('#nav').querySelectorAll('button, a[href]')].filter(x => x.offsetParent !== null);
    if (!f.length) return;
    if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
  }
});

function mostrarVista() {
  const ruta = rutaActual(), sub = subRuta();
  window.PC_SUB = sub;
  const completa = '#/' + ruta + (sub ? '/' + sub : '');
  if (location.hash !== completa && location.hash) history.replaceState(null, '', completa);
  document.querySelectorAll('[data-vista]').forEach(s => s.hidden = s.dataset.vista !== ruta);
  document.querySelectorAll('#nav-menu a[data-ruta]').forEach(a => a.toggleAttribute('aria-current', a.dataset.ruta === ruta));
  document.querySelectorAll('#nav-menu a[aria-current]').forEach(a => a.setAttribute('aria-current', 'page'));
  const [g, s] = ruta.split('/');
  const grupo = MENU.find(x => x.id === g), item = grupo.items.find(i => i[0] === s);
  if ($('#grupo-' + g).hidden) abrirGrupo(g, true);
  $('#migas').replaceChildren(grupo.t, ' › ', el('b', {text: item[1]}));
  document.title = `${item[1]} · GTA VI Radar`;
  window.dispatchEvent(new CustomEvent('vista', {detail: ruta}));
}

// ----- estado de los datos (cabecera) y vistas de Sistema
function edadHoras() { return (Date.now() - new Date(DATA.generated_at)) / 36e5; }
function pintarEstadoDatos() {
  const p = $('#estado-datos-pill');
  if (DATA.demo) p.replaceChildren(el('b', {text: 'DEMO'}), ' datos inventados');
  else if (edadHoras() > (DATA.datos_antiguos_horas || 3)) p.replaceChildren('⚠ ', el('b', {text: 'Datos antiguos'}), ` (${ago(DATA.generated_at)})`);
  else p.replaceChildren('● ', el('b', {text: 'Datos al día'}));
}
function pintarEjecuciones() {
  const r = DATA.last_run || {};
  if (!r.started_at) { $('#ejecuciones').replaceChildren(el('div', {class: 'empty', text: 'Aún no hay ejecuciones del Radar registradas en estos datos.'})); return; }
  let stats = {}; try { stats = JSON.parse(r.stats || '{}'); } catch { /* ignorar */ }
  $('#ejecuciones').replaceChildren(el('h2', {text: 'Última ejecución del Radar'}),
    el('dl', {class: 'kv'}, el('dt', {text: 'Empezó'}), el('dd', {text: `${new Date(r.started_at).toLocaleString('es-ES')} (${ago(r.started_at)})`}),
      el('dt', {text: 'Terminó'}), el('dd', {text: r.finished_at ? new Date(r.finished_at).toLocaleString('es-ES') : 'sin terminar'}),
      el('dt', {text: 'Errores'}), el('dd', {class: r.error ? 'bad' : 'ok', text: r.error || 'ninguno'}),
      ...Object.entries(stats).filter(([k]) => k !== 'errores').flatMap(([k, v]) => [el('dt', {text: k}), el('dd', {text: typeof v === 'object' ? JSON.stringify(v) : String(v)})])),
    el('p', {class: 'am', text: 'El Radar se ejecuta en GitHub Actions (radar.yml). Esta página muestra la última ejecución incluida en los datos del panel.'}));
}
async function pintarConfiguracion() {
  const filas = [['Datos', DATA.demo ? 'DEMOSTRACIÓN (inventados)' : 'reales'], ['Generados', `${new Date(DATA.generated_at).toLocaleString('es-ES')} (${ago(DATA.generated_at)})`],
    ['Zona horaria de los días', (DATA.series || {}).zona || '—'], ['Lanzamiento (config.yaml)', DATA.release_date || '—'],
    ['Aviso de datos antiguos', `a partir de ${DATA.datos_antiguos_horas || 3} h`], ['Dónde se abre', window.PC_ESTUDIO ? 'Estudio de tu Mac' : 'Web pública / archivo (solo lectura)']];
  const caja = [el('h2', {text: 'Estado de los datos'}), el('dl', {class: 'kv'}, ...filas.flatMap(([k, v]) => [el('dt', {text: k}), el('dd', {text: v})]))];
  if (window.PC_ESTUDIO) {
    try {
      const d = await api('/api/estado-datos');
      caja.push(el('h2', {text: 'Conexiones (solo se indica si existen; nunca su valor)'}),
        el('dl', {class: 'kv'}, ...d.conexiones.flatMap(c => [el('dt', {text: c.nombre}), el('dd', {class: c.ok ? 'ok' : 'am', text: c.ok ? 'conectada' : 'no conectada · ' + c.como})])));
    } catch (e) { caja.push(el('p', {class: 'bad', text: 'No se pudo consultar el Estudio: ' + e.message})); }
  }
  $('#estado-datos').replaceChildren(...caja);
}

function iniciarNavegacion() {
  construirMenu();
  contraer(guardado.leer('nav.contraida', false));
  $('#nav-contraer').addEventListener('click', () => contraer(!document.body.classList.contains('nav-contraida')));
  $('#nav-abrir').addEventListener('click', () => menuMovil(true));
  $('#nav-cerrar').addEventListener('click', () => menuMovil(false));
  $('#nav-velo').addEventListener('click', () => menuMovil(false));
  window.addEventListener('hashchange', mostrarVista);
  window.addEventListener('vista', e => { if (e.detail === 'sistema/configuracion') pintarConfiguracion(); });
  window.addEventListener('estudio-listo', () => { if (rutaActual() === 'sistema/configuracion') pintarConfiguracion(); });
  pintarEstadoDatos(); pintarEjecuciones();
  mostrarVista();
}

Investigar.iniciar();
Canal.iniciar();
iniciarNavegacion();
arrancarPanel();
Hoy.iniciar();

const DATA = /*__DATA__*/null;
const $ = s => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) n.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return n;
};
const safeUrl = u => (typeof u === 'string' && /^https?:\/\//i.test(u)) ? u : null;
const nf = new Intl.NumberFormat('es-ES');
const fmt = n => n == null ? '—' : n >= 1e6 ? (n / 1e6).toFixed(1).replace('.', ',') + ' M' : n >= 1e4 ? Math.round(n / 1e3) + ' k' : nf.format(Math.round(n));
const ago = iso => { if (!iso) return ''; const h = (Date.now() - new Date(iso)) / 36e5;
  return h < 1 ? `hace ${Math.max(1, Math.round(h * 60))} min` : h < 48 ? `hace ${Math.round(h)} h` : `hace ${Math.round(h / 24)} d`; };
const TOPIC = {lanzamiento:'Lanzamiento',precio_ediciones:'Precio y ediciones',plataformas_pc:'Plataformas / PC',rendimiento_fps:'Rendimiento y FPS',mapa:'Mapa',personajes:'Personajes',historia:'Historia',gameplay:'Gameplay',vehiculos:'Vehículos',online:'GTA Online',trailer:'Tráileres',filtraciones_rumores:'Filtraciones y rumores',comparativa_gta5:'GTA 5 vs GTA 6',graficos_tecnologia:'Gráficos y tecnología',polemica:'Polémicas',humor_memes:'Memes',reacciones:'Reacciones',guias_trucos:'Guías y trucos',ventas_negocio:'Ventas y negocio',otros:'Otros'};
const TYPE = {trailer:'Tráiler',gameplay:'Gameplay',leak:'Filtración',rumor:'Rumor',news:'Noticia',analysis:'Análisis',theory:'Teoría',reaction:'Reacción',review:'Review',comparison:'Comparativa',meme:'Meme',interview:'Entrevista',stream:'Directo',short:'Short',podcast:'Podcast',guide:'Guía',other:'Otro'};
const RISK = {low:['s-good','● Riesgo bajo'],medium:['s-info','◆ Riesgo medio'],high:['s-warn','▲ Riesgo alto'],critical:['s-crit','■ Riesgo crítico']};
const VER = {official:['s-info','Oficial'],reported:['','Reportado por medios'],unverified:['s-warn','Sin verificar'],opinion:['','Opinión']};
const SEVL = {critical:'■ Crítica',high:'▲ Alta',medium:'◆ Media',low:'○ Baja'};
const RISKN = {low:0,medium:1,high:2,critical:3};

const state = {period: 24, lang: '', fmt: '', topic: '', risk: '', score: 0, q: '', sort: 'score'};

// ---------- tooltip
const tip = $('#tip');
function showTip(e, value, label) {
  tip.replaceChildren(el('b', {text: value}), el('span', {text: label}));
  tip.style.display = 'block';
  const r = e.target.getBoundingClientRect ? e.target.getBoundingClientRect() : null;
  const x = e.clientX ?? (r ? r.left + r.width / 2 : 0), y = e.clientY ?? (r ? r.top : 0);
  tip.style.left = Math.min(window.innerWidth - tip.offsetWidth - 8, x + 12) + 'px';
  tip.style.top = (y - tip.offsetHeight - 10) + 'px';
}
const hideTip = () => tip.style.display = 'none';
function hover(node, value, label) {
  node.tabIndex = 0;
  node.addEventListener('pointermove', e => showTip(e, value, label));
  node.addEventListener('focus', e => showTip(e, value, label));
  node.addEventListener('pointerleave', hideTip); node.addEventListener('blur', hideTip);
}

// ---------- filtros
function filtered() {
  const cut = Date.now() - state.period * 36e5;
  const q = state.q.trim().toLowerCase();
  return DATA.videos.filter(v => {
    if (new Date(v.published_at) < cut) return false;
    const lg = (v.language || '').slice(0, 2);
    if (state.lang === 'other' ? ['es', 'en'].includes(lg) : state.lang && lg !== state.lang) return false;
    if (state.fmt === 'short' && !v.is_short) return false;
    if (state.fmt === 'long' && v.is_short) return false;
    if (state.topic && !(v.topics || []).includes(state.topic)) return false;
    const rk = RISKN[v.risk || 'low'];
    if (state.risk === 'low' && rk > 0) return false;
    if (state.risk === 'medium' && rk < 1) return false;
    if (state.risk === 'high' && rk < 2) return false;
    if ((v.score || 0) < state.score) return false;
    if (q && !`${v.title} ${v.channel} ${(v.entities || []).join(' ')} ${v.summary || ''}`.toLowerCase().includes(q)) return false;
    return true;
  });
}

function render() {
  renderChips();
  const vids = filtered();
  const cut = Date.now() - state.period * 36e5;
  renderKpis(vids, cut);
  renderVideos(vids);
  renderTopics(vids);
  renderHourly(vids);
  renderAlerts(cut);
  renderNews(cut);
}

// chips con los filtros activos de Vídeos: cada uno con ✕ y «Limpiar filtros» (los valores por defecto no salen)
const FILTROS = {lang: ['#f-lang', ''], fmt: ['#f-fmt', ''], topic: ['#f-topic', ''], risk: ['#f-risk', ''], score: ['#f-score', 0], q: ['#f-q', '']};
function renderChips() {
  let caja = $('#f-chips');
  if (!caja) { caja = el('div', {class: 'chips', id: 'f-chips', 'aria-live': 'polite'}); document.querySelector('[data-vista="investigar/videos"] .filters').after(caja); }
  const nombre = (k, v) => { const s = $(FILTROS[k][0]); if (k === 'score') return 'score ≥ ' + v; if (k === 'q') return '«' + v + '»';
    const o = s && [...s.options].find(o => o.value === v); return o ? o.textContent : v; };
  const quitar = k => { state[k] = FILTROS[k][1]; const s = $(FILTROS[k][0]); if (s) s.value = FILTROS[k][1]; if (k === 'score') $('#f-score-v').textContent = '0'; render(); };
  const activos = Object.keys(FILTROS).filter(k => state[k] && state[k] !== FILTROS[k][1]);
  caja.replaceChildren(...activos.map(k => el('span', {class: 'chip'}, nombre(k, state[k]), el('button', {type: 'button', 'aria-label': 'Quitar filtro ' + nombre(k, state[k]), text: '✕', onclick: () => quitar(k)}))),
    ...(activos.length > 1 ? [el('button', {type: 'button', class: 'btn', text: 'Limpiar filtros', onclick: () => { activos.forEach(k => { state[k] = FILTROS[k][1]; const s = $(FILTROS[k][0]); if (s) s.value = FILTROS[k][1]; }); $('#f-score-v').textContent = '0'; render(); }})] : []));
}

function renderKpis(vids, cut) {
  const creators = new Set(vids.map(v => v.channel));
  const views = vids.reduce((a, v) => a + (v.views || 0), 0);
  const maxv = vids.reduce((a, v) => Math.max(a, v.velocity || 0), 0);
  const news = DATA.news.filter(n => new Date(n.published_at) >= cut).length;
  const alerts = DATA.alerts.filter(a => new Date(a.created_at) >= cut && ['critical', 'high'].includes(a.severity)).length;
  const items = [[fmt(vids.length), `Vídeos (${state.period} h)`], [fmt(creators.size), 'Creadores activos'],
    [fmt(views), 'Vistas acumuladas'], [fmt(maxv), 'Vistas/hora (máx.)'], [fmt(news), 'Noticias en medios'],
    [fmt(alerts), 'Alertas altas o críticas']];
  $('#kpis').replaceChildren(...items.map(([v, l]) => el('div', {class: 'kpi'}, el('div', {class: 'v', text: v}), el('div', {class: 'l', text: l}))));
}

function renderVideos(vids) {
  const key = {score: v => v.score || 0, momentum: v => v.momentum || 0, velocity: v => v.velocity || 0,
    views: v => v.views || 0, recent: v => +new Date(v.published_at)}[state.sort];
  const list = [...vids].sort((a, b) => key(b) - key(a)).slice(0, 120);
  $('#vcount').textContent = `${vids.length} vídeos · mostrando ${list.length}`;
  if (!list.length) { $('#videos').replaceChildren(el('div', {class: 'empty', text: 'Nada con estos filtros. Prueba a ampliar el periodo o bajar el score mínimo.'})); return; }
  $('#videos').replaceChildren(...list.map(v => {
    const url = safeUrl(v.url), th = safeUrl(v.thumb);
    const badges = el('div', {class: 'badges'},
      v.content_type ? el('span', {class: 'b', text: TYPE[v.content_type] || v.content_type}) : null,
      ...(v.topics || []).map(t => el('span', {class: 'b', text: TOPIC[t] || t})),
      v.risk ? el('span', {class: 'b ' + RISK[v.risk][0], text: RISK[v.risk][1]}) : null,
      v.verification && VER[v.verification] ? el('span', {class: 'b ' + VER[v.verification][0], text: VER[v.verification][1]}) : null,
      v.is_short ? el('span', {class: 'b', text: 'Short'}) : null);
    const comps = [['Momentum', v.momentum], ['Engagement', v.engagement], ['Relevancia', v.relevance],
      ['Autoridad', v.authority], ['Novedad', v.novelty], ['Riesgo', v.risk_score]];
    const brk = el('details', {class: 'br'}, el('summary', {text: 'Desglose del score'}),
      el('div', {class: 'brk'}, ...comps.flatMap(([l, x]) => [el('span', {text: l}),
        el('div', {class: 'track'}, el('div', {class: 'fill', style: `width:${Math.max(0, Math.min(100, x || 0))}%`})),
        el('span', {text: x == null ? '—' : Math.round(x)})])),
      (v.claims || []).length ? el('div', {class: 'am', style: 'margin-top:6px'}, 'Afirma: ' + v.claims.join(' · ')) : null);
    return el('article', {class: 'vid', 'data-id': v.id, 'data-url': url || ''},
      url ? el('a', {href: url, target: '_blank', rel: 'noopener'}, th ? el('img', {class: 'thumb', src: th, alt: '', loading: 'lazy'}) : el('div', {class: 'thumb'})) : el('div', {class: 'thumb'}),
      el('div', {},
        el('div', {class: 'vt'}, url ? el('a', {href: url, target: '_blank', rel: 'noopener', text: v.title}) : v.title),
        el('div', {class: 'meta'}, el('span', {text: v.channel || '—'}),
          v.channel_subs != null ? el('span', {text: `${fmt(v.channel_subs)} subs`}) : null,
          el('span', {text: ago(v.published_at)}), v.language ? el('span', {text: v.language.toUpperCase()}) : null,
          v.found_via ? el('span', {text: 'vía ' + v.found_via}) : null),
        el('div', {class: 'metrics'}, el('span', {}, el('b', {text: fmt(v.velocity)}), ' vistas/h'),
          el('span', {}, el('b', {text: fmt(v.views)}), ' vistas'), el('span', {}, el('b', {text: fmt(v.likes)}), ' likes'),
          el('span', {}, el('b', {text: fmt(v.comments)}), ' coment.')),
        badges, v.summary ? el('div', {class: 'sum', text: v.summary}) : null, brk),
      el('div', {class: 'score'}, el('div', {class: 'n', text: v.score == null ? '—' : Math.round(v.score)}), el('div', {class: 't', text: 'score'})));
  }));
}

function renderTopics(vids) {
  const cur = {}, half = {}; const mid = Date.now() - state.period * 36e5 / 2;
  vids.forEach(v => (v.topics || []).forEach(t => { cur[t] = (cur[t] || 0) + 1; if (new Date(v.published_at) >= mid) half[t] = (half[t] || 0) + 1; }));
  const rows = Object.entries(cur).sort((a, b) => b[1] - a[1]).slice(0, 10);
  if (!rows.length) { $('#topics').replaceChildren(el('div', {class: 'empty', text: 'Sin datos en el periodo.'})); $('#topics-table').replaceChildren(); return; }
  const max = rows[0][1];
  $('#topics').replaceChildren(...rows.map(([t, n]) => {
    const recent = half[t] || 0, older = n - recent, g = (recent + 1) / (older + 1);
    const row = el('div', {class: 'hbar', role: 'button'},
      el('span', {class: 'lab', text: TOPIC[t] || t}),
      el('div', {}, el('div', {class: 'bar', style: `width:${(n / max * 100).toFixed(1)}%`})),
      el('span', {class: 'val'}, el('b', {text: n}), g >= 1.5 ? el('span', {class: 'up', text: ` ↑x${g.toFixed(1)}`}) : null));
    hover(row, `${n} vídeos`, `${TOPIC[t] || t} · ${recent} en la mitad más reciente del periodo`);
    row.addEventListener('click', () => { state.topic = state.topic === t ? '' : t; $('#f-topic').value = state.topic; render(); });
    return row;
  }));
  $('#topics-table').replaceChildren(el('table', {class: 'tbl'}, el('tr', {}, el('th', {text: 'Tema'}), el('th', {class: 'num', text: 'Vídeos'})),
    ...rows.map(([t, n]) => el('tr', {}, el('td', {text: TOPIC[t] || t}), el('td', {class: 'num', text: n})))));
}

function renderHourly(vids) {
  const H = state.period, now = new Date(); now.setMinutes(0, 0, 0);
  const buckets = [];
  for (let i = H - 1; i >= 0; i--) buckets.push({t: new Date(now - i * 36e5), n: 0});
  vids.forEach(v => { const d = new Date(v.published_at); d.setMinutes(0, 0, 0);
    const i = buckets.findIndex(b => +b.t === +d); if (i >= 0) buckets[i].n++; });
  const W = 340, Ht = 120, pad = {l: 26, r: 14, b: 18, t: 6}, iw = W - pad.l - pad.r, ih = Ht - pad.b - pad.t;
  const max = Math.max(1, ...buckets.map(b => b.n));
  const step = Math.max(1, Math.ceil(max / 3));
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', `0 0 ${W} ${Ht}`); svg.setAttribute('width', '100%');
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', 'Vídeos publicados por hora');
  const mk = (tag, a) => { const n = document.createElementNS(ns, tag); for (const k in a) n.setAttribute(k, a[k]); return n; };
  for (let y = 0; y <= max; y += step) { const yy = pad.t + ih - (y / max) * ih;
    svg.append(mk('line', {x1: pad.l, x2: W - pad.r, y1: yy, y2: yy, class: 'gridline'}));
    const tx = mk('text', {x: pad.l - 6, y: yy + 3, 'text-anchor': 'end'}); tx.textContent = y; svg.append(tx); }
  const bw = iw / buckets.length, gap = Math.min(2, bw * 0.3);
  buckets.forEach((b, i) => {
    const h = (b.n / max) * ih, x = pad.l + i * bw + gap / 2, w = Math.max(1, bw - gap), y = pad.t + ih - h;
    if (b.n > 0) {
      const r = Math.min(4, w / 2, h);
      const p = mk('path', {class: 'colbar', d: `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`});
      hover(p, `${b.n} vídeos`, b.t.toLocaleString('es-ES', {weekday: 'short', hour: '2-digit', minute: '2-digit'}));
      svg.append(p);
    }
    const every = H <= 6 ? 1 : H <= 24 ? 6 : 12;
    if (b.t.getHours() % every === 0) { const tx = mk('text', {x: x + w / 2, y: Ht - 4, 'text-anchor': 'middle'});
      tx.textContent = b.t.getHours() + 'h'; svg.append(tx); }
  });
  $('#hourly').replaceChildren(svg);
  $('#hourly-table').replaceChildren(el('table', {class: 'tbl'}, el('tr', {}, el('th', {text: 'Hora'}), el('th', {class: 'num', text: 'Vídeos'})),
    ...buckets.filter(b => b.n).map(b => el('tr', {}, el('td', {text: b.t.toLocaleString('es-ES', {day: '2-digit', hour: '2-digit', minute: '2-digit'})}), el('td', {class: 'num', text: b.n})))));
}

function renderAlerts(cut) {
  const SR = {critical: 3, high: 2, medium: 1, low: 0};
  const list = DATA.alerts.filter(a => new Date(a.created_at) >= cut)
    .sort((a, b) => (SR[b.severity] - SR[a.severity]) || (new Date(b.created_at) - new Date(a.created_at)));
  $('#acount').textContent = list.length ? `· ${list.length}` : '';
  if (!list.length) { $('#alerts').replaceChildren(el('div', {class: 'empty', text: 'Sin alertas en el periodo.'})); return; }
  $('#alerts').replaceChildren(...list.slice(0, 25).map(a => { const u = safeUrl(a.url);
    return el('div', {class: 'alert'}, el('span', {class: 'sev ' + a.severity, text: SEVL[a.severity] || a.severity}),
      el('div', {}, el('div', {class: 'at'}, u ? el('a', {href: u, target: '_blank', rel: 'noopener', text: a.title}) : a.title),
        el('div', {class: 'am', text: `${a.message || ''} · ${ago(a.created_at)}`}))); }));
}

function renderNews(cut) {
  const lg = state.lang;
  const list = DATA.news.filter(n => new Date(n.published_at) >= cut && (!lg || (lg === 'other' ? !['es', 'en'].includes(n.language) : n.language === lg)));
  if (!list.length) { $('#news').replaceChildren(el('div', {class: 'empty', text: 'Sin noticias en el periodo.'})); return; }
  $('#news').replaceChildren(...list.map(n => { const u = safeUrl(n.url);
    return el('div', {class: 'news'}, el('div', {class: 'vt'}, u ? el('a', {href: u, target: '_blank', rel: 'noopener', text: n.title}) : n.title),
      el('div', {class: 'meta'}, el('span', {text: n.source}), el('span', {text: ago(n.published_at)}),
        n.official ? el('span', {class: 'b s-info', text: 'Oficial'}) : null,
        n.verification && VER[n.verification] ? el('span', {class: 'b ' + VER[n.verification][0], text: VER[n.verification][1]}) : null),
      n.summary ? el('div', {class: 'sum', text: n.summary}) : null); }));
}

function renderStatic() {
  $('#chan').textContent = `${DATA.channel?.nombre || ''} · ${DATA.channel?.subtitulo || ''}`;
  $('#demo').hidden = !DATA.demo;
  $('#avisos-datos').replaceChildren(...(DATA.avisos_datos || []).map(m => el('div', {class: 'aviso-dato', text: m})));
  const upd = new Date(DATA.generated_at);
  $('#updated').replaceChildren('Actualizado ', el('b', {text: ago(DATA.generated_at)}));
  $('#updated').title = upd.toLocaleString('es-ES');
  const rel = new Date(DATA.release_date + 'T00:00:00'), d = (rel - Date.now()) / 36e5;
  $('#countdown').replaceChildren(...(d > 0 ? ['Lanzamiento en ', el('b', {text: `${Math.floor(d / 24)} d ${Math.floor(d % 24)} h`})]
    : ['GTA VI disponible · ', el('b', {text: `día ${Math.floor(-d / 24) + 1}`})]));
  // temas en el selector
  const ts = new Set(); DATA.videos.forEach(v => (v.topics || []).forEach(t => ts.add(t)));
  [...ts].sort((a, b) => (TOPIC[a] || a).localeCompare(TOPIC[b] || b)).forEach(t => $('#f-topic').append(el('option', {value: t, text: TOPIC[t] || t})));
  // creadores
  const cr = DATA.creators || [];
  $('#creators').replaceChildren(cr.length ? el('table', {class: 'tbl'},
    el('tr', {}, ...['Creador', 'Suscriptores', 'Vídeos GTA 6', 'Vistas', 'Vistas/h máx.', 'Mejor score'].map((h, i) => el('th', {class: i ? 'num' : '', text: h}))),
    ...cr.map(c => el('tr', {'data-id': c.id, 'data-oficial': c.is_official ? '1' : null}, el('td', {}, c.name || '—', c.is_official ? el('span', {class: 'b s-info', style: 'margin-left:6px', text: 'Oficial'}) : null),
      el('td', {class: 'num', text: fmt(c.subscribers)}), el('td', {class: 'num', text: c.n_videos}), el('td', {class: 'num', text: fmt(c.views)}),
      el('td', {class: 'num', text: fmt(c.max_velocity)}), el('td', {class: 'num', text: c.best_score == null ? '—' : Math.round(c.best_score)}))))
    : el('div', {class: 'empty', text: 'Aún no hay creadores.'}));
  const em = DATA.emerging || [];
  $('#emerging').replaceChildren(...(em.length ? em.slice(0, 8).map(c => el('div', {class: 'q'}, el('b', {text: c.name}),
    el('div', {class: 'am', text: `${fmt(c.subscribers)} subs · ${fmt(c.views)} vistas en vídeos de GTA 6 (x${((c.views || 0) / Math.max(1, c.subscribers || 1)).toFixed(1)})`})))
    : [el('div', {class: 'empty', text: 'Ningún creador pequeño despuntando ahora mismo.'})]));
  const cq = DATA.community_questions || {};
  const qs = cq.preguntas || [];
  $('#community').replaceChildren(...(qs.length ? [...qs.map(q => el('div', {class: 'q'}, q.pregunta,
    q.frecuencia ? el('span', {class: 'b', style: 'margin-left:6px', text: q.frecuencia}) : null)),
    ...(cq.opiniones || []).length ? [el('div', {class: 'am', style: 'margin-top:8px', text: 'Opiniones dominantes: ' + cq.opiniones.join(' · ')})] : []]
    : [el('div', {class: 'empty', text: 'Se rellena con el briefing diario.'})]));
  // briefing (markdown sencillo, sin HTML)
  $('#briefing').replaceChildren(...(DATA.briefing ? mdToNodes(DATA.briefing.markdown) : [el('div', {class: 'empty', text: 'Aún no hay briefing. Se genera una vez al día.'})]));
  const eps = DATA.episodes || [];
  $('#episodes').replaceChildren(...(eps.length ? eps.map(e => el('div', {class: 'news'},
    el('div', {class: 'vt', text: e.title}), el('div', {class: 'meta'}, el('span', {text: e.date}), el('span', {text: e.format}),
      e.youtube_id ? el('a', {href: `https://studio.youtube.com/video/${encodeURIComponent(e.youtube_id)}/edit`, target: '_blank', rel: 'noopener', text: 'Abrir en YouTube Studio'}) : null)))
    : [el('div', {class: 'empty', text: 'Todavía no se ha publicado ningún episodio.'})]));
}

function renderOportunidades() {
  const O = DATA.oportunidades || {};
  const link = (u, text) => safeUrl(u) ? el('a', {href: safeUrl(u), target: '_blank', rel: 'noopener', text}) : text;
  const empty = t => el('div', {class: 'empty', text: t});
  const tbl = (heads, rows) => el('div', {class: 'tblwrap'}, el('table', {class: 'tbl'},
    el('tr', {}, ...heads.map((h, i) => el('th', {class: i ? 'num' : '', text: h}))), ...rows));
  const ideas = O.ideas || [];
  const temas = O.temas || [];
  $('#oportunidades').replaceChildren(
    el('h3', {text: 'Ideas para hoy'}),
    O.ideas_fecha ? el('div', {class: 'hint', text: `Generadas con IA el ${O.ideas_fecha} a partir de los datos del Radar. Contenido propio: nada de clips ajenos.`}) : null,
    ideas.length ? el('div', {class: 'ideas'}, ...ideas.map(i => el('div', {class: 'idea', 'data-titulo': i.titulo},
      el('div', {class: 'badges'}, el('span', {class: 'b s-info', text: i.formato === 'episodio' ? 'Episodio' : 'Short'}),
        i.tema ? el('span', {class: 'b', text: TOPIC[i.tema] || i.tema}) : null),
      el('div', {class: 'vt', text: i.titulo}), el('div', {class: 'am', text: i.por_que || ''}))))
      : empty('Se generan una vez al día con el briefing.'),

    el('h3', {text: 'Temas con hueco'}),
    el('div', {class: 'hint', text: 'Mucha demanda (vistas/hora en 48 h) y pocos vídeos en español. 100 = el mayor hueco ahora mismo.'}),
    temas.length ? el('div', {}, ...temas.map(t => { const row = el('div', {class: 'gap', 'data-titulo': `${t.label}: lo que nadie cuenta en español`, 'data-url': t.url || ''},
      el('div', {}, el('div', {class: 'vt', text: t.label}),
        el('div', {class: 'am'}, `${fmt(t.demanda)} vistas/h · ${t.videos} vídeos (${t.videos_es} en español) · ej.: `, link(t.url, t.ejemplo))),
      el('div', {class: 'track'}, el('div', {class: 'fill', style: `width:${t.hueco}%`})),
      el('div', {class: 'n', text: t.hueco}));
      hover(row, `Hueco ${t.hueco}/100`, `${t.label} · ${fmt(t.demanda)} vistas/h · ${t.videos_es} vídeos en español`); return row; }))
      : empty('Aún no hay datos suficientes.'),

    el('h3', {text: 'Formatos que funcionan'}),
    (O.formatos || []).length ? tbl(['Tipo', 'Formato', 'Vídeos', 'Vistas/h media'], O.formatos.map(f => el('tr', {},
      el('td', {text: TYPE[f.tipo] || f.tipo}), el('td', {class: 'num', text: f.formato}), el('td', {class: 'num', text: f.videos}),
      el('td', {class: 'num', text: fmt(f.vel_media)})))) : empty('Aún no hay datos suficientes.'),
    (O.duracion || []).length ? tbl(['Duración', 'Vídeos', 'Vistas/h media'], O.duracion.map(d => el('tr', {},
      el('td', {text: d.tramo}), el('td', {class: 'num', text: d.videos}), el('td', {class: 'num', text: fmt(d.vel_media)})))) : null,

    el('h3', {text: 'Títulos que rinden por encima de lo normal'}),
    el('div', {class: 'hint', text: 'Vistas/hora corregidas por el tamaño del canal. Para inspirarte en el ángulo, no para copiar.'}),
    (O.titulos || []).length ? el('div', {}, ...O.titulos.map(t => el('div', {class: 'news'},
      el('div', {class: 'vt'}, link(t.url, t.title)),
      el('div', {class: 'meta'}, el('span', {class: 'xbadge', text: `x${t.x} sobre lo normal`}), el('span', {text: t.channel || '—'}),
        el('span', {text: `${fmt(t.subs)} subs`}), el('span', {text: `${fmt(t.velocity)} vistas/h`}), t.is_short ? el('span', {class: 'b', text: 'Short'}) : null))))
      : empty('Aún no hay datos suficientes.'),

    el('h3', {text: `Creadores a seguir · ${O.vigilados || 0} de ${O.max_vigilados || 200} canales vigilados por el Radar`}),
    (O.creadores || []).length ? tbl(['Creador', 'Suscriptores', 'Vídeos (48 h)', 'Vistas/h máx.', 'Rendimiento'],
      O.creadores.map(c => el('tr', {}, el('td', {}, link(c.url, c.name || '—'),
        c.vigilado ? el('span', {class: 'b s-good', style: 'margin-left:6px', text: 'Vigilado'}) : null),
        el('td', {class: 'num', text: fmt(c.subs)}), el('td', {class: 'num', text: c.videos}),
        el('td', {class: 'num', text: fmt(c.vel_max)}), el('td', {class: 'num'}, el('span', {class: 'xbadge', text: `x${c.x}`})))))
      : empty('Aún no hay creadores.'));
}

function inline(text) {
  const out = []; const re = /\*\*(.+?)\*\*|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/[^\s)]+)/g; let m, last = 0;
  while ((m = re.exec(text))) { if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1]) out.push(el('b', {text: m[1]})); else if (m[2]) out.push(el('a', {href: m[3], target: '_blank', rel: 'noopener', text: m[2]}));
    else out.push(el('a', {href: m[4], target: '_blank', rel: 'noopener', text: m[4]})); last = re.lastIndex; }
  if (last < text.length) out.push(text.slice(last)); return out;
}
function mdToNodes(md) {
  const nodes = []; let list = null;
  for (const raw of (md || '').split('\n')) { const line = raw.trimEnd();
    const h = line.match(/^#{1,4}\s+(.*)/), li = line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)/);
    if (li) { if (!list) { list = el('ul'); nodes.push(list); } list.append(el('li', {}, ...inline(li[1]))); continue; }
    list = null;
    if (h) nodes.push(el('h3', {}, ...inline(h[1]))); else if (line.trim()) nodes.push(el('p', {}, ...inline(line))); }
  return nodes;
}

// ---------- eventos
document.querySelectorAll('#f-period button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#f-period button').forEach(x => x.setAttribute('aria-pressed', x === b));
  state.period = +b.dataset.v; render(); }));
[['#f-lang', 'lang'], ['#f-fmt', 'fmt'], ['#f-topic', 'topic'], ['#f-risk', 'risk'], ['#sort', 'sort']].forEach(([s, k]) =>
  $(s).addEventListener('change', e => { state[k] = e.target.value; render(); }));
$('#f-score').addEventListener('input', e => { state.score = +e.target.value; $('#f-score-v').textContent = e.target.value; render(); });
$('#f-q').addEventListener('input', e => { state.q = e.target.value; render(); });
document.querySelectorAll('[role=tab]').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('[role=tab]').forEach(x => x.setAttribute('aria-selected', x === t));
  document.querySelectorAll('[data-panel]').forEach(p => p.hidden = p.dataset.panel !== t.dataset.tab); }));

$('#csv').addEventListener('click', () => {
  const cols = ['title', 'channel', 'url', 'published_at', 'views', 'velocity', 'likes', 'comments', 'score', 'momentum',
    'content_type', 'topics', 'risk', 'verification', 'summary'];
  const esc = x => `"${String(Array.isArray(x) ? x.join(' | ') : x ?? '').replace(/"/g, '""')}"`;
  const rows = [cols.join(',')].concat(filtered().map(v => cols.map(c => esc(v[c])).join(',')));
  const a = el('a', {href: URL.createObjectURL(new Blob(['\ufeff' + rows.join('\n')], {type: 'text/csv'})),
    download: `gta6-radar-${new Date().toISOString().slice(0, 10)}.csv`});
  document.body.append(a); a.click(); a.remove();
});
// ---------- estudio (solo aparece si el panel lo sirve el Estudio: python -m estudio)
const FAB = {variantes: {}, plataformas: {}, ultimo: '', abiertos: new Set(), grabando: null};
const ETAPAS = ['Brief', 'Guion', 'Montaje', 'Revisión', 'Exportación'];
async function api(path, body) {
  const r = await fetch(path, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : {});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
  return data;
}
function showTab(name) {
  document.querySelectorAll('[role=tab]').forEach(x => x.setAttribute('aria-selected', x.dataset.tab === name));
  document.querySelectorAll('[data-panel]').forEach(p => p.hidden = p.dataset.panel !== name);
}
function boton(texto, fn, pri) {
  const b = el('button', {class: 'btn' + (pri ? ' pri' : ''), type: 'button', text: texto});
  b.addEventListener('click', async () => { b.disabled = true;
    try { await fn(); } catch (e) { alert(e.message); } finally { b.disabled = false; await fabPiezas(true); } });
  return b;
}
async function fabIdeas() {
  const d = await api('/api/ideas');
  FAB.variantes = d.variantes; FAB.plataformas = d.plataformas;
  $('#fab-info').textContent = (d.demo ? 'Ideas de DEMOSTRACIÓN (datos inventados) · ' : '') + `los vídeos se exportan a ${d.carpeta}`;
  $('#fab-ideas').replaceChildren(...(d.ideas.length ? d.ideas.map(i => {
    const sel = el('select', {'aria-label': 'Formato'}, ...Object.entries(FAB.variantes).map(([k, [f, n]]) => el('option', {value: k, text: `${f} · ${n}`})));
    sel.value = i.variante;
    const checks = Object.entries(FAB.plataformas).map(([k, v]) => { const c = el('input', {type: 'checkbox', value: k});
      c.checked = i.plataformas.includes(k); return [c, el('label', {class: 'chk'}, c, v)]; });
    const link = (i.fuentes || [])[0];
    return el('div', {class: 'fab-idea'},
      el('div', {class: 'badges'}, el('span', {class: 'b ' + (i.demo ? 's-warn' : 's-info'), text: i.origen})),
      el('div', {class: 'vt', text: i.titulo}), el('div', {class: 'am', text: i.por_que}),
      link && safeUrl(link.url) ? el('a', {class: 'am', href: safeUrl(link.url), target: '_blank', rel: 'noopener', text: 'Ver la señal ↗'}) : null,
      el('div', {class: 'row'}, sel, ...checks.map(([, l]) => l)),
      el('div', {class: 'row'},
        boton('Enviar al Estudio', async () => { await api('/api/enviar', {idea_id: i.id, variante: sel.value,
          plataformas: checks.filter(([c]) => c.checked).map(([c]) => c.value)}); }, true),
        boton('Descartar…', async () => { const m = prompt('¿Por qué la descartas? (sirve para aprender)');
          if (m) { await api('/api/descartar-idea', {idea_id: i.id, motivo: m}); await fabIdeas(); } })));
  }) : [el('div', {class: 'empty', text: 'No hay ideas ahora mismo. Descarga los datos del Radar o añade una a mano.'})]));
}
function pasos(p) {
  const i = ETAPAS.indexOf(p.etapa === 'Publicado' ? 'Exportación' : p.etapa);
  return el('ol', {class: 'steps', 'aria-label': 'Etapas'}, ...ETAPAS.map((e, j) =>
    el('li', {class: j < i || p.etapa === 'Publicado' ? 'hecho' : j === i ? 'aqui' : '', 'aria-current': j === i ? 'step' : null, text: e})));
}
function guionDetalle(p, cont) {
  const det = el('details', {class: 'gu'}, el('summary', {text: 'Ver el guion completo'}));
  if (FAB.abiertos.has(p.id)) det.open = true;
  det.addEventListener('toggle', async () => {
    if (!det.open) { FAB.abiertos.delete(p.id); return; }
    FAB.abiertos.add(p.id);
    if (det.dataset.cargado) return;
    const d = await api(`/api/piezas/${p.id}`); const g = d.guion.contenido; det.dataset.cargado = 1;
    if (!g) return;
    det.append(el('div', {class: 'am'}, 'Ganchos: ', ...g.ganchos.map((x, k) => el('span', {class: 'b' + (k === g.gancho_elegido ? ' s-good' : ''), style: 'margin:2px', text: x}))),
      ...g.escenas.map(e => el('div', {class: 'esc'}, el('span', {class: 'who', text: e.voz === 'leo' ? 'Leo' : 'Sofi'}), e.texto,
        e.en_pantalla ? el('div', {class: 'pan', text: 'En pantalla: ' + e.en_pantalla}) : null,
        (e.afirmaciones || []).length ? el('ul', {}, ...e.afirmaciones.map(a => el('li', {class: 'af'}, `[${a.etiqueta}] ${a.texto} · `,
          safeUrl(a.fuente) ? el('a', {href: safeUrl(a.fuente), target: '_blank', rel: 'noopener', text: 'fuente'}) : 'sin fuente', ` · ${a.fecha}`))) : null)),
      el('div', {class: 'am', style: 'margin-top:6px', text: 'Cierre: ' + (g.cierre || '—')}));
  });
  cont.append(det);
}
function piezaCard(p) {
  const c = el('article', {class: 'pieza'});
  const titulo = p.idea.titulo || p.id;
  c.append(el('div', {class: 'vt', text: titulo}),
    el('div', {class: 'meta'}, el('span', {text: `${p.formato} · ${p.variante_nombre}`}),
      el('span', {text: p.plataformas.map(x => FAB.plataformas[x] || x).join(' + ')}), el('span', {text: `encargo ${p.id}`}),
      p.legado ? el('span', {class: 'b', text: 'antes del flujo de aprobación'}) : null,
      p.idea.investigacion_id ? el('a', {class: 'b s-info', href: '#/investigar/investigaciones/' + p.idea.investigacion_id,
        text: `viene de una investigación · dossier v${p.idea.dossier_n}`}) : null),
    pasos(p), el('div', {class: 'sig'}, el('b', {text: p.etapa + ': '}), p.siguiente),
    p.fecha_prevista ? el('div', {class: 'am', text: '📅 Prevista para el ' + new Date(p.fecha_prevista + 'T12:00:00').toLocaleDateString('es-ES', {weekday: 'long', day: 'numeric', month: 'long'}) + ' (tu planificación: no se publica sola)'}) : '');
  const acciones = el('div', {class: 'row'});
  const v = p.version;
  if (p.etapa === 'Brief') acciones.append(boton('Aprobar idea', () => api(`/api/piezas/${p.id}/aprobar`, {tipo: 'idea'}), true));
  if (p.etapa === 'Guion') {
    if (p.guion.estado === 'falta') {
      const frase = `Escribe el guion del encargo ${p.id}`;
      c.append(el('div', {class: 'ask'}, 'Pídeselo a Claude en el chat:', el('code', {text: frase}),
        boton('Copiar', () => navigator.clipboard.writeText(frase))));
    }
    if (p.guion.errores.length) c.append(el('div', {class: 'err'}, 'El guion no es válido:', el('ul', {}, ...p.guion.errores.map(x => el('li', {text: x})))));
    if (p.guion.estado === 'valido') acciones.append(boton('Aprobar guion', () => api(`/api/piezas/${p.id}/aprobar`, {tipo: 'guion'}), true));
  }
  if ((p.guion.avisos || []).length) c.append(el('div', {class: 'am', text: 'Avisos: ' + p.guion.avisos.join(' · ')}));
  if (p.guion.estado === 'valido') guionDetalle(p, c);
  if (p.aprobado.guion && ['Montaje', 'Revisión'].includes(p.etapa)) c.append(opcionesPieza(p));
  if (p.etapa === 'Montaje') {
    const enMarcha = v && ['pendiente', 'en_curso'].includes(v.estado_produccion) && v.clave === p.clave;
    const faltanTomas = (p.opciones || {}).voz === 'propia' && (p.tomas || []).some(x => !x.valida);
    if (!enMarcha && !faltanTomas && !(v && v.estado_produccion === 'fallido' && v.clave === p.clave))
      acciones.append(boton('Crear vídeo', () => api(`/api/piezas/${p.id}/crear`, {}), true));
    if (v && v.estado_produccion === 'fallido') acciones.append(boton(`Reintentar (${v.intentos}/3)`, () => api(`/api/piezas/${p.id}/reintentar`, {}), true));
    if (v && v.estado_produccion === 'pendiente') acciones.append(boton('Cancelar', () => api(`/api/piezas/${p.id}/cancelar`, {})));
  }
  if (['Revisión', 'Exportación', 'Publicado'].includes(p.etapa) && v && v.video && !p.legado) {
    const q = v.calidad || {};
    c.append(el('div', {class: 'rev'},
      el('video', {src: `/media/${v.id}.mp4`, controls: '', preload: 'metadata', playsinline: ''}),
      el('div', {}, el('div', {class: 'am', text: `Versión ${v.n} · ${Math.round(v.duracion || 0)} s`}),
        el('div', {class: 'am', text: `Voz: ${(v.opciones || {}).voz === 'propia' ? 'la tuya' : 'Leo y Sofi (sintética)'} · Fondo: ${
          (v.opciones || {}).fondo_usado === 'video' ? 'vídeo real' : 'gráfico'}${(v.opciones || {}).fondo_motivo && (v.opciones || {}).fondo_usado !== 'video' ? ' (' + v.opciones.fondo_motivo + ')' : ''}`}),
        ...Object.entries(q).map(([pl, r]) => el('div', {class: 'am'}, `${FAB.plataformas[pl] || pl}: `,
          el('span', {class: r.ok ? 'ok' : 'bad', text: r.ok ? '✓ control de calidad' : '✗ ' + r.fallos.join(' · ')}))),
        ...p.cambios.filter(x => x.version_n).map(x => el('div', {class: 'am', text: `Cambios pedidos (v${x.version_n}): ${x.nota}`})))));
  }
  if (p.etapa === 'Revisión') acciones.append(
    boton('Aprobar vídeo', () => api(`/api/piezas/${p.id}/aprobar`, {tipo: 'video'}), true),
    boton('Pedir cambios…', async () => { const n = prompt('¿Qué hay que cambiar?'); if (n) await api(`/api/piezas/${p.id}/cambios`, {nota: n}); }));
  if (['Exportación', 'Publicado'].includes(p.etapa)) {
    const ex = p.exportacion || {};
    if (!p.legado && p.plataformas.some(pl => !(ex[pl] || {}).disponible))
      acciones.append(boton('Exportar a ' + p.plataformas.map(x => FAB.plataformas[x]).join(' y '), () => api(`/api/piezas/${p.id}/exportar`, {}), true));
    p.plataformas.forEach(pl => { const e = ex[pl]; if (!e) return;
      c.append(el('div', {class: 'am'}, `${FAB.plataformas[pl]}: `,
        el('span', {class: e.disponible ? 'ok' : 'bad', text: e.disponible ? (p.legado ? '✓ en la carpeta del Mac' : '✓ Disponible en el Mac (hash comprobado)') : '✗ ' + e.motivo}),
        e.subida_en ? el('span', {}, ' · subido ', safeUrl(e.url) ? el('a', {href: safeUrl(e.url), target: '_blank', rel: 'noopener', text: 'ver'}) : '',
          ' · ', el('a', {href: '#/canal/estadisticas', text: 'Registrar métricas', onclick: () => { window.PC_MEDIR = {plataforma: pl, url: e.url}; }})) :
          (e.disponible && !p.legado ? boton('Marcar subido…', async () => { const u = prompt(`URL del vídeo publicado en ${FAB.plataformas[pl]}`);
            if (u) await api(`/api/piezas/${p.id}/subido`, {plataforma: pl, url: u}); }) : null))); });
    if (Object.values(ex).some(e => e.disponible)) acciones.append(boton('Abrir en el Finder', () => api('/api/abrir-carpeta', {pieza: p.id})));
  }
  if (!['Publicado', 'Descartada'].includes(p.etapa))
    acciones.append(boton(p.fecha_prevista ? 'Cambiar fecha…' : 'Programar…', async () => {
      const f = prompt('Fecha prevista de publicación (AAAA-MM-DD). Vacío para quitarla. Es solo tu planificación: no publica nada.', p.fecha_prevista || '');
      if (f !== null) await api(`/api/piezas/${p.id}/programar`, {fecha: f.trim()}); }));
  if (!['Exportación', 'Publicado', 'Descartada'].includes(p.etapa))
    acciones.append(boton('Descartar…', async () => { const m = prompt('¿Por qué la descartas?'); if (m) await api(`/api/piezas/${p.id}/descartar`, {motivo: m}); }));
  c.append(acciones);
  return c;
}
function opcionesPieza(p) {
  const op = p.opciones || {};
  const sel = (nombre, valor, opciones) => { const s = el('select', {'aria-label': nombre},
      ...opciones.map(([v, t]) => el('option', {value: v, text: t}))); s.value = valor;
    s.addEventListener('change', async () => { try { await api(`/api/piezas/${p.id}/opciones`, {[nombre]: s.value}); }
      catch (e) { alert(e.message); } await fabPiezas(true); }); return s; };
  const caja = el('div', {class: 'fab-idea', style: 'margin:8px 0'},
    el('div', {class: 'row'}, el('label', {class: 'am'}, 'Fondo ', sel('fondo', op.fondo, [['video', 'Vídeo real (Miami / Florida)'], ['grafico', 'Gráfico']])),
      el('label', {class: 'am'}, 'Voz ', sel('voz', op.voz, [['propia', 'La mía (grabar)'], ['sintetica', 'Leo y Sofi (sintética)']]))));
  if (op.voz === 'propia' && (p.tomas || []).length) {
    const hechas = p.tomas.filter(x => x.valida).length;
    caja.append(el('div', {class: 'am', text: `Tu voz: ${hechas} de ${p.tomas.length} escenas grabadas. Lee el texto tal cual, con naturalidad; puedes repetir cada una.`}));
    p.tomas.forEach(x => {
      const grab = el('button', {class: 'btn' + (x.valida ? '' : ' pri'), type: 'button', text: x.valida ? 'Repetir' : '● Grabar'});
      grab.addEventListener('click', () => grabarToma(p.id, x.escena, grab));
      const oir = x.grabada ? el('button', {class: 'btn', type: 'button', text: '▶ Escuchar'}) : null;
      if (oir) oir.addEventListener('click', () => new Audio(`/media/toma/${p.id}/${x.escena}.wav?${Date.now()}`).play());
      caja.append(el('div', {class: 'esc'},
        el('span', {class: 'who', text: `${x.escena + 1}.`}), x.texto,
        el('div', {class: 'row', style: 'margin-top:4px'}, grab, oir,
          el('span', {class: x.valida ? 'ok am' : 'am', text: x.valida ? `✓ ${x.duracion} s` : (x.aviso || 'Sin grabar')}))));
    });
  }
  return caja;
}
async function grabarToma(id, n, boton) {
  if (FAB.grabando) {  // segundo clic: parar
    if (FAB.grabando.boton === boton) FAB.grabando.rec.stop();
    return;
  }
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({audio: true}); }
  catch { alert('No hay permiso para usar el micrófono. Permítelo en el navegador y vuelve a intentarlo.'); return; }
  const rec = new MediaRecorder(stream); const trozos = [];
  rec.ondataavailable = e => e.data.size && trozos.push(e.data);
  rec.onstop = async () => {
    stream.getTracks().forEach(tr => tr.stop());
    const blob = new Blob(trozos, {type: rec.mimeType || 'audio/webm'});
    boton.textContent = 'Guardando…';
    try {
      const r = await fetch(`/api/piezas/${id}/voz/${n}`, {method: 'POST', headers: {'Content-Type': blob.type}, body: blob});
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.error || `Error ${r.status}`);
    } catch (e) { alert(e.message); }
    FAB.grabando = null; await fabPiezas(true);
  };
  FAB.grabando = {rec, boton}; rec.start(); boton.textContent = '■ Parar'; boton.classList.add('pri');
}
async function fabPiezas(forzar) {
  if (FAB.grabando && !forzar) return;  // no repintar mientras grabas
  const d = await api('/api/piezas');
  const firma = JSON.stringify(d.piezas);
  if (!forzar && firma === FAB.ultimo) return;   // no repintar si nada cambió (no corta el vídeo)
  FAB.ultimo = firma;
  $('#fab-piezas').replaceChildren(...(d.piezas.length ? d.piezas.map(piezaCard)
    : [el('div', {class: 'empty', text: 'Aún no hay piezas. Elige una idea abajo y pulsa «Enviar al Estudio».'})]));
}
async function initFabrica() {
  if (!/^https?:$/.test(location.protocol)) return;
  try { await fabIdeas(); } catch { return; }  // sin Estudio (GitHub Pages o archivo): sus secciones muestran el aviso
  window.PC_ESTUDIO = true;
  document.body.classList.add('con-estudio');
  window.dispatchEvent(new Event('estudio-listo'));
  $('#fab-carpeta').addEventListener('click', () => api('/api/abrir-carpeta', {}));
  $('#fab-mano').addEventListener('click', () => { $('#fab-mano-form').hidden = !$('#fab-mano-form').hidden; });
  $('#fab-mano-form').addEventListener('submit', async e => { e.preventDefault();
    try { await api('/api/enviar', {a_mano: true, titulo: $('#mano-titulo').value, por_que: $('#mano-porque').value, variante: 'ultima_hora', plataformas: ['tiktok', 'shorts']});
      e.target.reset(); e.target.hidden = true; await fabPiezas(true); } catch (err) { alert(err.message); } });
  await fabPiezas(true);
  setInterval(() => fabPiezas(false).catch(() => {}), 3000);
}

function arrancarPanel() { renderStatic(); renderOportunidades(); render(); initFabrica(); }

# Estado del proyecto — Punto de Control

Última actualización: 16-nov-2026 (Claude Code). Documentos: `docs/megaprompt-claude-code.md` (manda),
`docs/principios-producto.md`, `docs/plan-v2.md` (reconstruido del PDF; la versión anterior se sobrescribió por error).

## Novedades del 17-nov-2026

### Vídeo real de fondo + tu voz — HECHO Y PROBADO (con clips y tomas simulados)
- Por pieza se elige **fondo** (vídeo real | gráfico) y **voz** (la tuya | Leo y Sofi). Por defecto: vídeo real + tu voz.
- Fondo: Pexels (`PEXELS_API_KEY` en `.env`) o clips propios en `assets/broll/`; filtro que excluye «GTA», «Rockstar»,
  «gameplay»…; créditos (autor, URL, licencia) en el manifiesto y en los textos. Sin clave ni clips → fondo gráfico y
  se explica el motivo en la revisión.
- Tu voz: grabación por escena desde el navegador (micrófono), con Escuchar y Repetir; cada toma va ligada al texto exacto.
  «Crear vídeo» solo aparece con todas las tomas válidas. Regrabar, cambiar el texto, el fondo o la voz anula la
  aprobación del vídeo (clave de render por versión).
- Aviso de contenido sintético según la voz (`exportar.py`); `upload.py` acepta `sintetico=`.
- Pruebas: `tests/test_broll_voz.py` (5) + corte 1 (8) = 13 en verde. Recorrido en navegador: tomas subidas por la
  misma ruta que el micrófono, vídeo creado y revisado.
- **No probado todavía:** descarga real de Pexels (falta la clave de Javier) y grabación real con micrófono (la hace Javier).
- Limitación: con tu voz, los tiempos de los subtítulos son proporcionales dentro de cada toma (aproximados).

### Rediseño del panel — fase 1A HECHA Y PROBADA (17-nov)
- Panel dividido en `radar/panel/` (base.css, app.css, radar.js, util.js, graficas.js, hoy.js, nav.js);
  `radar/dashboard.py` los une en un único `index.html` (sin compilación nueva; funciona sin internet y en Pages).
  Comprobado: con los mismos datos, la división dio un HTML idéntico byte a byte antes de cambiar la navegación.
- Barra lateral con el menú integrado (Inicio · Investigar · Mi canal · Crear · Sistema), rutas `#/grupo/seccion`
  con atrás/adelante, grupos y barra contraída recordados (solo preferencias en el navegador), menú móvil con Esc,
  velo y foco atrapado/restaurado. Secciones aún no construidas aparecen como «fase 1B/2/3», no son enlaces.
- Correspondencia de lo anterior: Radar de contenido → Investigar › Vídeos; Medios → Noticias y fuentes;
  Oportunidades → Temas y tendencias; Creadores → Creadores y canales; Briefing → tarjeta en Inicio › Hoy;
  Alertas y comunidad → Inicio › Alertas; Estudio → Crear › Fábrica de ideas + En producción; Episodios → Crear ›
  Episodios y archivos; nuevas: Sistema › Automatizaciones y ejecuciones, Sistema › Configuración (estado de datos y
  conexiones sin mostrar valores).
- Hoy: 3 gráficas SVG propias (7/30/90 días; tooltip; teclado ←/→/Inicio/Fin/Intro; toque abre detalle; detalle del
  día conservando periodo, métrica y series; leyenda para ocultar series; hoy vs ayer con «Sin comparación» y sin
  porcentajes cuando ayer es 0; huecos sombreados, nunca 0) + resumen operativo con enlaces.
  - Radar: selector de métrica (publicados | detectados | máx. vistas/hora), nunca dos unidades en un eje.
  - Mi canal: vacío explicado (no hay métricas reales); demo marcada en la base demo.
  - Producción: REAL en el Estudio (eventos de `data/estudio.db`, con aviso de reconstruidos); en la web pública
    se explica que es privada.
- Probado: `tests/test_series.py` (4) + 13 anteriores = 17 en verde; navegador en escritorio y móvil (375 px,
  sin scroll horizontal), consola sin errores, rutas, atrás/adelante, Esc, foco, leyendas, detalle, comparaciones
  sin NaN/Infinity, todas las vistas antiguas con su contenido.
- Limitación: abierto como archivo (vista previa `data:`) el navegador bloquea la memoria de preferencias; el panel
  funciona igual con los valores por defecto.

### Centro de investigación — fase 1B HECHA Y PROBADA (17-nov)
- Solo en el Estudio (privado, `data/estudio.db`; tablas referencias, investigaciones, inv_refs, notas). En la web
  pública cada sección muestra el aviso «funciona en el Estudio de tu Mac» y no hay controles que guarden nada.
- **Buscador** (`estudio/busqueda.py`): busca en lo YA recopilado (noticias, vídeos, creadores, briefings y tus
  guardados, notas e investigaciones), sin tildes, con filtros (tipo, periodo, fuente, idioma, tema, verificación),
  chips para quitarlos y coincidencias marcadas. Índice FTS5 en `data/busqueda.db` (se regenera solo; borrarlo no
  pierde nada). NO consulta internet: los botones «Google ↗ / YouTube ↗» abren otra pestaña y lo dicen.
- **Noticias y fuentes**: Últimas / Sin leer / Guardadas, por fuente y tema; marcar leída, guardar, nota, añadir a
  investigación. Se distingue extracto del medio y resumen generado.
- **Vídeos**: cada vídeo del explorador tiene Guardar, Nota y Añadir a investigación.
- **Biblioteca**: filtros, nota y etiquetas, archivar, eliminar (con confirmación y aviso de en cuántas investigaciones
  está), enlaces manuales. Se guarda una copia de lo que viste: si el Radar borra el original, la referencia sigue.
- **Mis investigaciones**: crear, estado, Resumen (qué sé / qué falta / conclusión), Fuentes (qué aporta, quitar sin
  borrar de la biblioteca), Notas (apunte, pregunta, idea, enfoque). Afirmaciones, Cronología y Dossier: fase 2.
- **Inicio › Continuar investigando**: investigaciones activas y lo guardado hace poco.
- Probado: `tests/test_investigacion.py` (4) + 17 anteriores = 21 en verde; navegador (Estudio aislado) en escritorio y
  móvil: buscar, guardar, crear investigación desde un resultado, leída/sin leer, acciones en 28/28 vídeos, resumen,
  notas, continuar. Corregido de paso: la miga de pan repetía la sección.
- Limitación: los avisos usan las ventanas del navegador (prompt/confirm); quedan bien pero son sencillas.

### Centro de investigación — fase 2A HECHA Y PROBADA (17-nov)
- **Afirmaciones** (`estudio/verificacion.py`): la unidad es la afirmación concreta. Evidencias a favor / en contra /
  solo repite (las que repiten nunca cuentan como independientes). 6 estados manuales, sin puntuación de «verdad».
  «Confirmado» exige una evidencia a favor independiente y una nota; «Contradicho», una evidencia en contra y una
  nota. Historial que solo se añade. Pestaña en cada investigación + **Investigar › Rumores y verificación**
  (filtros; «revisión antigua» a los 7 días).
- **Cronología**: tres fechas (ocurrió / publicado / detectado), nunca inventadas. Eventos automáticos al añadir una
  fuente, crear una afirmación, confirmarla o contradecirla y cambiar el estado de la investigación (se ocultan, no se
  borran); manuales editables. Pestaña + **Investigar › Cronología** con filtros. Las fuentes añadidas antes de la 2A
  no tienen evento (no se reconstruyen fechas que no se registraron).
- **Dossier** (`estudio/dossier.py`): generado por código, sin IA. Afirmaciones por estado con su etiqueta del guion
  (Confirmado→CONFIRMADO, Atribuida→REPORTADO, resto→RUMOR, Contradicho→no se afirma salvo «Verdad o bulo»),
  incertidumbres aparte, fuentes y cronología. Versiones congeladas, Copiar Markdown y Descargar .md.
  **Crear › Guiones y dossiers** lista los dossiers y sus piezas.
- **Paso a la Fábrica**: «Crear idea de vídeo» desde una versión del dossier; muestra antes lo que recibirá el guion.
  La pieza entra en la etapa Idea (no se aprueba ni publica nada) con investigación y dossier en la idea; no se duplica.
  `python -m fabrica.encargo <id>` imprime el dossier (etiquetas, fuentes, «NO AFIRMAR»). La tarjeta de la pieza
  enlaza a su investigación. El buscador también encuentra afirmaciones y dossiers.
- Probado: `tests/test_verificacion.py` (4) + 21 anteriores = 25 en verde; navegador (Estudio aislado) en escritorio y
  móvil sin scroll horizontal: crear afirmación, bloqueo de Confirmado sin evidencia, evidencia, confirmar,
  cronología, dossier, crear idea, pieza en En producción con su origen.

### Mi canal — fase 2B HECHA Y PROBADA (17-nov)
- Una sola fuente de verdad (`estudio/canal.py`, privado): `mis_videos` + `mediciones` (siempre ACUMULADAS desde la
  publicación; vacío ≠ 0; sin duplicados por vídeo y minuto; una bajada pide confirmación) + `medicion_log` (altas,
  correcciones y borrados). Al marcar una pieza como subida, el vídeo entra solo en Mis vídeos.
- Fórmulas en la cabecera de `estudio/canal.py`: vistas del día = diferencia entre mediciones, al día de la posterior
  («acumula N días», sin repartir); vistas a 48 h solo con medición entre 40 y 56 h (sin interpolar); índice a 48 h
  = ÷ mediana de las 20 piezas anteriores de la plataforma (si no, «historial insuficiente»); retención de grupo solo
  con duraciones a ±25 %; ingresos/costes no se muestran (no hay registro). Días en Europe/Madrid.
- **Mi canal › Estadísticas**: formulario rápido (TikTok/Shorts/YouTube, todo opcional, unidades, errores junto al
  campo), comparación 7/28 días con cobertura, gráfica diaria, desgloses por plataforma y formato, tabla ordenable
  con Corregir y Borrar. **Lo que más rinde** (tema, formato, serie, colaboración; «pocos datos» < 5; sin ganador),
  **Mis vídeos** (48 h e índice con su fórmula), **Colaboradores** (destacados y emergentes con criterio visible,
  posibles, guardados con estado y nota; no envía nada), **Sistema › Fuentes vigiladas** (pública).
- **Hoy › Mi canal** usa tus mediciones reales en el Estudio (la web pública sigue con la demo etiquetada).
  En producción: «Registrar métricas» junto al vídeo subido. Investigar › Creadores: «Guardar» como colaborador.
- Probado: `tests/test_canal.py` (9) + 25 anteriores = 34 en verde; navegador (Estudio aislado) en escritorio y móvil
  sin scroll horizontal.
- Limitación: TikTok y YouTube se registran a mano. Conectar YouTube Analytics es una integración aparte (pide OK).

### Fase 3 — HECHA Y PROBADA (17-nov)
- **Asistente en el chat (0 €)**: `/investigar <id> [pregunta]` (`.claude/commands/investigar.md`) lee
  `python -m estudio.asistente <id>` y responde citando [F1]/[A1]/[N1], separando datos, inferencias y propuestas; no
  busca fuera salvo petición expresa y no modifica nada. En cada investigación: «Preguntar en el chat» copia la orden.
- **Google News (externo, gratis)** en el Buscador (`estudio/externo.py`): solo con botón, aviso de que la consulta va
  a Google News, límite 1 cada 5 s y 30/hora, resultados marcados «externo» con medio y fecha; Guardar / Añadir a
  investigación / Crear vídeo de esto. YouTube sigue siendo solo un enlace.
- **Seguimiento** (`estudio/seguimiento.py`): consultas por investigación; novedades = lo que el Radar detectó después
  de tu última revisión. Pestaña «Seguimiento», Inicio › Continuar y Sistema › Automatizaciones. Se calcula con los
  datos del Radar de tu Mac (no avisa con el Mac apagado).
- **Crear › Revisión** (solo lo que espera tu decisión, con la misma tarjeta de pieza) y **Crear › Calendario**
  (`fecha_prevista`, mes con previstas, publicadas y lanzamiento; lista en móvil; «Programar…»; no publica nada).
- **«Crear vídeo de esto»** en noticias, vídeos, buscador, Google News y Temas: diálogo → pieza en etapa Idea con la
  fuente como señal. **Chips** de filtros en Vídeos. **Atajos**: g+h/b/n/i/r/p/c/e, «/» y «?» (nunca escribiendo).
- Probado: `tests/test_fase3.py` (4) + 34 = 38 en verde; navegador: Google News real (40 resultados), seguimiento,
  Revisión, Calendario (escritorio y móvil), diálogo, chips, atajos; consola sin errores.

### Versión de lanzamiento: web real y rediseño — HECHO (17-nov)
- **Web real**: la base del Radar cuenta como real si tiene ejecuciones o noticias (antes exigía vídeos). Datos
  descargados hoy: 719 noticias reales, 0 vídeos → aviso honesto «falta YOUTUBE_API_KEY en GitHub Secrets».
- **Modo lanzamiento**: cuenta atrás hasta el 19-nov; desde ese día «Día N» y, la primera semana, bloque en Hoy con
  las noticias y los vídeos que más crecen desde el lanzamiento.
- **Rediseño** (`radar/panel/marca.css`, va la última): identidad «Punto de Control» (noche + atardecer
  naranja→rosa→violeta, sin nada de Rockstar), Inter incrustada en el HTML (WOFF2 reducidos, 67 KB, licencia OFL
  en `radar/panel/fuentes/LICENCIA.txt`, sin CDN), iconos SVG propios, tarjetas, botones, cabecera con cristal,
  degradado bajo las líneas de las gráficas (solo en tramos con datos), h1 por vista. Contrastes AA medidos
  (texto secundario 4,9–7,8:1). Sin scroll horizontal en móvil en 6 vistas. Arreglado: el bloque negro de la
  gráfica de Estadísticas.
- **GitHub**: «Shorts diarios» y «Podcast diario» fallan porque GitHub tiene el código antiguo (sin `ia.modo`);
  las protecciones ya están en los commits locales: se arregla al hacer push (pendiente del OK de Javier).
- Probado: `tests/test_lanzamiento.py` (2) + 38 = 40 en verde.
- Pendiente: vídeos con gameplay propio y montaje profesional (propuesto como sesión aparte).

### Pendiente
- Lo que pide Javier en megaprompt 2.0 (choques en su cabecera) y conectar YouTube Analytics (con su OK).

### Documentos
- `README.md` sustituido por la versión de Javier, ampliada con Estudio, modo suscripción, fondo real y tu voz.
- `docs/megaprompt-2.0.md` guardado; sus choques con lo construido están en su cabecera (carpeta por pieza vs. por día,
  lista de estados, costes). Pendiente: la respuesta completa que pide su apartado 20.

## Corte 1 (H1 + H2) — criterios de aceptación del megaprompt §14

| Criterio | Estado | Cómo se comprobó |
|---|---|---|
| Con datos demo y sin claves: abrir el Estudio, elegir oportunidad, ver su guion, aprobar idea y guion, Crear y ver la etapa en curso | ✅ HECHO Y PROBADO | Recorrido a mano en el navegador (Estudio aislado, puerto 8091) + `tests.test_corte1` |
| MP4 vertical real con voz, subtítulos y etiqueta en pantalla | ✅ HECHO Y PROBADO | 1080×1920 comprobado con ffprobe; voz Edge real en el navegador, voz simulada en las pruebas |
| Aprobar vídeo → Exportar → `TikTok/` y `YouTube Shorts/` con `.txt`, `.srt` y manifiesto | ✅ HECHO Y PROBADO | Archivos en disco + sha256 releído («Disponible en el Mac (hash comprobado)») |
| Repetir Exportar no duplica nada | ✅ HECHO Y PROBADO | `test_2_exportar_dos_veces_no_duplica` |
| Editar el guion invalida la aprobación del vídeo (y la del guion) | ✅ HECHO Y PROBADO | `test_3_editar_guion_invalida_aprobaciones` |
| Fallo de voz o de render se reintenta sin perder el guion | ✅ HECHO Y PROBADO | `test_4_fallo_de_voz…` (proveedor de voz caído simulado) |

Además probado: crear no se duplica (`test_5`), sin guion o sin aprobar se bloquea con mensaje (`test_6`),
guion no válido explica todos los errores (`test_7`), exportación a carpeta sin permisos falla con mensaje y no dice
«Disponible» (`test_8`). Ejecutar: `python -m unittest tests.test_corte1 -v` (≈ 15 s, no toca tus datos).

## Qué hay (EXISTENTE VERIFICADO)
- **Estudio** (`python -m estudio`, puerto 8080; `--puerto 8090` si está ocupado): pestaña Estudio con
  piezas por etapas Brief → Guion → Montaje → Revisión → Exportación, siguiente paso explícito, ideas para hoy
  (kits del calendario, temas con hueco, alertas) e ideas a mano. Sin «score de viralidad» a la vista.
- **Estados separados** (`estudio/db.py`): editorial, producción por versión, aprobaciones idea/guion/vídeo con hash,
  exportación verificada, publicación con URL. Migración automática de las piezas anteriores («antes del flujo»).
- **Guion por escenas** (`fabrica/guion.py`, esquema del megaprompt §9): 3 ganchos, escenas leo/sofi con texto en
  pantalla, afirmaciones con etiqueta + fuente + fecha; validación que lista todos los errores; los guiones antiguos se
  convierten solos.
- **Formatos de arranque:** A (lista por país, última hora), B (verdad o bulo, GTA 5 frente a GTA 6), C (guía breve).
- **Cola de render** (`fabrica/cola.py`): un vídeo a la vez, idempotente, cancelación, reintentos (máx. 3),
  recuperación tras cerrar el Estudio, etapas visibles sin porcentajes. Caché de voces por frase.
- **Exportar** (`fabrica/exportar.py`): solo la versión aprobada; `.mp4 .txt .srt _portada.jpg .manifiesto.json`;
  idempotente; versión nueva = `_v2` sin pisar; «Marcar subido» pide la URL y mueve a `subidos/`.
- **Modo suscripción** (`ia.modo: suscripcion`): ninguna llamada de pago; `radar/llm.py` lo impide con un mensaje claro;
  podcast y Shorts automáticos se saltan con aviso. Guiones: `/guiones-del-dia` (`.claude/commands/`),
  `python -m fabrica.encargo [id]` y `--validar`. Ideas del día en `estudio/ideas/AAAA-MM-DD.json`.
- **Piezas reales hechas** (16-nov): «¿Juegas antes que México?» (hora por país) y «¿GTA 6 en PC el 19? → BULO»,
  en `~/Movies/Punto de Control/2026-11-16/` (04 y 05). Los 01–03 de esa carpeta son DEMO: no publicar.

## SIMULADO / DEMO
- Las ideas salen de `data/demo.db` (marcadas «demo») mientras `data/radar.db` no tenga vídeos: el Radar de GitHub
  no tiene todavía `YOUTUBE_API_KEY`.
- En las pruebas automáticas la voz es un tono generado (sin internet).

## PENDIENTE (siguientes cortes)
- Navegación Hoy · Radar · Biblioteca · Resultados (hoy todo vive en la pestaña Estudio del panel).
- Comentarios por momento del vídeo; diff entre versiones en la revisión.
- Variación obligatoria de color/disposición/ritmo (H9) y control de parecido con lo publicado en 7 días.
- Zona segura y «texto + voz desde el fotograma 1» se cumplen por diseño de las plantillas, no se miden aún.
- Vídeo largo de YouTube, 3 portadas, voz +10 % en TikTok.
- Corte 2 en adelante: historias, prioridad explicable, fuentes nuevas, resultados a 48 h.

## BLOQUEADO / depende de Javier
- `YOUTUBE_API_KEY` en GitHub Secrets (gratis) para que el Radar traiga vídeos reales.
- El puerto 8080 lo ocupa un `python -m http.server` lanzado desde Antigravity; Claude no tiene permiso para cerrarlo.

## Supuestos tomados
- `estudio/ideas/` y `estudio/guiones/` fuera de git (datos del día). `data/estudio.db` aparte de `radar.db`.
- Manda el megaprompt sobre plan-v2: Crear solo con idea + guion aprobados; sin «score» de viralidad visible.
- Los cortes son los del megaprompt (8), no los de principios-producto (6).
- `fabrica.producir` ya no exporta: solo fabrica para revisar (exportar es un paso aparte).

## Siguiente paso
Javier prueba el corte 1 (3 pasos en README) y decide: publicar las piezas del 18-19 nov con este flujo, o empezar el
corte 2 (historias y prioridad explicable).

# Estado del proyecto — Punto de Control

Última actualización: 16-nov-2026 (Claude Code). Documentos: `docs/megaprompt-claude-code.md` (manda),
`docs/principios-producto.md`, `docs/plan-v2.md` (reconstruido del PDF; la versión anterior se sobrescribió por error).

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

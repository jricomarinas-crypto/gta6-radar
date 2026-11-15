---
name: operar-canal-gta6
description: Operar y diagnosticar el sistema GTA VI Radar + Podcast (GitHub Actions, cuotas de YouTube, claves, errores, costes, rama data, Telegram). Úsala cuando Javier pregunte por el estado, un fallo, un error en Actions, la cuota, las claves o cómo cambiar horarios.
---

# Operar el canal GTA 6

## Piezas y horarios (UTC)
| Workflow | Archivo | Cuándo | Qué hace |
|---|---|---|---|
| Radar GTA 6 | `.github/workflows/radar.yml` | cada hora, minuto 17 | `python -m radar.run` → ingesta, IA, score, alertas, panel |
| Podcast diario GTA 6 | `.github/workflows/podcast.yml` | 13:41 | `radar.run --briefing` + `podcast.run` (incluye el Agente Editor) |
| Agentes | `.github/workflows/agentes.yml` | 07:23 diario + cuando falla Radar/Podcast; lunes 08:37 | `agentes.operaciones` / `agentes.estrategia` |

Los datos viven en la rama `data` (`data/radar.db`, SQLite). `tools/datos_git.sh traer|guardar` la recupera y la guarda (un único commit que se reescribe).
Para verla en local: `.venv/bin/python tools/descargar_datos.py`.

## Tablas útiles (`data/radar.db`)
- `runs(kind, started_at, stats JSON, error)` → cada pasada del Radar con unidades y búsquedas de YouTube usadas
- `videos`, `creators`, `snapshots`, `news`, `alerts`, `briefings`, `episodes`, `comments`
- `kv`: `estrategia` (informe semanal), `palabras_extra` (búsquedas añadidas por el Agente de Estrategia),
  `community_questions`, `search_idx`, `handle:@canal` → channelId

## Fallos típicos
| Síntoma en el log | Causa | Arreglo |
|---|---|---|
| `Falta la variable X` | Secret no creado | `gh secret set X` |
| `invalid_grant`, `Token has been expired or revoked` | App OAuth en modo Prueba (caduca a 7 días) o permiso revocado | Publicar la app en Google Cloud → repetir `tools/get_youtube_token.py` → `gh secret set YT_REFRESH_TOKEN` |
| `quotaExceeded` / "cupo de búsquedas agotado" | >100 búsquedas/día | Bajar `radar.busquedas_por_ejecucion` o el cron del Radar |
| `uploadLimitExceeded` | Límite de subidas de canal nuevo | `podcast.subida.subir_shorts: false` unos días |
| Vídeo subido pero "bloqueado como privado" | Proyecto de API sin auditar | Normal: publicar a mano o pedir la auditoría de YouTube API Services |
| `thumbnails.set` 403 | Canal sin verificar | youtube.com/verify |
| 401/403 de Anthropic | Clave mal copiada / sin saldo | Revisar `ANTHROPIC_API_KEY` y facturación |
| 529 / `overloaded_error` | Anthropic saturado | `gh run rerun <id> --failed` más tarde |
| Error de `web_search` | Búsqueda web desactivada en la organización | console.anthropic.com → Settings → Privacy |
| `WSServerHandshakeError` / 403 en edge-tts | Cambió el servicio de Microsoft | Subir versión de `edge-tts` en requirements.txt o `podcast.voz.proveedor: elevenlabs` |
| `La IA no devolvió JSON válido` | Respuesta cortada | Reintentar; si se repite, subir `max_tokens` en `podcast/script.py` |
| `Get Pages site failed` | Pages sin activar | Settings → Pages → GitHub Actions, o borrar la variable `PUBLICAR_PANEL` |
| `push` rechazado en `datos_git.sh` | Permisos de Actions | Settings → Actions → General → Workflow permissions: Read and write |

## Comandos gh que más se usan
```bash
gh run list --limit 15
gh run view <id> --log-failed | tail -150
gh run rerun <id> --failed
gh workflow run "Radar GTA 6"
gh workflow run "Podcast diario GTA 6" -f subir=false
gh workflow run "Agentes (operaciones y estrategia)" -f agente=operaciones   # o estrategia
gh run download <id> -D output/descarga
gh secret list
gh issue list --label agente-operaciones
```

## Cambiar horarios
Edita el `cron` del workflow (UTC). España = UTC+1 en invierno. Latinoamérica (México) = UTC-6.
Para que el episodio salga antes, adelanta `podcast.yml`; deja al menos 30 min respecto al minuto 17 del Radar.

## Costes
- YouTube API y GitHub Actions (repo público): gratis.
- Claude: pago por uso. Lo que más gasta: clasificación (modelo rápido) y guion + editor + búsquedas web (modelo principal). Para bajar el coste: `radar.clasificar_max_por_ejecucion`, `ia.busquedas_web_por_episodio`, o Radar cada 2 h.
- ElevenLabs solo si `podcast.voz.proveedor: elevenlabs`.

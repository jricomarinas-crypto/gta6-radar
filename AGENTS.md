# AGENTS.md — GTA VI Radar + Podcast

Guía para cualquier agente de IA que trabaje en este repositorio (Antigravity, Claude Code, Codex…).
El dueño del proyecto es Javier: háblale en **español**, de forma breve y con pasos concretos.

## Qué es
Sistema automático para un canal de YouTube sobre GTA 6 (público hispano de Latinoamérica):
1. **Radar** (`radar/`, cada hora en GitHub Actions): ingesta de YouTube y medios → clasificación con IA → score → alertas → panel → briefing.
2. **Podcast** (`podcast/`, diario): investigación web + datos del Radar → guion (2 presentadores) → **Agente Editor** → voces → vídeo, 3 Shorts y miniatura → subida a YouTube en privado.
3. **Agentes automáticos** (`agentes/`):
   - **Agente Editor** (`podcast/editor.py`): revisa cada guion contra el dossier antes de grabarlo.
   - **Agente de Operaciones** (`agentes/operaciones.py`): informe de salud diario y diagnóstico automático cuando falla algo (abre un issue con la solución).
   - **Agente de Estrategia** (`agentes/estrategia.py`): análisis semanal del rendimiento del canal; reorienta formatos, temas y palabras clave del Radar.

## Mapa
| Ruta | Para qué |
|---|---|
| `config.yaml` | Todo lo configurable (canal, presentadores, voces, formatos, palabras clave, umbrales, pesos) |
| `radar/youtube.py`, `radar/news.py` | Ingesta (cuota de YouTube: 100 búsquedas/día + 10.000 unidades) |
| `radar/classify.py`, `radar/scoring.py`, `radar/trends.py` | IA, score y alertas |
| `radar/dashboard_template.html` | Panel web |
| `podcast/script.py`, `podcast/editor.py` | Investigación, guion y revisión |
| `podcast/tts.py`, `podcast/render.py`, `podcast/upload.py` | Voces, montaje y subida |
| `.github/workflows/` | `radar.yml` (cada hora), `podcast.yml` (diario), `agentes.yml` (operaciones diario + estrategia semanal) |
| `tools/` | Token de YouTube, datos demo, descarga de la base de datos, guardado en la rama `data` |
| `.agents/` | Reglas, workflows (`/comando`) y skills de Antigravity |

## Comandos
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt pyflakes
python -m pyflakes radar podcast agentes          # comprobación rápida
python tools/datos_demo.py                         # panel demo → site/index.html
python -m podcast.run --demo --sin-subir           # episodio demo → output/<fecha>/ (necesita ffmpeg)
python tools/descargar_datos.py && python -m radar.chat   # preguntar al Radar con datos reales
gh run list --limit 10                             # estado de GitHub Actions
python -m estudio                                  # Estudio en http://localhost:8080 (--puerto 8090 si está ocupado)
python -m fabrica.encargo [id]                     # piezas que esperan guion / detalle de una
python -m fabrica.encargo --validar <ruta.json>    # valida un guion
python -m unittest tests.test_corte1 -v            # pruebas del corte 1 (carpeta temporal, no toca tus datos)
```

## Estudio y Fábrica — modo suscripción (0 €)
Documento maestro: `docs/megaprompt-claude-code.md` (manda sobre `docs/principios-producto.md` y `docs/plan-v2.md`).
`docs/megaprompt-2.0.md` es la evolución propuesta por Javier: sus choques con lo construido están en su cabecera; no los resuelvas sin su OK.
Vídeos: por defecto fondo de vídeo real (Pexels / `assets/broll/`) y voz de Javier grabada en el Estudio (`fabrica/broll.py`, `fabrica/voz_propia.py`).
Estado honesto en `docs/ESTADO.md`: actualízalo al terminar cada sesión.
`ia.modo: suscripcion` → la app no llama a ninguna IA. Cuando Javier diga «Escribe el guion del encargo X» o `/guiones-del-dia`:
1. `python -m fabrica.encargo X` (idea, formato, ruta del guion en `estudio/guiones/AAAA-MM-DD/X.json`).
2. Verifica cada dato con búsqueda web en fuentes primarias o medios fiables (nunca otros creadores); anota la fecha.
3. Escribe el JSON con el esquema de la cabecera de `fabrica/guion.py` y valídalo con `--validar`.
4. NO apruebes nada: idea, guion y vídeo los aprueba Javier en el Estudio; él pulsa Crear vídeo y Exportar.
Asistente de investigación (0 €): `/investigar <id> [pregunta]` → `python -m estudio.asistente <id>` imprime la investigación
numerada ([F1] fuentes, [A1] afirmaciones, [N1] notas); responde citando, sin buscar fuera salvo que Javier lo pida y sin modificar nada.
El render necesita ffmpeg con libass (`ffmpeg-full`); el Estudio lo antepone en el PATH solo.


## Reglas que no se rompen
- **Secretos**: nunca en el código, en commits ni en el chat. Van en GitHub Secrets (`gh secret set NOMBRE`, que pide el valor en la terminal) o en `.env` (ignorado por git).
- **YouTube**: nada se publica sin que Javier lo confirme. Las subidas son en privado.
- **Contenido**: sin tráilers, gameplay ni logos de Rockstar. Los datos van etiquetados CONFIRMADO / REPORTADO / RUMOR / OPINIÓN. Español neutro latinoamericano en los guiones.
- **Cuotas**: no superar 100 búsquedas/día de YouTube (`busquedas_por_ejecucion` × ejecuciones/día).
- **Git**: pide confirmación antes de `git push`. Antes de hacer commit de código, pasa `pyflakes` y, si tocas el montaje, `python -m podcast.run --demo --sin-subir`.

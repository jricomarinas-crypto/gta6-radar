---
description: Deja el sistema funcionando desde cero (GitHub, claves, primera ejecución). Úsalo una sola vez.
---

# /puesta-en-marcha

Objetivo: que el Radar, el Podcast y los Agentes queden corriendo en GitHub Actions. Ve paso a paso, explica cada
paso en una frase a Javier y espera su confirmación antes de cualquier paso que cree o publique algo.
Lee `README.md` (sección "Puesta en marcha") para el detalle de cada clave.

## 1. Herramientas
// turbo
1. Ejecuta `which git python3 ffmpeg gh brew` y `python3 --version`.
2. Si falta algo, propón instalarlo con Homebrew (`brew install gh ffmpeg python@3.12`) y espera a que Javier diga que sí.
   Si no hay Homebrew, dale el comando oficial de https://brew.sh para que lo ejecute él.

## 2. Entorno local de pruebas
1. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pyflakes`
// turbo
2. `.venv/bin/python -m pyflakes radar podcast agentes`
3. `.venv/bin/python tools/datos_demo.py` y abre `site/index.html` en el navegador de Antigravity para enseñarle el panel demo.

## 3. GitHub
1. `gh auth status`. Si no está autenticado, pide a Javier que ejecute `gh auth login` en la terminal (GitHub.com → HTTPS → navegador).
2. Pregunta: ¿repositorio público (recomendado: minutos gratis ilimitados y panel en Pages) o privado?
3. Si no hay repo git: `git init -b main && git add . && git commit -m "GTA VI Radar + Podcast"`.
   Comprueba antes con `git status --ignored` que `.env` y `tools/client_secret.json` NO se van a subir.
4. Con su confirmación: `gh repo create gta6-radar --public --source=. --push` (o `--private`).
5. Si es privado: cambia el cron de `.github/workflows/radar.yml` a `"17 */2 * * *"`, haz commit y push.

## 4. Claves (Javier las pega en la terminal, nunca en el chat)
Para cada una, explica de dónde sacarla (README) y ejecuta el comando para que él pegue el valor:
1. `gh secret set ANTHROPIC_API_KEY` (console.anthropic.com; recuerda activar la búsqueda web en Settings → Privacy y poner límite de gasto).
2. `gh secret set YOUTUBE_API_KEY` (Google Cloud → YouTube Data API v3 → Clave de API).
3. Subida a YouTube: guíale para crear el ID de cliente OAuth (app de escritorio, app **publicada**), guardar el JSON
   como `tools/client_secret.json` y ejecutar `.venv/bin/pip install google-auth-oauthlib && .venv/bin/python tools/get_youtube_token.py`.
   Después: `gh secret set YT_CLIENT_ID`, `gh secret set YT_CLIENT_SECRET`, `gh secret set YT_REFRESH_TOKEN`.
4. Opcional Telegram: `gh secret set TELEGRAM_BOT_TOKEN` y `gh secret set TELEGRAM_CHAT_ID`.
// turbo
5. Comprueba con `gh secret list`.

## 5. Panel web (solo repo público)
1. Con su confirmación: `gh api -X POST "repos/{owner}/{repo}/pages" -f build_type=workflow` (sustituye owner/repo con `gh repo view --json nameWithOwner -q .nameWithOwner`).
2. `gh variable set PUBLICAR_PANEL --body si`

## 6. Primera ejecución
1. `gh workflow run "Radar GTA 6"` y sigue el progreso con `gh run watch`.
2. Cuando termine bien: `gh workflow run "Podcast diario GTA 6" -f subir=false` (primera prueba sin subir a YouTube).
3. `gh run download <id> -D output/primera-prueba` y abre el episodio y `editor.md` para revisarlos con Javier.
4. `gh workflow run "Agentes (operaciones y estrategia)" -f agente=operaciones` para comprobar el informe de salud.
5. Resume qué queda funcionando, a qué hora corre cada cosa y qué tiene que hacer Javier cada día (revisar y publicar en YouTube Studio).

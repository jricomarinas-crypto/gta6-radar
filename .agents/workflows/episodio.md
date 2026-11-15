---
description: Genera o revisa el episodio de hoy (guion, informe del Editor, vídeo, Shorts, título y miniatura) antes de publicarlo.
---

# /episodio

## 1. ¿Existe ya el de hoy?
// turbo
1. `gh run list --workflow "Podcast diario GTA 6" --limit 3`
2. Si no hay ejecución de hoy o falló, pregunta a Javier si lanzarlo: `gh workflow run "Podcast diario GTA 6"`
   (con `-f subir=false` si solo quiere probar) y sigue con `gh run watch`.

## 2. Descargar y revisar
// turbo
1. `gh run download <id> -D output/revision-$(date +%F)`
2. Lee `guion.json`, `dossier.md` y `editor.md`. Usa la skill `editor-guiones-gta6`.
3. Dale a Javier una revisión de 6 líneas como máximo:
   - Título propuesto y 2 alternativas (honestas, ≤ 70 caracteres, con "GTA 6")
   - Datos marcados como RUMOR que conviene vigilar
   - Lo que corrigió el Agente Editor y si queda algo dudoso
   - Si los Shorts tienen buen gancho
   - Hora recomendada de publicación (tarde de Latinoamérica: 18:00-20:00 hora de México)
4. Abre el vídeo y la miniatura para que los vea:
   `open "$(find output/revision-$(date +%F) -name episodio.mp4 | head -1)"; open "$(find output/revision-$(date +%F) -name miniatura.jpg | head -1)"`

## 3. Publicar
Javier publica en YouTube Studio (los vídeos están en privado). Si quiere cambiar título o descripción, dáselos listos para copiar.
Si quiere subir los Shorts a TikTok, recuérdale que están en la misma carpeta (`short_*.mp4`).

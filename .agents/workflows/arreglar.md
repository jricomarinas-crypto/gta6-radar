---
description: Diagnostica y arregla el último fallo de GitHub Actions (Radar, Podcast o Agentes).
---

# /arreglar

## 1. Localizar el fallo
// turbo
1. `gh run list --status failure --limit 5`
// turbo
2. `gh run view <id-del-fallo-más-reciente> --log-failed | tail -150`
// turbo
3. `gh issue list --label agente-operaciones --state open` y lee el diagnóstico del Agente de Operaciones si existe (`gh issue view <n>`).

## 2. Decidir
Usa la skill `operar-canal-gta6` (tabla de fallos típicos). Clasifica:
- **Configuración** (clave mal puesta, OAuth caducado, Pages sin activar, cuota): explica a Javier qué hacer, con el comando exacto
  (`gh secret set …`, pasos en Google Cloud). No toques código.
- **Código**: sigue con el paso 3.
- **Servicio externo caído** (Anthropic 529, Microsoft TTS): propón reintentar con `gh run rerun <id> --failed` más tarde.

## 3. Arreglar código
1. Reproduce en local si es posible (`.venv/bin/python -m radar.run --solo-panel`, `.venv/bin/python -m podcast.run --demo --sin-subir`).
2. Haz el cambio mínimo. Nada de refactorizaciones.
// turbo
3. `.venv/bin/python -m pyflakes radar podcast agentes`
4. Enseña el diff a Javier (`git diff`) y, con su OK: `git commit -am "fix: …" && git push`.
5. `gh run rerun <id> --failed` y `gh run watch` hasta que pase.
6. Si había un issue del Agente de Operaciones, ciérralo con un comentario: `gh issue close <n> -c "Arreglado en <commit>"`.

---
description: Revisa la estrategia del canal (qué funciona, temas, formatos) y propone cambios en config.yaml.
---

# /estrategia

1. Pregunta a Javier si quiere lanzar ahora el Agente de Estrategia en GitHub
   (`gh workflow run "Agentes (operaciones y estrategia)" -f agente=estrategia`, luego `gh run watch`) o usar el último informe.
// turbo
2. `.venv/bin/python tools/descargar_datos.py`
// turbo
3. `.venv/bin/python -c "import sqlite3,json;c=sqlite3.connect('data/radar.db');r=c.execute(\"select v from kv where k='estrategia'\").fetchone();print(json.dumps(json.loads(r[0]),ensure_ascii=False,indent=1) if r else 'sin informe todavía')"`
4. Con el informe, el panel (`.venv/bin/python -m radar.run --solo-panel` → `site/index.html`) y `config.yaml`, propone como máximo 5 cambios concretos, por ejemplo:
   - reordenar o quitar formatos en `podcast.formatos`
   - añadir palabras clave en `radar.palabras_clave` o canales en `radar.creadores_prioritarios` (con su @)
   - ajustar `podcast.duracion_minutos` o `shorts_por_episodio`
   - umbrales de `radar.alertas` si hay demasiadas o muy pocas alertas
5. Aplica solo los que Javier apruebe, valida con `.venv/bin/python -c "import yaml;yaml.safe_load(open('config.yaml'))"`,
   enséñale el `git diff` y, con su OK, `git commit -am "config: …" && git push`.

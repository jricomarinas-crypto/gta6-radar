---
description: Parte de situación del sistema (ejecuciones, errores, cuota, último episodio, alertas).
---

# /estado

// turbo-all
1. `gh run list --limit 20 --json name,conclusion,createdAt,url --jq '.[] | "\(.createdAt[5:16]) \(.conclusion // "en curso") \(.name)"'`
2. `gh issue list --label agente-operaciones --state open`
3. `.venv/bin/python tools/descargar_datos.py`
4. `.venv/bin/python -c "import sqlite3,json;c=sqlite3.connect('data/radar.db');print(json.dumps({'ultima_ejecucion':c.execute('select started_at,stats,error from runs order by id desc limit 1').fetchone(),'videos_24h':c.execute(\"select count(*) from videos where published_at>=datetime('now','-1 day')\").fetchone()[0],'alertas_24h':c.execute(\"select count(*) from alerts where created_at>=strftime('%Y-%m-%dT%H:%M:%SZ','now','-1 day')\").fetchone()[0],'ultimo_episodio':c.execute('select date,title,youtube_id from episodes order by date desc limit 1').fetchone()},ensure_ascii=False,indent=1))"`

Después resume en 5 líneas como máximo:
- 🟢/🟡/🔴 estado general
- Radar: última ejecución, vídeos nuevos, errores
- Podcast: último episodio y si se subió
- Issues abiertos del Agente de Operaciones
- Qué tiene que hacer Javier (si algo). Si hay fallos, sugiere `/arreglar`.

---
description: Prueba todo en el Mac sin gastar cuota (panel demo + episodio demo con voces reales).
---

# /probar-local

// turbo-all
1. `test -d .venv || python3 -m venv .venv`
2. `.venv/bin/pip install -q -r requirements.txt pyflakes`
3. `.venv/bin/python -m pyflakes radar podcast agentes`
4. `.venv/bin/python tools/datos_demo.py`
5. `which ffmpeg || echo "Falta ffmpeg: brew install ffmpeg"`
6. `.venv/bin/python -m podcast.run --demo --sin-subir`
7. `open site/index.html; open "$(find output -maxdepth 1 -name '20*' | sort | tail -1)"`

Resume a Javier qué ha salido (duración del episodio, número de Shorts) y que el panel usa datos inventados.

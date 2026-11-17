"""Panel del Radar: una página HTML estática (se publica en GitHub Pages o se abre en local).

La plantilla (dashboard_template.html) es solo el esqueleto. Los estilos y el código viven en radar/panel/
y se incrustan aquí, en el orden de CSS y JS: así el resultado sigue siendo UN archivo que funciona sin
internet y en GitHub Pages, sin ningún proceso de compilación nuevo.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import diario, fuentes, oportunidades
from .briefing import snapshot
from .config import ROOT, cfg
from .db import jload, kv_get

AQUI = Path(__file__).parent
TEMPLATE = AQUI / "dashboard_template.html"
PANEL = AQUI / "panel"
CSS = ["base.css", "app.css"]                              # orden de carga
JS = ["radar.js", "util.js", "graficas.js", "hoy.js", "investigar.js", "canal.js", "crear.js", "nav.js"]       # radar.js define DATA y utilidades; nav.js arranca


def _leer(nombres: list[str]) -> str:
    return "\n".join((PANEL / n).read_text(encoding="utf-8").rstrip("\n") for n in nombres if (PANEL / n).exists())


def html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    t = TEMPLATE.read_text(encoding="utf-8")
    t = t.replace("/*__CSS__*/", _leer(CSS), 1).replace("/*__JS__*/", _leer(JS), 1)
    return t.replace("/*__DATA__*/null", payload, 1)


def build(con, out_dir: Path | None = None, demo: bool = False) -> Path:
    out_dir = out_dir or (ROOT / "site")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = snapshot(con, 48)
    b = con.execute("SELECT date, markdown FROM briefings ORDER BY date DESC LIMIT 1").fetchone()
    data["briefing"] = dict(b) if b else None
    data["episodes"] = [
        {"date": r["date"], "title": r["title"], "format": r["format"], "youtube_id": r["youtube_id"],
         "shorts": jload(r["shorts"])}
        for r in con.execute("SELECT * FROM episodes ORDER BY date DESC LIMIT 10")
    ]
    data["oportunidades"] = oportunidades.calcular(con)
    data["channel"] = cfg()["canal"]
    data["release_date"] = cfg()["canal"].get("lanzamiento")
    data["demo"] = demo
    data["series"] = {
        "zona": cfg().get("panel", {}).get("zona_horaria", "Europe/Madrid"),
        "hoy": diario.hoy().isoformat(),
        "radar": diario.serie(con, 90),
        # Mi canal y Producción de demostración: solo existen en la base demo (nunca se mezclan con datos reales)
        "canal_demo": jload(kv_get(con, "demo_canal"), None) if demo else None,
        "produccion_demo": jload(kv_get(con, "demo_produccion"), None) if demo else None,
    }
    data["fuentes"] = fuentes.resumen(con)
    data["datos_antiguos_horas"] = cfg().get("panel", {}).get("datos_antiguos_horas", 3)
    out = out_dir / "index.html"
    out.write_text(html(data), encoding="utf-8")
    return out

"""Panel del Radar: una página HTML estática (se publica en GitHub Pages o se abre en local)."""
from __future__ import annotations

import json
from pathlib import Path

from . import oportunidades
from .briefing import snapshot
from .config import ROOT, cfg
from .db import jload

TEMPLATE = (Path(__file__).parent / "dashboard_template.html")


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
    data["release_date"] = "2026-11-19"
    data["demo"] = demo
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    out = out_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out

"""Una pasada del Radar.

    python -m radar.run              # ingesta + IA + scoring + alertas + panel
    python -m radar.run --briefing   # además: preguntas de la comunidad + briefing diario
    python -m radar.run --solo-panel # solo regenera el panel con lo que ya hay
"""
from __future__ import annotations

import argparse
import traceback

from . import classify, dashboard, llm, news, oportunidades, scoring, trends, youtube
from .briefing import community_questions, daily_briefing
from .config import cfg, env
from .db import connect, iso, jdump, prune
from .notify import send


def step(name, fn, stats, *a, **k):
    print(f"▶ {name}")
    try:
        out = fn(*a, **k)
        if isinstance(out, dict):
            stats.update(out)
        elif out is not None:
            stats[name] = out
        return out
    except Exception as e:  # noqa: BLE001 — un fallo no tumba el resto
        traceback.print_exc()
        stats.setdefault("errores", []).append(f"{name}: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefing", action="store_true")
    ap.add_argument("--solo-panel", action="store_true")
    args = ap.parse_args()

    con = connect()
    if args.solo_panel:
        print("Panel:", dashboard.build(con))
        return
    run_id = con.execute("INSERT INTO runs(kind,started_at) VALUES('radar',?)", (iso(),)).lastrowid
    con.commit()
    stats: dict = {}
    has_ai = llm.disponible()  # ia.modo=api y clave puesta; en modo suscripción el Radar va sin IA (0 €)

    if env("YOUTUBE_API_KEY"):
        step("YouTube", youtube.run_ingestion, stats, con)
    else:
        print("⚠ Sin YOUTUBE_API_KEY: me salto YouTube")
    step("medios", news.ingest_rss, stats, con)
    step("reddit", news.ingest_reddit, stats, con)
    if has_ai:
        step("clasificación IA", classify.classify_pending, stats, con)
    else:
        print("⚠ IA desactivada (ia.modo: suscripcion o sin ANTHROPIC_API_KEY): me salto la clasificación con IA")
    step("scoring", scoring.score_videos, stats, con)
    step("alertas", trends.detect_alerts, stats, con)

    if cfg()["avisos"].get("enviar_alertas", True):
        pend = trends.pending_notifications(con)
        if pend:
            lines = ["🚨 GTA VI RADAR — alertas"]
            for a in pend[:12]:
                lines.append(f"\n[{a['severity'].upper()}] {a['title']}\n{a['message'] or ''}\n{a['url'] or ''}")
            send("\n".join(lines))
        trends.mark_notified(con)

    if args.briefing and has_ai:
        if env("YOUTUBE_API_KEY"):
            step("comunidad", lambda: len((community_questions(con) or {}).get("preguntas", [])), stats)
        md = step("briefing", daily_briefing, stats, con)
        stats.pop("briefing", None)
        if md and cfg()["avisos"].get("enviar_briefing_diario", True):
            send("📋 BRIEFING DIARIO — GTA VI RADAR\n\n" + md)
        step("ideas para hoy", oportunidades.generar_ideas, stats, con)

    step("limpieza", prune, stats, con)
    step("panel", lambda: str(dashboard.build(con)), stats)
    con.execute("UPDATE runs SET finished_at=?, stats=?, error=? WHERE id=?",
                (iso(), jdump(stats), "; ".join(stats.get("errores", [])) or None, run_id))
    con.commit()
    print("✔ Radar terminado:", jdump(stats))


if __name__ == "__main__":
    main()

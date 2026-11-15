"""Motor de puntuación: Momentum, Engagement, Relevancia, Autoridad, Novedad y Riesgo (0-100)."""
from __future__ import annotations

import math
from bisect import bisect_left

from .config import cfg
from .db import hours_ago, jload, now, parse_iso
from .youtube import is_gta6

RISK = {"low": 10, "medium": 40, "high": 75, "critical": 100}


def _pct(sorted_vals, x):
    if len(sorted_vals) < 2:
        return 50.0
    return 100.0 * bisect_left(sorted_vals, x) / (len(sorted_vals) - 1)


def score_videos(con, days: int = 7) -> int:
    w = cfg()["radar"]["pesos"]
    rows = con.execute(
        """SELECT v.*, c.subscribers, c.is_priority, c.is_official FROM videos v
           LEFT JOIN creators c ON c.id=v.creator_id
           WHERE v.published_at >= ? AND COALESCE(v.is_related,1)=1""", (hours_ago(days * 24),)).fetchall()
    if not rows:
        return 0
    vel = sorted(math.log1p(r["velocity"] or 0) for r in rows)
    over = sorted((r["velocity"] or 0) / math.sqrt((r["subscribers"] or 0) + 1000) for r in rows)
    eng_vals = []
    for r in rows:
        eng_vals.append(((r["likes"] or 0) + 2 * (r["comments"] or 0)) / max(r["views"] or 0, 1))
    eng_sorted = sorted(eng_vals)
    t_now = now()
    for r, eng in zip(rows, eng_vals):
        momentum = 0.7 * _pct(vel, math.log1p(r["velocity"] or 0)) + \
            0.3 * _pct(over, (r["velocity"] or 0) / math.sqrt((r["subscribers"] or 0) + 1000))
        engagement = _pct(eng_sorted, eng) * (1.0 if (r["views"] or 0) >= 500 else 0.5)
        # relevancia
        if r["is_related"] == 0:
            relevance = 0
        else:
            relevance = 50 if is_gta6(r["title"]) else 25
            if r["is_related"] == 1:
                relevance += 30
            topics = jload(r["topics"])
            if topics and topics != ["otros"]:
                relevance += 20
        # autoridad
        subs = r["subscribers"] or 0
        authority = min(100.0, math.log10(subs + 1) / 7 * 100)
        if r["is_priority"]:
            authority = min(100.0, authority + 20)
        if r["is_official"]:
            authority = 100.0
        # novedad
        novelty = (r["novelty"] * 100) if r["novelty"] is not None else 40.0
        pub = parse_iso(r["published_at"])
        if pub and (t_now - pub).total_seconds() < 24 * 3600:
            novelty = min(100.0, novelty + 10)
        if r["is_official"]:
            novelty = max(novelty, 90.0)
        risk = RISK.get(r["risk_level"] or "low", 10)
        overall = (w["momentum"] * momentum + w["engagement"] * engagement + w["relevancia"] * relevance
                   + w["autoridad"] * authority + w["novedad"] * novelty + w["riesgo"] * risk)
        con.execute(
            """UPDATE videos SET momentum_score=?,engagement_score=?,relevance_score=?,authority_score=?,
               novelty_score=?,risk_score=?,overall_score=? WHERE id=?""",
            (round(momentum, 1), round(engagement, 1), relevance, round(authority, 1), round(novelty, 1),
             risk, round(overall, 1), r["id"]),
        )
    con.execute("UPDATE videos SET overall_score=0 WHERE is_related=0")
    con.commit()
    return len(rows)

"""Resumen del radar (para panel, briefing diario y podcast) y briefing escrito por la IA."""
from __future__ import annotations

from .config import cfg
from .db import hours_ago, iso, jdump, jload, kv_get, kv_set, now
from .llm import ask, ask_json
from .trends import TOPIC_LABEL, topic_trends


def _video_dict(r) -> dict:
    return {
        "id": r["id"], "title": r["title"], "url": r["url"], "thumb": r["thumbnail_url"],
        "channel": r["cname"], "channel_subs": r["subs"], "published_at": r["published_at"],
        "views": r["views"], "likes": r["likes"], "comments": r["comments"],
        "velocity": round(r["velocity"] or 0), "is_short": bool(r["is_short"]), "language": r["language"],
        "content_type": r["content_type"], "topics": jload(r["topics"]), "entities": jload(r["entities"]),
        "risk": r["risk_level"], "verification": r["verification"], "summary": r["summary"],
        "claims": jload(r["key_claims"]), "found_via": r["found_via"],
        "score": r["overall_score"], "momentum": r["momentum_score"], "engagement": r["engagement_score"],
        "relevance": r["relevance_score"], "authority": r["authority_score"], "novelty": r["novelty_score"],
        "risk_score": r["risk_score"],
    }


def snapshot(con, hours: int = 48, limit: int = 300) -> dict:
    vids = con.execute(
        """SELECT v.*, c.name cname, c.subscribers subs FROM videos v LEFT JOIN creators c ON c.id=v.creator_id
           WHERE v.published_at>=? AND COALESCE(v.is_related,1)=1
           ORDER BY COALESCE(v.overall_score,0) DESC LIMIT ?""", (hours_ago(hours), limit)).fetchall()
    videos = [_video_dict(r) for r in vids]
    news = [dict(source=r["source"], title=r["title"], url=r["url"], published_at=r["published_at"],
                 summary=r["ai_summary"] or r["summary"], topics=jload(r["topics"]), verification=r["verification"],
                 official=bool(r["is_official"]), novelty=r["novelty"], language=r["language"])
            for r in con.execute("""SELECT * FROM news WHERE published_at>=? AND COALESCE(is_related,1)=1
                                    ORDER BY COALESCE(novelty,0) DESC, published_at DESC LIMIT 80""", (hours_ago(hours),))]
    creators = [dict(r) for r in con.execute(
        """SELECT c.id, c.name, c.handle, c.subscribers, c.avatar_url, c.is_official, c.is_priority,
                  COUNT(v.id) n_videos, SUM(v.views) views, MAX(v.velocity) max_velocity,
                  ROUND(AVG(v.overall_score),1) avg_score, MAX(v.overall_score) best_score
           FROM creators c JOIN videos v ON v.creator_id=c.id
           WHERE v.published_at>=? AND COALESCE(v.is_related,1)=1
           GROUP BY c.id ORDER BY best_score DESC LIMIT 60""", (hours_ago(hours * 2),))]
    emerging = [c for c in creators if (c["subscribers"] or 0) <= cfg()["radar"]["alertas"]["emergente_max_suscriptores"]
                and (c["views"] or 0) >= 3 * max(c["subscribers"] or 1, 1)]
    alerts = [dict(r) for r in con.execute("SELECT * FROM alerts WHERE created_at>=? ORDER BY id DESC LIMIT 60",
                                           (hours_ago(hours),))]
    hourly = {}
    for r in con.execute("SELECT substr(published_at,1,13) h, COUNT(*) n FROM videos WHERE published_at>=? "
                         "AND COALESCE(is_related,1)=1 GROUP BY h", (hours_ago(hours),)):
        hourly[r["h"]] = r["n"]
    kpis = {
        "videos_total": con.execute("SELECT COUNT(*) FROM videos WHERE COALESCE(is_related,1)=1").fetchone()[0],
        "videos_24h": con.execute("SELECT COUNT(*) FROM videos WHERE published_at>=? AND COALESCE(is_related,1)=1",
                                  (hours_ago(24),)).fetchone()[0],
        "creators_24h": con.execute("SELECT COUNT(DISTINCT creator_id) FROM videos WHERE published_at>=? "
                                    "AND COALESCE(is_related,1)=1", (hours_ago(24),)).fetchone()[0],
        "news_24h": con.execute("SELECT COUNT(*) FROM news WHERE published_at>=? AND COALESCE(is_related,1)=1",
                                (hours_ago(24),)).fetchone()[0],
        "views_24h": con.execute("SELECT COALESCE(SUM(views),0) FROM videos WHERE published_at>=? "
                                 "AND COALESCE(is_related,1)=1", (hours_ago(24),)).fetchone()[0],
        "alerts_critical": sum(1 for a in alerts if a["severity"] in ("critical", "high")),
        "max_velocity": max((v["velocity"] for v in videos), default=0),
    }
    langs, types = {}, {}
    for v in videos:
        langs[(v["language"] or "?")[:2]] = langs.get((v["language"] or "?")[:2], 0) + 1
        types[v["content_type"] or "sin clasificar"] = types.get(v["content_type"] or "sin clasificar", 0) + 1
    return {
        "generated_at": iso(), "hours": hours, "kpis": kpis, "videos": videos, "news": news,
        "creators": creators, "emerging": emerging, "alerts": alerts, "topics": topic_trends(con),
        "hourly": hourly, "languages": langs, "content_types": types,
        "community_questions": jload(kv_get(con, "community_questions"), {}),
        "last_run": dict(con.execute("SELECT * FROM runs WHERE kind='radar' ORDER BY id DESC LIMIT 1").fetchone() or {}),
    }


def community_questions(con, top_n: int | None = None) -> dict:
    """Lee comentarios de los vídeos top y saca las preguntas que más se repiten."""
    from .youtube import fetch_top_comments

    rc = cfg()["radar"]
    top_n = top_n or rc.get("comentarios_videos_top", 5)
    top = [r["id"] for r in con.execute(
        """SELECT id FROM videos WHERE published_at>=? AND COALESCE(is_related,1)=1 AND comments>20
           ORDER BY overall_score DESC LIMIT ?""", (hours_ago(48), top_n))]
    if top:
        fetch_top_comments(con, top, rc.get("comentarios_por_video", 60))
    rows = con.execute("SELECT c.text, c.likes FROM comments c WHERE c.video_id IN (%s) ORDER BY likes DESC LIMIT 300"
                       % ",".join("?" * len(top)), top).fetchall() if top else []
    if not rows:
        return {}
    txt = "\n".join(f"- ({r['likes']} likes) {r['text'][:300]}" for r in rows)
    res = ask_json(
        "Estos son comentarios de los vídeos de GTA 6 más vistos de los últimos 2 días.\n"
        "Extrae las 8 preguntas o dudas que más se repiten y las 3 opiniones dominantes.\n"
        'Devuelve JSON: {"preguntas":[{"pregunta":"...","frecuencia":"alta|media|baja"}],'
        '"opiniones":["..."]}. En español neutro, sin inventar.\n\n' + txt,
        model=cfg()["ia"]["modelo_rapido"], max_tokens=2000)
    res["fecha"] = now().strftime("%Y-%m-%d")
    kv_set(con, "community_questions", jdump(res))
    con.commit()
    return res


def daily_briefing(con) -> str:
    snap = snapshot(con, 24, limit=40)
    compact = {
        "kpis": snap["kpis"],
        "top_videos": [{k: v[k] for k in ("title", "channel", "url", "views", "velocity", "content_type",
                                          "topics", "summary", "claims", "verification", "risk", "score")}
                       for v in snap["videos"][:15]],
        "emergentes": [{k: c[k] for k in ("name", "subscribers", "views", "n_videos")} for c in snap["emerging"][:8]],
        "temas": [{k: t[k] for k in ("label", "n_24h", "n_prev", "growth")} for t in snap["topics"][:10]],
        "alertas": [{k: a[k] for k in ("type", "severity", "title", "message", "url")} for a in snap["alerts"][:15]],
        "noticias": [{k: n[k] for k in ("source", "title", "url", "verification", "official")} for n in snap["news"][:15]],
        "comunidad": snap["community_questions"],
    }
    md = ask(
        "Escribe el BRIEFING DIARIO del radar de GTA 6 para el equipo de un canal de YouTube en español.\n"
        f"Fecha: {now().strftime('%d/%m/%Y')}. Datos del radar (JSON):\n{jdump(compact)}\n\n"
        "Estructura (markdown, conciso, accionable):\n"
        "1. Resumen ejecutivo (3 frases)\n2. Contenido con más momentum (top 5 con enlace y por qué)\n"
        "3. Creadores emergentes\n4. Temas dominantes y en alza\n5. Alertas críticas\n"
        "6. Rumores y nivel de verificación (separa HECHO / REPORTADO / RUMOR)\n"
        "7. Oportunidades de contenido para nuestro podcast (3 ideas concretas con ángulo)\n"
        "8. Qué evitar (bulos, riesgo de copyright)\n"
        "Usa solo los datos dados; si algo no está, no lo inventes. Cita enlaces.",
        max_tokens=3000)
    day = now().strftime("%Y-%m-%d")
    con.execute("INSERT OR REPLACE INTO briefings(date,markdown,data,created_at) VALUES(?,?,?,?)",
                (day, md, jdump(compact), iso()))
    con.commit()
    return md


__all__ = ["snapshot", "daily_briefing", "community_questions", "TOPIC_LABEL"]

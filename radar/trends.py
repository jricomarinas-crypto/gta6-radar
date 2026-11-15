"""Tendencias por tema y motor de alertas."""
from __future__ import annotations

from collections import defaultdict

from .config import cfg
from .db import hours_ago, iso, jload, now

SEV = {"low": 0, "medium": 1, "high": 2, "critical": 3}
TOPIC_LABEL = {
    "lanzamiento": "Lanzamiento", "precio_ediciones": "Precio y ediciones", "plataformas_pc": "Plataformas / PC",
    "rendimiento_fps": "Rendimiento y FPS", "mapa": "Mapa", "personajes": "Personajes", "historia": "Historia",
    "gameplay": "Gameplay", "vehiculos": "Vehículos", "online": "GTA Online", "trailer": "Tráileres",
    "filtraciones_rumores": "Filtraciones y rumores", "comparativa_gta5": "GTA 5 vs GTA 6",
    "graficos_tecnologia": "Gráficos y tecnología", "polemica": "Polémicas", "humor_memes": "Memes",
    "reacciones": "Reacciones", "guias_trucos": "Guías y trucos", "ventas_negocio": "Ventas y negocio", "otros": "Otros",
}


def topic_trends(con) -> list[dict]:
    t24, t48 = hours_ago(24), hours_ago(48)
    cur, prev, score = defaultdict(int), defaultdict(int), defaultdict(float)
    items = defaultdict(list)
    for r in con.execute("""SELECT id,title,url,topics,published_at,COALESCE(overall_score,0) s,views
                            FROM videos WHERE published_at>=? AND COALESCE(is_related,1)=1""", (t48,)):
        for t in jload(r["topics"]):
            if r["published_at"] >= t24:
                cur[t] += 1
                score[t] += r["s"]
                items[t].append((r["s"], r["title"], r["url"]))
            else:
                prev[t] += 1
    for r in con.execute("""SELECT title,url,topics,published_at,source FROM news
                            WHERE published_at>=? AND COALESCE(is_related,1)=1""", (t48,)):
        for t in jload(r["topics"]):
            if r["published_at"] >= t24:
                cur[t] += 1
                score[t] += 40
            else:
                prev[t] += 1
    out = []
    for t in set(cur) | set(prev):
        n, p = cur.get(t, 0), prev.get(t, 0)
        top = sorted(items[t], reverse=True)[:3]
        out.append({
            "topic": t, "label": TOPIC_LABEL.get(t, t), "n_24h": n, "n_prev": p,
            "growth": round((n + 1) / (p + 1), 2), "score": round(score.get(t, 0), 1),
            "top": [{"title": x[1], "url": x[2]} for x in top],
        })
    out.sort(key=lambda x: (x["score"], x["n_24h"]), reverse=True)
    return out


def _add(con, key, type_, severity, title, message, entity_type=None, entity_id=None, url=None) -> bool:
    cur = con.execute(
        """INSERT OR IGNORE INTO alerts(dedupe_key,type,severity,title,message,entity_type,entity_id,url,created_at)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (key, type_, severity, title, message, entity_type, entity_id, url, iso()))
    return cur.rowcount > 0


def detect_alerts(con) -> int:
    a = cfg()["radar"]["alertas"]
    day = now().strftime("%Y-%m-%d")
    n = 0
    fmt = lambda x: f"{int(x):,}".replace(",", ".")  # noqa: E731
    # 1) vídeo viral
    for r in con.execute("""SELECT v.*, c.name cname FROM videos v LEFT JOIN creators c ON c.id=v.creator_id
                            WHERE v.velocity>=? AND v.published_at>=? AND COALESCE(v.is_related,1)=1""",
                         (a["viral_vistas_por_hora"], hours_ago(72))):
        sev = "critical" if r["velocity"] >= 5 * a["viral_vistas_por_hora"] else "high"
        n += _add(con, f"viral:{r['id']}:{day}", "viral_video", sev, f"Explotando: {r['title']}",
                  f"{r['cname']} · {fmt(r['velocity'])} vistas/hora · {fmt(r['views'])} vistas en total",
                  "video", r["id"], r["url"])
    # 2) creador emergente
    for r in con.execute("""SELECT v.*, c.name cname, c.subscribers subs FROM videos v JOIN creators c ON c.id=v.creator_id
                            WHERE c.subscribers IS NOT NULL AND c.subscribers<=? AND v.views>=? AND v.published_at>=?
                            AND COALESCE(v.is_related,1)=1""",
                         (a["emergente_max_suscriptores"], a["emergente_min_vistas"], hours_ago(72))):
        ratio = r["views"] / max(r["subs"], 1)
        if ratio >= a["emergente_ratio_vistas_subs"]:
            n += _add(con, f"emergente:{r['creator_id']}:{day}", "emerging_creator", "high" if ratio >= 10 else "medium",
                      f"Creador emergente: {r['cname']}",
                      f"«{r['title']}» lleva {fmt(r['views'])} vistas con {fmt(r['subs'])} suscriptores (x{ratio:.1f})",
                      "creator", r["creator_id"], r["url"])
    # 3) anuncio oficial (canal oficial o web de Rockstar)
    for r in con.execute("""SELECT v.* FROM videos v JOIN creators c ON c.id=v.creator_id
                            WHERE c.is_official=1 AND v.published_at>=?""", (hours_ago(24),)):
        n += _add(con, f"oficial:{r['id']}", "official_announcement", "critical", f"Rockstar publica: {r['title']}",
                  "Nuevo vídeo en un canal oficial.", "video", r["id"], r["url"])
    for r in con.execute("""SELECT * FROM news WHERE published_at>=? AND
                            (is_official=1 OR (verification='official' AND COALESCE(novelty,0)>=0.6))""", (hours_ago(24),)):
        n += _add(con, f"oficial:{r['id']}", "official_announcement", "critical" if r["is_official"] else "high",
                  f"Anuncio oficial: {r['title']}", r["ai_summary"] or r["source"], "news", r["id"], r["url"])
    # 4) noticia de alto impacto
    for r in con.execute("""SELECT * FROM news WHERE published_at>=? AND COALESCE(novelty,0)>=0.8
                            AND verification IN ('reported','official')""", (hours_ago(24),)):
        n += _add(con, f"noticia:{r['id']}", "breaking_news", "medium", f"Noticia: {r['title']}",
                  f"{r['source']} · {r['ai_summary'] or ''}", "news", r["id"], r["url"])
    # 5) desinformación / filtración con tracción
    for r in con.execute("""SELECT * FROM videos WHERE published_at>=? AND risk_level IN ('high','critical')
                            AND verification='unverified' AND velocity>=?""",
                         (hours_ago(72), a["viral_vistas_por_hora"] / 4)):
        kind = "copyright_risk" if r["content_type"] == "leak" else "misinformation"
        n += _add(con, f"riesgo:{r['id']}", kind, "high",
                  ("Filtración con tracción: " if kind == "copyright_risk" else "Posible bulo con tracción: ") + r["title"],
                  f"{fmt(r['velocity'])} vistas/hora · afirma: " + "; ".join(jload(r["key_claims"])[:2]),
                  "video", r["id"], r["url"])
    # 6) temas que se disparan (incluye pico de rumores y polémica)
    for t in topic_trends(con):
        if t["n_24h"] >= a["tema_min_items"] and t["growth"] >= a["tema_crecimiento"]:
            if t["topic"] == "filtraciones_rumores":
                typ, sev = "rumor_spike", "high"
            elif t["topic"] == "polemica":
                typ, sev = "controversy", "high"
            else:
                typ, sev = "trend_change", "medium"
            n += _add(con, f"tema:{t['topic']}:{day}", typ, sev, f"Tema en alza: {t['label']}",
                      f"{t['n_24h']} piezas en 24 h (x{t['growth']} respecto al día anterior)", "topic", t["topic"],
                      t["top"][0]["url"] if t["top"] else None)
    con.commit()
    print(f"  [alertas] {n} nuevas")
    return n


def pending_notifications(con) -> list:
    min_sev = SEV[cfg()["radar"]["alertas"].get("severidad_minima_notificar", "high")]
    rows = con.execute("SELECT * FROM alerts WHERE notified=0 ORDER BY id").fetchall()
    return [r for r in rows if SEV.get(r["severity"], 0) >= min_sev]


def mark_notified(con) -> None:
    con.execute("UPDATE alerts SET notified=1 WHERE notified=0")
    con.commit()

"""Radar masivo: vigila cientos de canales de YouTube por RSS, sin gastar cuota.

Cada canal tiene un feed gratuito (youtube.com/feeds/videos.xml?channel_id=UC…) con sus 15 últimos vídeos.
Lo leemos en paralelo, nos quedamos con los de GTA 6 nuevos y solo entonces pedimos sus estadísticas
a la API (1 unidad por cada 50 vídeos).

Qué canales se vigilan (máx. radar.vigilancia.max_canales), por orden de prioridad:
  1. oficiales y prioritarios de config.yaml
  2. los que han publicado ≥ min_videos_14d vídeos de GTA 6 en 14 días, por su mejor score
  3. creadores emergentes (pocos suscriptores, muchas vistas)
Se dejan de vigilar los que llevan 21 días sin publicar nada de GTA 6.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import feedparser
import requests

from .config import cfg
from .db import hours_ago
from .youtube import is_gta6

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
UA = {"User-Agent": "Mozilla/5.0 (GTA6-Radar personal)"}


def _conf() -> dict:
    return {"activar": True, "max_canales": 200, "min_videos_14d": 2, **(cfg()["radar"].get("vigilancia") or {})}


def actualizar_lista(con) -> int:
    """Recalcula qué canales se vigilan. Devuelve cuántos quedan vigilados."""
    c = _conf()
    a = cfg()["radar"]["alertas"]
    elegidos: list[str] = []

    def add(ids):
        for i in ids:
            if i not in elegidos and len(elegidos) < int(c["max_canales"]):
                elegidos.append(i)

    add(r["id"] for r in con.execute(
        "SELECT id FROM creators WHERE platform='youtube' AND (is_official=1 OR is_priority=1)"))
    add(r["creator_id"] for r in con.execute(
        """SELECT v.creator_id, COUNT(*) n, MAX(COALESCE(v.overall_score,0)) best FROM videos v
           WHERE v.platform='youtube' AND v.creator_id IS NOT NULL AND v.published_at>=? AND COALESCE(v.is_related,1)=1
           GROUP BY v.creator_id HAVING n>=? ORDER BY best DESC""", (hours_ago(14 * 24), int(c["min_videos_14d"]))))
    add(r["creator_id"] for r in con.execute(
        """SELECT v.creator_id, MAX(v.views*1.0/MAX(c.subscribers,1)) ratio FROM videos v
           JOIN creators c ON c.id=v.creator_id
           WHERE v.published_at>=? AND COALESCE(v.is_related,1)=1 AND c.subscribers<=? AND v.views>=?
           GROUP BY v.creator_id ORDER BY ratio DESC""",
        (hours_ago(14 * 24), a["emergente_max_suscriptores"], a["emergente_min_vistas"] / 4)))
    # los que ya estaban vigilados siguen si han publicado algo de GTA 6 en 21 días
    add(r["creator_id"] for r in con.execute(
        """SELECT DISTINCT v.creator_id FROM videos v JOIN creators c ON c.id=v.creator_id
           WHERE c.is_watched=1 AND v.published_at>=? AND COALESCE(v.is_related,1)=1""", (hours_ago(21 * 24),)))

    con.execute("UPDATE creators SET is_watched=0")
    con.executemany("UPDATE creators SET is_watched=1 WHERE id=?", [(i,) for i in elegidos])
    con.commit()
    return len(elegidos)


def _leer_feed(channel_id: str) -> list[dict]:
    try:
        r = requests.get(FEED.format(channel_id), headers=UA, timeout=15)
        if r.status_code != 200:
            return []
        parsed = feedparser.parse(r.content)
    except requests.RequestException:
        return []
    out = []
    for e in parsed.entries:
        vid = e.get("yt_videoid")
        if vid:
            out.append({"id": vid, "title": e.get("title", ""), "summary": e.get("summary", "") or ""})
    return out


def leer_feeds(con, channel_ids: list[str] | None = None) -> set[str]:
    """IDs de vídeos de GTA 6 que aún no tenemos, sacados de los feeds de los canales vigilados."""
    if channel_ids is None:
        channel_ids = [r["external_id"] for r in con.execute(
            "SELECT external_id FROM creators WHERE platform='youtube' AND is_watched=1")]
    if not channel_ids:
        return set()
    with ThreadPoolExecutor(max_workers=12) as pool:
        resultados = list(pool.map(_leer_feed, channel_ids))
    known = {r["external_id"] for r in con.execute("SELECT external_id FROM videos WHERE platform='youtube'")}
    nuevos = {v["id"] for vids in resultados for v in vids
              if v["id"] not in known and is_gta6(v["title"], v["summary"])}
    leidos = sum(1 for vids in resultados if vids)
    print(f"  [vigilancia] {leidos}/{len(channel_ids)} canales leídos por RSS · {len(nuevos)} vídeos nuevos de GTA 6")
    return nuevos

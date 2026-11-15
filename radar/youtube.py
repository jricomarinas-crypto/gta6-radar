"""Ingesta de YouTube (Data API v3) con control de cuota.

Cuota por defecto de Google (2026): 100 búsquedas/día, 100 subidas/día y 10.000 unidades
para todo lo demás. Aquí casi todo cuesta 1 unidad; las búsquedas van a su propio cupo.
"""
from __future__ import annotations

import re
from datetime import timedelta

import requests

from .config import cfg, env
from .db import hours_ago, iso, jload, kv_get, kv_set, now, parse_iso

API = "https://www.googleapis.com/youtube/v3/"


class Quota:
    units = 0
    searches = 0


def _api(endpoint: str, **params) -> dict:
    params["key"] = env("YOUTUBE_API_KEY", required=True)
    r = requests.get(API + endpoint, params=params, timeout=30)
    if endpoint == "search":
        Quota.searches += 1
    else:
        Quota.units += 1
    if r.status_code == 403 and "quota" in r.text.lower():
        raise QuotaExceeded(endpoint)
    r.raise_for_status()
    return r.json()


class QuotaExceeded(RuntimeError):
    pass


# ---------------------------------------------------------------- utilidades
_GTA_RE = None


def is_gta6(*texts: str) -> bool:
    global _GTA_RE
    if _GTA_RE is None:
        terms = cfg()["radar"]["filtro_gta6"]
        pat = "|".join(re.escape(t).replace(r"\ ", r"\s?") for t in terms)
        _GTA_RE = re.compile(rf"(?<![\w]){pat}(?![\w])", re.I)
    return bool(_GTA_RE.search(" ".join(t or "" for t in texts)))


def parse_duration(s: str | None) -> int:
    if not s:
        return 0
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s)
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def _batches(seq, n=50):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


# ---------------------------------------------------------------- canales
def resolve_handles(con, handles: list[str]) -> dict[str, str]:
    """@handle → channelId (cacheado en la base de datos)."""
    out = {}
    for h in handles:
        h = h.strip()
        if not h:
            continue
        key = f"handle:{h.lower()}"
        cid = kv_get(con, key)
        if not cid:
            try:
                data = _api("channels", part="id", forHandle=h)
                items = data.get("items") or []
                if not items:
                    print(f"  [YouTube] no encuentro el canal {h}")
                    continue
                cid = items[0]["id"]
                kv_set(con, key, cid)
            except requests.HTTPError as e:
                print(f"  [YouTube] error resolviendo {h}: {e}")
                continue
        out[h] = cid
    con.commit()
    return out


def refresh_channels(con, channel_ids: list[str], force: bool = False) -> None:
    stale = []
    for cid in set(channel_ids):
        row = con.execute("SELECT updated_at FROM creators WHERE id=?", (f"youtube:{cid}",)).fetchone()
        upd = parse_iso(row["updated_at"]) if row else None
        if force or not upd or now() - upd > timedelta(hours=24):
            stale.append(cid)
    for batch in _batches(stale):
        data = _api("channels", part="snippet,statistics", id=",".join(batch), maxResults=50)
        for it in data.get("items", []):
            sn, st = it.get("snippet", {}), it.get("statistics", {})
            con.execute(
                """INSERT INTO creators(id,platform,external_id,handle,name,avatar_url,description,subscribers,
                       video_count,total_views,country,language,first_seen_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET handle=excluded.handle,name=excluded.name,
                       avatar_url=excluded.avatar_url,description=excluded.description,
                       subscribers=excluded.subscribers,video_count=excluded.video_count,
                       total_views=excluded.total_views,country=excluded.country,updated_at=excluded.updated_at""",
                (
                    f"youtube:{it['id']}", "youtube", it["id"], sn.get("customUrl"), sn.get("title"),
                    ((sn.get("thumbnails") or {}).get("default") or {}).get("url"),
                    (sn.get("description") or "")[:500],
                    None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0) or 0),
                    int(st.get("videoCount", 0) or 0), int(st.get("viewCount", 0) or 0),
                    sn.get("country"), sn.get("defaultLanguage"), iso(), iso(),
                ),
            )
    con.commit()


# ---------------------------------------------------------------- descubrimiento
def discover_by_search(con) -> set[str]:
    rc = cfg()["radar"]
    kws = list(rc["palabras_clave"])
    # palabras clave nuevas que propone el Agente de Estrategia (máx. 6, siempre de GTA 6)
    for kw in jload(kv_get(con, "palabras_extra"), [])[:6]:
        if kw not in kws and is_gta6(kw):
            kws.append(kw)
    n = int(rc.get("busquedas_por_ejecucion", 3))
    idx = int(kv_get(con, "search_idx", 0))
    found = set()
    after = hours_ago(rc.get("ventana_busqueda_horas", 48))
    for i in range(n):
        kw = kws[(idx + i) % len(kws)]
        # alterna: búsqueda en español y búsqueda global
        lang = "es" if (idx + i) % 2 == 0 else None
        params = dict(part="id", type="video", q=kw, publishedAfter=after, order="viewCount", maxResults=50)
        if lang:
            params["relevanceLanguage"] = lang
        try:
            data = _api("search", **params)
        except QuotaExceeded:
            print("  [YouTube] cupo de búsquedas agotado por hoy")
            break
        ids = [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]
        print(f"  [YouTube] búsqueda «{kw}»{' (es)' if lang else ''}: {len(ids)} vídeos")
        found.update(ids)
    kv_set(con, "search_idx", (idx + n) % len(kws))
    con.commit()
    return found


def discover_trending(con) -> list[dict]:
    """Tendencias de la categoría Gaming por país (1 unidad cada una)."""
    items = []
    for region in cfg()["radar"].get("regiones_tendencias", []):
        try:
            data = _api("videos", part="snippet,statistics,contentDetails", chart="mostPopular",
                        videoCategoryId="20", regionCode=region, maxResults=50)
        except requests.HTTPError as e:
            print(f"  [YouTube] tendencias {region}: {e}")
            continue
        hits = [it for it in data.get("items", []) if is_gta6(it["snippet"].get("title"), it["snippet"].get("description"),
                                                              " ".join(it["snippet"].get("tags") or []))]
        for it in hits:
            it["_found_via"] = f"tendencias {region}"
        print(f"  [YouTube] tendencias Gaming {region}: {len(hits)} de GTA 6")
        items.extend(hits)
    return items


def discover_channels(con) -> tuple[set[str], set[str]]:
    """Últimas subidas de canales oficiales y prioritarios (1 unidad por canal)."""
    rc = cfg()["radar"]
    official = resolve_handles(con, rc.get("canales_oficiales") or [])
    priority = resolve_handles(con, rc.get("creadores_prioritarios") or [])
    refresh_channels(con, list(official.values()) + list(priority.values()))  # crea las fichas antes de marcarlas
    for cid in official.values():
        con.execute("UPDATE creators SET is_official=1 WHERE id=?", (f"youtube:{cid}",))
    for cid in priority.values():
        con.execute("UPDATE creators SET is_priority=1 WHERE id=?", (f"youtube:{cid}",))
    ids, official_videos = set(), set()
    for cid in list(official.values()) + list(priority.values()):
        try:
            data = _api("playlistItems", part="contentDetails", playlistId="UU" + cid[2:], maxResults=15)
        except requests.HTTPError as e:
            print(f"  [YouTube] canal {cid}: {e}")
            continue
        vids = [it["contentDetails"]["videoId"] for it in data.get("items", [])]
        ids.update(vids)
        if cid in official.values():
            official_videos.update(vids)
    con.commit()
    return ids, official_videos


# ---------------------------------------------------------------- guardar / actualizar
def _upsert_video(con, it: dict, found_via: str, force_related: bool = False) -> bool:
    sn, st, cd = it.get("snippet", {}), it.get("statistics", {}), it.get("contentDetails", {})
    title, desc = sn.get("title", ""), sn.get("description", "")
    tags = " ".join(sn.get("tags") or [])
    vid = f"youtube:{it['id']}"
    exists = con.execute("SELECT 1 FROM videos WHERE id=?", (vid,)).fetchone()
    if not exists and not force_related and not is_gta6(title, desc, tags):
        return False
    dur = parse_duration(cd.get("duration"))
    is_short = 1 if dur and (dur <= 61 or (dur <= 180 and "#short" in (title + desc).lower())) else 0
    views, likes, comms = (int(st.get(k, 0) or 0) for k in ("viewCount", "likeCount", "commentCount"))
    ts = iso()
    con.execute(
        """INSERT INTO videos(id,platform,external_id,creator_id,title,description,url,thumbnail_url,published_at,
               duration_s,is_short,language,found_via,views,likes,comments,first_seen_at,last_scraped_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET title=excluded.title,description=excluded.description,
               thumbnail_url=excluded.thumbnail_url,views=excluded.views,likes=excluded.likes,
               comments=excluded.comments,last_scraped_at=excluded.last_scraped_at""",
        (
            vid, "youtube", it["id"], f"youtube:{sn.get('channelId')}", title, desc[:2000],
            f"https://www.youtube.com/watch?v={it['id']}",
            ((sn.get("thumbnails") or {}).get("medium") or {}).get("url"),
            sn.get("publishedAt"), dur, is_short,
            (sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "")[:5], found_via,
            views, likes, comms, ts, ts,
        ),
    )
    con.execute("INSERT OR REPLACE INTO snapshots(video_id,captured_at,views,likes,comments) VALUES(?,?,?,?,?)",
                (vid, ts, views, likes, comms))
    return True


def fetch_and_store(con, video_ids, found_via: str, force_ids: set[str] | None = None) -> int:
    force_ids = force_ids or set()
    stored = 0
    for batch in _batches(video_ids):
        data = _api("videos", part="snippet,statistics,contentDetails", id=",".join(batch), maxResults=50)
        for it in data.get("items", []):
            if _upsert_video(con, it, found_via, force_related=it["id"] in force_ids):
                stored += 1
    con.commit()
    return stored


def compute_velocity(con, video_id: str) -> float:
    snaps = con.execute("SELECT captured_at, views FROM snapshots WHERE video_id=? ORDER BY captured_at DESC LIMIT 12",
                        (video_id,)).fetchall()
    if not snaps:
        return 0.0
    latest_t, latest_v = parse_iso(snaps[0]["captured_at"]), snaps[0]["views"] or 0
    # busca un snapshot de hace ≥ 50 min para medir el ritmo reciente
    for s in snaps[1:]:
        t = parse_iso(s["captured_at"])
        dh = (latest_t - t).total_seconds() / 3600
        if dh >= 0.8:
            return max(0.0, (latest_v - (s["views"] or 0)) / dh)
    row = con.execute("SELECT published_at FROM videos WHERE id=?", (video_id,)).fetchone()
    pub = parse_iso(row["published_at"]) if row else None
    if not pub:
        return 0.0
    hours = max(1.0, (latest_t - pub).total_seconds() / 3600)
    return latest_v / hours


def run_ingestion(con) -> dict:
    stats = {}
    rc = cfg()["radar"]
    # 1) descubrir
    search_ids = discover_by_search(con)
    trend_items = discover_trending(con)
    chan_ids, official_ids = discover_channels(con)
    # 2) guardar lo nuevo
    for it in trend_items:
        _upsert_video(con, it, it["_found_via"])
    con.commit()
    known = {r["external_id"] for r in con.execute("SELECT external_id FROM videos")}
    new_search = [i for i in search_ids if i not in known]
    new_chan = [i for i in chan_ids if i not in known]
    stats["nuevos_busqueda"] = fetch_and_store(con, new_search, "búsqueda")
    stats["nuevos_canales"] = fetch_and_store(con, new_chan, "canal vigilado", force_ids=official_ids)
    stats["tendencias"] = len(trend_items)
    # 3) refrescar métricas de los vídeos recientes que ya seguimos
    recent = [r["external_id"] for r in con.execute(
        "SELECT external_id FROM videos WHERE platform='youtube' AND published_at >= ? AND last_scraped_at < ?",
        (hours_ago(rc.get("seguimiento_dias", 7) * 24), hours_ago(0.5)))]
    fetch_and_store(con, recent, "seguimiento")
    stats["actualizados"] = len(recent)
    # 4) velocidades
    for r in con.execute("SELECT id FROM videos WHERE published_at >= ?", (hours_ago(rc.get("seguimiento_dias", 7) * 24),)).fetchall():
        con.execute("UPDATE videos SET velocity=? WHERE id=?", (compute_velocity(con, r["id"]), r["id"]))
    con.commit()
    # 5) canales de los vídeos
    cids = [r["creator_id"].split(":", 1)[1] for r in con.execute(
        "SELECT DISTINCT creator_id FROM videos WHERE creator_id IS NOT NULL AND published_at >= ?", (hours_ago(7 * 24),))]
    refresh_channels(con, cids)
    stats["unidades_api"] = Quota.units
    stats["busquedas_api"] = Quota.searches
    return stats


def fetch_top_comments(con, video_ids: list[str], per_video: int = 60) -> int:
    n = 0
    for vid in video_ids:
        ext = vid.split(":", 1)[1]
        try:
            data = _api("commentThreads", part="snippet", videoId=ext, order="relevance",
                        maxResults=min(100, per_video), textFormat="plainText")
        except requests.HTTPError:
            continue  # comentarios desactivados
        for it in data.get("items", []):
            top = it["snippet"]["topLevelComment"]["snippet"]
            con.execute("INSERT OR REPLACE INTO comments(id,video_id,text,likes,published_at) VALUES(?,?,?,?,?)",
                        (it["id"], vid, (top.get("textDisplay") or "")[:600], top.get("likeCount", 0), top.get("publishedAt")))
            n += 1
    con.commit()
    return n

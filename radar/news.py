"""Medios por RSS (Google News + webs de videojuegos) y Reddit opcional."""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from .config import cfg, env
from .db import iso
from .youtube import is_gta6

OFFICIAL_DOMAINS = ("rockstargames.com", "take2games.com")
UA = {"User-Agent": "Mozilla/5.0 (GTA6-Radar personal; +https://github.com)"}


def _date(entry) -> str | None:
    for k in ("published_parsed", "updated_parsed"):
        t = entry.get(k)
        if t:
            return iso(datetime.fromtimestamp(time.mktime(t), tz=timezone.utc))
    for k in ("published", "updated"):
        if entry.get(k):
            try:
                return iso(parsedate_to_datetime(entry[k]))
            except (TypeError, ValueError):
                pass
    return None


def ingest_rss(con) -> int:
    new = 0
    for feed in cfg()["radar"].get("medios_rss", []):
        try:
            r = requests.get(feed["url"], headers=UA, timeout=25)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
        except requests.RequestException as e:
            print(f"  [RSS] {feed['nombre']}: {e}")
            continue
        count = 0
        for e in parsed.entries[:80]:
            title, link = e.get("title", ""), e.get("link", "")
            summary = e.get("summary", "") or ""
            if not is_gta6(title, summary):
                continue
            source = feed["nombre"]
            # Google News pone el medio al final del título: "Titular - Medio"
            if "news.google" in feed["url"]:
                src = (e.get("source") or {}).get("title")
                if src:
                    source = src
            nid = hashlib.sha1((link or title).encode()).hexdigest()[:16]
            is_off = int(any(d in link for d in OFFICIAL_DOMAINS) or "rockstar games" in source.lower())
            cur = con.execute(
                """INSERT OR IGNORE INTO news(id,source,title,url,published_at,summary,language,is_official,first_seen_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (nid, source, title, link, _date(e), _strip(summary)[:600], feed.get("idioma"), is_off, iso()),
            )
            count += cur.rowcount
        print(f"  [RSS] {feed['nombre']}: {count} nuevas")
        new += count
    con.commit()
    return new


def _strip(html: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").strip()


# ------------------------------------------------------------------ Reddit (opcional)
SUBREDDITS = ["GTA6", "GrandTheftAutoVI", "GTA", "GamingLeaksAndRumours"]


def ingest_reddit(con) -> int:
    """Solo funciona con credenciales de la API de Reddit YA aprobadas (Reddit cerró el alta libre en 2025)."""
    cid, secret = env("REDDIT_CLIENT_ID"), env("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        return 0
    try:
        tok = requests.post("https://www.reddit.com/api/v1/access_token", auth=(cid, secret),
                            data={"grant_type": "client_credentials"},
                            headers={"User-Agent": "gta6-radar/1.0"}, timeout=20).json()["access_token"]
    except Exception as e:  # noqa: BLE001
        print(f"  [Reddit] sin acceso: {e}")
        return 0
    new = 0
    h = {"Authorization": f"bearer {tok}", "User-Agent": "gta6-radar/1.0"}
    for sub in SUBREDDITS:
        try:
            data = requests.get(f"https://oauth.reddit.com/r/{sub}/hot", params={"limit": 50}, headers=h, timeout=20).json()
        except Exception as e:  # noqa: BLE001
            print(f"  [Reddit] r/{sub}: {e}")
            continue
        for ch in data.get("data", {}).get("children", []):
            p = ch["data"]
            if sub not in ("GTA6", "GrandTheftAutoVI") and not is_gta6(p.get("title"), p.get("selftext")):
                continue
            nid = "reddit_" + p["id"]
            title = f"{p.get('title')} (r/{sub} · {p.get('score', 0)} votos · {p.get('num_comments', 0)} coment.)"
            cur = con.execute(
                """INSERT INTO news(id,source,title,url,published_at,summary,language,first_seen_at)
                   VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title""",
                (nid, f"Reddit r/{sub}", title, "https://www.reddit.com" + p.get("permalink", ""),
                 iso(datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc)),
                 (p.get("selftext") or "")[:600], "en", iso()),
            )
            new += max(0, cur.rowcount)
    con.commit()
    print(f"  [Reddit] {new} publicaciones")
    return new

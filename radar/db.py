"""Base de datos SQLite del Radar (un único archivo: data/radar.db)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from .config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS creators (
    id TEXT PRIMARY KEY,              -- youtube:UCxxxx
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    handle TEXT, name TEXT, avatar_url TEXT, description TEXT,
    subscribers INTEGER, video_count INTEGER, total_views INTEGER,
    country TEXT, language TEXT,
    is_priority INTEGER DEFAULT 0, is_official INTEGER DEFAULT 0,
    authority_score REAL,
    first_seen_at TEXT, updated_at TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,              -- youtube:VIDEOID
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    creator_id TEXT,
    title TEXT, description TEXT, url TEXT, thumbnail_url TEXT,
    published_at TEXT, duration_s INTEGER, is_short INTEGER DEFAULT 0,
    language TEXT, found_via TEXT,
    views INTEGER DEFAULT 0, likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
    velocity REAL DEFAULT 0,          -- vistas/hora recientes
    -- clasificación IA
    is_related INTEGER, content_type TEXT, topics TEXT, entities TEXT,
    sentiment TEXT, risk_level TEXT, novelty REAL, summary TEXT,
    key_claims TEXT, verification TEXT, classified_at TEXT,
    -- scores 0-100
    momentum_score REAL, engagement_score REAL, relevance_score REAL,
    authority_score REAL, novelty_score REAL, risk_score REAL, overall_score REAL,
    first_seen_at TEXT, last_scraped_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_videos_pub ON videos(published_at);
CREATE INDEX IF NOT EXISTS idx_videos_score ON videos(overall_score);

CREATE TABLE IF NOT EXISTS snapshots (
    video_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    views INTEGER, likes INTEGER, comments INTEGER,
    PRIMARY KEY (video_id, captured_at)
);

CREATE TABLE IF NOT EXISTS news (
    id TEXT PRIMARY KEY,
    source TEXT, title TEXT, url TEXT, published_at TEXT, summary TEXT, language TEXT,
    is_official INTEGER DEFAULT 0,
    is_related INTEGER, content_type TEXT, topics TEXT, entities TEXT, sentiment TEXT,
    risk_level TEXT, novelty REAL, ai_summary TEXT, key_claims TEXT, verification TEXT,
    classified_at TEXT, first_seen_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_news_pub ON news(published_at);

CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY, video_id TEXT, text TEXT, likes INTEGER, published_at TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT UNIQUE,
    type TEXT, severity TEXT, title TEXT, message TEXT,
    entity_type TEXT, entity_id TEXT, url TEXT,
    created_at TEXT, notified INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS briefings (
    date TEXT PRIMARY KEY, markdown TEXT, data TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY, date TEXT, format TEXT, title TEXT, topic_keys TEXT,
    youtube_id TEXT, shorts TEXT, sources TEXT, created_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT, started_at TEXT, finished_at TEXT, stats TEXT, error TEXT
);

CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
"""


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or now()).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def hours_ago(h: float) -> str:
    return iso(now() - timedelta(hours=h))


def connect(path=DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def jdump(x) -> str:
    return json.dumps(x, ensure_ascii=False)


def jload(s, default=None):
    if not s:
        return default if default is not None else []
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return default if default is not None else []


def kv_get(con, k, default=None):
    row = con.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return row["v"] if row else default


def kv_set(con, k, v):
    con.execute("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))


def prune(con, snapshot_days: int = 14, video_days: int = 45):
    """Mantiene la base de datos pequeña (va en una rama de Git)."""
    con.execute("DELETE FROM snapshots WHERE captured_at < ?", (hours_ago(snapshot_days * 24),))
    old = hours_ago(video_days * 24)
    con.execute("DELETE FROM comments WHERE video_id IN (SELECT id FROM videos WHERE published_at < ?)", (old,))
    con.execute("DELETE FROM videos WHERE published_at < ? AND COALESCE(overall_score,0) < 60", (old,))
    con.execute("DELETE FROM news WHERE published_at < ?", (old,))
    con.execute("DELETE FROM runs WHERE started_at < ?", (hours_ago(30 * 24),))
    con.commit()

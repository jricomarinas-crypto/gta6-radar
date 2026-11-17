"""Fuentes vigiladas (Sistema › Fuentes vigiladas). Público: no contiene nada privado ni claves.

Qué vigila el Radar según config.yaml y cuánto ha traído cada fuente (por la fecha en que el Radar lo vio):
- Medios RSS: noticias por medio. Los feeds de Google News guardan el medio original como fuente, así que su
  aportación no se puede atribuir al feed: se dice así en vez de inventar un número.
- YouTube: vídeos por vía de entrada (búsqueda, canal vigilado, tendencias por país).
"""
from __future__ import annotations

from .config import cfg
from .db import hours_ago


def _cuenta(con, sql: str, args: tuple) -> dict:
    return {"h24": con.execute(sql, (*args, hours_ago(24))).fetchone()[0],
            "d7": con.execute(sql, (*args, hours_ago(24 * 7))).fetchone()[0]}


def resumen(con) -> dict:
    r = cfg()["radar"]
    rss = []
    for f in r.get("medios_rss", []):
        google = "news.google" in f["url"]
        rss.append({"nombre": f["nombre"], "url": f["url"], "idioma": f.get("idioma"), "google_news": google,
                    "cuenta": None if google else _cuenta(
                        con, "SELECT COUNT(*) FROM news WHERE source=? AND COALESCE(first_seen_at, published_at)>=?", (f["nombre"],))})
    vias = [x["v"] for x in con.execute("SELECT DISTINCT found_via v FROM videos WHERE found_via IS NOT NULL ORDER BY 1")]
    youtube = [{"via": v, "cuenta": _cuenta(con, "SELECT COUNT(*) FROM videos WHERE found_via=? AND first_seen_at>=?", (v,))}
               for v in vias]
    vig = r.get("vigilancia") or {}
    return {
        "rss": rss,
        "youtube_vias": youtube,
        "palabras_clave": r.get("palabras_clave", []),
        "busquedas_por_ejecucion": r.get("busquedas_por_ejecucion"),
        "regiones_tendencias": r.get("regiones_tendencias", []),
        "canales_oficiales": r.get("canales_oficiales", []),
        "creadores_prioritarios": r.get("creadores_prioritarios", []),
        "vigilancia": {"activar": vig.get("activar", True), "max_canales": vig.get("max_canales", 200),
                       "min_videos_14d": vig.get("min_videos_14d", 2),
                       "vigilados": con.execute("SELECT COUNT(*) FROM creators WHERE is_watched=1").fetchone()[0]},
        "noticias_total": _cuenta(con, "SELECT COUNT(*) FROM news WHERE COALESCE(first_seen_at, published_at)>=?", ()),
        "videos_total": _cuenta(con, "SELECT COUNT(*) FROM videos WHERE first_seen_at>=?", ()),
    }

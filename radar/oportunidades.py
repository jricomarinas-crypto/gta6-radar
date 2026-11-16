"""Oportunidades: qué hacer hoy para crecer, a partir de lo que mide el Radar.

- Temas con hueco: mucha demanda (vistas/hora) y poca oferta en español.
- Formatos que funcionan: vistas/hora medias por tipo de contenido, Short o vídeo largo.
- Títulos que rinden por encima de lo normal para el tamaño del canal (inspiración, no para copiar).
- Creadores a seguir (y si ya están vigilados por el Radar masivo).
- 3 ideas de vídeo para hoy (IA, una vez al día con el briefing).
"""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import median

from .config import cfg
from .db import hours_ago, jdump, jload, kv_get, kv_set, now
from .trends import TOPIC_LABEL

DURACION = [(0, 61, "Short (≤ 1 min)"), (61, 300, "1-5 min"), (300, 600, "5-10 min"), (600, 1200, "10-20 min"),
            (1200, 10 ** 9, "Más de 20 min")]


def _rinde(velocity: float, subs: int | None) -> float:
    # misma idea que el momentum de scoring.py: vistas/hora corregidas por el tamaño del canal
    return (velocity or 0) / math.sqrt((subs or 0) + 1000)


def calcular(con, horas: int = 48) -> dict:
    rows = con.execute(
        """SELECT v.*, c.name cname, c.subscribers subs, c.is_watched FROM videos v
           LEFT JOIN creators c ON c.id=v.creator_id
           WHERE v.published_at>=? AND COALESCE(v.is_related,1)=1""", (hours_ago(horas),)).fetchall()
    # 1) temas con hueco
    dem, n_all, n_es, top = defaultdict(float), defaultdict(int), defaultdict(int), {}
    for r in rows:
        for t in jload(r["topics"], []) or []:
            if t == "otros":
                continue
            dem[t] += r["velocity"] or 0
            n_all[t] += 1
            if (r["language"] or "").startswith("es"):
                n_es[t] += 1
            if t not in top or (r["velocity"] or 0) > (top[t]["velocity"] or 0):
                top[t] = r
    hueco = {t: dem[t] / (1 + n_es[t]) for t in dem}
    mx = max(hueco.values(), default=0) or 1
    temas = [{"topic": t, "label": TOPIC_LABEL.get(t, t), "demanda": round(dem[t]), "videos": n_all[t],
              "videos_es": n_es[t], "hueco": round(hueco[t] / mx * 100), "ejemplo": top[t]["title"], "url": top[t]["url"]}
             for t in sorted(hueco, key=hueco.get, reverse=True)[:8]]

    # 2) formatos y duración
    fmt = defaultdict(list)
    for r in rows:
        fmt[(r["content_type"] or "other", "Short" if r["is_short"] else "Largo")].append(r["velocity"] or 0)
    formatos = sorted(({"tipo": k[0], "formato": k[1], "videos": len(v), "vel_media": round(sum(v) / len(v))}
                       for k, v in fmt.items() if len(v) >= 2), key=lambda x: -x["vel_media"])[:8]
    dur = defaultdict(list)
    for r in rows:
        d = r["duration_s"] or 0
        for lo, hi, lab in DURACION:
            if lo < d <= hi or (lo == 0 and d == 0):
                dur[lab].append(r["velocity"] or 0)
                break
    duracion = [{"tramo": lab, "videos": len(dur[lab]), "vel_media": round(sum(dur[lab]) / len(dur[lab]))}
                for _, _, lab in DURACION if dur[lab]]

    # 3) títulos que rinden por encima de lo normal
    ratios = [_rinde(r["velocity"], r["subs"]) for r in rows if (r["velocity"] or 0) > 0]
    base = median(ratios) if ratios else 1
    titulos = sorted(({"title": r["title"], "channel": r["cname"], "url": r["url"], "velocity": round(r["velocity"] or 0),
                       "subs": r["subs"], "x": round(_rinde(r["velocity"], r["subs"]) / (base or 1), 1),
                       "is_short": bool(r["is_short"])} for r in rows if (r["velocity"] or 0) > 0),
                     key=lambda x: -x["x"])
    vistos, titulos_top = set(), []
    for t in titulos:  # un título por canal, para variedad
        if t["channel"] not in vistos:
            vistos.add(t["channel"])
            titulos_top.append(t)
        if len(titulos_top) == 8:
            break

    # 4) creadores a seguir
    por_canal = defaultdict(list)
    for r in rows:
        if r["creator_id"]:
            por_canal[r["creator_id"]].append(r)
    creadores = []
    for cid, vs in por_canal.items():
        best = max(vs, key=lambda r: _rinde(r["velocity"], r["subs"]))
        creadores.append({"name": best["cname"], "subs": best["subs"], "videos": len(vs),
                          "vel_max": round(max(r["velocity"] or 0 for r in vs)),
                          "x": round(_rinde(best["velocity"], best["subs"]) / (base or 1), 1),
                          "vigilado": bool(best["is_watched"]), "url": f"https://www.youtube.com/channel/{cid.split(':', 1)[1]}"})
    creadores.sort(key=lambda c: -c["x"])

    ideas = jload(kv_get(con, "ideas_hoy"), {}) or {}
    vigilados = con.execute("SELECT COUNT(*) FROM creators WHERE is_watched=1").fetchone()[0]
    return {"temas": temas, "formatos": formatos, "duracion": duracion, "titulos": titulos_top,
            "creadores": creadores[:12], "ideas": ideas.get("ideas", []), "ideas_fecha": ideas.get("fecha"),
            "vigilados": vigilados, "max_vigilados": (cfg()["radar"].get("vigilancia") or {}).get("max_canales", 200)}


def generar_ideas(con) -> int:
    """3 ideas de vídeo para hoy (IA). Se guardan en kv para el panel, el podcast y los Shorts."""
    from .llm import ask_json  # aquí: el panel no necesita la librería de IA

    datos = calcular(con)
    ctx = {k: datos[k] for k in ("temas", "formatos", "duracion", "titulos")}
    prompt = f"""Eres el estratega de «{cfg()['canal']['nombre']}», canal de YouTube y TikTok sobre GTA 6 para público
hispano de Latinoamérica. El canal hace contenido PROPIO: un podcast diario con dos presentadores (Leo, analista; Sofi, fan)
y Shorts verticales. No usa clips de otros creadores ni de Rockstar.

DATOS DEL RADAR (últimas 48 h):
{jdump(ctx)}

Propón 3 ideas de vídeo para HOY que aprovechen los temas con hueco (mucha demanda, poca oferta en español)
y los formatos que mejor rinden. Inspírate en por qué funcionan los títulos que rinden, pero NO los copies.
Nada de clickbait falso: el título tiene que poder cumplirse con datos verificables.

Devuelve SOLO JSON:
{{"ideas": [{{"titulo": "≤ 70 caracteres, con 'GTA 6'", "formato": "short|episodio",
  "tema": "slug del tema", "por_que": "1 frase con el dato del radar que lo justifica"}}]}}"""
    ideas = (ask_json(prompt, max_tokens=1500) or {}).get("ideas", [])[:3]
    kv_set(con, "ideas_hoy", jdump({"fecha": now().strftime("%Y-%m-%d"), "ideas": ideas}))
    con.commit()
    return len(ideas)

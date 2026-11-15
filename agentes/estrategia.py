"""Agente de Estrategia: cada semana mira qué funciona en TU canal y reorienta el podcast y el Radar.

    python -m agentes.estrategia

- Lee las estadísticas públicas de tus episodios y Shorts (vistas, likes, comentarios, vistas/hora).
- Lee los comentarios de tus vídeos: preguntas de tu audiencia y respuestas sugeridas (no publica nada).
- Cruza todo con las tendencias de 7 días del Radar.
- Guarda recomendaciones que el podcast usa al elegir formato y tema, y añade palabras clave al Radar.
"""
from __future__ import annotations

import requests

from radar.config import cfg, env
from radar.db import connect, hours_ago, iso, jdump, jload, kv_set, now, parse_iso
from radar.llm import ask_json
from radar.notify import send
from radar.trends import TOPIC_LABEL

API = "https://www.googleapis.com/youtube/v3/"


def _yt(endpoint, **params):
    params["key"] = env("YOUTUBE_API_KEY", required=True)
    r = requests.get(API + endpoint, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def own_videos(con, days=35) -> list[dict]:
    eps = con.execute("SELECT * FROM episodes WHERE date>=? ORDER BY date DESC", (hours_ago(days * 24)[:10],)).fetchall()
    meta = {}
    for e in eps:
        if e["youtube_id"]:
            meta[e["youtube_id"]] = {"tipo": "episodio", "formato": e["format"], "temas": jload(e["topic_keys"]), "fecha": e["date"]}
        for sid in jload(e["shorts"]):
            meta[sid] = {"tipo": "short", "formato": e["format"], "temas": jload(e["topic_keys"]), "fecha": e["date"]}
    out = []
    ids = list(meta)
    for i in range(0, len(ids), 50):
        data = _yt("videos", part="snippet,statistics", id=",".join(ids[i:i + 50]))
        for it in data.get("items", []):  # los vídeos privados no aparecen: solo cuentan los publicados
            st = it.get("statistics", {})
            pub = parse_iso(it["snippet"].get("publishedAt"))
            hours = max(1.0, (now() - pub).total_seconds() / 3600) if pub else 1.0
            views = int(st.get("viewCount", 0) or 0)
            out.append({**meta[it["id"]], "id": it["id"], "titulo": it["snippet"].get("title"), "vistas": views,
                        "likes": int(st.get("likeCount", 0) or 0), "comentarios": int(st.get("commentCount", 0) or 0),
                        "horas_publicado": round(hours), "vistas_hora": round(views / hours, 1)})
    return out


def own_comments(videos: list[dict], per_video=40) -> list[dict]:
    out = []
    for v in sorted(videos, key=lambda x: x["comentarios"], reverse=True)[:8]:
        if not v["comentarios"]:
            continue
        try:
            data = _yt("commentThreads", part="snippet", videoId=v["id"], order="relevance", maxResults=per_video,
                       textFormat="plainText")
        except requests.HTTPError:
            continue
        for it in data.get("items", []):
            sn = it["snippet"]["topLevelComment"]["snippet"]
            out.append({"video": v["titulo"], "texto": (sn.get("textDisplay") or "")[:300], "likes": sn.get("likeCount", 0)})
    return out


def radar_week(con) -> list[dict]:
    counts = {}
    for r in con.execute("SELECT topics, COALESCE(overall_score,0) s FROM videos WHERE published_at>=? "
                         "AND COALESCE(is_related,1)=1", (hours_ago(7 * 24),)):
        for t in jload(r["topics"]):
            c = counts.setdefault(t, {"tema": TOPIC_LABEL.get(t, t), "videos": 0, "score_total": 0})
            c["videos"] += 1
            c["score_total"] += r["s"]
    return sorted(counts.values(), key=lambda x: x["score_total"], reverse=True)[:15]


def main():
    con = connect()
    videos = own_videos(con) if env("YOUTUBE_API_KEY") else []
    comments = own_comments(videos) if videos else []
    trends = radar_week(con)
    formats = [f["id"] for f in cfg()["podcast"]["formatos"]]
    res = ask_json(
        f"""Eres el AGENTE DE ESTRATEGIA de «{cfg()['canal']['nombre']}», podcast diario de GTA 6 en YouTube para Latinoamérica.
Fecha: {now().strftime('%d/%m/%Y')}.

RENDIMIENTO DE NUESTROS VÍDEOS PUBLICADOS (últimas 5 semanas; vacío = aún no hay vídeos públicos):
{jdump(videos)}

COMENTARIOS DE NUESTRA AUDIENCIA:
{jdump(comments[:150])}

TENDENCIAS DEL RADAR (7 días):
{jdump(trends)}

FORMATOS POSIBLES: {formats}

Analiza qué funciona y qué no (por formato, tema y Short vs episodio; usa vistas/hora para comparar vídeos de distinta edad).
No inventes datos: si hay pocos vídeos, dilo y apóyate en las tendencias del Radar.
Devuelve SOLO JSON:
{{"resumen": "3 frases", "que_funciona": ["..."], "que_no_funciona": ["..."],
  "formatos_prioridad": ["ids de formato de más a menos recomendable"],
  "temas_prioritarios": ["..."], "temas_evitar": ["..."],
  "ideas_episodios": [{{"titulo": "...", "formato": "id", "por_que": "..."}}],
  "preguntas_audiencia": ["preguntas reales de nuestros comentarios"],
  "respuestas_sugeridas": [{{"comentario": "...", "respuesta": "respuesta breve y cercana"}}],
  "palabras_clave_radar": ["hasta 4 búsquedas nuevas de YouTube que deberíamos vigilar, todas con 'GTA 6'"],
  "acciones_para_el_dueno": ["3 acciones concretas para esta semana"]}}""",
        model=cfg()["ia"]["modelo_principal"], max_tokens=5000)
    res["fecha"] = iso()
    res["n_videos_analizados"] = len(videos)
    kv_set(con, "estrategia", jdump(res))
    kws = [k for k in res.get("palabras_clave_radar", []) if isinstance(k, str) and "gta" in k.lower()][:4]
    kv_set(con, "palabras_extra", jdump(kws))
    con.commit()

    msg = [f"📈 ESTRATEGIA SEMANAL ({len(videos)} vídeos analizados)", res.get("resumen", ""),
           "\n✅ Funciona: " + "; ".join(res.get("que_funciona", [])[:3]),
           "❌ No funciona: " + "; ".join(res.get("que_no_funciona", [])[:3]),
           "\n🎯 Formatos prioritarios: " + ", ".join(res.get("formatos_prioridad", [])[:3]),
           "💡 Ideas: " + " | ".join(i.get("titulo", "") for i in res.get("ideas_episodios", [])[:3]),
           "\n📝 Para ti esta semana:\n" + "\n".join(f"- {a}" for a in res.get("acciones_para_el_dueno", [])[:3])]
    if res.get("respuestas_sugeridas"):
        msg.append("\n💬 Respuestas sugeridas a comentarios:")
        for r in res["respuestas_sugeridas"][:5]:
            msg.append(f"«{r.get('comentario', '')[:120]}»\n→ {r.get('respuesta', '')}")
    if kws:
        msg.append("\n🔎 Nuevas búsquedas en el Radar: " + ", ".join(kws))
    send("\n".join(m for m in msg if m))
    print("\n".join(msg))


if __name__ == "__main__":
    main()

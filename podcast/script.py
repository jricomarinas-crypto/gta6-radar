"""Investigación (Radar + verificación web) y guion del episodio."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from radar.briefing import snapshot
from radar.config import cfg
from radar.db import jdump, jload, kv_get
from radar.llm import ask_json, research_with_web

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def today_str() -> str:
    d = datetime.now(ZoneInfo(cfg()["canal"].get("zona_horaria", "UTC")))
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def radar_context(con) -> dict:
    s = snapshot(con, 48, limit=30)
    b = con.execute("SELECT markdown FROM briefings ORDER BY date DESC LIMIT 1").fetchone()
    return {
        "top_videos": [{k: v[k] for k in ("title", "channel", "url", "views", "velocity", "content_type", "topics",
                                          "summary", "claims", "verification", "risk")} for v in s["videos"][:20]],
        "temas": [{k: t[k] for k in ("label", "n_24h", "n_prev", "growth")} for t in s["topics"][:12]],
        "alertas": [{k: a[k] for k in ("type", "severity", "title", "message", "url")} for a in s["alerts"][:15]],
        "noticias": [{k: n[k] for k in ("source", "title", "url", "summary", "verification", "official")} for n in s["news"][:20]],
        "comunidad": s["community_questions"],
        "briefing": (b["markdown"] if b else "")[:6000],
    }


def history(con, n=14) -> list[dict]:
    return [{"fecha": r["date"], "formato": r["format"], "titulo": r["title"], "temas": jload(r["topic_keys"])}
            for r in con.execute("SELECT * FROM episodes ORDER BY date DESC LIMIT ?", (n,))]


def research(con) -> tuple[str, list[dict], dict]:
    p = cfg()["podcast"]
    ctx = radar_context(con)
    hist = history(con)
    last_fmt = hist[0]["formato"] if hist else None
    formats = [f for f in p["formatos"] if f["id"] != last_fmt]
    estrategia = jload(kv_get(con, "estrategia"), {})
    prio = estrategia.get("formatos_prioridad") or []
    formats.sort(key=lambda f: prio.index(f["id"]) if f["id"] in prio else len(prio))
    est_txt = jdump({k: estrategia.get(k) for k in ("resumen", "formatos_prioridad", "temas_prioritarios", "temas_evitar",
                                                    "ideas_episodios", "preguntas_audiencia") if estrategia.get(k)})
    prompt = f"""Hoy es {today_str()}. Eres el investigador de un podcast diario en YouTube sobre GTA 6
(Grand Theft Auto VI, de Rockstar Games) para público hispano (Latinoamérica).

LO QUE DETECTA NUESTRO RADAR (últimas 48 h):
{jdump(ctx)}

EPISODIOS ANTERIORES (no repitas el mismo ángulo):
{jdump(hist)}

FORMATOS DISPONIBLES HOY (ordenados por prioridad según el rendimiento del canal):
{jdump(formats)}

RECOMENDACIONES DEL AGENTE DE ESTRATEGIA (análisis semanal de nuestro canal; tenlas en cuenta, pero manda la actualidad):
{est_txt or "todavía no hay datos"}

Tu trabajo:
1. Elige el FORMATO y el ÁNGULO del episodio de hoy: lo que más interesa ahora mismo a la audiencia según el radar
   (momentum, temas en alza, preguntas de la comunidad), que aporte algo y que no hayamos cubierto ya.
2. Verifica con búsqueda web los datos clave en fuentes primarias (Rockstar Newswire, Take-Two, plataformas)
   y medios fiables. No te fíes de vídeos de creadores como fuente de hechos.
3. Devuelve un DOSSIER en texto con:
   - FORMATO elegido (id) y ÁNGULO (1 frase)
   - HECHOS: 8-14 puntos, cada uno con etiqueta [CONFIRMADO] (fuente oficial), [REPORTADO] (medio fiable citando fuente),
     [RUMOR] (filtración/sin verificar) u [OPINIÓN], el medio y la URL
   - LO QUE NO SE SABE TODAVÍA
   - PREGUNTAS DE LA COMUNIDAD que el episodio debe responder
   - QUÉ DICE LA CONVERSACIÓN (tendencias del radar, sin copiar contenido de otros creadores)
Sé riguroso: si dos fuentes se contradicen, dilo."""
    text, sources = research_with_web(prompt, max_uses=int(cfg()["ia"].get("busquedas_web_por_episodio", 6)))
    return text, sources, ctx


def write_script(dossier: str, sources: list[dict], con) -> dict:
    p = cfg()["podcast"]
    hosts = {h["id"]: h for h in p["presentadores"]}
    words = int(p["duracion_minutos"] * 150)
    n_shorts = int(p.get("shorts_por_episodio", 3))
    a, b = hosts["A"], hosts["B"]
    system = f"""Eres guionista de «{cfg()['canal']['nombre']}», {cfg()['canal']['subtitulo']}: un podcast en vídeo con dos
presentadores (voces sintéticas) para público hispano de Latinoamérica. Español neutro latinoamericano
(nada de "vosotros", ni expresiones solo de España).

Presentadores:
- A = {a['nombre']} ({a['rol']}): {a['personalidad']}
- B = {b['nombre']} ({b['rol']}): {b['personalidad']}

Reglas de oro:
- SOLO afirma lo que está en el dossier. Cada dato con su grado: si es rumor, dilo como rumor.
- Nunca inventes cifras, fechas, citas ni nombres. Nada de "fuentes cercanas" que no estén en el dossier.
- Conversación natural: frases cortas, interrupciones breves, reacciones ("¿en serio?", "ojo con esto"),
  bromas suaves, pero sin relleno. Cada línea 1-3 frases. Nada de acotaciones, emojis ni markdown.
- Los números se escriben como se dicen cuando ayuda ("treinta cuadros por segundo"); puedes escribir "GTA 6", "PS5", "FPS".
- Primer segmento = gancho de 15-25 s con el dato más potente, luego {a['nombre']} saluda y presenta el episodio.
- Último segmento = cierre: resumen en 2 frases + pregunta a la audiencia para comentarios + despedida.
- No digas que eres una IA ni hables de "guion". No pidas suscripción más de una vez.
- No describas ni copies vídeos de otros creadores; puedes decir "en la comunidad se comenta…".
"""
    prompt = f"""DOSSIER DE HOY ({today_str()}):
{dossier}

FUENTES CITADAS: {jdump(sources[:25])}

Escribe el episodio. Duración objetivo: ~{words} palabras habladas en total (unos {p['duracion_minutos']} minutos).
Entre 5 y 8 segmentos. Marca {n_shorts} segmentos que funcionen solos como Short vertical: deben tener
120-180 palabras y empezar con una frase gancho que se entienda sin contexto.

Devuelve SOLO este JSON:
{{
  "formato": "id del formato",
  "titulo": "título YouTube ≤ 70 caracteres, atractivo pero honesto (sin clickbait falso), incluye 'GTA 6'",
  "titulo_miniatura": "2-4 palabras en MAYÚSCULAS para la miniatura",
  "subtitulo_miniatura": "≤ 5 palabras",
  "descripcion": "2 párrafos para YouTube (sin enlaces; los añado yo)",
  "etiquetas": ["8-15 etiquetas"],
  "temas_clave": ["slugs cortos de lo que cubre, p. ej. fps-ps5-pro"],
  "segmentos": [
    {{
      "capitulo": "título corto del capítulo (≤ 32 caracteres)",
      "tarjeta": {{"titular": "≤ 40 caracteres", "detalle": "≤ 70 caracteres",
                  "estado": "CONFIRMADO|REPORTADO|RUMOR|OPINIÓN", "fuente": "medio u organismo (≤ 40 caracteres)"}},
      "lineas": [{{"habla": "A|B", "texto": "..."}}]
    }}
  ],
  "shorts": [{{"segmento": 2, "titulo": "título del Short ≤ 60 caracteres", "gancho": "≤ 6 palabras para el texto grande"}}],
  "fuentes": [{{"titulo": "...", "url": "https://..."}}]
}}"""
    ep = ask_json(prompt, system=system, max_tokens=16000)
    return validate(ep)


def validate(ep: dict) -> dict:
    segs = [s for s in ep.get("segmentos", []) if s.get("lineas")]
    if len(segs) < 3:
        raise ValueError("Guion demasiado corto")
    for s in segs:
        s["lineas"] = [ln for ln in s["lineas"] if ln.get("texto", "").strip() and ln.get("habla") in ("A", "B")]
        s.setdefault("tarjeta", {})
    ep["segmentos"] = segs
    ep["shorts"] = [x for x in ep.get("shorts", []) if isinstance(x.get("segmento"), int) and 0 <= x["segmento"] < len(segs)]
    ep["titulo"] = (ep.get("titulo") or "GTA 6: lo último")[:100]
    return ep


def flatten(ep: dict) -> list[dict]:
    out = []
    for si, s in enumerate(ep["segmentos"]):
        for ln in s["lineas"]:
            out.append({"seg": si, "speaker": ln["habla"], "text": ln["texto"].strip()})
    return out

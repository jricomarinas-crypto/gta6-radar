"""Radar Agent: chat en tu terminal que consulta la base de datos del Radar (no inventa).

    python -m radar.chat                       # modo conversación
    python -m radar.chat "¿qué vídeos crecen más rápido ahora?"

Necesita data/radar.db (descárgala con:  python tools/descargar_datos.py)
y ANTHROPIC_API_KEY en el archivo .env
"""
from __future__ import annotations

import json
import sqlite3
import sys

from .briefing import snapshot
from .config import DB_PATH, cfg
from .db import connect, hours_ago, jload
from .llm import client

SYSTEM = """Eres Radar Agent, el analista del radar de contenido sobre GTA 6 de un canal de YouTube en español.
Reglas:
- Usa SIEMPRE las herramientas para obtener datos; nunca inventes cifras, vídeos ni fuentes.
- Cita título, canal, fecha y métricas, con el enlace.
- Si no hay datos suficientes, dilo claramente.
- Distingue HECHO (oficial), REPORTADO (medios), RUMOR (sin verificar) y OPINIÓN.
- Respuestas accionables y breves, en español."""

TOOLS = [
    {"name": "trending_videos", "description": "Vídeos de GTA 6 ordenados por score, momentum, vistas/hora o vistas.",
     "input_schema": {"type": "object", "properties": {
         "hours": {"type": "integer", "description": "ventana en horas (por defecto 24)"},
         "order": {"type": "string", "enum": ["score", "momentum", "velocity", "views", "recent"]},
         "topic": {"type": "string", "description": "filtra por tema (lanzamiento, mapa, rendimiento_fps, filtraciones_rumores…)"},
         "language": {"type": "string", "description": "es, en…"},
         "limit": {"type": "integer"}}}},
    {"name": "search_videos", "description": "Busca vídeos por texto en título, descripción, resumen o entidades.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "hours": {"type": "integer"},
                                                       "limit": {"type": "integer"}}, "required": ["query"]}},
    {"name": "overview", "description": "Resumen del radar: KPIs, temas en alza, creadores emergentes, alertas, noticias y preguntas de la comunidad.",
     "input_schema": {"type": "object", "properties": {"hours": {"type": "integer"}}}},
    {"name": "news", "description": "Noticias de medios sobre GTA 6.",
     "input_schema": {"type": "object", "properties": {"hours": {"type": "integer"}, "query": {"type": "string"}}}},
    {"name": "sql", "description": "Consulta SQL de solo lectura (SELECT) sobre la base SQLite. Tablas: videos, creators, "
                                   "snapshots, news, alerts, comments, briefings, episodes. Devuelve máx. 100 filas.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]

ORDER = {"score": "overall_score", "momentum": "momentum_score", "velocity": "velocity", "views": "views",
         "recent": "published_at"}


def _videos(con, where, params, order="overall_score", limit=15):
    rows = con.execute(
        f"""SELECT v.title,v.url,c.name channel,c.subscribers subs,v.published_at,v.views,v.likes,v.comments,
                   ROUND(v.velocity) vistas_hora,v.content_type,v.topics,v.summary,v.key_claims,v.verification,
                   v.risk_level,ROUND(v.overall_score) score,ROUND(v.momentum_score) momentum
            FROM videos v LEFT JOIN creators c ON c.id=v.creator_id
            WHERE COALESCE(v.is_related,1)=1 AND {where} ORDER BY COALESCE({order},0) DESC LIMIT ?""",
        (*params, limit)).fetchall()
    return [dict(r) | {"topics": jload(r["topics"]), "key_claims": jload(r["key_claims"])} for r in rows]


def run_tool(con, name, args):
    h = int(args.get("hours") or 24)
    lim = min(int(args.get("limit") or 15), 50)
    if name == "trending_videos":
        where, params = "v.published_at>=?", [hours_ago(h)]
        if args.get("topic"):
            where += " AND v.topics LIKE ?"
            params.append(f'%"{args["topic"]}"%')
        if args.get("language"):
            where += " AND v.language LIKE ?"
            params.append(args["language"] + "%")
        return _videos(con, where, params, ORDER.get(args.get("order", "score"), "overall_score"), lim)
    if name == "search_videos":
        q = f"%{args['query']}%"
        return _videos(con, "v.published_at>=? AND (v.title LIKE ? OR v.description LIKE ? OR v.summary LIKE ? OR v.entities LIKE ?)",
                       [hours_ago(int(args.get("hours") or 168)), q, q, q, q], "overall_score", lim)
    if name == "overview":
        s = snapshot(con, h, limit=20)
        return {k: s[k] for k in ("kpis", "topics", "emerging", "alerts", "community_questions")} | {
            "top_videos": [{k: v[k] for k in ("title", "channel", "url", "views", "velocity", "score")} for v in s["videos"][:10]],
            "news": s["news"][:10]}
    if name == "news":
        q = f"%{args.get('query', '')}%"
        return [dict(r) for r in con.execute(
            "SELECT source,title,url,published_at,ai_summary,verification,is_official FROM news "
            "WHERE published_at>=? AND title LIKE ? ORDER BY published_at DESC LIMIT 30", (hours_ago(h), q))]
    if name == "sql":
        q = args["query"].strip().rstrip(";")
        if not q.lower().startswith(("select", "with")):
            return {"error": "Solo se permiten consultas SELECT"}
        ro = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        ro.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in ro.execute(q).fetchmany(100)]
        except sqlite3.Error as e:
            return {"error": str(e)}
    return {"error": "herramienta desconocida"}


def answer(con, history: list) -> str:
    model = cfg()["ia"]["modelo_principal"]
    while True:
        resp = client().messages.create(model=model, max_tokens=3000, system=SYSTEM, tools=TOOLS, messages=history)
        history.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                print(f"  · consultando {b.name} {json.dumps(b.input, ensure_ascii=False)}")
                out = run_tool(con, b.name, b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out, ensure_ascii=False, default=str)[:60000]})
        history.append({"role": "user", "content": results})


def main():
    if not DB_PATH.exists():
        sys.exit("No encuentro data/radar.db. Descárgala con:  python tools/descargar_datos.py")
    con = connect()
    history = []
    if len(sys.argv) > 1:
        history.append({"role": "user", "content": " ".join(sys.argv[1:])})
        print(answer(con, history))
        return
    print("Radar Agent — pregunta lo que quieras sobre GTA 6 (Ctrl+C para salir)\n")
    while True:
        try:
            q = input("Tú › ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        history.append({"role": "user", "content": q})
        print("\nRadar › " + answer(con, history) + "\n")


if __name__ == "__main__":
    main()

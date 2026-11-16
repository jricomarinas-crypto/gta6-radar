"""Serie diaria de producción (gráfica «Producción» de Hoy), a partir de la tabla de eventos.

Qué cuenta cada serie (días en panel.zona_horaria):
- fabricados  = vídeos terminados ese día (evento video_fabricado: una versión renderizada sin errores).
- aprobados   = vídeos aprobados ese día (evento video_aprobado).
- publicados  = publicaciones marcadas como subidas ese día (evento publicado; una por plataforma: un Short
                subido a TikTok y a YouTube Shorts cuenta 2).
Antes del primer evento guardado no hay datos (None). Desde ese día, un día sin eventos es un 0 real.
"""
from __future__ import annotations

from datetime import timedelta

from radar.diario import dia_local, hoy

from . import db

TIPOS = {"fabricados": "video_fabricado", "aprobados": "video_aprobado", "publicados": "publicado"}


def produccion(con, dias: int = 90) -> dict:
    eventos = [dict(r) for r in con.execute("SELECT * FROM eventos ORDER BY fecha")]
    primero = dia_local(eventos[0]["fecha"]) if eventos else None
    cuenta, reconstruido = {}, set()
    for e in eventos:
        d = dia_local(e["fecha"])
        for serie, tipo in TIPOS.items():
            if e["tipo"] == tipo:
                cuenta[(d, serie)] = cuenta.get((d, serie), 0) + 1
                if e["origen"] == "reconstruido":
                    reconstruido.add(d)
    h = hoy()
    filas = []
    for i in range(dias - 1, -1, -1):
        d = (h - timedelta(days=i)).isoformat()
        con_datos = primero is not None and d >= primero
        filas.append({"fecha": d, **{s: (cuenta.get((d, s), 0) if con_datos else None) for s in TIPOS},
                      "reconstruido": d in reconstruido})
    return {"dias": filas, "desde": primero, "hay_reconstruidos": bool(reconstruido)}


def eventos_del_dia(con, fecha: str) -> list[dict]:
    out = []
    for e in con.execute("SELECT * FROM eventos ORDER BY fecha"):
        if dia_local(e["fecha"]) == fecha:
            t = db.trabajo(con, e["trabajo_id"]) or {}
            out.append({"pieza": e["trabajo_id"], "titulo": (t.get("idea") or {}).get("titulo"), "tipo": e["tipo"],
                        "version": e["version_n"], "plataforma": e["plataforma"], "hora": e["fecha"], "origen": e["origen"]})
    return out

"""Seguimiento de investigaciones (fase 3): novedades del Radar desde tu última revisión. Privado.

- Cada investigación seguida tiene consultas (una por línea, p. ej. «precio México»).
- NOVEDAD = noticia o vídeo que el Radar DETECTÓ después de «revisado_en» y que coincide con alguna consulta
  (mismo buscador que Investigar › Buscador). Lo ya añadido a la investigación no cuenta como novedad.
- Se calcula al abrir el Estudio con los datos del Radar que hay en tu Mac (tools/descargar_datos.py los actualiza).
"""
from __future__ import annotations

from radar.db import iso

from . import busqueda
from .investigacion import NoValido, inv


def _consultas(texto) -> list[str]:
    lineas = texto.splitlines() if isinstance(texto, str) else list(texto or [])
    return [c.strip()[:80] for c in lineas if c.strip()][:10]


def seguir(con, iid: str, consultas) -> dict:
    if not inv(con, iid):
        raise NoValido("Esa investigación no existe.")
    cs = _consultas(consultas)
    if not cs:
        raise NoValido("Escribe al menos una consulta (una por línea).")
    ahora = iso()
    con.execute("""INSERT INTO seguimientos(inv_id,consultas,activo,revisado_en,creado_en) VALUES(?,?,1,?,?)
                   ON CONFLICT(inv_id) DO UPDATE SET consultas=excluded.consultas, activo=1""", (iid, "\n".join(cs), ahora, ahora))
    con.commit()
    return estado(con, iid)


def dejar(con, iid: str) -> dict:
    con.execute("UPDATE seguimientos SET activo=0 WHERE inv_id=?", (iid,))
    con.commit()
    return {"ok": True}


def revisado(con, iid: str) -> dict:
    con.execute("UPDATE seguimientos SET revisado_en=? WHERE inv_id=?", (iso(), iid))
    con.commit()
    return estado(con, iid)


def estado(con, iid: str) -> dict | None:
    r = con.execute("SELECT * FROM seguimientos WHERE inv_id=?", (iid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["consultas"] = d["consultas"].splitlines()
    return d


def novedades(radar, con, iid: str, demo: bool = False) -> list[dict]:
    s = estado(con, iid)
    if not s or not s["activo"]:
        return []
    ya = {r["clave"] for r in con.execute("SELECT r.clave FROM inv_refs ir JOIN referencias r ON r.id=ir.ref_id WHERE ir.inv_id=?", (iid,))}
    vistos, out = set(), []
    for c in s["consultas"]:
        res = busqueda.buscar(radar, con, c, ["noticia", "video"], demo=demo, limite=100)
        for x in res.get("resultados", []):
            k = f"{x['tipo']}:{x['clave']}"
            if k in vistos or k in ya or not x["detectado"] or x["detectado"] <= (s["revisado_en"] or ""):
                continue
            vistos.add(k)
            out.append({**x, "consulta": c})
    return sorted(out, key=lambda x: x["detectado"], reverse=True)


def todos(radar, con, demo: bool = False) -> list[dict]:
    out = []
    for r in con.execute("""SELECT s.inv_id, i.titulo FROM seguimientos s JOIN investigaciones i ON i.id=s.inv_id
                            WHERE s.activo=1 ORDER BY i.actividad_en DESC"""):
        e = estado(con, r["inv_id"])
        out.append({**e, "titulo": r["titulo"], "n_novedades": len(novedades(radar, con, r["inv_id"], demo))})
    return out

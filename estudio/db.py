"""Base de datos del Estudio (data/estudio.db): encargos, piezas fabricadas e ideas descartadas.

Va aparte de radar.db para que descargar los datos del Radar o la rama `data` de GitHub no la pisen.
"""
from __future__ import annotations

import secrets
import sqlite3

from radar.config import DATA_DIR
from radar.db import iso, jdump, jload

DB = DATA_DIR / "estudio.db"
ESTADOS = ("esperando_guion", "fabricando", "listo", "error")

SCHEMA = """
CREATE TABLE IF NOT EXISTS trabajos (
    id TEXT PRIMARY KEY,
    idea_id TEXT, idea TEXT, formato TEXT, plataformas TEXT,
    estado TEXT, progreso REAL DEFAULT 0, paso TEXT, error TEXT,
    creado_en TEXT, terminado_en TEXT
);
CREATE TABLE IF NOT EXISTS piezas (
    id TEXT PRIMARY KEY,
    trabajo_id TEXT, plataforma TEXT, formato TEXT, ruta TEXT, duracion REAL,
    calidad TEXT, subida_en TEXT
);
CREATE TABLE IF NOT EXISTS descartes (idea_id TEXT PRIMARY KEY, descartada_en TEXT);
"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _trabajo(r) -> dict:
    d = dict(r)
    d["idea"] = jload(d.get("idea"), {})
    d["plataformas"] = jload(d.get("plataformas"), [])
    return d


def crear_trabajo(con, idea: dict, formato: str, plataformas: list[str]) -> dict:
    tid = secrets.token_hex(3)  # corto para poder decirlo en el chat: «encargo a1b2c3»
    con.execute("""INSERT INTO trabajos(id,idea_id,idea,formato,plataformas,estado,progreso,paso,creado_en)
                   VALUES(?,?,?,?,?,'esperando_guion',0,'Esperando el guion',?)""",
                (tid, idea["id"], jdump(idea), formato, jdump(plataformas), iso()))
    con.commit()
    return trabajo(con, tid)


def trabajo(con, tid: str) -> dict | None:
    r = con.execute("SELECT * FROM trabajos WHERE id=?", (tid,)).fetchone()
    if not r:
        return None
    t = _trabajo(r)
    t["piezas"] = [dict(p, calidad=jload(p["calidad"], {})) for p in
                   con.execute("SELECT * FROM piezas WHERE trabajo_id=? ORDER BY plataforma", (tid,))]
    return t


def trabajos(con, limite: int = 30) -> list[dict]:
    return [trabajo(con, r["id"]) for r in
            con.execute("SELECT id FROM trabajos ORDER BY creado_en DESC LIMIT ?", (limite,))]


def progreso(con, tid: str, valor: float, paso: str, estado: str = "fabricando", error: str | None = None) -> None:
    fin = iso() if estado in ("listo", "error") else None
    con.execute("UPDATE trabajos SET progreso=?, paso=?, estado=?, error=?, terminado_en=COALESCE(?, terminado_en) WHERE id=?",
                (round(valor, 2), paso, estado, error, fin, tid))
    con.commit()


def guardar_pieza(con, tid: str, plataforma: str, formato: str, ruta: str, duracion: float, calidad: dict) -> None:
    con.execute("INSERT OR REPLACE INTO piezas(id,trabajo_id,plataforma,formato,ruta,duracion,calidad) VALUES(?,?,?,?,?,?,?)",
                (f"{tid}-{plataforma}", tid, plataforma, formato, ruta, duracion, jdump(calidad)))
    con.commit()


def descartar(con, idea_id: str) -> None:
    con.execute("INSERT OR REPLACE INTO descartes(idea_id,descartada_en) VALUES(?,?)", (idea_id, iso()))
    con.commit()


def descartadas(con) -> set[str]:
    return {r["idea_id"] for r in con.execute("SELECT idea_id FROM descartes")}

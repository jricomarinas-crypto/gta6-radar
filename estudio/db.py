"""Base de datos del Estudio (data/estudio.db), con estados separados (megaprompt §7).

- trabajos      → la pieza: estado editorial (en_estudio | descartada) y publicación.
- versiones     → cada render del guion: estado de producción (pendiente | en_curso | listo | fallido) y etapa.
- aprobaciones  → idea / guion / vídeo por separado. Guardan el hash del guion que se aprobó:
                  si el guion cambia, la aprobación deja de valer sola (se invalida lo afectado).
- exportaciones → qué versión está en la carpeta del Mac, con su manifiesto y cuándo se comprobó el hash.

Va aparte de radar.db para que descargar los datos del Radar no la pise.
"""
from __future__ import annotations

import secrets
import sqlite3

from radar.db import iso, jdump, jload

from . import rutas

VERSION_ESQUEMA = 3
# Eventos de producción (solo se añaden, nunca se pisan). Tipos:
#   pieza_creada · idea_aprobado · guion_aprobado · video_fabricado · video_aprobado · exportado · publicado
# origen = 'registro' (ocurrió con el Estudio funcionando) | 'reconstruido' (deducido de fechas guardadas antes de v3)

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS trabajos (
    id TEXT PRIMARY KEY,
    idea_id TEXT, idea TEXT, formato TEXT, plataformas TEXT,
    estado TEXT, progreso REAL DEFAULT 0, paso TEXT, error TEXT,
    creado_en TEXT, terminado_en TEXT
);
CREATE TABLE IF NOT EXISTS piezas (
    id TEXT PRIMARY KEY, trabajo_id TEXT, plataforma TEXT, formato TEXT, ruta TEXT, duracion REAL,
    calidad TEXT, subida_en TEXT
);
CREATE TABLE IF NOT EXISTS descartes (idea_id TEXT PRIMARY KEY, descartada_en TEXT);
CREATE TABLE IF NOT EXISTS versiones (
    id TEXT PRIMARY KEY,
    trabajo_id TEXT NOT NULL, n INTEGER NOT NULL,
    guion_hash TEXT, guion TEXT,
    video_ruta TEXT, srt_ruta TEXT, portada_ruta TEXT, duracion REAL, calidad TEXT,
    estado_produccion TEXT NOT NULL DEFAULT 'pendiente', etapa TEXT, error TEXT, intentos INTEGER DEFAULT 0,
    legado INTEGER DEFAULT 0,
    creada_en TEXT, actualizada_en TEXT,
    UNIQUE (trabajo_id, n)
);
CREATE TABLE IF NOT EXISTS aprobaciones (
    trabajo_id TEXT NOT NULL, tipo TEXT NOT NULL, version_n INTEGER, guion_hash TEXT, creada_en TEXT,
    PRIMARY KEY (trabajo_id, tipo)
);
CREATE TABLE IF NOT EXISTS cambios (trabajo_id TEXT, version_n INTEGER, nota TEXT, creada_en TEXT);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trabajo_id TEXT NOT NULL, tipo TEXT NOT NULL, version_n INTEGER, plataforma TEXT,
    fecha TEXT NOT NULL, origen TEXT NOT NULL DEFAULT 'registro'
);
CREATE INDEX IF NOT EXISTS idx_eventos_fecha ON eventos(fecha);
-- Investigación (fase 1B). Todo privado: solo en tu Mac.
-- referencias: una fila por recurso (noticia, vídeo, creador, enlace). Guarda una copia de lo que viste
--              (por si el Radar borra el original) y su estado: leída, guardada en la biblioteca, archivada, nota.
CREATE TABLE IF NOT EXISTS referencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL, clave TEXT NOT NULL UNIQUE,
    titulo TEXT, url TEXT, fuente TEXT, publicado_en TEXT, detectado_en TEXT, extracto TEXT,
    datos TEXT, etiquetas TEXT DEFAULT '[]', nota TEXT,
    guardada INTEGER DEFAULT 0, leida INTEGER DEFAULT 0, archivada INTEGER DEFAULT 0,
    creada_en TEXT, actualizada_en TEXT
);
CREATE TABLE IF NOT EXISTS investigaciones (
    id TEXT PRIMARY KEY, titulo TEXT NOT NULL, pregunta TEXT, descripcion TEXT, temas TEXT DEFAULT '[]',
    estado TEXT NOT NULL DEFAULT 'abierta',     -- abierta | recopilando | contrastando | lista | archivada
    que_se TEXT, que_falta TEXT, conclusion TEXT,
    creada_en TEXT, actividad_en TEXT
);
-- una referencia puede estar en varias investigaciones sin duplicarse
CREATE TABLE IF NOT EXISTS inv_refs (
    inv_id TEXT NOT NULL, ref_id INTEGER NOT NULL, aporte TEXT, consultada_en TEXT, anadida_en TEXT,
    PRIMARY KEY (inv_id, ref_id)
);
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, inv_id TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'apunte',        -- apunte | pregunta | idea | enfoque
    texto TEXT NOT NULL, creada_en TEXT, actualizada_en TEXT
);
CREATE TABLE IF NOT EXISTS tomas (
    trabajo_id TEXT NOT NULL, escena INTEGER NOT NULL,
    texto_hash TEXT NOT NULL,           -- huella del texto grabado: si la escena cambia, la toma deja de valer
    ruta TEXT NOT NULL, duracion REAL, creada_en TEXT,
    PRIMARY KEY (trabajo_id, escena)
);
CREATE TABLE IF NOT EXISTS exportaciones (
    version_id TEXT NOT NULL, plataforma TEXT NOT NULL,
    ruta TEXT, manifiesto_ruta TEXT, nombre TEXT, exportada_en TEXT, verificada_en TEXT,
    subida_en TEXT, url TEXT,
    PRIMARY KEY (version_id, plataforma)
);
"""

COLUMNAS_TRABAJOS = {
    "estado_editorial": "TEXT DEFAULT 'en_estudio'",
    "motivo_descarte": "TEXT",
    "estado_publicacion": "TEXT DEFAULT 'no_publicado'",
    "variante": "TEXT",
    "nn": "TEXT",
    "fondo": "TEXT",   # video | grafico
    "voz": "TEXT",     # propia | sintetica
}
COLUMNAS_VERSIONES = {
    "clave": "TEXT",     # huella de guion + fondo + voz + tomas: si cambia, hace falta un vídeo nuevo
    "opciones": "TEXT",  # {fondo, voz, creditos[]} usados en ese render
}


def connect() -> sqlite3.Connection:
    path = rutas.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=15, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrar(con)
    return con


def _migrar(con) -> None:
    cols = {r["name"] for r in con.execute("PRAGMA table_info(trabajos)")}
    for c, tipo in COLUMNAS_TRABAJOS.items():
        if c not in cols:
            con.execute(f"ALTER TABLE trabajos ADD COLUMN {c} {tipo}")
    cols_v = {r["name"] for r in con.execute("PRAGMA table_info(versiones)")}
    for c, tipo in COLUMNAS_VERSIONES.items():
        if c not in cols_v:
            con.execute(f"ALTER TABLE versiones ADD COLUMN {c} {tipo}")
            if c == "clave":  # versiones anteriores: su clave es la huella del guion (voz sintética, fondo gráfico)
                con.execute("UPDATE versiones SET clave=guion_hash WHERE clave IS NULL")
    row = con.execute("SELECT v FROM meta WHERE k='version_esquema'").fetchone()
    actual = int(row["v"]) if row else 1
    if actual < 2:
        # v1 → v2: los encargos ya fabricados pasan a «versión 1, exportada antes del flujo de aprobación»
        for t in con.execute("SELECT * FROM trabajos").fetchall():
            con.execute("UPDATE trabajos SET variante=COALESCE(variante, formato) WHERE id=?", (t["id"],))
            if t["estado"] != "listo":
                continue
            vid = f"{t['id']}-v1"
            con.execute("""INSERT OR IGNORE INTO versiones(id,trabajo_id,n,estado_produccion,etapa,legado,creada_en,actualizada_en)
                           VALUES(?,?,1,'listo','Hecho antes del flujo de aprobación',1,?,?)""",
                        (vid, t["id"], t["terminado_en"] or t["creado_en"], iso()))
            for p in con.execute("SELECT * FROM piezas WHERE trabajo_id=?", (t["id"],)):
                con.execute("""INSERT OR IGNORE INTO exportaciones(version_id,plataforma,ruta,exportada_en,subida_en)
                               VALUES(?,?,?,?,?)""", (vid, p["plataforma"], p["ruta"], t["terminado_en"], p["subida_en"]))
        con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('version_esquema','2')")
        actual = 2
    if actual < 3:
        # v2 → v3: eventos de producción, reconstruidos de las fechas que ya había (origen='reconstruido')
        rec = []
        for t in con.execute("SELECT id, creado_en FROM trabajos"):
            rec.append((t["id"], "pieza_creada", None, None, t["creado_en"]))
        for v in con.execute("SELECT trabajo_id, n, actualizada_en, creada_en, legado FROM versiones WHERE estado_produccion='listo'"):
            rec.append((v["trabajo_id"], "video_fabricado", v["n"], None, v["creada_en"] if v["legado"] else v["actualizada_en"]))
        for a in con.execute("SELECT trabajo_id, tipo, version_n, creada_en FROM aprobaciones"):
            rec.append((a["trabajo_id"], f"{a['tipo']}_aprobado", a["version_n"], None, a["creada_en"]))
        for e in con.execute("""SELECT v.trabajo_id, v.n, e.plataforma, e.exportada_en, e.subida_en
                                FROM exportaciones e JOIN versiones v ON v.id=e.version_id"""):
            if e["exportada_en"]:
                rec.append((e["trabajo_id"], "exportado", e["n"], e["plataforma"], e["exportada_en"]))
            if e["subida_en"]:
                rec.append((e["trabajo_id"], "publicado", e["n"], e["plataforma"], e["subida_en"]))
        con.executemany("""INSERT INTO eventos(trabajo_id,tipo,version_n,plataforma,fecha,origen)
                           VALUES(?,?,?,?,?,'reconstruido')""", [r for r in rec if r[4]])
        con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('eventos_desde',?)", (iso(),))
        con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('version_esquema','3')")
    con.commit()


def evento(con, tid: str, tipo: str, version_n: int | None = None, plataforma: str | None = None) -> None:
    con.execute("INSERT INTO eventos(trabajo_id,tipo,version_n,plataforma,fecha,origen) VALUES(?,?,?,?,?,'registro')",
                (tid, tipo, version_n, plataforma, iso()))
    con.commit()


# ------------------------------------------------------------------ trabajos (piezas)
def crear_trabajo(con, idea: dict, variante: str, formato: str, plataformas: list[str]) -> dict:
    tid = secrets.token_hex(3)  # corto para decirlo en el chat: «encargo a1b2c3»
    con.execute("""INSERT INTO trabajos(id,idea_id,idea,formato,variante,plataformas,estado,paso,creado_en,
                                        estado_editorial,estado_publicacion)
                   VALUES(?,?,?,?,?,?,'en_estudio','Brief',?,'en_estudio','no_publicado')""",
                (tid, idea["id"], jdump(idea), formato, variante, jdump(plataformas), iso()))
    con.commit()
    evento(con, tid, "pieza_creada")
    return trabajo(con, tid)


def trabajo(con, tid: str) -> dict | None:
    r = con.execute("SELECT * FROM trabajos WHERE id=?", (tid,)).fetchone()
    if not r:
        return None
    t = dict(r)
    t["idea"] = jload(t.get("idea"), {})
    t["plataformas"] = jload(t.get("plataformas"), [])
    return t


def trabajos(con, limite: int = 40, incluir_descartados: bool = False) -> list[dict]:
    q = "SELECT id FROM trabajos" + ("" if incluir_descartados else " WHERE COALESCE(estado_editorial,'en_estudio')!='descartada'")
    return [trabajo(con, r["id"]) for r in con.execute(q + " ORDER BY creado_en DESC LIMIT ?", (limite,))]


def trabajo_activo_de_idea(con, idea_id: str) -> dict | None:
    r = con.execute("""SELECT id FROM trabajos t WHERE idea_id=? AND COALESCE(estado_editorial,'en_estudio')='en_estudio'
                       AND COALESCE(estado_publicacion,'no_publicado')='no_publicado'
                       AND NOT EXISTS (SELECT 1 FROM versiones v WHERE v.trabajo_id=t.id AND v.legado=1)
                       ORDER BY creado_en DESC LIMIT 1""", (idea_id,)).fetchone()
    return trabajo(con, r["id"]) if r else None


# ------------------------------------------------------------------ versiones
def version(con, vid: str) -> dict | None:
    r = con.execute("SELECT * FROM versiones WHERE id=?", (vid,)).fetchone()
    if not r:
        return None
    v = dict(r)
    v["guion"] = jload(v.get("guion"), {})
    v["calidad"] = jload(v.get("calidad"), {})
    v["opciones"] = jload(v.get("opciones"), {})
    return v


def versiones(con, tid: str) -> list[dict]:
    return [version(con, r["id"]) for r in con.execute("SELECT id FROM versiones WHERE trabajo_id=? ORDER BY n DESC", (tid,))]


def ultima_version(con, tid: str) -> dict | None:
    r = con.execute("SELECT id FROM versiones WHERE trabajo_id=? ORDER BY n DESC LIMIT 1", (tid,)).fetchone()
    return version(con, r["id"]) if r else None


def nueva_version(con, tid: str, guion: dict, guion_hash: str, clave: str | None = None,
                  opciones: dict | None = None) -> dict:
    n = (con.execute("SELECT MAX(n) m FROM versiones WHERE trabajo_id=?", (tid,)).fetchone()["m"] or 0) + 1
    vid = f"{tid}-v{n}"
    con.execute("""INSERT INTO versiones(id,trabajo_id,n,guion_hash,guion,estado_produccion,etapa,creada_en,actualizada_en,
                                         clave,opciones)
                   VALUES(?,?,?,?,?,'pendiente','En cola',?,?,?,?)""",
                (vid, tid, n, guion_hash, jdump(guion), iso(), iso(), clave or guion_hash, jdump(opciones or {})))
    con.commit()
    return version(con, vid)


def actualizar_version(con, vid: str, **campos) -> None:
    for k in ("calidad", "opciones"):
        if k in campos:
            campos[k] = jdump(campos[k])
    campos["actualizada_en"] = iso()
    sets = ", ".join(f"{k}=?" for k in campos)
    con.execute(f"UPDATE versiones SET {sets} WHERE id=?", (*campos.values(), vid))
    con.commit()


# ------------------------------------------------------------------ aprobaciones
def aprobar(con, tid: str, tipo: str, version_n: int | None, guion_hash: str | None) -> None:
    con.execute("INSERT OR REPLACE INTO aprobaciones(trabajo_id,tipo,version_n,guion_hash,creada_en) VALUES(?,?,?,?,?)",
                (tid, tipo, version_n, guion_hash, iso()))
    con.commit()
    evento(con, tid, f"{tipo}_aprobado", version_n)


def aprobaciones(con, tid: str) -> dict[str, dict]:
    return {r["tipo"]: dict(r) for r in con.execute("SELECT * FROM aprobaciones WHERE trabajo_id=?", (tid,))}


def quitar_aprobacion(con, tid: str, tipo: str) -> None:
    con.execute("DELETE FROM aprobaciones WHERE trabajo_id=? AND tipo=?", (tid, tipo))
    con.commit()


# ------------------------------------------------------------------ exportaciones
def exportaciones(con, vid: str) -> dict[str, dict]:
    return {r["plataforma"]: dict(r) for r in con.execute("SELECT * FROM exportaciones WHERE version_id=?", (vid,))}


def guardar_exportacion(con, vid: str, plataforma: str, **campos) -> None:
    con.execute("INSERT OR IGNORE INTO exportaciones(version_id,plataforma) VALUES(?,?)", (vid, plataforma))
    sets = ", ".join(f"{k}=?" for k in campos)
    con.execute(f"UPDATE exportaciones SET {sets} WHERE version_id=? AND plataforma=?", (*campos.values(), vid, plataforma))
    con.commit()


# ------------------------------------------------------------------ descartes de ideas
def descartar(con, idea_id: str, motivo: str = "") -> None:
    con.execute("INSERT OR REPLACE INTO descartes(idea_id,descartada_en) VALUES(?,?)", (idea_id, iso()))
    con.execute("INSERT INTO cambios(trabajo_id,version_n,nota,creada_en) VALUES(?,NULL,?,?)",
                (f"idea:{idea_id}", f"Descartada: {motivo}", iso()))
    con.commit()


def descartadas(con) -> set[str]:
    return {r["idea_id"] for r in con.execute("SELECT idea_id FROM descartes")}

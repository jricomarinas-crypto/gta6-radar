"""Buscador local (fase 1B): busca en lo YA RECOPILADO, no en internet.

Índice FTS5 de SQLite en data/busqueda.db, reconstruido desde:
- Radar: noticias, vídeos, creadores y briefings.
- Estudio (privado): referencias guardadas, notas e investigaciones.
Es un índice, no una fuente de verdad: si se borra, se vuelve a crear. Se reconstruye si tiene más de 60 s.
"""
from __future__ import annotations

import re
import sqlite3
import time
import unicodedata

from radar.db import jload

from . import rutas

TIPOS = {"noticia": "Noticia", "video": "Vídeo", "creador": "Creador", "briefing": "Briefing",
         "referencia": "Referencia guardada", "nota": "Nota propia", "investigacion": "Investigación"}
MAX_EDAD_S = 60


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def _abrir() -> sqlite3.Connection:
    con = sqlite3.connect(rutas.busqueda_db())
    con.row_factory = sqlite3.Row
    con.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(
        titulo, texto, buscable,
        tipo UNINDEXED, clave UNINDEXED, url UNINDEXED, fuente UNINDEXED, fecha UNINDEXED, detectado UNINDEXED,
        idioma UNINDEXED, temas UNINDEXED, verificacion UNINDEXED, privado UNINDEXED, demo UNINDEXED,
        tokenize = 'unicode61 remove_diacritics 2')""")
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    return con


def reconstruir(radar, estudio, demo: bool = False) -> int:
    con = _abrir()
    con.execute("DELETE FROM docs")
    filas = []

    def add(tipo, clave, titulo, texto, url="", fuente="", fecha="", detectado="", idioma="", temas=None,
            verificacion="", privado=0):
        titulo, texto = titulo or "", texto or ""
        filas.append((titulo, texto, _norm(f"{titulo} {texto} {fuente}"), tipo, clave, url or "", fuente or "",
                      fecha or "", detectado or "", (idioma or "")[:2], ",".join(temas or []), verificacion or "",
                      privado, 0 if privado else int(demo)))

    for n in radar.execute("SELECT * FROM news WHERE COALESCE(is_related,1)=1"):
        add("noticia", n["id"], n["title"], n["ai_summary"] or n["summary"], n["url"], n["source"], n["published_at"],
            n["first_seen_at"], n["language"], jload(n["topics"]), n["verification"])
    for v in radar.execute("""SELECT v.*, c.name cname FROM videos v LEFT JOIN creators c ON c.id=v.creator_id
                              WHERE COALESCE(v.is_related,1)=1"""):
        add("video", v["id"], v["title"], f"{v['summary'] or ''} {(v['description'] or '')[:600]}", v["url"], v["cname"],
            v["published_at"], v["first_seen_at"], v["language"], jload(v["topics"]), v["verification"])
    for c in radar.execute("SELECT * FROM creators"):
        add("creador", c["id"], c["name"], f"{c['handle'] or ''} {(c['description'] or '')[:400]}",
            f"https://www.youtube.com/channel/{c['external_id']}", "YouTube", "", c["first_seen_at"], c["language"])
    for b in radar.execute("SELECT * FROM briefings"):
        add("briefing", b["date"], f"Briefing del {b['date']}", b["markdown"], "", "Radar", b["date"])
    if estudio is not None:
        for r in estudio.execute("SELECT * FROM referencias WHERE guardada=1 OR nota IS NOT NULL AND nota!=''"):
            add("referencia", str(r["id"]), r["titulo"], f"{r['nota'] or ''} {r['extracto'] or ''}", r["url"], r["fuente"],
                r["publicado_en"], r["creada_en"], privado=1)
        for x in estudio.execute("SELECT n.*, i.titulo it FROM notas n JOIN investigaciones i ON i.id=n.inv_id"):
            add("nota", f"{x['inv_id']}:{x['id']}", f"Nota ({x['tipo']}) · {x['it']}", x["texto"], "", "Tus notas",
                x["creada_en"], x["creada_en"], privado=1)
        for i in estudio.execute("SELECT * FROM investigaciones"):
            add("investigacion", i["id"], i["titulo"],
                " ".join(filter(None, [i["pregunta"], i["descripcion"], i["que_se"], i["que_falta"], i["conclusion"]])),
                "", "Tus investigaciones", i["actividad_en"], i["creada_en"], privado=1)
    con.executemany("INSERT INTO docs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", filas)
    con.execute("INSERT OR REPLACE INTO meta VALUES('construido', ?)", (str(time.time()),))
    con.commit()
    con.close()
    return len(filas)


# Todo el Radar va de GTA 6: «gta», «6», «vi»… y los artículos no ayudan a encontrar nada si hay otras palabras.
VACIAS = {"gta", "6", "vi", "grand", "theft", "auto", "de", "del", "la", "el", "los", "las", "en", "y", "que", "un",
          "una", "a", "al", "con", "por", "para", "lo", "se", "the", "of", "and", "in", "to"}


def consulta_fts(texto: str) -> str | None:
    """Convierte lo que escribes en una consulta segura: cada palabra entre comillas, con prefijo (gta6 → gta6*)."""
    palabras = re.findall(r"[0-9a-z]+", _norm(texto))[:12]
    utiles = [p for p in palabras if p not in VACIAS] or palabras
    return " AND ".join(f'"{p}"*' for p in utiles) if utiles else None


def buscar(radar, estudio, texto: str, tipos: list[str] | None = None, dias: int | None = None, fuente: str = "",
           idioma: str = "", tema: str = "", verificacion: str = "", demo: bool = False, limite: int = 60) -> dict:
    con = _abrir()
    m = con.execute("SELECT v FROM meta WHERE k='construido'").fetchone()
    if not m or time.time() - float(m["v"]) > MAX_EDAD_S:
        con.close()
        reconstruir(radar, estudio, demo)
        con = _abrir()
    q = consulta_fts(texto)
    if not q:
        return {"resultados": [], "total": 0, "aviso": "Escribe al menos una palabra."}
    where, args = ["docs MATCH ?"], [f"buscable : ({q})"]
    tipos = [t for t in (tipos or []) if t in TIPOS]
    if tipos:
        where.append(f"tipo IN ({','.join('?' * len(tipos))})")
        args += tipos
    if dias:
        corte = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - int(dias) * 86400))
        where.append("(fecha >= ? OR (fecha = '' AND detectado >= ?))")
        args += [corte, corte]
    for col, val in (("fuente", fuente), ("idioma", idioma), ("verificacion", verificacion)):
        if val:
            where.append(f"{col} = ?")
            args.append(val[:80])
    if tema:
        where.append("(',' || temas || ',') LIKE ?")
        args.append(f"%,{tema[:40]},%")
    sql = (f"SELECT tipo, clave, titulo, url, fuente, fecha, detectado, idioma, temas, verificacion, privado, demo, "
           f"texto FROM docs WHERE {' AND '.join(where)} "
           f"ORDER BY bm25(docs, 10.0, 1.0, 1.0) LIMIT ?")
    filas = [dict(r) for r in con.execute(sql, (*args, int(limite)))]
    total = con.execute(f"SELECT COUNT(*) FROM docs WHERE {' AND '.join(where)}", args).fetchone()[0]
    con.close()
    palabras = [p.strip('"*') for p in q.split(" AND ")]
    for f in filas:
        f["extracto"] = extracto(f.pop("texto"), palabras)
        f["titulo_marcado"] = extracto(f["titulo"], palabras, 400)
        f["temas"] = [t for t in f["temas"].split(",") if t]
        f["tipo_nombre"] = TIPOS.get(f["tipo"], f["tipo"])
    return {"resultados": filas, "total": total}


def extracto(texto: str, palabras: list[str], ancho: int = 220) -> str:
    """Trozo del texto alrededor de la primera coincidencia, con cada palabra encontrada entre \\u0001 y \\u0002."""
    texto = re.sub(r"\s+", " ", texto or "").strip()
    trozos = [(m.start(), m.end()) for m in re.finditer(r"\w+", texto)
              if any(_norm(m.group()).startswith(p) for p in palabras)]
    ini = max(0, trozos[0][0] - 60) if trozos else 0
    fin = min(len(texto), ini + ancho)
    out, pos = [], ini
    for a, b in trozos:
        if a < ini or b > fin:
            continue
        out += [texto[pos:a], "\u0001", texto[a:b], "\u0002"]
        pos = b
    out.append(texto[pos:fin])
    return ("…" if ini else "") + "".join(out) + ("…" if fin < len(texto) else "")


def fuentes_disponibles(radar) -> list[str]:
    return [r[0] for r in radar.execute("SELECT DISTINCT source FROM news WHERE source IS NOT NULL ORDER BY source")]

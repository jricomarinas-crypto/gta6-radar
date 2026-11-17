"""Creadores y colaboradores (fase 2B). Privado (data/estudio.db).

- Guardar un colaborador o cambiar su estado NO envía nada a nadie: es tu lista de seguimiento.
- No se inventan datos de contacto, afinidades ni puntuaciones: solo lo que hay en el Radar y lo que tú escribes.
- Criterios visibles:
  DESTACADOS = los creadores con más vistas sumadas en vídeos de GTA 6 publicados en las últimas 96 h (según el Radar).
  EMERGENTES = ≤ radar.alertas.emergente_max_suscriptores y vistas en esos vídeos ≥ 3 × sus suscriptores
               (el mismo criterio que el Radar en Investigar › Creadores).
"""
from __future__ import annotations

from radar.config import cfg
from radar.db import hours_ago, iso, jdump, jload

from .investigacion import NoValido

ESTADOS = {"por_revisar": "Por revisar", "interesante": "Interesante", "contactar": "Contactar",
           "contactado": "Contactado", "activa": "Colaboración activa", "archivado": "Archivado"}
VENTANA_H = 96


def _fila(r) -> dict:
    d = dict(r)
    d["temas"] = jload(d.get("temas"), [])
    d["estado_nombre"] = ESTADOS.get(d["estado"], d["estado"])
    return d


def creadores_radar(radar, limite: int = 40) -> dict:
    filas = [dict(r) for r in radar.execute(
        """SELECT c.id, c.name, c.handle, c.subscribers, c.language, c.external_id, c.platform,
                  COUNT(v.id) n_videos, SUM(v.views) views, MAX(v.velocity) max_velocity, MAX(v.last_scraped_at) medido_en
           FROM creators c JOIN videos v ON v.creator_id=c.id
           WHERE v.published_at>=? AND COALESCE(v.is_related,1)=1 AND COALESCE(c.is_official,0)=0
           GROUP BY c.id ORDER BY views DESC LIMIT 200""", (hours_ago(VENTANA_H),))]
    for f in filas:
        f["url"] = f"https://www.youtube.com/channel/{f['external_id']}" if f["external_id"] else None
        f["mejores"] = [dict(x) for x in radar.execute(
            """SELECT title, url, views, velocity FROM videos WHERE creator_id=? AND COALESCE(is_related,1)=1
               ORDER BY views DESC LIMIT 3""", (f["id"],))]
        temas = {}
        for x in radar.execute("SELECT topics FROM videos WHERE creator_id=? AND published_at>=?", (f["id"], hours_ago(VENTANA_H))):
            for t in jload(x["topics"], []):
                temas[t] = temas.get(t, 0) + 1
        f["temas"] = [t for t, _ in sorted(temas.items(), key=lambda kv: -kv[1])[:4]]
    a = cfg()["radar"]["alertas"]
    emerg = [f for f in filas if (f["subscribers"] or 0) <= a["emergente_max_suscriptores"]
             and (f["views"] or 0) >= 3 * max(f["subscribers"] or 1, 1)]
    return {"destacados": filas[:limite], "emergentes": emerg[:limite],
            "criterios": {"destacados": f"Más vistas sumadas en vídeos de GTA 6 publicados en las últimas {VENTANA_H} h (según el Radar). No incluye canales oficiales.",
                          "emergentes": f"Hasta {a['emergente_max_suscriptores']:,} suscriptores y vistas ≥ 3 × sus suscriptores en esos vídeos.".replace(",", ".")}}


def guardar(con, creador_radar: str | None = None, radar=None, nombre: str = "", plataforma: str = "youtube",
            url: str = "", nota: str = "") -> dict:
    """Desde un creador del Radar (copia nombre, enlace, idioma y temas) o a mano. No se duplica."""
    if creador_radar:
        ya = con.execute("SELECT * FROM colaboradores WHERE creador_radar=?", (creador_radar,)).fetchone()
        if ya:
            return _fila(ya)
        c = radar.execute("SELECT * FROM creators WHERE id=?", (creador_radar,)).fetchone() if radar else None
        if not c:
            raise NoValido("Ese creador ya no está en los datos del Radar.")
        temas = {}
        for x in radar.execute("SELECT topics FROM videos WHERE creator_id=?", (creador_radar,)):
            for t in jload(x["topics"], []):
                temas[t] = temas.get(t, 0) + 1
        nombre, url = c["name"], f"https://www.youtube.com/channel/{c['external_id']}" if c["external_id"] else ""
        idioma, temas = c["language"], [t for t, _ in sorted(temas.items(), key=lambda kv: -kv[1])[:5]]
        plataforma = c["platform"] or "youtube"
    else:
        nombre = str(nombre or "").strip()[:120]
        if len(nombre) < 2:
            raise NoValido("Escribe el nombre del creador.")
        url = str(url or "").strip()[:300]
        if url and not url.startswith(("https://", "http://")):
            raise NoValido("El enlace tiene que empezar por https://")
        idioma, temas = None, []
    ahora = iso()
    cur = con.execute("""INSERT INTO colaboradores(creador_radar,nombre,plataforma,url,idioma,temas,estado,nota,creado_en,actualizado_en)
                         VALUES(?,?,?,?,?,?,'por_revisar',?,?,?)""",
                      (creador_radar, nombre, plataforma, url, idioma, jdump(temas), str(nota or "")[:2000], ahora, ahora))
    con.commit()
    return _fila(con.execute("SELECT * FROM colaboradores WHERE id=?", (cur.lastrowid,)).fetchone())


def actualizar(con, cid: int, estado: str | None = None, nota: str | None = None) -> dict:
    r = con.execute("SELECT * FROM colaboradores WHERE id=?", (cid,)).fetchone()
    if not r:
        raise NoValido("Ese colaborador no existe.")
    cambios = {}
    if estado is not None:
        if estado not in ESTADOS:
            raise NoValido("Estado desconocido.")
        cambios["estado"] = estado
    if nota is not None:
        cambios["nota"] = str(nota)[:2000]
    if cambios:
        cambios["actualizado_en"] = iso()
        con.execute(f"UPDATE colaboradores SET {', '.join(k + '=?' for k in cambios)} WHERE id=?", (*cambios.values(), cid))
        con.commit()
    return _fila(con.execute("SELECT * FROM colaboradores WHERE id=?", (cid,)).fetchone())


def borrar(con, cid: int) -> dict:
    con.execute("DELETE FROM colaboradores WHERE id=?", (cid,))
    con.commit()
    return {"ok": True}


def lista(con, estados: list[str] | None = None) -> list[dict]:
    q = "SELECT * FROM colaboradores"
    args: list = []
    if estados:
        q += f" WHERE estado IN ({','.join('?' * len(estados))})"
        args = list(estados)
    return [_fila(r) for r in con.execute(q + " ORDER BY actualizado_en DESC", args)]


def guardados_por_creador(con) -> dict:
    return {r["creador_radar"]: {"id": r["id"], "estado": r["estado"]}
            for r in con.execute("SELECT id, creador_radar, estado FROM colaboradores WHERE creador_radar IS NOT NULL")}

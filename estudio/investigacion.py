"""Investigación (fase 1B): referencias, biblioteca, investigaciones y notas. Todo privado (data/estudio.db).

- Una referencia se identifica por su clave estable: «noticia:<id>», «video:youtube:<id>», «creador:youtube:<id>»
  o «enlace:<huella de la URL>». Crearla dos veces devuelve la misma (no se duplica).
- Al crearla se guarda una copia de lo que viste (titular, fecha, enlace, extracto): si el Radar borra el original
  más adelante, tu referencia sigue completa.
- Quitar una referencia de una investigación NO la borra de la biblioteca.
"""
from __future__ import annotations

import hashlib
import secrets
from urllib.parse import urlparse

from radar.db import iso, jdump, jload

TIPOS = ("noticia", "video", "creador", "enlace")
ESTADOS = ("abierta", "recopilando", "contrastando", "lista", "archivada")
ESTADOS_NOMBRE = {"abierta": "Abierta", "recopilando": "Recopilando fuentes", "contrastando": "Contrastando",
                  "lista": "Lista para convertir en contenido", "archivada": "Archivada"}
TIPOS_NOTA = ("apunte", "pregunta", "idea", "enfoque")
MAX = {"titulo": 200, "texto": 5000, "nota": 2000, "aporte": 1000, "corto": 300}


class NoValido(ValueError):
    pass


def _txt(v, n: int) -> str:
    return str(v or "").strip()[:n]


def _url_ok(u: str) -> str:
    u = _txt(u, 1000)
    p = urlparse(u)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise NoValido("El enlace tiene que empezar por http:// o https://")
    return u


# ------------------------------------------------------------------ referencias
def _fila_ref(r) -> dict:
    d = dict(r)
    d["datos"] = jload(d.get("datos"), {})
    d["etiquetas"] = jload(d.get("etiquetas"), [])
    return d


def ref(con, rid: int) -> dict | None:
    r = con.execute("SELECT * FROM referencias WHERE id=?", (rid,)).fetchone()
    return _fila_ref(r) if r else None


def ref_por_clave(con, clave: str) -> dict | None:
    r = con.execute("SELECT * FROM referencias WHERE clave=?", (clave,)).fetchone()
    return _fila_ref(r) if r else None


def _desde_radar(radar, tipo: str, origen: str) -> dict:
    """Copia de lo que hay en el Radar ahora mismo (lo que se guarda en la referencia)."""
    if tipo == "noticia":
        n = radar.execute("SELECT * FROM news WHERE id=?", (origen,)).fetchone()
        if not n:
            raise NoValido("Esa noticia ya no está en los datos del Radar.")
        return {"clave": f"noticia:{n['id']}", "titulo": n["title"], "url": n["url"], "fuente": n["source"],
                "publicado_en": n["published_at"], "detectado_en": n["first_seen_at"],
                "extracto": n["ai_summary"] or n["summary"] or "",
                "datos": {"verificacion": n["verification"], "temas": jload(n["topics"]), "idioma": n["language"],
                          "oficial": bool(n["is_official"]), "resumen_es_ia": bool(n["ai_summary"])}}
    if tipo == "video":
        v = radar.execute("""SELECT v.*, c.name cname FROM videos v LEFT JOIN creators c ON c.id=v.creator_id
                             WHERE v.id=?""", (origen,)).fetchone()
        if not v:
            raise NoValido("Ese vídeo ya no está en los datos del Radar.")
        return {"clave": f"video:{v['id']}", "titulo": v["title"], "url": v["url"], "fuente": v["cname"],
                "publicado_en": v["published_at"], "detectado_en": v["first_seen_at"], "extracto": v["summary"] or "",
                "datos": {"vistas": v["views"], "vistas_hora": v["velocity"], "medido_en": v["last_scraped_at"],
                          "temas": jload(v["topics"]), "idioma": v["language"], "short": bool(v["is_short"]),
                          "miniatura": v["thumbnail_url"]}}
    if tipo == "creador":
        c = radar.execute("SELECT * FROM creators WHERE id=?", (origen,)).fetchone()
        if not c:
            raise NoValido("Ese creador ya no está en los datos del Radar.")
        ext = c["external_id"]
        return {"clave": f"creador:{c['id']}", "titulo": c["name"], "url": f"https://www.youtube.com/channel/{ext}",
                "fuente": "YouTube", "publicado_en": None, "detectado_en": c["first_seen_at"], "extracto": c["description"] or "",
                "datos": {"suscriptores": c["subscribers"], "idioma": c["language"], "handle": c["handle"]}}
    raise NoValido("Tipo de referencia desconocido.")


def crear_ref(con, tipo: str, origen: str | None = None, radar=None, url: str | None = None,
              titulo: str | None = None, fuente: str | None = None, publicado_en: str | None = None,
              datos: dict | None = None) -> dict:
    """Crea (o devuelve si ya existe) una referencia. Para «enlace» hacen falta url y título."""
    if tipo not in TIPOS:
        raise NoValido("Tipo de referencia desconocido.")
    if tipo == "enlace":
        u = _url_ok(url)
        t = _txt(titulo, MAX["titulo"]) or urlparse(u).netloc
        d = {"clave": "enlace:" + hashlib.sha1(u.encode()).hexdigest()[:16], "titulo": t, "url": u,
             "fuente": _txt(fuente, 120) or urlparse(u).netloc, "publicado_en": _txt(publicado_en, 40) or None,
             "detectado_en": None, "extracto": "", "datos": datos or {"manual": True}}
    else:
        if radar is None or not origen:
            raise NoValido("Falta el elemento del Radar.")
        d = _desde_radar(radar, tipo, str(origen)[:120])
    ya = ref_por_clave(con, d["clave"])
    if ya:
        return ya
    ahora = iso()
    con.execute("""INSERT INTO referencias(tipo,clave,titulo,url,fuente,publicado_en,detectado_en,extracto,datos,creada_en,actualizada_en)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (tipo, d["clave"], d["titulo"], d["url"], d["fuente"], d["publicado_en"], d["detectado_en"],
                 _txt(d["extracto"], MAX["texto"]), jdump(d["datos"]), ahora, ahora))
    con.commit()
    return ref_por_clave(con, d["clave"])


def actualizar_ref(con, rid: int, **campos) -> dict:
    r = ref(con, rid)
    if not r:
        raise NoValido("Esa referencia no existe.")
    cambios = {}
    for k in ("guardada", "leida", "archivada"):
        if k in campos and campos[k] is not None:
            cambios[k] = 1 if campos[k] else 0
    if campos.get("nota") is not None:
        cambios["nota"] = _txt(campos["nota"], MAX["nota"])
    if campos.get("etiquetas") is not None:
        et = campos["etiquetas"]
        if isinstance(et, str):
            et = et.split(",")
        cambios["etiquetas"] = jdump(sorted({_txt(e, 40).lower() for e in et if _txt(e, 40)})[:20])
    if cambios:
        cambios["actualizada_en"] = iso()
        con.execute(f"UPDATE referencias SET {', '.join(k + '=?' for k in cambios)} WHERE id=?", (*cambios.values(), rid))
        con.commit()
    return ref(con, rid)


def eliminar_ref(con, rid: int) -> int:
    """Borra la referencia y la quita de todas las investigaciones. Devuelve en cuántas estaba."""
    n = con.execute("SELECT COUNT(*) FROM inv_refs WHERE ref_id=?", (rid,)).fetchone()[0]
    con.execute("DELETE FROM inv_refs WHERE ref_id=?", (rid,))
    con.execute("DELETE FROM referencias WHERE id=?", (rid,))
    con.commit()
    return n


def biblioteca(con, texto: str = "", tipo: str = "", etiqueta: str = "", archivadas: bool = False) -> list[dict]:
    q = "SELECT * FROM referencias WHERE (guardada=1 OR id IN (SELECT ref_id FROM inv_refs)) AND archivada=?"
    args: list = [1 if archivadas else 0]
    if tipo in TIPOS:
        q += " AND tipo=?"
        args.append(tipo)
    if texto:
        q += " AND (titulo LIKE ? OR nota LIKE ? OR fuente LIKE ?)"
        args += [f"%{texto[:80]}%"] * 3
    out = []
    for r in con.execute(q + " ORDER BY actualizada_en DESC LIMIT 300", args):
        d = _fila_ref(r)
        if etiqueta and etiqueta.lower() not in d["etiquetas"]:
            continue
        d["investigaciones"] = [dict(x) for x in con.execute(
            "SELECT i.id, i.titulo FROM inv_refs ir JOIN investigaciones i ON i.id=ir.inv_id WHERE ir.ref_id=?", (d["id"],))]
        out.append(d)
    return out


def estados_refs(con, claves: list[str]) -> dict[str, dict]:
    """Estado (leída, guardada, nota, en qué investigaciones) de varios elementos del Radar a la vez."""
    out = {}
    for i in range(0, len(claves), 400):
        trozo = claves[i:i + 400]
        for r in con.execute(f"SELECT * FROM referencias WHERE clave IN ({','.join('?' * len(trozo))})", trozo):
            n = con.execute("SELECT COUNT(*) FROM inv_refs WHERE ref_id=?", (r["id"],)).fetchone()[0]
            out[r["clave"]] = {"id": r["id"], "leida": bool(r["leida"]), "guardada": bool(r["guardada"]),
                               "nota": r["nota"] or "", "en_investigaciones": n}
    return out


# ------------------------------------------------------------------ investigaciones
def crear_inv(con, titulo: str, pregunta: str = "", descripcion: str = "", temas=None) -> dict:
    t = _txt(titulo, MAX["titulo"])
    if len(t) < 3:
        raise NoValido("Ponle un título (mínimo 3 letras).")
    iid = secrets.token_hex(3)
    ahora = iso()
    con.execute("""INSERT INTO investigaciones(id,titulo,pregunta,descripcion,temas,estado,creada_en,actividad_en)
                   VALUES(?,?,?,?,?,'abierta',?,?)""",
                (iid, t, _txt(pregunta, MAX["corto"]), _txt(descripcion, MAX["texto"]),
                 jdump([_txt(x, 40) for x in (temas or []) if _txt(x, 40)][:10]), ahora, ahora))
    con.commit()
    return inv(con, iid)


def _tocar(con, iid: str) -> None:
    con.execute("UPDATE investigaciones SET actividad_en=? WHERE id=?", (iso(), iid))
    con.commit()


def inv(con, iid: str, completa: bool = False) -> dict | None:
    r = con.execute("SELECT * FROM investigaciones WHERE id=?", (iid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["temas"] = jload(d.get("temas"), [])
    d["n_fuentes"] = con.execute("SELECT COUNT(*) FROM inv_refs WHERE inv_id=?", (iid,)).fetchone()[0]
    d["n_notas"] = con.execute("SELECT COUNT(*) FROM notas WHERE inv_id=?", (iid,)).fetchone()[0]
    if completa:
        d["fuentes"] = [{**_fila_ref(x), "aporte": x["aporte"], "consultada_en": x["consultada_en"], "anadida_en": x["anadida_en"]}
                        for x in con.execute("""SELECT r.*, ir.aporte, ir.consultada_en, ir.anadida_en FROM inv_refs ir
                                                JOIN referencias r ON r.id=ir.ref_id WHERE ir.inv_id=? ORDER BY ir.anadida_en""", (iid,))]
        d["notas"] = [dict(x) for x in con.execute("SELECT * FROM notas WHERE inv_id=? ORDER BY creada_en", (iid,))]
    return d


def lista_inv(con, incluir_archivadas: bool = False) -> list[dict]:
    q = "SELECT id FROM investigaciones" + ("" if incluir_archivadas else " WHERE estado!='archivada'")
    return [inv(con, r["id"]) for r in con.execute(q + " ORDER BY actividad_en DESC")]


def actualizar_inv(con, iid: str, **campos) -> dict:
    if not inv(con, iid):
        raise NoValido("Esa investigación no existe.")
    cambios = {}
    if campos.get("estado") is not None:
        if campos["estado"] not in ESTADOS:
            raise NoValido("Estado desconocido.")
        cambios["estado"] = campos["estado"]
    if campos.get("titulo") is not None:
        t = _txt(campos["titulo"], MAX["titulo"])
        if len(t) < 3:
            raise NoValido("El título necesita al menos 3 letras.")
        cambios["titulo"] = t
    for k, n in (("pregunta", MAX["corto"]), ("descripcion", MAX["texto"]), ("que_se", MAX["texto"]),
                 ("que_falta", MAX["texto"]), ("conclusion", MAX["texto"])):
        if campos.get(k) is not None:
            cambios[k] = _txt(campos[k], n)
    if cambios.get("estado") and cambios["estado"] != inv(con, iid)["estado"]:
        from .verificacion import evento
        evento(con, "actualizacion", f"Estado: {ESTADOS_NOMBRE.get(cambios['estado'], cambios['estado'])}", inv_id=iid,
               automatico=True, commit=False)
    if cambios:
        cambios["actividad_en"] = iso()
        con.execute(f"UPDATE investigaciones SET {', '.join(k + '=?' for k in cambios)} WHERE id=?", (*cambios.values(), iid))
        con.commit()
    return inv(con, iid, completa=True)


def anadir_ref(con, iid: str, rid: int, aporte: str = "") -> dict:
    if not inv(con, iid):
        raise NoValido("Esa investigación no existe.")
    if not ref(con, rid):
        raise NoValido("Esa referencia no existe.")
    ahora = iso()
    nueva = con.execute("""INSERT INTO inv_refs(inv_id,ref_id,aporte,consultada_en,anadida_en) VALUES(?,?,?,?,?)
                   ON CONFLICT(inv_id,ref_id) DO NOTHING""", (iid, rid, _txt(aporte, MAX["aporte"]), ahora, ahora)).rowcount
    if nueva:  # en la cronología con sus fechas reales (publicado / detectado); «ocurrió» se deja vacío
        from .verificacion import evento
        r = ref(con, rid)
        evento(con, "publicacion", r["titulo"] or "Fuente añadida", inv_id=iid, ref_id=rid,
               publicado_en=r["publicado_en"], detectado_en=r["detectado_en"], automatico=True, commit=False)
    con.commit()
    _tocar(con, iid)
    return inv(con, iid, completa=True)


def editar_aporte(con, iid: str, rid: int, aporte: str) -> dict:
    con.execute("UPDATE inv_refs SET aporte=? WHERE inv_id=? AND ref_id=?", (_txt(aporte, MAX["aporte"]), iid, rid))
    con.commit()
    _tocar(con, iid)
    return inv(con, iid, completa=True)


def quitar_ref(con, iid: str, rid: int) -> dict:
    con.execute("DELETE FROM inv_refs WHERE inv_id=? AND ref_id=?", (iid, rid))
    con.commit()
    _tocar(con, iid)
    return inv(con, iid, completa=True)


def nota(con, iid: str, texto: str, tipo: str = "apunte", nid: int | None = None) -> dict:
    if not inv(con, iid):
        raise NoValido("Esa investigación no existe.")
    t = _txt(texto, MAX["texto"])
    if not t:
        raise NoValido("La nota está vacía.")
    tipo = tipo if tipo in TIPOS_NOTA else "apunte"
    if nid:
        con.execute("UPDATE notas SET texto=?, tipo=?, actualizada_en=? WHERE id=? AND inv_id=?", (t, tipo, iso(), nid, iid))
    else:
        con.execute("INSERT INTO notas(inv_id,tipo,texto,creada_en,actualizada_en) VALUES(?,?,?,?,?)", (iid, tipo, t, iso(), iso()))
    con.commit()
    _tocar(con, iid)
    return inv(con, iid, completa=True)


def borrar_nota(con, iid: str, nid: int) -> dict:
    con.execute("DELETE FROM notas WHERE id=? AND inv_id=?", (nid, iid))
    con.commit()
    _tocar(con, iid)
    return inv(con, iid, completa=True)

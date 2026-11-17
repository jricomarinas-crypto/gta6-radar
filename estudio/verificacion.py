"""Verificación y cronología (fase 2A). Todo privado (data/estudio.db).

- La unidad es la AFIRMACIÓN concreta («GTA 6 costará 80 dólares»), no el artículo.
- Evidencias: referencias de la biblioteca marcadas «a favor», «en contra» o «solo repite». Las que solo repiten
  nunca cuentan como independientes: que mucha gente lo diga no lo hace más cierto.
- No hay puntuación de «verdad». El estado lo pone Javier y cada cambio queda en un historial que no se borra.
- Para «Confirmado» hace falta al menos una evidencia a favor marcada como independiente (fuente primaria).
- Cronología con tres fechas distintas: cuándo ocurrió, cuándo se publicó y cuándo lo detectó el Radar.
  Si una fecha no se conoce, se queda vacía.
"""
from __future__ import annotations

import re

from radar.db import iso, jload

from .investigacion import MAX, NoValido, _txt, inv, ref

ESTADOS = {
    "pendiente": "Pendiente de revisar",
    "sin_evidencia": "Sin evidencia suficiente",
    "atribuida": "Información atribuida",
    "confirmado": "Confirmado por fuente primaria",
    "contradicho": "Contradicho por evidencia",
    "no_verificable": "No verificable con los datos disponibles",
}
# Etiqueta que lleva cada estado en un guion (fabrica/guion.py). «DESMENTIDO» solo cabe en la variante verdad/bulo.
ETIQUETA = {"confirmado": "CONFIRMADO", "atribuida": "REPORTADO", "pendiente": "RUMOR", "sin_evidencia": "RUMOR",
            "no_verificable": "RUMOR", "contradicho": "DESMENTIDO"}
RELACIONES = {"a_favor": "A favor", "en_contra": "En contra", "repite": "Solo repite"}
TIPOS_EVENTO = {"anuncio": "Anuncio", "publicacion": "Publicación relevante", "rumor": "Aparece un rumor",
                "confirmacion": "Confirmación", "desmentido": "Desmentido o contradicción",
                "actualizacion": "Actualización de la investigación"}
DIAS_REVISION = 7  # pasado este tiempo sin revisar, la ficha avisa «revisión antigua»


def _fecha(v) -> str | None:
    """Acepta AAAA-MM-DD o una fecha ISO. Vacía → None (desconocida). Otra cosa → error claro."""
    v = _txt(v, 40)
    if not v:
        return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}([T ][\d:.]+(Z|[+-]\d{2}:?\d{2})?)?", v):
        raise NoValido("La fecha tiene que ser AAAA-MM-DD (o déjala vacía si no se conoce).")
    return v


def _historial(con, aid: int, campo: str, antes, despues, nota: str = "") -> None:
    con.execute("INSERT INTO afirm_historial(afirmacion_id,campo,antes,despues,nota,cuando) VALUES(?,?,?,?,?,?)",
                (aid, campo, None if antes is None else str(antes), None if despues is None else str(despues),
                 _txt(nota, MAX["nota"]), iso()))


# ------------------------------------------------------------------ afirmaciones
def crear_afirm(con, texto: str, inv_id: str | None = None, quien_primero: str = "", fecha_origen: str = "",
                ref_origen: int | None = None, nota: str = "") -> dict:
    t = _txt(texto, MAX["corto"])
    if len(t) < 8:
        raise NoValido("Escribe la afirmación completa (mínimo 8 letras).")
    if inv_id and not inv(con, inv_id):
        raise NoValido("Esa investigación no existe.")
    r = ref(con, int(ref_origen)) if ref_origen else None
    if ref_origen and not r:
        raise NoValido("La referencia de origen no existe.")
    fo = _fecha(fecha_origen)
    ahora = iso()
    cur = con.execute("""INSERT INTO afirmaciones(texto,quien_primero,fecha_origen,ref_origen,estado,nota,creada_en,revisada_en)
                         VALUES(?,?,?,?,'pendiente',?,?,NULL)""",
                      (t, _txt(quien_primero, MAX["corto"]), fo, r["id"] if r else None, _txt(nota, MAX["nota"]), ahora))
    aid = cur.lastrowid
    _historial(con, aid, "creada", None, "pendiente")
    if inv_id:
        con.execute("INSERT OR IGNORE INTO inv_afirm VALUES(?,?,?)", (inv_id, aid, ahora))
    evento(con, "rumor", f"Aparece: «{t}»", inv_id=inv_id, afirmacion_id=aid, ref_id=r["id"] if r else None,
           ocurrio_en=fo, publicado_en=r["publicado_en"] if r else None, detectado_en=r["detectado_en"] if r else None,
           automatico=True, commit=False)
    con.commit()
    return afirm(con, aid, completa=True)


def afirm(con, aid: int, completa: bool = False) -> dict | None:
    r = con.execute("SELECT * FROM afirmaciones WHERE id=?", (aid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["estado_nombre"] = ESTADOS.get(d["estado"], d["estado"])
    d["etiqueta"] = ETIQUETA.get(d["estado"], "RUMOR")
    ev = [dict(x) for x in con.execute("""SELECT e.*, r.titulo, r.url, r.fuente, r.publicado_en, r.tipo FROM afirm_evidencias e
                                          JOIN referencias r ON r.id=e.ref_id WHERE e.afirmacion_id=? ORDER BY e.anadida_en""", (aid,))]
    d["cuentas"] = {
        "a_favor": sum(e["relacion"] == "a_favor" for e in ev),
        "en_contra": sum(e["relacion"] == "en_contra" for e in ev),
        "repite": sum(e["relacion"] == "repite" for e in ev),
        # las que solo repiten nunca son independientes, aunque alguien las marcara así
        "independientes": sum(bool(e["independiente"]) and e["relacion"] != "repite" for e in ev),
    }
    d["investigaciones"] = [dict(x) for x in con.execute(
        "SELECT i.id, i.titulo FROM inv_afirm ia JOIN investigaciones i ON i.id=ia.inv_id WHERE ia.afirmacion_id=?", (aid,))]
    ult = d["revisada_en"] or d["creada_en"]
    d["revision_antigua"] = bool(ult and con.execute("SELECT julianday('now') - julianday(?)", (ult[:19],)).fetchone()[0]
                                 > DIAS_REVISION)
    if completa:
        d["evidencias"] = ev
        d["historial"] = [dict(x) for x in con.execute(
            "SELECT * FROM afirm_historial WHERE afirmacion_id=? ORDER BY id DESC", (aid,))]
        d["origen"] = ref(con, d["ref_origen"]) if d["ref_origen"] else None
    return d


def lista_afirm(con, estado: str = "", inv_id: str = "", texto: str = "") -> list[dict]:
    q, args = "SELECT id FROM afirmaciones WHERE 1=1", []
    if estado in ESTADOS:
        q += " AND estado=?"
        args.append(estado)
    if inv_id:
        q += " AND id IN (SELECT afirmacion_id FROM inv_afirm WHERE inv_id=?)"
        args.append(inv_id)
    if texto:
        q += " AND (texto LIKE ? OR nota LIKE ? OR quien_primero LIKE ?)"
        args += [f"%{texto[:80]}%"] * 3
    return [afirm(con, r["id"], completa=True) for r in con.execute(q + " ORDER BY COALESCE(revisada_en, creada_en) DESC LIMIT 300", args)]


def _existe(con, aid: int) -> dict:
    a = afirm(con, aid)
    if not a:
        raise NoValido("Esa afirmación no existe.")
    return a


def editar_afirm(con, aid: int, **campos) -> dict:
    a = _existe(con, aid)
    cambios = {}
    if campos.get("texto") is not None:
        t = _txt(campos["texto"], MAX["corto"])
        if len(t) < 8:
            raise NoValido("Escribe la afirmación completa (mínimo 8 letras).")
        cambios["texto"] = t
    if campos.get("quien_primero") is not None:
        cambios["quien_primero"] = _txt(campos["quien_primero"], MAX["corto"])
    if campos.get("fecha_origen") is not None:
        cambios["fecha_origen"] = _fecha(campos["fecha_origen"])
    if campos.get("nota") is not None:
        cambios["nota"] = _txt(campos["nota"], MAX["nota"])
    for k, v in cambios.items():
        if (a.get(k) or None) != (v or None):
            _historial(con, aid, k, a.get(k), v)
    if cambios:
        con.execute(f"UPDATE afirmaciones SET {', '.join(k + '=?' for k in cambios)} WHERE id=?", (*cambios.values(), aid))
    con.commit()
    return afirm(con, aid, completa=True)


def cambiar_estado(con, aid: int, estado: str, nota: str = "") -> dict:
    """Valoración manual. Confirmado exige una evidencia independiente a favor; Confirmado y Contradicho, una nota."""
    a = _existe(con, aid)
    if estado not in ESTADOS:
        raise NoValido("Estado desconocido.")
    nota = _txt(nota, MAX["nota"])
    if estado in ("confirmado", "contradicho") and not nota:
        raise NoValido("Explica en una nota por qué la marcas así (queda en el historial).")
    if estado == "confirmado":
        ok = con.execute("""SELECT COUNT(*) FROM afirm_evidencias WHERE afirmacion_id=? AND relacion='a_favor'
                            AND independiente=1""", (aid,)).fetchone()[0]
        if not ok:
            raise NoValido("Para «Confirmado» añade antes una evidencia A FAVOR marcada como fuente independiente "
                           "(oficial o primaria). Que muchos lo repitan no la confirma.")
    if estado == "contradicho":
        if not con.execute("SELECT COUNT(*) FROM afirm_evidencias WHERE afirmacion_id=? AND relacion='en_contra'",
                           (aid,)).fetchone()[0]:
            raise NoValido("Para «Contradicho» añade antes la evidencia EN CONTRA.")
    ahora = iso()
    _historial(con, aid, "estado", a["estado"], estado, nota)  # también si no cambia: cuenta como revisión
    con.execute("UPDATE afirmaciones SET estado=?, revisada_en=? WHERE id=?", (estado, ahora, aid))
    if estado != a["estado"] and estado in ("confirmado", "contradicho"):
        evento(con, "confirmacion" if estado == "confirmado" else "desmentido",
               f"{'Confirmado' if estado == 'confirmado' else 'Contradicho'}: «{a['texto']}»",
               afirmacion_id=aid, nota=nota, automatico=True, commit=False)
    con.commit()
    return afirm(con, aid, completa=True)


def evidencia(con, aid: int, ref_id: int, relacion: str, independiente: bool = False, nota: str = "") -> dict:
    _existe(con, aid)
    if relacion not in RELACIONES:
        raise NoValido("Relación desconocida (a favor, en contra o solo repite).")
    if not ref(con, int(ref_id)):
        raise NoValido("Esa referencia no existe.")
    indep = 0 if relacion == "repite" else int(bool(independiente))
    previa = con.execute("SELECT relacion, independiente FROM afirm_evidencias WHERE afirmacion_id=? AND ref_id=?",
                         (aid, ref_id)).fetchone()
    con.execute("""INSERT INTO afirm_evidencias(afirmacion_id,ref_id,relacion,independiente,nota,anadida_en) VALUES(?,?,?,?,?,?)
                   ON CONFLICT(afirmacion_id,ref_id) DO UPDATE SET relacion=excluded.relacion,
                   independiente=excluded.independiente, nota=excluded.nota""",
                (aid, ref_id, relacion, indep, _txt(nota, MAX["aporte"]), iso()))
    antes = f"{previa['relacion']}{' (independiente)' if previa['independiente'] else ''}" if previa else None
    _historial(con, aid, f"evidencia #{ref_id}", antes, f"{relacion}{' (independiente)' if indep else ''}")
    con.commit()
    return afirm(con, aid, completa=True)


def quitar_evidencia(con, aid: int, ref_id: int) -> dict:
    _existe(con, aid)
    if con.execute("DELETE FROM afirm_evidencias WHERE afirmacion_id=? AND ref_id=?", (aid, ref_id)).rowcount:
        _historial(con, aid, f"evidencia #{ref_id}", "quitada", None)
    con.commit()
    return afirm(con, aid, completa=True)


def enlazar(con, inv_id: str, aid: int) -> dict:
    _existe(con, aid)
    if not inv(con, inv_id):
        raise NoValido("Esa investigación no existe.")
    con.execute("INSERT OR IGNORE INTO inv_afirm VALUES(?,?,?)", (inv_id, aid, iso()))
    con.commit()
    return afirm(con, aid, completa=True)


def desenlazar(con, inv_id: str, aid: int) -> dict:
    """La quita de la investigación; la afirmación y su historial siguen en Rumores y verificación."""
    con.execute("DELETE FROM inv_afirm WHERE inv_id=? AND afirmacion_id=?", (inv_id, aid))
    con.commit()
    return {"ok": True}


# ------------------------------------------------------------------ cronología
def evento(con, tipo: str, titulo: str, inv_id: str | None = None, afirmacion_id: int | None = None,
           ref_id: int | None = None, ocurrio_en=None, publicado_en=None, detectado_en=None, nota: str = "",
           automatico: bool = False, commit: bool = True) -> dict:
    if tipo not in TIPOS_EVENTO:
        raise NoValido("Tipo de evento desconocido.")
    t = _txt(titulo, MAX["corto"])
    if not t:
        raise NoValido("Ponle un título al evento.")
    if inv_id and not inv(con, inv_id):
        raise NoValido("Esa investigación no existe.")
    r = ref(con, int(ref_id)) if ref_id else None
    if not automatico:  # en los manuales, las fechas de la referencia salen de la referencia, no se escriben
        ocurrio_en = _fecha(ocurrio_en)
        publicado_en = r["publicado_en"] if r else _fecha(publicado_en)
        detectado_en = r["detectado_en"] if r else None
    cur = con.execute("""INSERT INTO cronologia(inv_id,afirmacion_id,ref_id,tipo,titulo,nota,ocurrio_en,publicado_en,
                         detectado_en,automatico,creado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                      (inv_id, afirmacion_id, r["id"] if r else None, tipo, t, _txt(nota, MAX["nota"]), ocurrio_en,
                       publicado_en, detectado_en, int(automatico), iso()))
    if commit:
        con.commit()
    return {"id": cur.lastrowid}


def _evento_manual(con, eid: int) -> dict:
    e = con.execute("SELECT * FROM cronologia WHERE id=?", (eid,)).fetchone()
    if not e:
        raise NoValido("Ese evento no existe.")
    return dict(e)


def editar_evento(con, eid: int, **campos) -> dict:
    e = _evento_manual(con, eid)
    if "oculto" in campos and campos["oculto"] is not None:  # ocultar/mostrar vale para todos
        con.execute("UPDATE cronologia SET oculto=? WHERE id=?", (int(bool(campos["oculto"])), eid))
    if e["automatico"] and any(campos.get(k) is not None for k in ("titulo", "tipo", "nota", "ocurrio_en")):
        raise NoValido("Los eventos automáticos no se editan: puedes ocultarlos.")
    cambios = {}
    if campos.get("titulo") is not None:
        cambios["titulo"] = _txt(campos["titulo"], MAX["corto"]) or e["titulo"]
    if campos.get("tipo") is not None:
        if campos["tipo"] not in TIPOS_EVENTO:
            raise NoValido("Tipo de evento desconocido.")
        cambios["tipo"] = campos["tipo"]
    if campos.get("nota") is not None:
        cambios["nota"] = _txt(campos["nota"], MAX["nota"])
    if campos.get("ocurrio_en") is not None:
        cambios["ocurrio_en"] = _fecha(campos["ocurrio_en"])
    if cambios:
        con.execute(f"UPDATE cronologia SET {', '.join(k + '=?' for k in cambios)} WHERE id=?", (*cambios.values(), eid))
    con.commit()
    return _evento_manual(con, eid)


def borrar_evento(con, eid: int) -> dict:
    e = _evento_manual(con, eid)
    if e["automatico"]:
        raise NoValido("Los eventos automáticos no se borran: puedes ocultarlos.")
    con.execute("DELETE FROM cronologia WHERE id=?", (eid,))
    con.commit()
    return {"ok": True}


def cronologia(con, inv_id: str = "", tipo: str = "", desde: str = "", hasta: str = "", fuente: str = "",
               tema: str = "", ocultos: bool = False) -> list[dict]:
    """Eventos ordenados por la fecha más fiable que tengan: ocurrió → publicado → detectado → registrado."""
    q = """SELECT c.*, r.fuente, r.url, r.datos, i.titulo inv_titulo,
                  COALESCE(c.ocurrio_en, c.publicado_en, c.detectado_en, c.creado_en) orden,
                  CASE WHEN c.ocurrio_en IS NOT NULL THEN 'ocurrio' WHEN c.publicado_en IS NOT NULL THEN 'publicado'
                       WHEN c.detectado_en IS NOT NULL THEN 'detectado' ELSE 'registrado' END fecha_usada
           FROM cronologia c LEFT JOIN referencias r ON r.id=c.ref_id LEFT JOIN investigaciones i ON i.id=c.inv_id WHERE 1=1"""
    args: list = []
    if inv_id:
        q += " AND (c.inv_id=? OR c.afirmacion_id IN (SELECT afirmacion_id FROM inv_afirm WHERE inv_id=?))"
        args += [inv_id, inv_id]
    if tipo in TIPOS_EVENTO:
        q += " AND c.tipo=?"
        args.append(tipo)
    if not ocultos:
        q += " AND c.oculto=0"
    if fuente:
        q += " AND r.fuente=?"
        args.append(fuente[:80])
    out = []
    for x in con.execute(q + " ORDER BY orden DESC LIMIT 500", args):
        d = dict(x)
        temas = jload(d.pop("datos"), {}).get("temas") or []
        if tema and tema not in temas:
            continue
        if desde and (d["orden"] or "") < desde:
            continue
        if hasta and (d["orden"] or "")[:10] > hasta:
            continue
        d["temas"] = temas
        d["tipo_nombre"] = TIPOS_EVENTO.get(d["tipo"], d["tipo"])
        out.append(d)
    return out

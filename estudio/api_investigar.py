"""API de investigación del Estudio (fase 1B). La usa estudio/servidor.py.

GET  /api/buscar?q=&tipos=noticia,video&dias=&fuente=&idioma=&tema=&verificacion=
GET  /api/noticias?vista=ultimas|sin_leer|guardadas&fuente=&tema=
GET  /api/biblioteca?q=&tipo=&etiqueta=&archivadas=1
GET  /api/investigaciones            GET /api/investigaciones/<id>
POST /api/estados {claves:[...]}                         estado de varios elementos del Radar
POST /api/referencias {tipo, origen | url+titulo, guardada?, leida?, nota?}
POST /api/referencias/<id> {guardada?, leida?, archivada?, nota?, etiquetas?}
POST /api/referencias/<id>/eliminar
POST /api/investigaciones {titulo, pregunta?, descripcion?}
POST /api/investigaciones/<id> {estado?, titulo?, pregunta?, descripcion?, que_se?, que_falta?, conclusion?}
POST /api/investigaciones/<id>/fuentes {ref_id | tipo+origen | url+titulo, aporte?}
POST /api/investigaciones/<id>/fuentes/<ref>        {aporte}
POST /api/investigaciones/<id>/fuentes/<ref>/quitar
POST /api/investigaciones/<id>/notas {texto, tipo, id?}
POST /api/investigaciones/<id>/notas/<nota>/borrar
Devuelve (código, datos) o None si la ruta no es suya.
"""
from __future__ import annotations

import re
from contextlib import closing
from urllib.parse import parse_qs

from radar.db import jload
from radar.trends import TOPIC_LABEL

from . import busqueda, db, ideas
from . import investigacion as inv

RE_INV = r"([0-9a-f]{6})"


def _q(query: str) -> dict:
    return {k: v[0] for k, v in parse_qs(query).items()}


def _crear_ref(con, body: dict) -> dict:
    tipo = str(body.get("tipo", ""))
    if tipo == "enlace":
        return inv.crear_ref(con, "enlace", url=body.get("url"), titulo=body.get("titulo"))
    with closing(ideas.radar_db()) as radar:
        return inv.crear_ref(con, tipo, origen=str(body.get("origen", "")), radar=radar)


def get(path: str, query: str):
    q = _q(query)
    con = db.connect()
    if path == "/api/buscar":
        with closing(ideas.radar_db()) as radar:
            tipos = [t for t in q.get("tipos", "").split(",") if t]
            dias = int(q["dias"]) if q.get("dias", "").isdigit() else None
            res = busqueda.buscar(radar, con, q.get("q", "")[:200], tipos, dias, q.get("fuente", ""), q.get("idioma", ""),
                                  q.get("tema", ""), q.get("verificacion", ""), demo=ideas.es_demo(radar))
            res["fuentes"] = busqueda.fuentes_disponibles(radar)
            res["demo"] = ideas.es_demo(radar)
        res["temas"] = TOPIC_LABEL
        res["tipos"] = busqueda.TIPOS
        return 200, res
    if path == "/api/noticias":
        vista = q.get("vista", "ultimas")
        with closing(ideas.radar_db()) as radar:
            demo = ideas.es_demo(radar)
            filas = [dict(r) for r in radar.execute(
                "SELECT * FROM news WHERE COALESCE(is_related,1)=1 ORDER BY published_at DESC LIMIT 400")]
            fuentes = sorted({f["source"] for f in filas if f["source"]})
        estados = inv.estados_refs(con, [f"noticia:{f['id']}" for f in filas])
        out = []
        for f in filas:
            e = estados.get(f"noticia:{f['id']}", {})
            temas = jload(f["topics"], [])
            if vista == "sin_leer" and e.get("leida"):
                continue
            if vista == "guardadas" and not e.get("guardada"):
                continue
            if q.get("fuente") and f["source"] != q["fuente"]:
                continue
            if q.get("tema") and q["tema"] not in temas:
                continue
            out.append({"id": f["id"], "titulo": f["title"], "url": f["url"], "fuente": f["source"],
                        "publicado_en": f["published_at"], "detectado_en": f["first_seen_at"],
                        "resumen": f["ai_summary"] or f["summary"] or "", "resumen_es_ia": bool(f["ai_summary"]),
                        "verificacion": f["verification"], "oficial": bool(f["is_official"]), "temas": temas,
                        "idioma": f["language"], "estado": e})
        return 200, {"noticias": out[:200], "total": len(out), "fuentes": fuentes, "temas": TOPIC_LABEL, "demo": demo}
    if path == "/api/biblioteca":
        return 200, {"referencias": inv.biblioteca(con, q.get("q", ""), q.get("tipo", ""), q.get("etiqueta", ""),
                                                   q.get("archivadas") == "1")}
    if path == "/api/investigaciones":
        return 200, {"investigaciones": inv.lista_inv(con, q.get("todas") == "1"), "estados": inv.ESTADOS}
    m = re.fullmatch(r"/api/investigaciones/" + RE_INV, path)
    if m:
        d = inv.inv(con, m.group(1), completa=True)
        return (200, d) if d else (404, {"error": "Esa investigación no existe."})
    return None


def post(path: str, body: dict):
    con = db.connect()
    try:
        if path == "/api/estados":
            claves = [str(c)[:160] for c in (body.get("claves") or [])][:2000]
            return 200, {"estados": inv.estados_refs(con, claves)}
        if path == "/api/referencias":
            r = _crear_ref(con, body)
            if any(body.get(k) is not None for k in ("guardada", "leida", "nota")):
                r = inv.actualizar_ref(con, r["id"], guardada=body.get("guardada"), leida=body.get("leida"), nota=body.get("nota"))
            return 200, r
        m = re.fullmatch(r"/api/referencias/(\d+)(/eliminar)?", path)
        if m:
            rid = int(m.group(1))
            if m.group(2):
                return 200, {"ok": True, "estaba_en_investigaciones": inv.eliminar_ref(con, rid)}
            return 200, inv.actualizar_ref(con, rid, **{k: body.get(k) for k in ("guardada", "leida", "archivada", "nota", "etiquetas")})
        if path == "/api/investigaciones":
            return 200, inv.crear_inv(con, body.get("titulo", ""), body.get("pregunta", ""), body.get("descripcion", ""))
        m = re.fullmatch(r"/api/investigaciones/" + RE_INV + r"(?:/(fuentes|notas)(?:/(\d+))?(?:/(quitar|borrar))?)?", path)
        if m:
            iid, sub, num, accion = m.groups()
            if not sub:
                return 200, inv.actualizar_inv(con, iid, **{k: body.get(k) for k in
                                                          ("estado", "titulo", "pregunta", "descripcion", "que_se", "que_falta", "conclusion")})
            if sub == "fuentes":
                if num and accion == "quitar":
                    return 200, inv.quitar_ref(con, iid, int(num))
                if num:
                    return 200, inv.editar_aporte(con, iid, int(num), body.get("aporte", ""))
                rid = body.get("ref_id")
                if not rid:
                    rid = _crear_ref(con, body)["id"]
                return 200, inv.anadir_ref(con, iid, int(rid), body.get("aporte", ""))
            if sub == "notas":
                if num and accion == "borrar":
                    return 200, inv.borrar_nota(con, iid, int(num))
                return 200, inv.nota(con, iid, body.get("texto", ""), body.get("tipo", "apunte"), int(num) if num else None)
        return None
    except inv.NoValido as e:
        return 409, {"error": str(e)}
    except (TypeError, ValueError) as e:
        return 400, {"error": f"Datos no válidos ({e.__class__.__name__})."}

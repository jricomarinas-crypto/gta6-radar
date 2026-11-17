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
Fase 2A:
GET  /api/afirmaciones?estado=&inv=&q=     GET /api/afirmaciones/<id>
POST /api/afirmaciones {texto, inv_id?, quien_primero?, fecha_origen?, ref_origen?, nota?}
POST /api/afirmaciones/<id> {texto?, quien_primero?, fecha_origen?, nota?}
POST /api/afirmaciones/<id>/estado {estado, nota}
POST /api/afirmaciones/<id>/evidencias {ref_id, relacion, independiente?, nota?}
POST /api/afirmaciones/<id>/evidencias/<ref>/quitar
POST /api/investigaciones/<id>/afirmaciones/<afirm>[/quitar]      enlazar / desenlazar
GET  /api/cronologia?inv=&tipo=&desde=&hasta=&fuente=&tema=&ocultos=1
POST /api/cronologia {tipo, titulo, inv_id?, ref_id?, ocurrio_en?, publicado_en?, nota?}
POST /api/cronologia/<id> {titulo?, tipo?, nota?, ocurrio_en?, oculto?}    POST /api/cronologia/<id>/borrar
GET  /api/investigaciones/<id>/dossier          vista previa (sin guardar)
POST /api/investigaciones/<id>/dossier          guarda una versión congelada
GET  /api/dossiers?inv=                          GET /api/dossiers/<id>
POST /api/dossiers/<id>/idea {variante, plataformas}   crea la pieza en el Estudio (etapa Idea; no aprueba nada)
Fase 3:
POST /api/externo/google-news {q, region}       búsqueda EXTERNA explícita (gratis; la consulta va a Google News)
POST /api/referencias {tipo:"enlace", url, titulo, fuente?, publicado_en?, guardada?}   guardar un resultado externo
GET  /api/seguimientos                           seguimientos activos con su número de novedades
GET  /api/investigaciones/<id>/seguimiento       estado + novedades
POST /api/investigaciones/<id>/seguimiento {consultas} | /dejar | /revisado
Devuelve (código, datos) o None si la ruta no es suya.
"""
from __future__ import annotations

import re
from contextlib import closing
from urllib.parse import parse_qs

from radar.db import jload
from radar.trends import TOPIC_LABEL

from . import busqueda, db, ideas
from . import dossier as dos
from . import externo, seguimiento as seg
from . import verificacion as ver
from . import investigacion as inv

RE_INV = r"([0-9a-f]{6})"


def _q(query: str) -> dict:
    return {k: v[0] for k, v in parse_qs(query).items()}


def _crear_ref(con, body: dict) -> dict:
    tipo = str(body.get("tipo", ""))
    if tipo == "enlace":
        externo_ = body.get("externo")
        return inv.crear_ref(con, "enlace", url=body.get("url"), titulo=body.get("titulo"), fuente=body.get("fuente"),
                             publicado_en=body.get("publicado_en"),
                             datos={"externo": str(externo_)[:40], "consultado_en": body.get("consultado_en")} if externo_ else None)
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
        if d:
            d["n_afirmaciones"] = len(ver.lista_afirm(con, inv_id=m.group(1)))
            d["piezas"] = [p for x in dos.lista(con, m.group(1)) for p in x["piezas"]]
        return (200, d) if d else (404, {"error": "Esa investigación no existe."})
    if path == "/api/afirmaciones":
        return 200, {"afirmaciones": ver.lista_afirm(con, q.get("estado", ""), q.get("inv", ""), q.get("q", "")),
                     "estados": ver.ESTADOS, "relaciones": ver.RELACIONES, "dias_revision": ver.DIAS_REVISION}
    m = re.fullmatch(r"/api/afirmaciones/(\d+)", path)
    if m:
        d = ver.afirm(con, int(m.group(1)), completa=True)
        return (200, d) if d else (404, {"error": "Esa afirmación no existe."})
    if path == "/api/cronologia":
        return 200, {"eventos": ver.cronologia(con, q.get("inv", ""), q.get("tipo", ""), q.get("desde", ""), q.get("hasta", ""),
                                               q.get("fuente", ""), q.get("tema", ""), q.get("ocultos") == "1"),
                     "tipos": ver.TIPOS_EVENTO, "temas": TOPIC_LABEL}
    m = re.fullmatch(r"/api/investigaciones/" + RE_INV + r"/dossier", path)
    if m:
        try:
            d = dos.generar(con, m.group(1))
        except inv.NoValido as e:
            return 404, {"error": str(e)}
        return 200, {"contenido": d, "markdown": dos.markdown(d), "versiones": dos.lista(con, m.group(1)),
                     "variantes": {k: v[1] for k, v in ideas.VARIANTES.items()}, "plataformas": ideas.PLATAFORMAS}
    if path == "/api/seguimientos":
        with closing(ideas.radar_db()) as radar:
            return 200, {"seguimientos": seg.todos(radar, con, ideas.es_demo(radar))}
    m = re.fullmatch(r"/api/investigaciones/" + RE_INV + r"/seguimiento", path)
    if m:
        with closing(ideas.radar_db()) as radar:
            return 200, {"seguimiento": seg.estado(con, m.group(1)),
                         "novedades": seg.novedades(radar, con, m.group(1), ideas.es_demo(radar))}
    if path == "/api/dossiers":
        return 200, {"dossiers": dos.lista(con, q.get("inv", ""))}
    m = re.fullmatch(r"/api/dossiers/(\d+)", path)
    if m:
        d = dos.obtener(con, int(m.group(1)))
        return (200, d) if d else (404, {"error": "Ese dossier no existe."})
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
        if path == "/api/externo/google-news":
            return 200, externo.google_news(body.get("q", ""), body.get("region", "latam"))
        m = re.fullmatch(r"/api/investigaciones/" + RE_INV + r"/seguimiento(?:/(dejar|revisado))?", path)
        if m:
            if m.group(2) == "dejar":
                return 200, seg.dejar(con, m.group(1))
            if m.group(2) == "revisado":
                return 200, seg.revisado(con, m.group(1))
            return 200, seg.seguir(con, m.group(1), body.get("consultas", ""))
        if path == "/api/afirmaciones":
            return 200, ver.crear_afirm(con, body.get("texto", ""), body.get("inv_id") or None, body.get("quien_primero", ""),
                                        body.get("fecha_origen", ""), body.get("ref_origen") or None, body.get("nota", ""))
        m = re.fullmatch(r"/api/afirmaciones/(\d+)(?:/(estado|evidencias)(?:/(\d+)/quitar)?)?", path)
        if m:
            aid, sub, rid = int(m.group(1)), m.group(2), m.group(3)
            if not sub:
                return 200, ver.editar_afirm(con, aid, **{k: body.get(k) for k in ("texto", "quien_primero", "fecha_origen", "nota")})
            if sub == "estado":
                return 200, ver.cambiar_estado(con, aid, body.get("estado", ""), body.get("nota", ""))
            if rid:
                return 200, ver.quitar_evidencia(con, aid, int(rid))
            return 200, ver.evidencia(con, aid, int(body.get("ref_id") or 0), body.get("relacion", ""),
                                      bool(body.get("independiente")), body.get("nota", ""))
        m = re.fullmatch(r"/api/investigaciones/" + RE_INV + r"/afirmaciones/(\d+)(/quitar)?", path)
        if m:
            if m.group(3):
                return 200, ver.desenlazar(con, m.group(1), int(m.group(2)))
            return 200, ver.enlazar(con, m.group(1), int(m.group(2)))
        if path == "/api/cronologia":
            return 200, ver.evento(con, body.get("tipo", ""), body.get("titulo", ""), body.get("inv_id") or None,
                                   ref_id=body.get("ref_id") or None, ocurrio_en=body.get("ocurrio_en"),
                                   publicado_en=body.get("publicado_en"), nota=body.get("nota", ""))
        m = re.fullmatch(r"/api/cronologia/(\d+)(/borrar)?", path)
        if m:
            if m.group(2):
                return 200, ver.borrar_evento(con, int(m.group(1)))
            return 200, ver.editar_evento(con, int(m.group(1)), **{k: body.get(k) for k in ("titulo", "tipo", "nota", "ocurrio_en", "oculto")})
        m = re.fullmatch(r"/api/investigaciones/" + RE_INV + r"/dossier", path)
        if m:
            return 200, dos.guardar(con, m.group(1))
        m = re.fullmatch(r"/api/dossiers/(\d+)/idea", path)
        if m:
            return 200, dos.crear_idea(con, int(m.group(1)), body.get("variante", ""), body.get("plataformas") or [])
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

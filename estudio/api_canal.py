"""API de Mi canal (fase 2B). La usa estudio/servidor.py. Devuelve (código, datos) o None si la ruta no es suya.

GET  /api/canal/videos?plataforma=&campo=&valor=        GET /api/canal/mediciones?plataforma=&video=
GET  /api/canal/estadisticas                            diario, periodos y desgloses
GET  /api/canal/serie                                   la gráfica «Mi canal» de Hoy (None si no hay mediciones)
GET  /api/canal/rinde?agrupar=formato&plataforma=&dias=&orden=
GET  /api/colaboradores                                 destacados, emergentes (Radar) y guardados
POST /api/canal/videos {plataforma, url, titulo?, publicado_en}      POST /api/canal/videos/<id> {serie?, colaboracion?, ...}
POST /api/canal/mediciones {video_id | plataforma+url+publicado_en, medido_en, métricas…, nota?, confirmar?, id?}
POST /api/canal/mediciones/<id>/borrar
POST /api/colaboradores {creador_radar | nombre+url, nota?}     POST /api/colaboradores/<id> {estado?, nota?}
POST /api/colaboradores/<id>/borrar
Nada de esto envía mensajes ni publica nada.
"""
from __future__ import annotations

import re
from contextlib import closing
from urllib.parse import parse_qs

from . import canal, colaboradores as col, db, ideas
from .investigacion import NoValido


def _q(query: str) -> dict:
    return {k: v[0] for k, v in parse_qs(query).items()}


def _desgloses(con, dias: int = 28) -> dict:
    """Vistas nuevas en los últimos N días por plataforma y por formato (suma de incrementos, nunca de acumulados)."""
    from datetime import timedelta
    from radar.diario import hoy
    corte = (hoy() - timedelta(days=dias - 1)).isoformat()
    por_pl, por_fmt = {}, {}
    for x in canal.incrementos(con):
        if x["fecha"] < corte:
            continue
        por_pl[x["plataforma"]] = por_pl.get(x["plataforma"], 0) + x["valor"]
        f = ideas.VARIANTES.get(x["variante"] or "", ("", x["formato"] or "(sin formato)"))[1] or "(sin formato)"
        por_fmt[f] = por_fmt.get(f, 0) + x["valor"]
    return {"dias": dias, "plataforma": por_pl, "formato": por_fmt}


def get(path: str, query: str):
    q = _q(query)
    con = db.connect()
    if path == "/api/canal/videos":
        return 200, {"videos": canal.mis_videos(con, q.get("plataforma", ""), q.get("campo", ""), q.get("valor", "")),
                     "plataformas": canal.PLATAFORMAS, "ventana": canal.VENTANA_48, "historial": canal.HISTORIAL_INDICE}
    if path == "/api/canal/mediciones":
        v = q.get("video", "")
        return 200, {"mediciones": canal.lista_mediciones(con, q.get("plataforma", ""), int(v) if v.isdigit() else None),
                     "metricas": {k: m[3] for k, m in canal.METRICAS.items()}, "plataformas": canal.PLATAFORMAS}
    if path == "/api/canal/estadisticas":
        return 200, {"diario": canal.diario(con, 90), "periodos": canal.periodos(con), "desgloses": _desgloses(con),
                     "plataformas": canal.PLATAFORMAS, "hay_datos": canal.serie_hoy(con, 1) is not None}
    if path == "/api/canal/serie":
        return 200, {"serie": canal.serie_hoy(con, 90)}
    if path == "/api/canal/rinde":
        try:
            dias = int(q["dias"]) if q.get("dias", "").isdigit() else None
            r = canal.rinde(con, q.get("agrupar", "formato"), q.get("plataforma", ""), dias, q.get("orden", "n"))
        except NoValido as e:
            return 400, {"error": str(e)}
        return 200, {**r, "agrupaciones": canal.AGRUPAR, "min_grupo": canal.MIN_GRUPO, "plataformas": canal.PLATAFORMAS}
    if path == "/api/colaboradores":
        with closing(ideas.radar_db()) as radar:
            r = col.creadores_radar(radar)
            demo = ideas.es_demo(radar)
        return 200, {**r, "guardados": col.lista(con), "por_creador": col.guardados_por_creador(con), "estados": col.ESTADOS, "demo": demo}
    return None


def post(path: str, body: dict):
    con = db.connect()
    try:
        if path == "/api/canal/videos":
            return 200, canal.crear_video(con, body.get("plataforma", ""), body.get("url", ""), body.get("titulo", ""),
                                          body.get("publicado_en", ""))
        m = re.fullmatch(r"/api/canal/videos/(\d+)", path)
        if m:
            return 200, canal.editar_video(con, int(m.group(1)), **{k: body.get(k) for k in
                                                                    ("titulo", "serie", "colaboracion", "temas", "publicado_en", "duracion_s")})
        if path == "/api/canal/mediciones":
            vid = body.get("video_id")
            if not vid and body.get("url") is not None:  # vídeo nuevo desde el formulario rápido
                err = {**canal.validar_video(body.get("plataforma", ""), body.get("url", ""), body.get("publicado_en", ""))[1],
                       **canal.validar_metricas(body)[1]}  # todos los errores a la vez, sin crear nada
                if err:
                    raise canal.Errores(err)
                vid = canal.crear_video(con, body.get("plataforma", ""), body.get("url", ""), body.get("titulo", ""),
                                        body.get("publicado_en", ""))["id"]
            return 200, canal.medir(con, int(vid or 0), body.get("medido_en", ""), body, body.get("nota", ""),
                                    bool(body.get("confirmar")), int(body["id"]) if body.get("id") else None)
        m = re.fullmatch(r"/api/canal/mediciones/(\d+)/borrar", path)
        if m:
            return 200, canal.borrar_medicion(con, int(m.group(1)))
        if path == "/api/colaboradores":
            if body.get("creador_radar"):
                with closing(ideas.radar_db()) as radar:
                    return 200, col.guardar(con, str(body["creador_radar"])[:120], radar, nota=body.get("nota", ""))
            return 200, col.guardar(con, None, None, body.get("nombre", ""), body.get("plataforma", "youtube"),
                                    body.get("url", ""), body.get("nota", ""))
        m = re.fullmatch(r"/api/colaboradores/(\d+)(/borrar)?", path)
        if m:
            if m.group(2):
                return 200, col.borrar(con, int(m.group(1)))
            return 200, col.actualizar(con, int(m.group(1)), body.get("estado"), body.get("nota"))
        return None
    except canal.Errores as e:
        return 409, {"error": str(e), "errores": e.errores, "confirmar": e.confirmar}
    except NoValido as e:
        return 409, {"error": str(e)}
    except (TypeError, ValueError) as e:
        return 400, {"error": f"Datos no válidos ({e.__class__.__name__})."}

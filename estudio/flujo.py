"""Reglas del corte 1 (megaprompt §7, §11 y §14). El servidor y las pruebas usan estas mismas funciones.

Brief → (aprobar idea) → Guion (archivo JSON) → (aprobar guion) → Crear vídeo → Revisión → (aprobar vídeo) → Exportar

- Aprobar guarda el hash del guion. Si el guion cambia, las aprobaciones de guion y vídeo dejan de valer.
- Crear vídeo no duplica: si ya hay una versión con ese guion en cola, fabricándose o lista, devuelve esa.
- Exportar solo exporta la versión con el vídeo aprobado.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fabrica.exportar import ExportacionFallida, verificar
from fabrica import voz_propia
from fabrica.guion import GuionNoValido, hash_guion, validar
from radar.db import iso

from . import db, rutas
from .ideas import PLATAFORMAS, VARIANTES, slug

MAX_INTENTOS = 3


class Bloqueado(RuntimeError):
    """La acción no se puede hacer todavía; el mensaje dice qué falta."""


# ------------------------------------------------------------------ guion (archivo)
def ruta_guion(t: dict) -> Path:
    return rutas.guiones_dir() / t["creado_en"][:10] / f"{t['id']}.json"


def leer_guion(t: dict) -> dict:
    """{estado: falta|no_valido|valido, guion, hash, errores, avisos, ruta}"""
    ruta = ruta_guion(t)
    if not ruta.exists():
        return {"estado": "falta", "ruta": str(ruta), "errores": [], "avisos": []}
    try:
        g, avisos = validar(json.loads(ruta.read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        return {"estado": "no_valido", "ruta": str(ruta), "errores": [f"El archivo no es JSON válido: {e}"], "avisos": []}
    except GuionNoValido as e:
        return {"estado": "no_valido", "ruta": str(ruta), "errores": e.errores, "avisos": []}
    return {"estado": "valido", "ruta": str(ruta), "guion": g, "hash": hash_guion(g), "errores": [], "avisos": avisos}


# ------------------------------------------------------------------ estado calculado de una pieza
def estado(con, tid: str) -> dict:
    t = db.trabajo(con, tid)
    if not t:
        raise Bloqueado("No existe esa pieza")
    gi = leer_guion(t)
    ap = db.aprobaciones(con, tid)
    vs = db.versiones(con, tid)
    ult = vs[0] if vs else None
    h = gi.get("hash")
    idea_ok = "idea" in ap
    guion_ok = idea_ok and gi["estado"] == "valido" and ap.get("guion", {}).get("guion_hash") == h
    v_ap = next((v for v in vs if "video" in ap and v["n"] == ap["video"]["version_n"]), None)
    escenas = (gi.get("guion") or {}).get("escenas", [])
    clave, op = voz_propia.clave_render(con, t, h, escenas) if h else (None, voz_propia.opciones(t))
    tomas = voz_propia.estado(con, tid, escenas) if op["voz"] == "propia" and escenas else []
    faltan_tomas = [x["escena"] + 1 for x in tomas if not x["valida"]]
    video_ok = guion_ok and v_ap is not None and v_ap.get("clave") == clave and ap["video"]["guion_hash"] == h
    legado = bool(ult and ult.get("legado"))

    export = {}
    if v_ap:
        for pl, e in db.exportaciones(con, v_ap["id"]).items():
            ok, motivo = verificar(e.get("manifiesto_ruta"))
            export[pl] = {"ruta": e["ruta"], "disponible": ok and bool(e.get("verificada_en")), "motivo": motivo,
                          "subida_en": e.get("subida_en"), "url": e.get("url")}
    if legado:
        for pl, e in db.exportaciones(con, ult["id"]).items():
            export[pl] = {"ruta": e["ruta"], "disponible": Path(e["ruta"] or "").exists(), "motivo": "exportado antes del flujo",
                          "subida_en": e.get("subida_en"), "url": e.get("url")}

    # etapa actual y siguiente paso (megaprompt §6: dónde estás, qué falta, qué pasará al continuar)
    if t.get("estado_editorial") == "descartada":
        etapa, falta = "Descartada", t.get("motivo_descarte") or ""
    elif legado and not idea_ok:
        etapa, falta = "Exportación", "Hecha antes del flujo de aprobación: ya está en la carpeta del Mac (sin manifiesto)."
    elif not idea_ok:
        etapa, falta = "Brief", "Aprueba la idea para pedir el guion."
    elif gi["estado"] == "falta":
        etapa, falta = "Guion", f"Pide el guion a Claude: «Escribe el guion del encargo {tid}» (o /guiones-del-dia)."
    elif gi["estado"] == "no_valido":
        etapa, falta = "Guion", "El guion tiene errores; pide a Claude que los corrija."
    elif not guion_ok:
        etapa = "Guion"
        falta = ("El guion cambió desde que lo aprobaste: revísalo y vuelve a aprobarlo."
                 if "guion" in ap else "Revisa el guion y apruébalo para poder crear el vídeo.")
    elif (not ult or ult.get("clave") != clave or ult.get("legado")) and faltan_tomas:
        etapa = "Montaje"
        falta = ("Graba tu voz: faltan las escenas " + ", ".join(map(str, faltan_tomas)) +
                 " (o cambia la voz a Leo y Sofi).")
    elif not ult or ult.get("clave") != clave or ult.get("legado"):
        etapa, falta = "Montaje", "Pulsa «Crear vídeo»: se fabrica con el guion aprobado, el fondo y la voz elegidos."
    elif ult["estado_produccion"] in ("pendiente", "en_curso"):
        etapa, falta = "Montaje", f"Fabricando: {ult['etapa']}."
    elif ult["estado_produccion"] == "fallido":
        etapa, falta = "Montaje", ult["error"] or "Falló el montaje. Puedes reintentar."
    elif not video_ok:
        etapa, falta = "Revisión", "Mira el vídeo y apruébalo o pide cambios."
    elif not all(export.get(pl, {}).get("disponible") for pl in t["plataformas"]):
        etapa, falta = "Exportación", "Pulsa «Exportar» para dejar los archivos en la carpeta del Mac."
    elif all(export.get(pl, {}).get("subida_en") for pl in t["plataformas"]):
        etapa, falta = "Publicado", "Hecho. Registra los resultados a las 48 h (corte 6)."
    else:
        etapa, falta = "Exportación", "Disponible en el Mac. Súbelo y márcalo como subido con su URL."

    variante = t.get("variante") or t["formato"]
    return {
        "id": tid, "idea": t["idea"], "variante": variante,
        "formato": t["formato"] if t["formato"] in ("A", "B", "C") else VARIANTES.get(variante, ("?", ""))[0],
        "variante_nombre": VARIANTES.get(t.get("variante") or t["formato"], ("", ""))[1],
        "plataformas": t["plataformas"], "creado_en": t["creado_en"], "estado_editorial": t.get("estado_editorial"),
        "etapa": etapa, "siguiente": falta, "legado": legado,
        "aprobado": {"idea": idea_ok, "guion": guion_ok, "video": video_ok},
        "guion": {k: gi.get(k) for k in ("estado", "ruta", "errores", "avisos", "hash")},
        "version": ({k: ult[k] for k in ("id", "n", "estado_produccion", "etapa", "error", "intentos", "duracion",
                                         "calidad", "guion_hash", "clave", "opciones")}
                    | {"video": bool(ult.get("video_ruta"))}) if ult else None,
        "opciones": op, "tomas": tomas, "clave": clave,
        "exportacion": export,
        "cambios": [dict(r) for r in con.execute("SELECT nota, version_n, creada_en FROM cambios WHERE trabajo_id=? "
                                                  "ORDER BY creada_en DESC LIMIT 5", (tid,))],
    }


# ------------------------------------------------------------------ acciones
def enviar_al_estudio(con, idea: dict, variante: str, plataformas: list[str]) -> dict:
    if variante not in VARIANTES:
        raise Bloqueado("Formato desconocido")
    plataformas = [p for p in plataformas if p in PLATAFORMAS]
    if not plataformas:
        raise Bloqueado("Marca al menos una plataforma")
    activo = db.trabajo_activo_de_idea(con, idea["id"])
    if activo:  # no se duplica en silencio: se devuelve la pieza que ya existe
        return activo
    return db.crear_trabajo(con, idea, variante, VARIANTES[variante][0], plataformas)


def idea_a_mano(titulo: str, por_que: str) -> dict:
    titulo = (titulo or "").strip()[:120]
    if len(titulo) < 6:
        raise Bloqueado("Escribe un título de al menos 6 letras")
    return {"id": f"mano-{datetime.now():%Y%m%d%H%M}-{slug(titulo, 30)}", "titulo": titulo,
            "por_que": (por_que or "").strip()[:300] or "Idea de Javier", "fuentes": [], "origen": "a mano"}


def aprobar(con, tid: str, tipo: str) -> dict:
    st = estado(con, tid)
    t = db.trabajo(con, tid)
    if tipo == "idea":
        db.aprobar(con, tid, "idea", None, None)
    elif tipo == "guion":
        if not st["aprobado"]["idea"]:
            raise Bloqueado("Primero aprueba la idea.")
        gi = leer_guion(t)
        if gi["estado"] != "valido":
            raise Bloqueado("No hay un guion válido que aprobar." + (" " + "; ".join(gi["errores"]) if gi["errores"] else ""))
        db.aprobar(con, tid, "guion", None, gi["hash"])
    elif tipo == "video":
        v = db.ultima_version(con, tid)
        if not st["aprobado"]["guion"]:
            raise Bloqueado("El guion no está aprobado (o cambió): apruébalo antes que el vídeo.")
        if not v or v["estado_produccion"] != "listo" or v.get("clave") != st["clave"]:
            raise Bloqueado("No hay un vídeo terminado con el guion actual.")
        db.aprobar(con, tid, "video", v["n"], v["guion_hash"])
    else:
        raise Bloqueado("Tipo de aprobación desconocido")
    return estado(con, tid)


def pedir_cambios(con, tid: str, nota: str) -> dict:
    nota = (nota or "").strip()
    if not nota:
        raise Bloqueado("Escribe qué hay que cambiar.")
    v = db.ultima_version(con, tid)
    db.quitar_aprobacion(con, tid, "video")
    con.execute("INSERT INTO cambios(trabajo_id,version_n,nota,creada_en) VALUES(?,?,?,?)",
                (tid, v["n"] if v else None, nota[:1000], iso()))
    con.commit()
    return estado(con, tid)


def crear_video(con, tid: str) -> dict:
    st = estado(con, tid)
    if not (st["aprobado"]["idea"] and st["aprobado"]["guion"]):
        raise Bloqueado("Para crear el vídeo hacen falta la idea y el guion aprobados.")
    h, clave = st["guion"]["hash"], st["clave"]
    t = db.trabajo(con, tid)
    g = leer_guion(t)["guion"]
    if st["opciones"]["voz"] == "propia":
        try:
            voz_propia.rutas_validas(con, tid, g["escenas"])
        except voz_propia.TomaNoValida as e:
            raise Bloqueado(f"{e} O cambia la voz a «Leo y Sofi».") from e
    for v in db.versiones(con, tid):
        if v.get("clave") == clave and v["estado_produccion"] in ("pendiente", "en_curso", "listo"):
            return v  # idempotente: ya existe
        if v.get("clave") == clave and v["estado_produccion"] == "fallido":
            return reintentar(con, tid)
    return db.nueva_version(con, tid, g, h, clave, st["opciones"])


def reintentar(con, tid: str) -> dict:
    v = db.ultima_version(con, tid)
    if not v or v["estado_produccion"] != "fallido":
        raise Bloqueado("No hay nada que reintentar.")
    if (v["intentos"] or 0) >= MAX_INTENTOS:
        raise Bloqueado(f"Ya se reintentó {MAX_INTENTOS} veces. Revisa el error o pide un guion corregido.")
    db.actualizar_version(con, v["id"], estado_produccion="pendiente", etapa="En cola (reintento)", error=None)
    return db.version(con, v["id"])


def cancelar(con, tid: str) -> dict:
    v = db.ultima_version(con, tid)
    if not v or v["estado_produccion"] != "pendiente":
        raise Bloqueado("Solo se puede cancelar un vídeo que está en cola (no uno que ya se está fabricando).")
    db.actualizar_version(con, v["id"], estado_produccion="fallido", etapa="Cancelado",
                          error="Cancelado por ti. Puedes volver a crearlo cuando quieras.")
    return db.version(con, v["id"])


def exportar(con, tid: str) -> dict:
    from fabrica import exportar as exp

    st = estado(con, tid)
    if not st["aprobado"]["video"]:
        raise Bloqueado("Solo se exporta la versión con el vídeo aprobado. Apruébalo primero.")
    try:
        return exp.exportar(con, tid)
    except ExportacionFallida as e:
        raise Bloqueado(str(e)) from e


def marcar_subido(con, tid: str, plataforma: str, url: str) -> dict:
    from fabrica import exportar as exp

    if not str(url).startswith(("https://", "http://")):
        raise Bloqueado("Pega la URL pública del vídeo (empieza por https://).")
    st = estado(con, tid)
    if not st["exportacion"].get(plataforma, {}).get("disponible"):
        raise Bloqueado("Primero exporta esa plataforma.")
    try:
        exp.marcar_subido(con, tid, plataforma, url[:300])
    except ExportacionFallida as e:
        raise Bloqueado(str(e)) from e
    t = db.trabajo(con, tid)
    if all(st["exportacion"].get(p, {}).get("subida_en") or p == plataforma for p in t["plataformas"]):
        con.execute("UPDATE trabajos SET estado_publicacion='publicado' WHERE id=?", (tid,))
        con.commit()
    return estado(con, tid)


def descartar_pieza(con, tid: str, motivo: str) -> dict:
    motivo = (motivo or "").strip()
    if not motivo:
        raise Bloqueado("Di por qué la descartas: el motivo sirve para aprender.")
    con.execute("UPDATE trabajos SET estado_editorial='descartada', motivo_descarte=? WHERE id=?", (motivo[:300], tid))
    con.commit()
    return estado(con, tid)


def poner_opciones(con, tid: str, fondo: str | None, voz: str | None) -> dict:
    try:
        voz_propia.poner_opciones(con, tid, fondo, voz)
    except voz_propia.TomaNoValida as e:
        raise Bloqueado(str(e)) from e
    return estado(con, tid)


def guardar_toma(con, tid: str, n: int, datos: bytes, mime: str) -> dict:
    t = db.trabajo(con, tid)
    gi = leer_guion(t)
    if gi["estado"] != "valido":
        raise Bloqueado("Primero tiene que haber un guion válido.")
    try:
        voz_propia.guardar(con, t, gi["guion"]["escenas"], n, datos, mime)
    except voz_propia.TomaNoValida as e:
        raise Bloqueado(str(e)) from e
    return estado(con, tid)

"""Dossier de una investigación (fase 2A) y paso a la Fábrica.

- Lo genera el código a partir de lo que hay en la investigación: sin IA y sin inventar nada.
- «Guardar versión» lo congela (tabla dossiers): la pieza que salga de él sabe exactamente con qué datos se hizo.
- Las incertidumbres (pendientes, sin evidencia, no verificables y contradichas) van en su propia sección.
- Crear la idea NO aprueba ni publica nada: la pieza entra en el Estudio en la etapa Idea, como siempre.

Trazabilidad: Fuente → Afirmación → Investigación → Dossier (vN) → Idea → Guion → Pieza.
"""
from __future__ import annotations

from radar.db import iso, jdump, jload

from . import flujo
from . import verificacion as ver
from .ideas import PLATAFORMAS, VARIANTES
from .investigacion import ESTADOS_NOMBRE, NoValido, inv

GRUPOS = [("confirmadas", ("confirmado",), "Confirmado por fuente primaria"),
          ("atribuidas", ("atribuida",), "Información atribuida (REPORTADO)"),
          ("incertidumbres", ("pendiente", "sin_evidencia", "no_verificable"), "Incertidumbres (RUMOR: la voz lo dice)"),
          ("contradichas", ("contradicho",), "Contradichas: no se afirman (solo en «Verdad o bulo»)")]


def generar(con, iid: str) -> dict:
    i = inv(con, iid, completa=True)
    if not i:
        raise NoValido("Esa investigación no existe.")
    afs = ver.lista_afirm(con, inv_id=iid)
    corta = lambda a: {"id": a["id"], "texto": a["texto"], "estado": a["estado"], "estado_nombre": a["estado_nombre"],  # noqa: E731
                       "etiqueta": a["etiqueta"], "quien_primero": a["quien_primero"], "fecha_origen": a["fecha_origen"],
                       "nota": a["nota"], "revisada_en": a["revisada_en"], "cuentas": a["cuentas"],
                       "evidencias": [{k: e[k] for k in ("titulo", "url", "fuente", "publicado_en", "relacion", "independiente", "nota")}
                                      for e in a["evidencias"]]}
    grupos = {k: [corta(a) for a in afs if a["estado"] in estados] for k, estados, _ in GRUPOS}
    avisos = []
    if not i["fuentes"]:
        avisos.append("La investigación no tiene fuentes.")
    if not afs:
        avisos.append("No hay afirmaciones: el guion no tendrá datos verificados que citar.")
    if grupos["incertidumbres"]:
        avisos.append(f"{len(grupos['incertidumbres'])} afirmación(es) sin confirmar: si salen en el guion, van como RUMOR.")
    if any(a["revision_antigua"] for a in afs):
        avisos.append(f"Hay afirmaciones sin revisar desde hace más de {ver.DIAS_REVISION} días.")
    return {
        "investigacion": {k: i[k] for k in ("id", "titulo", "pregunta", "descripcion", "que_se", "que_falta", "conclusion", "estado")},
        "estado_nombre": ESTADOS_NOMBRE.get(i["estado"], i["estado"]),
        "afirmaciones": grupos,
        "fuentes": [{k: f[k] for k in ("id", "tipo", "titulo", "url", "fuente", "publicado_en", "consultada_en", "aporte")}
                    for f in i["fuentes"]],
        "cronologia": [{k: e[k] for k in ("tipo_nombre", "titulo", "ocurrio_en", "publicado_en", "detectado_en", "fecha_usada")}
                       for e in ver.cronologia(con, inv_id=iid)],
        "avisos": avisos,
        "generado_en": iso(),
    }


def _f(v) -> str:
    return (v or "")[:10] or "fecha desconocida"


def markdown(d: dict) -> str:
    i = d["investigacion"]
    L = [f"# Dossier: {i['titulo']}", "", f"_Generado {d['generado_en'][:16].replace('T', ' ')} · estado: {d['estado_nombre']}_", ""]
    if d["avisos"]:
        L += ["> **Avisos**"] + [f"> - {a}" for a in d["avisos"]] + [""]
    for k, t in (("pregunta", "Pregunta"), ("que_se", "Qué sé"), ("que_falta", "Qué falta por comprobar"),
                 ("conclusion", "Conclusión provisional")):
        if i.get(k):
            L += [f"## {t}", i[k], ""]
    for k, _, titulo in GRUPOS:
        afs = d["afirmaciones"][k]
        if not afs:
            continue
        L += [f"## {titulo}"]
        for a in afs:
            c = a["cuentas"]
            L.append(f"- **[{a['etiqueta']}]** {a['texto']} — {a['estado_nombre']}"
                     f" · {c['independientes']} independiente(s), {c['repite']} que solo repiten, {c['en_contra']} en contra"
                     + (f" · origen: {a['quien_primero']} ({_f(a['fecha_origen'])})" if a["quien_primero"] else ""))
            for e in a["evidencias"]:
                rel = ver.RELACIONES.get(e["relacion"], e["relacion"]) + (" · independiente" if e["independiente"] else "")
                L.append(f"  - {rel}: [{e['titulo']}]({e['url']}) — {e['fuente'] or '—'}, {_f(e['publicado_en'])}")
            if a["nota"]:
                L.append(f"  - Nota: {a['nota']}")
        L.append("")
    if d["fuentes"]:
        L += ["## Fuentes"]
        for f in d["fuentes"]:
            L.append(f"- [{f['titulo']}]({f['url']}) — {f['fuente'] or '—'} · publicado {_f(f['publicado_en'])}"
                     f" · consultado {_f(f['consultada_en'])}" + (f" · aporta: {f['aporte']}" if f["aporte"] else ""))
        L.append("")
    if d["cronologia"]:
        L += ["## Cronología"]
        for e in reversed(d["cronologia"]):
            fecha = e["ocurrio_en"] or e["publicado_en"] or e["detectado_en"]
            L.append(f"- {_f(fecha)} ({e['fecha_usada']}) · {e['tipo_nombre']}: {e['titulo']}")
        L.append("")
    return "\n".join(L)


def guardar(con, iid: str) -> dict:
    d = generar(con, iid)
    n = (con.execute("SELECT MAX(n) FROM dossiers WHERE inv_id=?", (iid,)).fetchone()[0] or 0) + 1
    cur = con.execute("INSERT INTO dossiers(inv_id,n,contenido,markdown,creado_en) VALUES(?,?,?,?,?)",
                      (iid, n, jdump(d), markdown(d), iso()))
    con.commit()
    return obtener(con, cur.lastrowid)


def _piezas(con, did: int) -> list[dict]:
    return [dict(r) for r in con.execute(
        """SELECT id, formato, variante, creado_en, estado_editorial, json_extract(idea,'$.titulo') titulo FROM trabajos
           WHERE json_extract(idea,'$.dossier_id')=? ORDER BY creado_en DESC""", (did,))]


def obtener(con, did: int) -> dict | None:
    r = con.execute("SELECT d.*, i.titulo inv_titulo FROM dossiers d JOIN investigaciones i ON i.id=d.inv_id WHERE d.id=?",
                    (did,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["contenido"] = jload(d["contenido"], {})
    d["piezas"] = _piezas(con, did)
    return d


def lista(con, iid: str = "") -> list[dict]:
    q = "SELECT d.id, d.inv_id, d.n, d.creado_en, i.titulo inv_titulo FROM dossiers d JOIN investigaciones i ON i.id=d.inv_id"
    rows = con.execute(q + (" WHERE d.inv_id=?" if iid else "") + " ORDER BY d.creado_en DESC LIMIT 200", (iid,) if iid else ())
    return [{**dict(r), "piezas": _piezas(con, r["id"])} for r in rows]


def idea_desde(dos: dict, variante: str) -> dict:
    """La idea que recibe la Fábrica: lleva el dossier congelado para que el guion use esos datos y sus etiquetas."""
    c = dos["contenido"]
    i = c["investigacion"]
    usables = c["afirmaciones"]["confirmadas"] + c["afirmaciones"]["atribuidas"] + c["afirmaciones"]["incertidumbres"]
    if variante == "verdad_bulo":
        usables += c["afirmaciones"]["contradichas"]
    return {
        "id": f"dossier-{dos['id']}", "titulo": i["titulo"][:120],
        "por_que": (i.get("conclusion") or i.get("pregunta") or "Investigación propia")[:300],
        "origen": f"investigación {i['id']} · dossier v{dos['n']}",
        "investigacion_id": i["id"], "dossier_id": dos["id"], "dossier_n": dos["n"],
        "fuentes": [{"titulo": f["titulo"], "url": f["url"]} for f in c["fuentes"] if f.get("url")],
        "afirmaciones": [{"texto": a["texto"], "etiqueta": a["etiqueta"], "estado": a["estado_nombre"],
                          "fuentes": [e["url"] for e in a["evidencias"] if e["relacion"] != "en_contra" and e.get("url")]}
                         for a in usables],
        "no_afirmar": [] if variante == "verdad_bulo" else [a["texto"] for a in c["afirmaciones"]["contradichas"]],
        "avisos": c["avisos"],
    }


def crear_idea(con, did: int, variante: str, plataformas: list[str]) -> dict:
    dos = obtener(con, did)
    if not dos:
        raise NoValido("Ese dossier no existe.")
    if variante not in VARIANTES:
        raise NoValido("Elige un formato.")
    plataformas = [p for p in (plataformas or []) if p in PLATAFORMAS]
    if not plataformas:
        raise NoValido("Marca al menos una plataforma.")
    try:
        return flujo.enviar_al_estudio(con, idea_desde(dos, variante), variante, plataformas)
    except flujo.Bloqueado as e:
        raise NoValido(str(e)) from e

"""Mi canal (fase 2B): tus vídeos publicados, sus mediciones y los cálculos. Privado (data/estudio.db).

FÓRMULAS (todas documentadas aquí; la pantalla las repite):
- Una MEDICIÓN es la foto de un vídeo en un momento: valores ACUMULADOS desde la publicación. Campo vacío = no lo
  sabes (None); 0 = cero de verdad. Nunca se suman dos mediciones acumuladas del mismo vídeo.
- VISTAS DEL DÍA = vistas de una medición − vistas de la medición anterior del mismo vídeo, y se asignan al día
  (zona del panel, Europe/Madrid) de la medición posterior. Si entre ambas pasan varios días, todo va a ese día y se
  marca «acumula N días» (no se reparte). La primera medición cuenta «desde la publicación». Un día sin mediciones
  no tiene dato (None), no cero.
- VISTAS A 48 H = la medición más cercana a 48 h desde la publicación, solo si está entre 40 y 56 h. No se interpola.
- ÍNDICE A 48 H = vistas a 48 h ÷ mediana de las vistas a 48 h de las 20 piezas ANTERIORES de la misma plataforma.
  Con menos de 20: «historial insuficiente (N/20)» y solo métricas directas.
- RETENCIÓN: dos campos por vídeo (tiempo medio visto en segundos y % que lo ve entero). En un grupo solo se da la
  mediana del % entero si todas las duraciones conocidas están a ±25 % de la mediana de duración; si no, «no comparable».
  Nunca se promedia el tiempo medio visto entre vídeos distintos.
- INGRESOS Y COSTES: no hay registro, así que no se muestran (nunca «0 €»).
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from radar.db import iso, jdump, jload, parse_iso
from radar.diario import dia_local, hoy, zona

from .investigacion import NoValido

PLATAFORMAS = {"tiktok": "TikTok", "shorts": "YouTube Shorts", "youtube": "YouTube largo"}
# campo: (tipo, mínimo, máximo, unidad que se ve en el formulario)
METRICAS = {
    "vistas": (int, 0, None, "visualizaciones acumuladas desde la publicación"),
    "tiempo_medio_s": (float, 0, 36000, "segundos de media que ve cada espectador"),
    "pct_completo": (float, 0, 100, "% de espectadores que lo ven entero"),
    "compartidos": (int, 0, None, "acumulado desde la publicación"),
    "seguidores_ganados": (int, 0, None, "acumulado desde la publicación"),
    "likes": (int, 0, None, "acumulado desde la publicación"),
    "comentarios": (int, 0, None, "acumulado desde la publicación"),
}
ACUMULADAS = ("vistas", "compartidos", "seguidores_ganados", "likes", "comentarios")
VENTANA_48 = (40, 56)
HISTORIAL_INDICE = 20
MIN_GRUPO = 5
TOLERANCIA_DURACION = 0.25


class Errores(NoValido):
    """Errores por campo: la interfaz los pinta junto a cada campo."""
    def __init__(self, errores: dict, confirmar: bool = False):
        super().__init__("; ".join(errores.values()))
        self.errores, self.confirmar = errores, confirmar


def _momento(v, campo: str, errores: dict, obligatorio: bool = True) -> str | None:
    """Fecha y hora → UTC al minuto. «AAAA-MM-DDTHH:MM» sin zona se entiende en la hora de Madrid (la de tu Mac)."""
    v = str(v or "").strip()
    if not v:
        if obligatorio:
            errores[campo] = "Falta la fecha y hora."
        return None
    if len(v) == 10:
        v += "T00:00"
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        errores[campo] = "Fecha no válida (AAAA-MM-DD HH:MM)."
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zona())
    dt = dt.astimezone(timezone.utc).replace(second=0, microsecond=0)
    if dt > datetime.now(timezone.utc) + timedelta(minutes=5):
        errores[campo] = "Está en el futuro."
        return None
    return iso(dt)


def validar_metricas(body: dict) -> tuple[dict, dict]:
    """Devuelve (valores, errores). Vacío → None (no lo sabes); «0» → 0 (cero de verdad)."""
    vals, err = {}, {}
    for k, (tipo, lo, hi, _) in METRICAS.items():
        raw = body.get(k)
        if raw is None or str(raw).strip() == "":
            vals[k] = None
            continue
        s = str(raw).strip().replace(" ", "").replace(" ", "")
        if tipo is int:
            s = s.replace(".", "").replace(",", "")  # 12.345 o 12,345 → 12345
        else:
            s = s.replace(",", ".")
        try:
            x = tipo(float(s)) if tipo is int and s.replace("-", "").isdigit() else tipo(s)
        except ValueError:
            err[k] = "Escribe solo el número."
            continue
        if x < lo or (hi is not None and x > hi):
            err[k] = f"Debe estar entre {lo} y {hi}." if hi is not None else f"No puede ser menor que {lo}."
            continue
        vals[k] = x
    return vals, err


# ------------------------------------------------------------------ vídeos
def _video(con, vid: int) -> dict | None:
    r = con.execute("SELECT * FROM mis_videos WHERE id=?", (vid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["temas"] = jload(d.get("temas"), [])
    return d


def validar_video(plataforma: str, url: str, publicado_en: str) -> tuple[tuple, dict]:
    err = {}
    if plataforma not in PLATAFORMAS:
        err["plataforma"] = "Elige TikTok, YouTube Shorts o YouTube largo."
    url = str(url or "").strip()[:300]
    if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
        err["url"] = "Pega la URL pública del vídeo (empieza por https://)."
    pub = _momento(publicado_en, "publicado_en", err)
    return (url, pub), err


def crear_video(con, plataforma: str, url: str, titulo: str = "", publicado_en: str = "", origen: str = "manual",
                **extra) -> dict:
    (url, pub), err = validar_video(plataforma, url, publicado_en)
    if err:
        raise Errores(err)
    ya = con.execute("SELECT id FROM mis_videos WHERE plataforma=? AND url=?", (plataforma, url)).fetchone()
    if ya:
        return _video(con, ya["id"])
    cur = con.execute("""INSERT INTO mis_videos(plataforma,url,titulo,publicado_en,pieza_id,formato,variante,temas,serie,
                         colaboracion,duracion_s,origen,creado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (plataforma, url, str(titulo or "")[:200] or url, pub, extra.get("pieza_id"), extra.get("formato"),
                       extra.get("variante"), jdump(extra.get("temas") or []), extra.get("serie"), extra.get("colaboracion"),
                       extra.get("duracion_s"), origen, iso()))
    con.commit()
    return _video(con, cur.lastrowid)


def video_desde_pieza(con, tid: str, plataforma: str, url: str) -> dict:
    """Al marcar una pieza como subida: el vídeo queda en Mis vídeos con formato, variante, temas y duración.
    La fecha de publicación es el momento en que la marcas (puedes corregirla)."""
    from . import db
    t = db.trabajo(con, tid)
    v = con.execute("SELECT duracion FROM versiones WHERE trabajo_id=? AND duracion IS NOT NULL ORDER BY n DESC LIMIT 1",
                    (tid,)).fetchone()
    idea = t["idea"] if t else {}
    temas = idea.get("temas") or ([idea["tema"]] if idea.get("tema") else [])
    return crear_video(con, plataforma, url, idea.get("titulo", ""), iso(), origen="fabrica", pieza_id=tid,
                       formato=t.get("formato") if t else None, variante=t.get("variante") if t else None,
                       temas=temas, duracion_s=v["duracion"] if v else None)


def editar_video(con, vid: int, **campos) -> dict:
    v = _video(con, vid)
    if not v:
        raise NoValido("Ese vídeo no existe.")
    cambios, err = {}, {}
    for k in ("titulo", "serie", "colaboracion"):
        if campos.get(k) is not None:
            cambios[k] = str(campos[k]).strip()[:120] or None
    if campos.get("temas") is not None:
        t = campos["temas"]
        t = t.split(",") if isinstance(t, str) else t
        cambios["temas"] = jdump(sorted({str(x).strip().lower()[:40] for x in t if str(x).strip()})[:10])
    if campos.get("publicado_en") is not None:
        cambios["publicado_en"] = _momento(campos["publicado_en"], "publicado_en", err)
    if campos.get("duracion_s") is not None:
        d = str(campos["duracion_s"]).strip().replace(",", ".")
        try:
            cambios["duracion_s"] = float(d) if d else None
            if cambios["duracion_s"] is not None and not 1 <= cambios["duracion_s"] <= 36000:
                err["duracion_s"] = "Duración en segundos (1 a 36000)."
        except ValueError:
            err["duracion_s"] = "Escribe los segundos."
    if err:
        raise Errores(err)
    if cambios:
        con.execute(f"UPDATE mis_videos SET {', '.join(k + '=?' for k in cambios)} WHERE id=?", (*cambios.values(), vid))
        con.commit()
    return _video(con, vid)


# ------------------------------------------------------------------ mediciones
def _medicion(con, mid: int) -> dict | None:
    r = con.execute("SELECT * FROM mediciones WHERE id=?", (mid,)).fetchone()
    return dict(r) if r else None


def _log(con, accion: str, mid, vid, antes, despues) -> None:
    con.execute("INSERT INTO medicion_log(medicion_id,video_id,accion,antes,despues,cuando) VALUES(?,?,?,?,?,?)",
                (mid, vid, accion, jdump(antes) if antes else None, jdump(despues) if despues else None, iso()))


def medir(con, video_id: int, medido_en: str, body: dict, nota: str = "", confirmar_bajada: bool = False,
          mid: int | None = None, origen: str = "manual") -> dict:
    """Alta (o corrección si mid) de una medición. Comprueba duplicados y bajadas de valores acumulados."""
    v = _video(con, int(video_id or 0))
    if not v:
        raise Errores({"video_id": "Elige el vídeo (o pega su URL)."})
    err = {}
    cuando = _momento(medido_en, "medido_en", err)
    vals, e2 = validar_metricas(body)
    err.update(e2)
    if cuando and v["publicado_en"] and cuando < v["publicado_en"]:
        err["medido_en"] = "Es anterior a la publicación del vídeo."
    if not err and all(x is None for x in vals.values()):
        err["vistas"] = "Rellena al menos una métrica."
    if err:
        raise Errores(err)
    dup = con.execute("SELECT id FROM mediciones WHERE video_id=? AND medido_en=? AND id!=?", (v["id"], cuando, mid or 0)).fetchone()
    if dup:
        raise Errores({"medido_en": "Ya hay una medición de este vídeo a esa hora: corrígela en la tabla."})
    if not confirmar_bajada:  # un acumulado no baja: si baja, probablemente es un error de tecleo
        prev = con.execute("""SELECT * FROM mediciones WHERE video_id=? AND medido_en<? AND id!=? ORDER BY medido_en DESC LIMIT 1""",
                           (v["id"], cuando, mid or 0)).fetchone()
        sig = con.execute("""SELECT * FROM mediciones WHERE video_id=? AND medido_en>? AND id!=? ORDER BY medido_en LIMIT 1""",
                          (v["id"], cuando, mid or 0)).fetchone()
        bajadas = {k: f"Es menor que la medición anterior ({prev[k]:,}). Los valores son acumulados: ¿seguro?".replace(",", ".")
                   for k in ACUMULADAS if prev and vals[k] is not None and prev[k] is not None and vals[k] < prev[k]}
        bajadas |= {k: f"Es mayor que la medición siguiente ({sig[k]:,}). ¿Seguro?".replace(",", ".")
                    for k in ACUMULADAS if sig and vals[k] is not None and sig[k] is not None and vals[k] > sig[k]}
        if bajadas:
            raise Errores(bajadas, confirmar=True)
    ahora = iso()
    nota = str(nota or "").strip()[:500]
    if mid:
        antes = _medicion(con, mid)
        if not antes:
            raise NoValido("Esa medición no existe.")
        con.execute(f"""UPDATE mediciones SET video_id=?, medido_en=?, {', '.join(k + '=?' for k in METRICAS)}, nota=?, actualizado_en=?
                        WHERE id=?""", (v["id"], cuando, *vals.values(), nota, ahora, mid))
        _log(con, "corregida", mid, v["id"], antes, _medicion(con, mid))
    else:
        cur = con.execute(f"""INSERT INTO mediciones(video_id,medido_en,{','.join(METRICAS)},nota,origen,creado_en,actualizado_en)
                              VALUES(?,?,{','.join('?' * len(METRICAS))},?,?,?,?)""", (v["id"], cuando, *vals.values(), nota, origen, ahora, ahora))
        mid = cur.lastrowid
        _log(con, "alta", mid, v["id"], None, _medicion(con, mid))
    con.commit()
    return _medicion(con, mid)


def borrar_medicion(con, mid: int) -> dict:
    m = _medicion(con, mid)
    if not m:
        raise NoValido("Esa medición no existe.")
    _log(con, "borrada", mid, m["video_id"], m, None)
    con.execute("DELETE FROM mediciones WHERE id=?", (mid,))
    con.commit()
    return {"ok": True}


def lista_mediciones(con, plataforma: str = "", video_id: int | None = None) -> list[dict]:
    q = """SELECT m.*, v.titulo, v.plataforma, v.url FROM mediciones m JOIN mis_videos v ON v.id=m.video_id WHERE 1=1"""
    args: list = []
    if plataforma in PLATAFORMAS:
        q += " AND v.plataforma=?"
        args.append(plataforma)
    if video_id:
        q += " AND v.id=?"
        args.append(video_id)
    return [dict(r) for r in con.execute(q + " ORDER BY m.medido_en DESC LIMIT 1000", args)]


# ------------------------------------------------------------------ cálculos
def _horas(desde: str | None, hasta: str | None) -> float | None:
    a, b = parse_iso(desde), parse_iso(hasta)
    return (b - a).total_seconds() / 3600 if a and b else None


def incrementos(con, campo: str = "vistas") -> list[dict]:
    """Un incremento por medición con dato: lo nuevo desde la medición anterior (con dato) del mismo vídeo."""
    out = []
    videos = {r["id"]: dict(r) for r in con.execute("SELECT * FROM mis_videos")}
    previo: dict[int, dict] = {}
    for m in con.execute(f"SELECT id, video_id, medido_en, {campo} v FROM mediciones WHERE {campo} IS NOT NULL ORDER BY video_id, medido_en"):
        vid, dia = m["video_id"], dia_local(m["medido_en"])
        p = previo.get(vid)
        if p:
            n = (datetime.fromisoformat(dia) - datetime.fromisoformat(dia_local(p["medido_en"]))).days
            out.append({"video_id": vid, "fecha": dia, "valor": m["v"] - p["v"], "dias": max(1, n), "desde_publicacion": False})
        else:
            pub = videos[vid]["publicado_en"]
            n = (datetime.fromisoformat(dia) - datetime.fromisoformat(dia_local(pub))).days + 1 if pub else None
            out.append({"video_id": vid, "fecha": dia, "valor": m["v"], "dias": n, "desde_publicacion": True})
        previo[vid] = dict(m)
    for x in out:
        v = videos[x["video_id"]]
        x["plataforma"], x["formato"], x["variante"] = v["plataforma"], v["formato"], v["variante"]
    return out


def diario(con, dias: int = 90) -> list[dict]:
    """Vistas nuevas por día y plataforma. None = ese día no hubo medición de esa plataforma (no es cero)."""
    h = hoy()
    fechas = [(h - timedelta(days=i)).isoformat() for i in range(dias - 1, -1, -1)]
    filas = {f: {"fecha": f, **{p: None for p in PLATAFORMAS}, "notas": []} for f in fechas}
    for x in incrementos(con):
        f = filas.get(x["fecha"])
        if not f:
            continue
        f[x["plataforma"]] = (f[x["plataforma"]] or 0) + x["valor"]
        if x["desde_publicacion"]:
            f["notas"].append(f"{PLATAFORMAS[x['plataforma']]}: incluye vistas desde la publicación")
        elif x["dias"] > 1:
            f["notas"].append(f"{PLATAFORMAS[x['plataforma']]}: acumula {x['dias']} días")
    return list(filas.values())


def serie_hoy(con, dias: int = 90) -> list[dict] | None:
    """Mismo formato que la demo de la gráfica de Hoy (tiktok, shorts, largo). None si no hay ninguna medición."""
    if not con.execute("SELECT 1 FROM mediciones WHERE vistas IS NOT NULL LIMIT 1").fetchone():
        return None
    return [{"fecha": d["fecha"], "tiktok": d["tiktok"], "shorts": d["shorts"], "largo": d["youtube"], "notas": d["notas"]}
            for d in diario(con, dias)]


def periodos(con) -> list[dict]:
    """Últimos N días frente a los N anteriores, con cuántos días tienen datos en cada tramo."""
    d = diario(con, 56)
    out = []
    for n in (7, 28):
        act, ant = d[-n:], d[-2 * n:-n]

        def tramo(filas):
            con_datos = [f for f in filas if any(f[p] is not None for p in PLATAFORMAS)]
            return {"vistas": sum(f[p] or 0 for f in con_datos for p in PLATAFORMAS) if con_datos else None,
                    "dias_con_datos": len(con_datos), "dias": len(filas),
                    "por_plataforma": {p: (sum(f[p] for f in filas if f[p] is not None)
                                           if any(f[p] is not None for f in filas) else None) for p in PLATAFORMAS}}
        a, b = tramo(act), tramo(ant)
        aviso = None
        if a["vistas"] is None or b["vistas"] is None:
            aviso = "Falta uno de los dos tramos: no se puede comparar."
        elif a["dias_con_datos"] != b["dias_con_datos"]:
            aviso = f"Cobertura distinta ({a['dias_con_datos']}/{n} frente a {b['dias_con_datos']}/{n} días con datos): compáralo con cuidado."
        out.append({"dias": n, "actual": a, "anterior": b, "aviso": aviso,
                    "cambio_pct": round((a["vistas"] - b["vistas"]) / b["vistas"] * 100, 1)
                    if a["vistas"] is not None and b["vistas"] else None})
    return out


def _ultimos(con, vid: int) -> dict:
    """Último valor conocido de cada métrica (cada una con su fecha: pueden venir de mediciones distintas)."""
    out = {}
    for k in METRICAS:
        r = con.execute(f"SELECT {k} v, medido_en FROM mediciones WHERE video_id=? AND {k} IS NOT NULL ORDER BY medido_en DESC LIMIT 1",
                        (vid,)).fetchone()
        out[k] = {"valor": r["v"], "medido_en": r["medido_en"]} if r else None
    return out


def vistas_48(con, v: dict) -> dict:
    if not v["publicado_en"]:
        return {"estado": "sin_fecha", "texto": "Falta la fecha de publicación."}
    best = None
    for m in con.execute("SELECT vistas, medido_en FROM mediciones WHERE video_id=? AND vistas IS NOT NULL", (v["id"],)):
        h = _horas(v["publicado_en"], m["medido_en"])
        if h is not None and VENTANA_48[0] <= h <= VENTANA_48[1] and (best is None or abs(h - 48) < abs(best[1] - 48)):
            best = (m["vistas"], h)
    if best:
        return {"estado": "ok", "vistas": best[0], "horas": round(best[1], 1), "texto": f"medido a las {best[1]:.0f} h"}
    edad = _horas(v["publicado_en"], iso())
    if edad is not None and edad < VENTANA_48[1]:
        return {"estado": "pendiente", "texto": f"La ventana de 48 h ({VENTANA_48[0]}–{VENTANA_48[1]} h) aún no ha pasado: mide entre esas horas."}
    return {"estado": "sin_ventana", "texto": f"Sin medición entre las {VENTANA_48[0]} y las {VENTANA_48[1]} h (no se interpola)."}


def indice_48(con, v: dict, v48: dict | None = None) -> dict:
    v48 = v48 or vistas_48(con, v)
    if v48["estado"] != "ok":
        return {"estado": "sin_dato", "texto": "Sin vistas a 48 h."}
    previas = []
    for r in con.execute("""SELECT * FROM mis_videos WHERE plataforma=? AND publicado_en IS NOT NULL AND publicado_en<? AND id!=?
                            ORDER BY publicado_en DESC""", (v["plataforma"], v["publicado_en"], v["id"])):
        x = vistas_48(con, dict(r))
        if x["estado"] == "ok":
            previas.append(x["vistas"])
        if len(previas) == HISTORIAL_INDICE:
            break
    if len(previas) < HISTORIAL_INDICE:
        return {"estado": "historial_insuficiente", "n": len(previas),
                "texto": f"Historial insuficiente ({len(previas)}/{HISTORIAL_INDICE} piezas anteriores de {PLATAFORMAS[v['plataforma']]} con dato a 48 h)."}
    med = statistics.median(previas)
    if not med:
        return {"estado": "sin_dato", "texto": "La mediana de las piezas anteriores es 0: el índice no tiene sentido."}
    return {"estado": "ok", "valor": round(v48["vistas"] / med, 2), "mediana": med,
            "texto": f"{v48['vistas'] / med:.2f} × la mediana de tus 20 piezas anteriores ({med:,.0f} vistas a 48 h)".replace(",", ".")}


def ficha_video(con, v: dict) -> dict:
    v48 = vistas_48(con, v)
    n = con.execute("SELECT COUNT(*), MAX(medido_en) FROM mediciones WHERE video_id=?", (v["id"],)).fetchone()
    return {**v, "plataforma_nombre": PLATAFORMAS.get(v["plataforma"], v["plataforma"]), "ultimos": _ultimos(con, v["id"]),
            "v48": v48, "indice48": indice_48(con, v, v48), "n_mediciones": n[0], "ultima_medicion": n[1]}


def mis_videos(con, plataforma: str = "", campo: str = "", valor: str = "") -> list[dict]:
    out = []
    for r in con.execute("SELECT * FROM mis_videos ORDER BY COALESCE(publicado_en, creado_en) DESC"):
        v = dict(r)
        v["temas"] = jload(v.get("temas"), [])
        if plataforma and v["plataforma"] != plataforma:
            continue
        if campo and _claves(v, campo) and valor not in _claves(v, campo):
            continue
        out.append(ficha_video(con, v))
    return out


AGRUPAR = {"tema": "Tema", "formato": "Formato", "serie": "Serie", "colaboracion": "Colaboración"}


def _claves(v: dict, campo: str) -> list[str]:
    if campo == "tema":
        return v["temas"] or ["(sin tema)"]
    if campo == "formato":
        from .ideas import VARIANTES
        return [VARIANTES.get(v.get("variante") or "", ("", v.get("formato") or "(sin formato)"))[1] or "(sin formato)"]
    return [v.get(campo) or f"(sin {AGRUPAR.get(campo, campo).lower()})"]


def _retencion_grupo(vs: list[dict]) -> dict:
    pares = [(x["ultimos"]["pct_completo"]["valor"], x["duracion_s"]) for x in vs if x["ultimos"]["pct_completo"]]
    if not pares:
        return {"estado": "sin_dato", "texto": "sin datos de retención"}
    duraciones = [d for _, d in pares]
    if any(d is None for d in duraciones):
        return {"estado": "no_comparable", "texto": "no comparable: falta la duración de algún vídeo"}
    md = statistics.median(duraciones)
    if any(abs(d - md) > md * TOLERANCIA_DURACION for d in duraciones):
        return {"estado": "no_comparable", "texto": "no comparable: duraciones distintas"}
    return {"estado": "ok", "valor": round(statistics.median(p for p, _ in pares), 1), "n": len(pares),
            "texto": f"mediana del % que lo ve entero ({len(pares)} vídeo(s) de duración parecida)"}


def rinde(con, agrupar: str = "formato", plataforma: str = "", dias: int | None = None, orden: str = "n") -> dict:
    if agrupar not in AGRUPAR:
        raise NoValido("Agrupación desconocida.")
    corte = iso(datetime.now(timezone.utc) - timedelta(days=dias)) if dias else None
    vids = [v for v in mis_videos(con, plataforma) if not corte or (v["publicado_en"] or "") >= corte]
    grupos: dict[str, list] = {}
    for v in vids:
        for k in _claves(v, agrupar):
            grupos.setdefault(k, []).append(v)
    out = []
    for k, vs in grupos.items():
        v48 = [x["v48"]["vistas"] for x in vs if x["v48"]["estado"] == "ok"]
        act = [x["ultimos"]["vistas"]["valor"] for x in vs if x["ultimos"]["vistas"]]
        seg = [x["ultimos"]["seguidores_ganados"]["valor"] for x in vs if x["ultimos"]["seguidores_ganados"]]
        com = [x["ultimos"]["compartidos"]["valor"] for x in vs if x["ultimos"]["compartidos"]]
        out.append({"clave": k, "n": len(vs), "pocos_datos": len(vs) < MIN_GRUPO,
                    "mediana_48": statistics.median(v48) if v48 else None, "n_48": len(v48),
                    "vistas_total": sum(act) if act else None, "mediana_vistas": statistics.median(act) if act else None, "n_vistas": len(act),
                    "seguidores_total": sum(seg) if seg else None, "n_seguidores": len(seg),
                    "compartidos_total": sum(com) if com else None, "n_compartidos": len(com),
                    "retencion": _retencion_grupo(vs), "videos": [x["id"] for x in vs]})
    clave = {"n": "n", "mediana_48": "mediana_48", "vistas_total": "vistas_total", "mediana_vistas": "mediana_vistas",
             "seguidores_total": "seguidores_total", "compartidos_total": "compartidos_total"}.get(orden, "n")
    out.sort(key=lambda g: (g[clave] is None, -(g[clave] or 0)))
    return {"grupos": out, "n_videos": len(vids), "multi": agrupar == "tema",
            "ingresos": "No hay ingresos ni costes registrados: no se muestran (no es lo mismo que 0 €). Vistas ≠ rentabilidad."}

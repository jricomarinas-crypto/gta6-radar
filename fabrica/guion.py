"""Guion de la Fábrica: esquema por escenas (megaprompt §9), validación y conversión.

Esquema (lo que escribe Claude en estudio/guiones/AAAA-MM-DD/<encargo>.json):

{
  "id": "2026-11-18-hora-por-pais",          # libre
  "oportunidad_id": "kit-hora-por-pais",     # la idea de la que sale
  "formato": "A | B | C",                    # A novedad verificada · B explicación/comparación · C guía breve
  "variante": "lista_pais | ultima_hora | verdad_bulo | comparacion | guia",
  "plataformas": ["tiktok", "shorts"],
  "duracion_objetivo_s": 35,
  "ganchos": ["gancho 1", "gancho 2", "gancho 3"],   # 3 tipos distintos; ≤ 6 palabras para el texto grande
  "gancho_elegido": 0,
  "escenas": [
    {"voz": "leo | sofi", "texto": "lo que se dice (< 12 palabras)", "en_pantalla": "texto grande (opcional)",
     "visual": "lista | tarjeta-etiqueta | veredicto | dato | pasos", "item": 0, "revela": false,
     "afirmaciones": [{"texto": "...", "etiqueta": "CONFIRMADO|REPORTADO|RUMOR|OPINIÓN",
                       "fuente": "https://...", "fecha": "2026-11-16"}]}
  ],
  "cierre": "pregunta para comentarios",
  "titulos": {"tiktok": "...", "shorts": "...", "youtube": null},
  "descripcion": "texto con fuentes",
  "hashtags": ["#GTA6"],
  "aviso_spoilers": false,
  "etiqueta": "opcional: la que sale en pantalla; si falta, la menos segura de las afirmaciones",
  "fuente": "opcional: medio u organismo que sale en pantalla",
  "fuentes": [{"titulo": "...", "url": "https://..."}],   # opcional: títulos legibles de las URLs
  "datos": {                                  # lo que dibuja cada variante
    "lista": [{"nombre": "México", "valor": "19 nov · 0:00"}], "nota": "Hora del centro de México",
    "afirmacion": "...", "veredicto": "VERDAD | BULO | A MEDIAS | SIN CONFIRMAR",
    "titular": "...", "detalle": "...", "hora": "...",
    "filas": [{"aspecto": "Mapa", "a": "GTA 5", "b": "GTA 6"}],
    "pasos": ["Paso 1", "Paso 2"]
  }
}
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date

from estudio.ideas import VARIANTES

ETIQUETAS = ("CONFIRMADO", "REPORTADO", "RUMOR", "OPINIÓN")
VEREDICTOS = ("VERDAD", "BULO", "A MEDIAS", "SIN CONFIRMAR")
VOCES = {"leo": "A", "sofi": "B"}
# de menos a más segura: la etiqueta de pantalla es la menos segura de las afirmaciones de hechos
ORDEN_ETIQUETA = ["RUMOR", "REPORTADO", "CONFIRMADO"]


class GuionNoValido(ValueError):
    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__("Guion no válido:\n- " + "\n- ".join(errores))


def convertir_antiguo(g: dict) -> dict:
    """Guiones por líneas (primera versión de la Fábrica) → esquema por escenas."""
    if "escenas" in g:
        return g
    var = g.get("formato")
    fuentes = g.get("fuentes", [])
    url = next((f["url"] for f in fuentes if str(f.get("url", "")).startswith("http")), "")
    etiqueta = (g.get("etiqueta") or "REPORTADO").upper()
    escenas = []
    for i, ln in enumerate(g.get("lineas", [])):
        e = {"voz": "leo" if ln.get("habla") == "A" else "sofi", "texto": ln.get("texto", "")}
        for k in ("item", "revela"):
            if k in ln:
                e[k] = ln[k]
        if i == 1 and url:
            e["afirmaciones"] = [{"texto": g.get("titulo", ""), "etiqueta": etiqueta, "fuente": url,
                                  "fecha": date.today().isoformat()}]
        escenas.append(e)
    t = g.get("textos", {})
    return {
        "id": g.get("id") or g.get("titulo", ""), "formato": VARIANTES.get(var, ("A", ""))[0], "variante": var,
        "ganchos": [g.get("gancho", "")], "gancho_elegido": 0, "escenas": escenas,
        "cierre": t.get("comentario_fijado", ""), "titulos": {"tiktok": t.get("tiktok"), "shorts": t.get("youtube_titulo")},
        "descripcion": t.get("youtube_descripcion", ""), "etiqueta": etiqueta, "fuente": g.get("fuente", ""),
        "fuentes": fuentes, "titulo": g.get("titulo"),
        "datos": {k: g[k] for k in ("lista", "nota", "afirmacion", "veredicto", "titular", "detalle", "hora") if k in g},
    }


def validar(g: dict) -> tuple[dict, list[str]]:
    """Devuelve (guion normalizado, avisos). Lanza GuionNoValido con TODOS los errores a la vez."""
    g = convertir_antiguo(json.loads(json.dumps(g)))
    errores, avisos = [], []
    var = g.get("variante")
    if var not in VARIANTES:
        errores.append(f"«variante» debe ser una de: {', '.join(VARIANTES)}")
    elif g.get("formato") != VARIANTES[var][0]:
        g["formato"] = VARIANTES[var][0]
    ganchos = [x for x in g.get("ganchos", []) if str(x).strip()]
    if not ganchos:
        errores.append("faltan los ganchos (se piden 3 de tipos distintos)")
    elif len(ganchos) < 3:
        avisos.append(f"hay {len(ganchos)} gancho(s); se recomiendan 3 de tipos distintos")
    g["ganchos"] = ganchos
    ge = g.get("gancho_elegido", 0)
    g["gancho_elegido"] = ge if isinstance(ge, int) and 0 <= ge < max(1, len(ganchos)) else 0
    if g.get("aviso_spoilers"):
        errores.append("el guion tiene spoilers: no se produce (regla: cero spoilers del final o de giros)")

    escenas = []
    for i, e in enumerate(g.get("escenas", [])):
        texto = str(e.get("texto", "")).strip()
        if e.get("voz") not in VOCES:
            errores.append(f"escena {i + 1}: «voz» debe ser leo o sofi")
            continue
        if not texto:
            errores.append(f"escena {i + 1}: falta el texto")
            continue
        if len(texto.split()) >= 16:
            avisos.append(f"escena {i + 1}: frase larga ({len(texto.split())} palabras; objetivo < 12)")
        for j, a in enumerate(e.get("afirmaciones", []) or []):
            et = str(a.get("etiqueta", "")).upper()
            a["etiqueta"] = et
            if et not in ETIQUETAS:
                errores.append(f"escena {i + 1}, afirmación {j + 1}: etiqueta debe ser {'/'.join(ETIQUETAS)}")
            if not str(a.get("fuente", "")).startswith("http"):
                errores.append(f"escena {i + 1}, afirmación {j + 1}: falta la fuente (URL)")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(a.get("fecha", ""))):
                errores.append(f"escena {i + 1}, afirmación {j + 1}: falta la fecha (AAAA-MM-DD)")
        escenas.append({**e, "texto": texto})
    if len(escenas) < 4:
        errores.append("hacen falta al menos 4 escenas (gancho, promesa, desarrollo, cierre)")
    g["escenas"] = escenas

    afirm = [a for e in escenas for a in (e.get("afirmaciones") or [])]
    if not afirm:
        errores.append("ninguna escena tiene afirmaciones con etiqueta, fuente y fecha")
    if any(a["etiqueta"] == "RUMOR" for a in afirm) and not any("rumor" in e["texto"].lower() for e in escenas):
        errores.append("hay un RUMOR pero ninguna escena lo dice como rumor en voz")

    d = g.setdefault("datos", {})
    if var == "lista_pais" and not 2 <= len(d.get("lista") or []) <= 8:
        errores.append("lista_pais necesita entre 2 y 8 filas en datos.lista")
    if var == "verdad_bulo":
        d["veredicto"] = str(d.get("veredicto", "")).upper()
        if not d.get("afirmacion") or d["veredicto"] not in VEREDICTOS:
            errores.append(f"verdad_bulo necesita datos.afirmacion y datos.veredicto ({'/'.join(VEREDICTOS)})")
    if var == "ultima_hora" and not d.get("titular"):
        errores.append("ultima_hora necesita datos.titular")
    if var == "comparacion" and not 2 <= len(d.get("filas") or []) <= 6:
        errores.append("comparacion necesita entre 2 y 6 filas en datos.filas")
    if var == "guia" and not 2 <= len(d.get("pasos") or []) <= 6:
        errores.append("guia necesita entre 2 y 6 pasos en datos.pasos")
    n_items = len(d.get("lista") or d.get("filas") or d.get("pasos") or [])
    for e in escenas:
        if "item" in e and not (isinstance(e["item"], int) and 0 <= e["item"] < n_items):
            e.pop("item")

    if errores:
        raise GuionNoValido(errores)
    g.setdefault("titulo", (g.get("titulos") or {}).get("shorts") or ganchos[0])
    return g, avisos


def hash_guion(g: dict) -> str:
    """Huella del contenido (no del formato del archivo): si cambia una coma, cambia; si solo cambian espacios, no."""
    return hashlib.sha256(json.dumps(g, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def etiqueta_pantalla(g: dict) -> str:
    if g.get("etiqueta", "").upper() in ETIQUETAS:
        return g["etiqueta"].upper()
    ets = {a["etiqueta"] for e in g["escenas"] for a in (e.get("afirmaciones") or [])}
    for et in ORDEN_ETIQUETA:
        if et in ets:
            return et
    return "OPINIÓN"


def fuentes(g: dict) -> list[dict]:
    titulos = {f.get("url"): f.get("titulo") for f in g.get("fuentes", []) if f.get("url")}
    out, vistos = [], set()
    for f in g.get("fuentes", []):
        if f.get("url") and f["url"] not in vistos:
            vistos.add(f["url"])
            out.append({"titulo": f.get("titulo") or f["url"], "url": f["url"]})
    for e in g["escenas"]:
        for a in e.get("afirmaciones") or []:
            if a["fuente"] not in vistos:
                vistos.add(a["fuente"])
                out.append({"titulo": titulos.get(a["fuente"]) or a["fuente"], "url": a["fuente"]})
    return out


def plano(g: dict) -> dict:
    """Lo que necesitan el montaje y el control de calidad, en forma sencilla."""
    d = g.get("datos", {})
    return {
        "formato": g["variante"], "titulo": g.get("titulo") or g["ganchos"][0],
        "gancho": g["ganchos"][g["gancho_elegido"]], "etiqueta": etiqueta_pantalla(g),
        "fuente": g.get("fuente") or "", "fuentes": fuentes(g), **d,
        "lineas": [{"habla": VOCES[e["voz"]], "texto": e["texto"], "item": e.get("item"), "revela": e.get("revela", False),
                    "en_pantalla": e.get("en_pantalla")} for e in g["escenas"]],
    }

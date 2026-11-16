"""Formato del guion de la Fábrica y su validación.

Estructura fija del plan v2: gancho (0-2 s), promesa (2-5 s), desarrollo con un giro, cierre con pregunta.
Frases de menos de 12 palabras. Español neutro latinoamericano.
"""
from __future__ import annotations

from estudio.ideas import FORMATOS

ETIQUETAS = ("CONFIRMADO", "REPORTADO", "RUMOR", "OPINIÓN")
VEREDICTOS = ("VERDAD", "BULO", "A MEDIAS", "SIN CONFIRMAR")

PLANTILLA = {
    "formato": "lista_pais | verdad_bulo | ultima_hora",
    "titulo": "título interno, honesto, con 'GTA 6'",
    "gancho": "≤ 6 palabras, texto grande del primer segundo",
    "etiqueta": "CONFIRMADO | REPORTADO | RUMOR | OPINIÓN",
    "fuente": "medio u organismo que sale en pantalla (≤ 40 caracteres)",
    "fuentes": [{"titulo": "...", "url": "https://..."}],
    "lista": [{"nombre": "México", "valor": "19 nov · 0:00"}],
    "nota": "(lista_pais, opcional) aclaración pequeña bajo la lista, p. ej. 'Hora del centro de México'",
    "afirmacion": "(verdad_bulo) la frase que circula",
    "veredicto": "(verdad_bulo) VERDAD | BULO | A MEDIAS | SIN CONFIRMAR",
    "titular": "(ultima_hora) ≤ 40 caracteres",
    "detalle": "(ultima_hora) ≤ 70 caracteres",
    "hora": "(ultima_hora, opcional) texto de la esquina, p. ej. '19 NOV · 7:00 CDMX'",
    "lineas": [{"habla": "A | B", "texto": "frase de < 12 palabras", "item": "(lista_pais) fila a resaltar",
                "revela": "(verdad_bulo) true en la línea que da el veredicto"}],
    "textos": {"tiktok": "texto corto para TikTok (sin hashtags)", "youtube_titulo": "≤ 90 caracteres con 'GTA 6'",
               "youtube_descripcion": "1-2 frases", "comentario_fijado": "pregunta para fijar en comentarios"},
}


def validar(g: dict) -> dict:
    errores = []
    if g.get("formato") not in FORMATOS:
        errores.append(f"formato debe ser uno de {list(FORMATOS)}")
    g["etiqueta"] = (g.get("etiqueta") or "").upper()
    if g["etiqueta"] not in ETIQUETAS:
        errores.append(f"etiqueta debe ser una de {ETIQUETAS}")
    lineas = [ln for ln in g.get("lineas", []) if ln.get("habla") in ("A", "B") and str(ln.get("texto", "")).strip()]
    if len(lineas) < 4:
        errores.append("hacen falta al menos 4 líneas (gancho, promesa, desarrollo, cierre)")
    g["lineas"] = lineas
    if not (g.get("gancho") or "").strip():
        errores.append("falta el gancho")
    if g.get("formato") == "lista_pais":
        lista = g.get("lista") or []
        if not 2 <= len(lista) <= 8:
            errores.append("lista_pais necesita entre 2 y 8 filas en 'lista'")
        for ln in lineas:
            if "item" in ln and not (isinstance(ln["item"], int) and 0 <= ln["item"] < len(lista)):
                ln.pop("item")
    if g.get("formato") == "verdad_bulo":
        g["veredicto"] = (g.get("veredicto") or "").upper()
        if not g.get("afirmacion") or g["veredicto"] not in VEREDICTOS:
            errores.append(f"verdad_bulo necesita 'afirmacion' y 'veredicto' ({VEREDICTOS})")
    if g.get("formato") == "ultima_hora" and not g.get("titular"):
        errores.append("ultima_hora necesita 'titular'")
    if not any(str(f.get("url", "")).startswith("http") for f in g.get("fuentes", [])):
        errores.append("hace falta al menos una fuente con URL")
    if errores:
        raise ValueError("Guion no válido:\n- " + "\n- ".join(errores))
    g.setdefault("titulo", g["gancho"])
    g.setdefault("textos", {})
    return g

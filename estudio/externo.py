"""Búsqueda EXTERNA en Google News (fase 3). Gratis y sin clave: es el RSS público de búsqueda de Google News.

- Solo se ejecuta al pulsar «Buscar en Google News»: nunca mientras escribes.
- Lo que escribes se envía a Google News (se avisa en pantalla). No se guarda nada salvo lo que tú guardes.
- Límite de cortesía: 1 búsqueda cada 5 s y 30 por hora (en memoria del Estudio). Si se pasa, se dice el motivo.
- Los enlaces son los de Google News (redirigen al artículo original); el medio original va aparte.
"""
from __future__ import annotations

import time
from calendar import timegm
from collections import deque
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import requests

from .investigacion import NoValido

REGIONES = {"latam": ("es-419", "MX", "MX:es-419", "Latinoamérica (español)"),
            "es": ("es", "ES", "ES:es", "España"),
            "us": ("en-US", "US", "US:en", "EE. UU. (inglés)")}
URL = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
UA = {"User-Agent": "Mozilla/5.0 (Punto de Control, uso personal)"}
MIN_SEPARACION_S, MAX_POR_HORA = 5, 30
_historial: deque = deque()


def _limite(ahora: float) -> None:
    while _historial and ahora - _historial[0] > 3600:
        _historial.popleft()
    if _historial and ahora - _historial[-1] < MIN_SEPARACION_S:
        raise NoValido(f"Espera {MIN_SEPARACION_S - int(ahora - _historial[-1])} s entre búsquedas externas (límite de cortesía).")
    if len(_historial) >= MAX_POR_HORA:
        raise NoValido(f"Has hecho {MAX_POR_HORA} búsquedas externas en la última hora: espera un poco (límite de cortesía).")


def _descargar(url: str) -> bytes:
    r = requests.get(url, headers=UA, timeout=15)
    r.raise_for_status()
    return r.content


def google_news(q: str, region: str = "latam", descargar=None, ahora: float | None = None) -> dict:
    q = " ".join(str(q or "").split())[:150]
    if len(q) < 2:
        raise NoValido("Escribe qué quieres buscar.")
    if region not in REGIONES:
        region = "latam"
    ahora = time.time() if ahora is None else ahora
    _limite(ahora)
    hl, gl, ceid, nombre = REGIONES[region]
    url = URL.format(q=quote_plus(q), hl=hl, gl=gl, ceid=ceid)
    _historial.append(ahora)
    try:
        crudo = (descargar or _descargar)(url)
    except requests.RequestException as e:
        raise NoValido(f"Google News no respondió ({e.__class__.__name__}). Prueba de nuevo en un rato.") from e
    feed = feedparser.parse(crudo)
    out = []
    for e in feed.entries[:40]:
        medio = (e.get("source") or {}).get("title") or ""
        titulo = e.get("title", "")
        if medio and titulo.endswith(" - " + medio):  # Google añade « - Medio» al titular
            titulo = titulo[: -len(" - " + medio)]
        pub = e.get("published_parsed")
        out.append({"titulo": titulo, "url": e.get("link", ""), "medio": medio or "medio desconocido",
                    "publicado_en": datetime.fromtimestamp(timegm(pub), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if pub else None})
    return {"resultados": out, "consulta": q, "region": nombre, "consultado_en": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "restantes_hora": MAX_POR_HORA - len(_historial)}

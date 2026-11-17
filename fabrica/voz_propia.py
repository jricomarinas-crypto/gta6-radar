"""Tu voz: una toma grabada por escena desde el Estudio (micrófono del navegador).

- Cada toma va ligada al TEXTO EXACTO de su escena (huella). Si cambias el guion, esa toma deja de valer
  y el Estudio te pide volver a grabarla.
- ffmpeg la convierte a WAV mono y recorta el silencio de los extremos (podcast.tts._to_wav).
- Subtítulos: el texto es el del guion; los tiempos por palabra se reparten de forma proporcional dentro de la toma
  (aproximados, no exactos a la sílaba).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from estudio import db, rutas
from podcast import tts
from radar.config import cfg
from radar.db import iso

MAX_BYTES = 25 * 1024 * 1024
TIPOS = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/mpeg": "mp3", "audio/wav": "wav",
         "audio/x-wav": "wav"}


class TomaNoValida(ValueError):
    pass


def huella(texto: str) -> str:
    return hashlib.sha1(texto.strip().encode()).hexdigest()[:16]


def opciones(t: dict) -> dict:
    f = cfg().get("fabrica", {})
    fondo = t.get("fondo") or f.get("fondo_por_defecto", "video")
    voz = t.get("voz") or f.get("voz_por_defecto", "propia")
    return {"fondo": fondo if fondo in ("video", "grafico") else "video",
            "voz": voz if voz in ("propia", "sintetica") else "propia"}


def guardar(con, t: dict, escenas: list[dict], n: int, datos: bytes, mime: str) -> dict:
    if not 0 <= n < len(escenas):
        raise TomaNoValida("Esa escena no existe en el guion actual.")
    if not datos or len(datos) > MAX_BYTES:
        raise TomaNoValida("La grabación está vacía o es demasiado grande (máx. 25 MB).")
    ext = TIPOS.get((mime or "").split(";")[0].strip().lower())
    if not ext:
        raise TomaNoValida("Formato de audio no admitido.")
    d = rutas.trabajo_dir(t["id"]) / "tomas"
    d.mkdir(parents=True, exist_ok=True)
    crudo, wav = d / f"escena_{n:02d}_original.{ext}", d / f"escena_{n:02d}.wav"
    crudo.write_bytes(datos)
    try:
        dur = tts._to_wav(crudo, wav)
    except Exception as e:  # noqa: BLE001
        raise TomaNoValida(f"No se pudo leer el audio ({e.__class__.__name__}). Vuelve a grabar.") from e
    if dur < 0.4:
        raise TomaNoValida("La toma es casi silencio. Acércate al micrófono y vuelve a grabar.")
    con.execute("INSERT OR REPLACE INTO tomas(trabajo_id,escena,texto_hash,ruta,duracion,creada_en) VALUES(?,?,?,?,?,?)",
                (t["id"], n, huella(escenas[n]["texto"]), str(wav), dur, iso()))
    con.commit()
    return {"escena": n, "duracion": round(dur, 1)}


def estado(con, tid: str, escenas: list[dict]) -> list[dict]:
    filas = {r["escena"]: dict(r) for r in con.execute("SELECT * FROM tomas WHERE trabajo_id=?", (tid,))}
    out = []
    for i, e in enumerate(escenas):
        f = filas.get(i)
        valida = bool(f) and f["texto_hash"] == huella(e["texto"]) and Path(f["ruta"]).exists()
        out.append({"escena": i, "texto": e["texto"], "grabada": bool(f), "valida": valida,
                    "duracion": round(f["duracion"], 1) if f else None,
                    "aviso": ("El texto cambió: vuelve a grabarla" if f and not valida else None)})
    return out


def rutas_validas(con, tid: str, escenas: list[dict]) -> list[Path]:
    est = estado(con, tid, escenas)
    faltan = [str(x["escena"] + 1) for x in est if not x["valida"]]
    if faltan:
        raise TomaNoValida("Falta grabar (o volver a grabar) la escena " + ", ".join(faltan) + ".")
    filas = {r["escena"]: r["ruta"] for r in con.execute("SELECT * FROM tomas WHERE trabajo_id=?", (tid,))}
    return [Path(filas[i]) for i in range(len(escenas))]


def clave_render(con, t: dict, guion_hash: str, escenas: list[dict]) -> tuple[str, dict]:
    """Huella de todo lo que cambia el vídeo: guion + fondo + voz (+ tomas). Devuelve (clave, opciones)."""
    op = opciones(t)
    partes = [guion_hash, op["fondo"], op["voz"]]
    if op["voz"] == "propia":
        filas = {r["escena"]: r for r in con.execute("SELECT * FROM tomas WHERE trabajo_id=?", (t["id"],))}
        partes += [f"{i}:{filas[i]['texto_hash']}:{filas[i]['creada_en']}" if i in filas else f"{i}:-"
                   for i in range(len(escenas))]
    clave = guion_hash if op == {"fondo": "grafico", "voz": "sintetica"} else \
        hashlib.sha256(json.dumps(partes).encode()).hexdigest()[:16]
    return clave, op


def poner_opciones(con, tid: str, fondo: str | None, voz: str | None) -> None:
    if fondo is not None and fondo not in ("video", "grafico"):
        raise TomaNoValida("Fondo desconocido.")
    if voz is not None and voz not in ("propia", "sintetica"):
        raise TomaNoValida("Voz desconocida.")
    if fondo:
        con.execute("UPDATE trabajos SET fondo=? WHERE id=?", (fondo, tid))
    if voz:
        con.execute("UPDATE trabajos SET voz=? WHERE id=?", (voz, tid))
    con.commit()
    db.trabajo(con, tid)

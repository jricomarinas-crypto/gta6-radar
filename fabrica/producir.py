"""Render de una versión: guion aprobado → voces → montaje → subtítulos → control de calidad.

Solo fabrica el vídeo para revisarlo; NO exporta a la carpeta del Mac (eso es el botón Exportar,
y solo con el vídeo aprobado). Lo normal es usarlo desde el Estudio (botón «Crear vídeo»), que lo pone en la cola.

    python -m fabrica.producir <encargo>     # igual que pulsar «Crear vídeo» y esperar
"""
from __future__ import annotations

import argparse
import shutil

from estudio import db, rutas
from podcast import script, tts

from . import broll, calidad, formatos, voces, voz_propia
from .guion import plano


class FalloMontaje(RuntimeError):
    """El montaje (ffmpeg) falló. Se puede reintentar: las voces ya están guardadas."""


def render_version(con, vid: str) -> dict:
    v = db.version(con, vid)
    t = db.trabajo(con, v["trabajo_id"])
    g = v["guion"]
    p = plano(g)
    base = rutas.trabajo_dir(t["id"])
    work = base / f"v{v['n']}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    op = v.get("opciones") or {"fondo": "grafico", "voz": "sintetica"}
    p["voz"] = op.get("voz")
    db.actualizar_version(con, vid, estado_produccion="en_curso", etapa="Voces", error=None)
    ep = {"segmentos": [{"lineas": [{"habla": ln["habla"], "texto": ln["texto"]} for ln in p["lineas"]]}]}
    if op.get("voz") == "propia":
        lines = voces.desde_tomas(script.flatten(ep), voz_propia.rutas_validas(con, t["id"], g["escenas"]))
    else:
        lines = voces.sintetizar(script.flatten(ep), base / "voces")
    clips = []
    if op.get("fondo") == "video":
        db.actualizar_version(con, vid, etapa="Vídeo de fondo")
        clips, motivo = broll.elegir(len(lines), vid, [e.get("broll") for e in g["escenas"]])
        op = {**op, "fondo_usado": "video" if clips else "grafico", "fondo_motivo": motivo,
              "creditos": [broll.credito(c) for c in dict.fromkeys(clips)]}
        db.actualizar_version(con, vid, opciones=op)

    db.actualizar_version(con, vid, etapa="Montaje")
    try:
        lines, total = tts.build_timeline(lines, work / "audio.wav")
        video, portada = formatos.montar(p, lines, work / "audio.wav", total, work / "render", clips=clips)
        srt = formatos.escribir_srt(lines, work / "subtitulos.srt")
        destino = work / "video.mp4"
        shutil.move(video, destino)
        shutil.move(portada, work / "portada.jpg")
    except Exception as e:  # noqa: BLE001
        raise FalloMontaje(f"El montaje falló ({e.__class__.__name__}: {e}). Puedes reintentar: las voces ya están guardadas.") from e

    db.actualizar_version(con, vid, etapa="Calidad")
    q = {pl: calidad.revisar(destino, p, pl) for pl in t["plataformas"]}
    shutil.rmtree(work / "render", ignore_errors=True)
    db.actualizar_version(con, vid, estado_produccion="listo", etapa="Listo para revisar", video_ruta=str(destino),
                          srt_ruta=str(srt), portada_ruta=str(work / "portada.jpg"), duracion=q[t["plataformas"][0]]["duracion"],
                          calidad=q)
    db.evento(con, t["id"], "video_fabricado", v["n"])
    return db.version(con, vid)


def main():
    from estudio import flujo
    from estudio.servidor import usar_ffmpeg_completo
    from . import cola

    usar_ffmpeg_completo()
    ap = argparse.ArgumentParser()
    ap.add_argument("encargo")
    a = ap.parse_args()
    con = db.connect()
    v = flujo.crear_video(con, a.encargo)
    cola.procesar_pendientes(con)
    v = db.version(con, v["id"])
    print(f"{v['id']}: {v['estado_produccion']} · {v['etapa']}" + (f" · {v['error']}" if v["error"] else ""))
    if v["video_ruta"]:
        print(f"Vídeo para revisar: {v['video_ruta']}")


if __name__ == "__main__":
    main()

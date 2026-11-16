"""Fabrica un encargo: guion → voces → montaje → control de calidad → carpeta del día.

    python -m fabrica.producir <encargo> <guion.json>            # encargo creado con el botón Crear del Estudio
    python -m fabrica.producir --nuevo <guion.json> [--plataformas tiktok,shorts]   # sin pasar por el Estudio

El progreso se ve en directo en la pestaña Fábrica (http://localhost:8080).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from estudio import db
from estudio.ideas import PLATAFORMAS, slug
from podcast import script, tts
from radar.config import OUTPUT_DIR, cfg

from . import calidad, exportar, formatos
from .guion import validar


def _avisar(titulo: str, texto: str) -> None:
    t = texto.replace('"', "'")
    subprocess.run(["osascript", "-e", f'display notification "{t}" with title "{titulo}" sound name "Glass"'],
                   check=False, capture_output=True)


def fabricar(tid: str, guion: dict, abrir: bool = True) -> dict:
    con = db.connect()
    t = db.trabajo(con, tid)
    if not t:
        raise SystemExit(f"No existe el encargo {tid}")
    work = OUTPUT_DIR / "fabrica" / tid
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        guion = validar(guion)
        if guion["formato"] != t["formato"]:
            con.execute("UPDATE trabajos SET formato=? WHERE id=?", (guion["formato"], tid))
            con.commit()
        (work / "guion.json").write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
        db.progreso(con, tid, 0.05, "Generando voces")
        hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
        ep = {"segmentos": [{"lineas": guion["lineas"]}]}
        lines = tts.synthesize(script.flatten(ep), hosts, work / "voces")
        lines, total = tts.build_timeline(lines, work / "audio.wav")
        db.progreso(con, tid, 0.45, f"Montando el vídeo ({total:.0f} s)")
        video, portada = formatos.montar(guion, lines, work / "audio.wav", total, work / "render")
        db.progreso(con, tid, 0.85, "Control de calidad")
        q = {p: calidad.revisar(video, guion, p) for p in t["plataformas"]}
        rutas = exportar.exportar(video, portada, guion, t["plataformas"], q, tid)
        for p, ruta in rutas.items():
            db.guardar_pieza(con, tid, p, guion["formato"], str(ruta), q[p]["duracion"], q[p])
        fallos = sum(len(x["fallos"]) for x in q.values())
        db.progreso(con, tid, 1.0, "Listo" + (f" · {fallos} avisos de calidad" if fallos else ""), "listo")
    except Exception as e:  # noqa: BLE001 — el error se enseña en el Estudio
        db.progreso(con, tid, 1.0, "Error", "error", f"{e.__class__.__name__}: {e}")
        raise
    dia = exportar.carpeta_dia()
    print(f"✔ Encargo {tid} listo: {guion['titulo']}")
    for p, ruta in rutas.items():
        estado = "calidad OK" if q[p]["ok"] else "REVISAR: " + "; ".join(q[p]["fallos"])
        print(f"  {PLATAFORMAS[p]}: {ruta}  ({q[p]['duracion']:.0f} s · {estado})")
    _avisar("Punto de Control", f"Listo: {guion['titulo']}")
    if abrir and cfg().get("estudio", {}).get("abrir_finder_al_terminar", True):
        subprocess.run(["open", str(dia)], check=False)
    return {"rutas": {k: str(v) for k, v in rutas.items()}, "calidad": q}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("encargo", nargs="?")
    ap.add_argument("guion")
    ap.add_argument("--nuevo", action="store_true", help="crea el encargo a partir del guion, sin el Estudio")
    ap.add_argument("--plataformas", default="tiktok,shorts")
    ap.add_argument("--sin-abrir", action="store_true", help="no abrir el Finder al terminar")
    args = ap.parse_args()
    guion = json.loads(Path(args.guion).read_text(encoding="utf-8"))
    tid = args.encargo
    if args.nuevo or not tid:
        plats = [p for p in args.plataformas.split(",") if p in PLATAFORMAS] or ["tiktok", "shorts"]
        idea = {"id": "manual-" + slug(guion.get("titulo") or guion.get("gancho", "")), "titulo": guion.get("titulo"),
                "por_que": "Encargo directo", "origen": "manual", "fuentes": []}
        tid = db.crear_trabajo(db.connect(), idea, guion.get("formato", "ultima_hora"), plats)["id"]
    fabricar(tid, guion, abrir=not args.sin_abrir)


if __name__ == "__main__":
    main()

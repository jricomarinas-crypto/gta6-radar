"""Genera (y sube) el episodio del día.

    python -m podcast.run                 # investiga, escribe, pone voces, monta y sube
    python -m podcast.run --sin-subir     # todo menos la subida
    python -m podcast.run --demo          # usa examples/episodio_demo.json (no necesita Claude)
    python -m podcast.run --guion ruta.json
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

from radar.config import OUTPUT_DIR, ROOT, cfg
from radar.db import connect, iso, jdump
from radar.notify import send

from . import editor, publicar, render, script, tts, upload

MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--guion")
    ap.add_argument("--sin-subir", action="store_true")
    ap.add_argument("--sin-shorts", action="store_true")
    args = ap.parse_args()

    con = connect()
    now = datetime.now(ZoneInfo(cfg()["canal"].get("zona_horaria", "UTC")))
    day = now.strftime("%Y-%m-%d")
    work = OUTPUT_DIR / day
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    # 1) guion
    dossier, sources = "", []
    editor_line = ""
    if args.demo or args.guion:
        ep = script.validate(json.loads((ROOT / (args.guion or "examples/episodio_demo.json")).read_text(encoding="utf-8")))
    else:
        print("▶ Investigando (radar + verificación web)…")
        dossier, sources, _ = script.research(con)
        (work / "dossier.md").write_text(dossier + "\n\nFuentes:\n" + "\n".join(f"- {s['title']}: {s['url']}" for s in sources),
                                         encoding="utf-8")
        print("▶ Escribiendo guion…")
        ep = script.write_script(dossier, sources, con)
        print("▶ Agente Editor revisando el guion…")
        try:
            rev = editor.review(ep, dossier)
            ep, n_fix = editor.apply(ep, rev)
            ep = script.validate(ep)
            (work / "editor.md").write_text(editor.report_md(rev, n_fix), encoding="utf-8")
            editor_line = f"Agente Editor: {rev.get('veredicto', '?')} · nota {rev.get('nota', '?')}/10 · {n_fix} correcciones"
        except Exception as e:  # noqa: BLE001 — si el editor falla, seguimos con el guion original
            editor_line = f"Agente Editor: no pudo revisar ({e.__class__.__name__})"
        print("  " + editor_line)
    (work / "guion.json").write_text(json.dumps(ep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Episodio: {ep['titulo']}  ({ep.get('formato')})")

    # 2) voces
    print("▶ Generando voces…")
    hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
    lines = tts.synthesize(script.flatten(ep), hosts, work / "voces")
    lines, total = tts.build_timeline(lines, work / "audio.wav")
    print(f"  Duración: {total / 60:.1f} min")

    # 3) vídeo, Shorts y miniatura
    n_ep = con.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] + 1
    meta = {"title": ep["titulo"], "badge": f"GTA 6 · EP. {n_ep} · {now.day} {MESES[now.month - 1]} {now.year}"}
    video = render.render_episode(ep, lines, work / "audio.wav", total, work / "render", meta)
    final = work / "episodio.mp4"
    shutil.move(video, final)
    thumb = render.thumbnail(meta, ep, work / "miniatura.jpg")
    shorts = []
    if not args.sin_shorts:
        for i, sh in enumerate(ep.get("shorts", [])[: int(cfg()["podcast"].get("shorts_por_episodio", 3))]):
            p = render.render_short(ep, lines, work / "audio.wav", sh, work / "render", meta, i)
            if p:
                dst = work / p.name
                shutil.move(p, dst)
                shorts.append((sh, dst))

    # 4) textos
    fuentes = ep.get("fuentes") or sources
    src_txt = "\n".join(f"• {s.get('titulo') or s.get('title')}: {s['url']}" for s in fuentes[:15] if s.get("url"))
    disclosure = ("Este podcast usa voces sintéticas. El guion se basa en las fuentes citadas en esta descripción; "
                  "los rumores se indican como tales.")
    desc = f"{ep.get('descripcion', '')}\n\nCapítulos:\n{render.chapters(ep, lines)}\n\nFuentes:\n{src_txt}\n\n{disclosure}\n\n#GTA6 #GTAVI #GrandTheftAutoVI"
    (work / "descripcion.txt").write_text(desc, encoding="utf-8")

    # 4b) pack para publicar (YouTube + TikTok)
    piezas = [publicar.pieza("episodio", final, ep["titulo"], desc, ep.get("etiquetas", []), thumb)]
    for sh, path in shorts:
        sdesc_pack = f"{sh.get('titulo', '')}\n\nEpisodio completo en el canal.\n\n{disclosure}\n\n#GTA6 #Shorts"
        piezas.append(publicar.pieza("short", path, sh.get("titulo", ep["titulo"]), sdesc_pack,
                                     ep.get("etiquetas", []), gancho=sh.get("gancho", "")))
    publicar.crear_pack(work, piezas, disclosure)

    # 5) subida
    yt_id, shorts_ids = None, []
    do_upload = cfg()["podcast"]["subida"].get("activar", True) and not args.sin_subir
    if do_upload and upload.available():
        print("▶ Subiendo a YouTube…")
        yt_id = upload.upload(final, ep["titulo"], desc, ep.get("etiquetas", []), thumb)
        if cfg()["podcast"]["subida"].get("subir_shorts", True):
            for sh, path in shorts:
                sdesc = (f"{sh.get('titulo', '')}\n\nEpisodio completo: https://youtu.be/{yt_id}\n\n{disclosure}\n\n"
                         "#GTA6 #Shorts")
                shorts_ids.append(upload.upload(path, f"{sh.get('titulo', ep['titulo'])[:90]} #Shorts", sdesc,
                                                ep.get("etiquetas", [])))
    elif do_upload:
        print("⚠ Sin credenciales de YouTube: los vídeos quedan en la carpeta output/")

    if not args.demo:
        con.execute("INSERT OR REPLACE INTO episodes(id,date,format,title,topic_keys,youtube_id,shorts,sources,created_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (day, day, ep.get("formato"), ep["titulo"], jdump(ep.get("temas_clave", [])), yt_id,
                     jdump(shorts_ids), jdump(fuentes), iso()))
        con.commit()

    msg = [f"🎙️ Episodio listo: {ep['titulo']}", f"Duración: {total / 60:.1f} min · Shorts: {len(shorts)}"]
    if editor_line:
        msg.append(editor_line)
    if yt_id:
        msg.append(f"Revísalo y publícalo: https://studio.youtube.com/video/{yt_id}/edit")
        msg += [f"Short: https://studio.youtube.com/video/{s}/edit" for s in shorts_ids]
    else:
        msg.append("Descárgalo de GitHub → Actions → la ejecución de hoy → Artifacts.")
    if cfg()["avisos"].get("enviar_aviso_episodio", True) and not args.demo:
        send("\n".join(msg))
    print("\n".join(msg))
    print(f"✔ Archivos en {work}")


if __name__ == "__main__":
    main()

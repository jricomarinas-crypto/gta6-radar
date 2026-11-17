"""Exportar la versión APROBADA a la carpeta del Mac (megaprompt §11).

~/Movies/Punto de Control/AAAA-MM-DD/
├── TikTok/          NN_slug.mp4 · .txt · .srt · _portada.jpg · .manifiesto.json
├── YouTube Shorts/  NN_slug.mp4 · .txt · .srt · .manifiesto.json
└── _revisar.md

- Idempotente: exportar dos veces la misma versión no copia nada si los archivos y sus hashes están bien.
- Una versión nueva de la misma pieza se exporta como NN_slug_v2 (no pisa la anterior en silencio).
- «Disponible en el Mac» solo cuando se han releído los archivos del disco y el sha256 coincide con el manifiesto.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from estudio import db, rutas
from estudio.ideas import slug
from podcast.publicar import HASHTAGS_TIKTOK, HORA

from .guion import fuentes, plano

CARPETAS = {"tiktok": "TikTok", "shorts": "YouTube Shorts"}
AVISO = "Este video usa voces sintéticas. Cada dato lleva su fuente; los rumores se indican como tales."
AVISO_PROPIA = "Narración: voz real del creador. Cada dato lleva su fuente; los rumores se indican como tales."


def _aviso(op: dict) -> str:
    return AVISO_PROPIA if op.get("voz") == "propia" else AVISO


def _creditos_txt(op: dict) -> str:
    cr = [c for c in op.get("creditos", []) if c.get("fuente") == "Pexels" and c.get("autor")]
    if not cr:
        return ""
    return "Vídeo de fondo: " + "; ".join(f"{c['autor']} (Pexels) {c.get('url', '')}".strip() for c in cr) + "\n\n"


def _ia_paso(op: dict, plataforma: str) -> str:
    if op.get("voz") == "propia":
        return ("- La voz es tuya y el vídeo de fondo es real: no hace falta la etiqueta de IA salvo que uses "
                "algo generado con IA (revísalo).")
    return ("- Activa «Contenido generado por IA» (voces sintéticas)." if plataforma == "tiktok"
            else "- Marca «Contenido alterado o sintético» en YouTube Studio.")


class ExportacionFallida(RuntimeError):
    pass


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _fuentes_txt(g: dict) -> str:
    return "\n".join(f"• {f['titulo']}: {f['url']}" for f in fuentes(g))


def _txt_tiktok(g: dict, op: dict | None = None) -> str:
    op = op or {}
    texto = ((g.get("titulos") or {}).get("tiktok") or g["ganchos"][g["gancho_elegido"]]).strip()
    tags = " ".join(g.get("hashtags") or []) or HASHTAGS_TIKTOK
    return (f"TEXTO PARA TIKTOK (copiar y pegar)\n\n{texto} {tags}\n\n"
            f"COMENTARIO FIJADO\n{g.get('cierre') or '¿Tú qué opinas? Te leo 👇'}\n\n"
            f"ANTES DE PUBLICAR\n{_ia_paso(op, 'tiktok')}\n- Mejor hora: {HORA}.\n\n"
            f"FUENTES (para responder dudas)\n{_fuentes_txt(g)}\n\n{_creditos_txt(op)}")


def _txt_shorts(g: dict, op: dict | None = None) -> str:
    op = op or {}
    titulo = ((g.get("titulos") or {}).get("shorts") or g.get("titulo") or "").strip()
    if "gta 6" not in titulo.lower() and "gta vi" not in titulo.lower():
        titulo = f"GTA 6: {titulo}"
    titulo = titulo[:90] + ("" if "#shorts" in titulo.lower() else " #Shorts")
    return (f"TÍTULO\n{titulo}\n\nDESCRIPCIÓN\n{(g.get('descripcion') or g.get('titulo') or '').strip()}\n\n"
            f"Fuentes:\n{_fuentes_txt(g)}\n\n{_creditos_txt(op)}{_aviso(op)}\n\n#GTA6 #Shorts\n\n"
            f"COMENTARIO FIJADO\n{g.get('cierre') or '¿Tú qué opinas?'}\n\n"
            f"ANTES DE PUBLICAR\n{_ia_paso(op, 'shorts')}\n- Mejor hora: {HORA}.\n")


def _siguiente_nn(dia: Path) -> int:
    nums = [int(m.group(1)) for sub in CARPETAS.values() for f in (dia / sub).glob("**/*.mp4")
            if (m := re.match(r"(\d+)_", f.name))]
    return max(nums, default=0) + 1


def verificar(manifiesto_ruta: str | None) -> tuple[bool, str]:
    """Relee los archivos del disco y compara su sha256 con el manifiesto."""
    if not manifiesto_ruta or not Path(manifiesto_ruta).exists():
        return False, "no hay manifiesto en el disco"
    m = json.loads(Path(manifiesto_ruta).read_text(encoding="utf-8"))
    base = Path(manifiesto_ruta).parent
    for nombre, h in m["archivos"].items():
        f = base / nombre
        if not f.exists():
            return False, f"falta {nombre}"
        if sha256(f) != h:
            return False, f"{nombre} no coincide con el manifiesto"
    return True, "hash comprobado"


def exportar(con, tid: str) -> dict:
    """Exporta la versión con el vídeo aprobado. El llamador comprueba la aprobación (estudio.flujo)."""
    t = db.trabajo(con, tid)
    ap = db.aprobaciones(con, tid)
    v = next(x for x in db.versiones(con, tid) if x["n"] == ap["video"]["version_n"])
    g, p = v["guion"], plano(v["guion"])
    previas = db.exportaciones(con, v["id"])
    resultado = {}
    try:
        if not t.get("nn"):
            dia = rutas.carpeta_base() / datetime.now().strftime("%Y-%m-%d")
            dia.mkdir(parents=True, exist_ok=True)
            con.execute("UPDATE trabajos SET nn=? WHERE id=?", (f"{dia.name}/{_siguiente_nn(dia):02d}", tid))
            con.commit()
            t = db.trabajo(con, tid)
        fecha_dir, nn = t["nn"].split("/")
        dia = rutas.carpeta_base() / fecha_dir
        nombre = f"{nn}_{slug(p['titulo'], 36)}" + (f"_v{v['n']}" if v["n"] > 1 else "")
        for pl in t["plataformas"]:
            prev = previas.get(pl)
            if prev and prev.get("verificada_en"):
                ok, _ = verificar(prev.get("manifiesto_ruta"))
                if ok:  # ya está en el Mac y el hash coincide: no se duplica nada
                    resultado[pl] = {"ruta": prev["ruta"], "estado": "ya exportado (hash comprobado)"}
                    continue
            sub = dia / CARPETAS[pl]
            sub.mkdir(parents=True, exist_ok=True)
            archivos = {f"{nombre}.mp4": Path(v["video_ruta"]), f"{nombre}.srt": Path(v["srt_ruta"])}
            if pl == "tiktok" and v.get("portada_ruta"):
                archivos[f"{nombre}_portada.jpg"] = Path(v["portada_ruta"])
            for dst, src in archivos.items():
                shutil.copy2(src, sub / dst)
            op = v.get("opciones") or {}
            (sub / f"{nombre}.txt").write_text(_txt_tiktok(g, op) if pl == "tiktok" else _txt_shorts(g, op), encoding="utf-8")
            hashes = {f: sha256(sub / f) for f in [*archivos, f"{nombre}.txt"]}
            manifiesto = {
                "pieza": tid, "version": v["n"], "plataforma": pl, "guion_hash": v["guion_hash"],
                "exportado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "archivos": hashes, "fuentes": fuentes(g),
                "voz": op.get("voz", "sintetica"), "fondo": op.get("fondo_usado", op.get("fondo", "grafico")),
                "materiales": op.get("creditos", []),
                "aprobaciones": {k: {"version": a["version_n"], "guion_hash": a["guion_hash"], "fecha": a["creada_en"]}
                                 for k, a in ap.items()},
                "publicado": False,
            }
            man = sub / f"{nombre}.manifiesto.json"
            man.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
            ok, motivo = verificar(str(man))
            db.guardar_exportacion(con, v["id"], pl, ruta=str(sub / f"{nombre}.mp4"), manifiesto_ruta=str(man),
                                   nombre=nombre, exportada_en=manifiesto["exportado_en"],
                                   verificada_en=manifiesto["exportado_en"] if ok else None)
            if not ok:
                raise ExportacionFallida(f"Se copió pero la comprobación falló: {motivo}. Vuelve a exportar.")
            resultado[pl] = {"ruta": str(sub / f"{nombre}.mp4"), "estado": "exportado (hash comprobado)"}
            db.evento(con, tid, "exportado", v["n"], pl)
            _revisar(dia, nombre, g, p, v, pl)
    except ExportacionFallida:
        raise
    except OSError as e:
        raise ExportacionFallida(f"No se pudo escribir en la carpeta del Mac ({e.strerror or e}). "
                                 "Revisa los permisos o la ruta en config.yaml (fabrica.carpeta_base) y vuelve a exportar.") from e
    return resultado


def _revisar(dia: Path, nombre: str, g: dict, p: dict, v: dict, pl: str) -> None:
    rev = dia / "_revisar.md"
    if not rev.exists():
        rev.write_text(f"# Revisar antes de publicar · {dia.name}\n\nVe cada vídeo una vez entero y marca la lista.\n",
                       encoding="utf-8")
    q = (v.get("calidad") or {}).get(pl, {})
    estado = "✅ calidad OK" if q.get("ok") else "🔴 REVISAR: " + "; ".join(q.get("fallos", []))
    afirm = [f"  - [{a['etiqueta']}] {a['texto']} ({a['fuente']}, {a['fecha']})"
             for e in g["escenas"] for a in (e.get("afirmaciones") or [])]
    with rev.open("a", encoding="utf-8") as f:
        f.write("\n".join([f"\n## {nombre} · {CARPETAS[pl]} (versión {v['n']})",
                           f"Formato {g['formato']} · {g['variante']} · Etiqueta en pantalla: **{p['etiqueta']}** · {estado}",
                           "Afirmaciones:", *afirm,
                           "- [ ] Los datos coinciden con las fuentes y el RUMOR se dice como rumor",
                           "- [ ] El título cumple lo que promete",
                           "- [ ] Sin spoilers del final ni de giros de la historia",
                           "- [ ] Etiqueta de contenido con IA activada al subir"]) + "\n")


def marcar_subido(con, tid: str, plataforma: str, url: str) -> None:
    v = db.version(con, f"{tid}-v{db.aprobaciones(con, tid)['video']['version_n']}")
    e = db.exportaciones(con, v["id"]).get(plataforma)
    if not e:
        raise ExportacionFallida("Esa plataforma no está exportada todavía.")
    ruta = Path(e["ruta"])
    subidos = ruta.parent / "subidos"
    subidos.mkdir(exist_ok=True)
    for f in ruta.parent.glob(e["nombre"] + "*"):
        if f.is_file():
            shutil.move(str(f), subidos / f.name)
    man = subidos / f"{e['nombre']}.manifiesto.json"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        m.update({"publicado": True, "url": url})
        man.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.guardar_exportacion(con, v["id"], plataforma, ruta=str(subidos / ruta.name), manifiesto_ruta=str(man),
                           subida_en=ahora, url=url)
    db.evento(con, tid, "publicado", v["n"], plataforma)

"""Control de calidad básico (plan v2, H2): imagen, duración, volumen, gancho, etiqueta y fuentes.

Los fallos no bloquean la pieza: la marcan en rojo en el Estudio y en _revisar.md, y Javier decide.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from radar.config import cfg

ETIQUETAS = ("CONFIRMADO", "REPORTADO", "RUMOR", "OPINIÓN")


def medir(video: Path) -> dict:
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True, check=True)
    info = json.loads(p.stdout)
    st = (info.get("streams") or [{}])[0]
    out = {"ancho": st.get("width"), "alto": st.get("height"), "duracion": float(info["format"]["duration"])}
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", e.stderr)
    out["lufs"] = float(m[-1]) if m else None
    return out


def revisar(video: Path, guion: dict, plataforma: str) -> dict:
    conf = cfg().get("fabrica", {})
    m = medir(video)
    fallos = []
    if (m["ancho"], m["alto"]) != (1080, 1920):
        fallos.append(f"imagen {m['ancho']}×{m['alto']} (debe ser 1080×1920)")
    dur = conf.get("duraciones", {})
    rango = dur.get("tiktok_larga") if plataforma == "tiktok" and m["duracion"] >= 61 else dur.get(plataforma)
    if rango and not (rango[0] <= m["duracion"] <= rango[1]):
        fallos.append(f"dura {m['duracion']:.0f} s (para {plataforma}: {rango[0]}–{rango[1]} s)")
    objetivo = float(conf.get("volumen_lufs", -14))
    if m["lufs"] is None or abs(m["lufs"] - objetivo) > 2:
        fallos.append(f"volumen {m['lufs']} LUFS (objetivo {objetivo:g})")
    if not (guion.get("gancho") or "").strip():
        fallos.append("sin gancho en el primer segundo")
    if (guion.get("etiqueta") or "").upper() not in ETIQUETAS:
        fallos.append("sin etiqueta CONFIRMADO/REPORTADO/RUMOR/OPINIÓN")
    if not any(str(f.get("url", "")).startswith("http") for f in guion.get("fuentes", [])):
        fallos.append("sin fuente con enlace")
    if guion.get("etiqueta", "").upper() == "RUMOR" and not any("rumor" in ln["texto"].lower() for ln in guion["lineas"]):
        fallos.append("es RUMOR pero la voz no lo dice")
    return {**m, "fallos": fallos, "ok": not fallos}

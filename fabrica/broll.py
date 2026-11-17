"""Vídeo de fondo real (b-roll): Miami y Florida, que es en lo que se inspira Leonida.

Fuentes, por orden:
1. API de Pexels (gratis, licencia que permite uso comercial) si hay PEXELS_API_KEY en .env.
   Los clips se guardan en assets/broll/_pexels/ (fuera de git) con autor, URL y licencia en creditos.json,
   así que nunca se descarga dos veces lo mismo.
2. Tus propios clips en assets/broll/*.mp4.
3. Nada → la pieza usa el fondo gráfico de siempre y se avisa (nunca falla en silencio).

Nunca entra material con «GTA», «Rockstar», «gameplay»… en el título o la URL (config: fabrica.broll.excluir).
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

import requests

from radar.config import ROOT, cfg, env

CARPETA = ROOT / "assets" / "broll"
CACHE = CARPETA / "_pexels"
API = "https://api.pexels.com/videos/search"
LICENCIA = "Pexels License (uso comercial permitido, sin atribución obligatoria)"


def _conf() -> dict:
    return cfg().get("fabrica", {}).get("broll", {}) or {}


def excluido(texto: str) -> bool:
    t = (texto or "").lower()
    return any(p in t for p in _conf().get("excluir", ["gta", "rockstar", "gameplay", "game", "trailer"]))


def _creditos() -> dict:
    f = CACHE / "creditos.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _guardar_creditos(c: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "creditos.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")


def _mejor_archivo(video: dict) -> dict | None:
    """El archivo vertical más cercano a 1080×1920 (sin pasarse mucho de tamaño)."""
    vert = [f for f in video.get("video_files", []) if f.get("height") and f.get("width")
            and f["height"] > f["width"] and f["height"] >= 1280 and f.get("file_type") == "video/mp4"]
    return min(vert, key=lambda f: abs(f["height"] - 1920)) if vert else None


def buscar_pexels(busqueda: str, cuantos: int) -> list[Path]:
    """Descarga (si no están ya) hasta `cuantos` clips verticales para esa búsqueda."""
    clave = env("PEXELS_API_KEY")
    creditos = _creditos()
    ya = [CACHE / f"{vid}.mp4" for vid, c in creditos.items() if c.get("busqueda") == busqueda and (CACHE / f"{vid}.mp4").exists()]
    if len(ya) >= cuantos or not clave:
        return ya[:cuantos]
    r = requests.get(API, params={"query": busqueda, "orientation": "portrait", "size": "medium", "per_page": 15},
                     headers={"Authorization": clave}, timeout=30)
    r.raise_for_status()
    out = list(ya)
    for v in r.json().get("videos", []):
        if len(out) >= cuantos:
            break
        vid = str(v["id"])
        if vid in creditos or excluido(v.get("url", "")) or excluido(busqueda):
            continue
        f = _mejor_archivo(v)
        if not f:
            continue
        CACHE.mkdir(parents=True, exist_ok=True)
        destino = CACHE / f"{vid}.mp4"
        with requests.get(f["link"], stream=True, timeout=120) as d:
            d.raise_for_status()
            with open(destino, "wb") as fh:
                for trozo in d.iter_content(1 << 20):
                    fh.write(trozo)
        creditos[vid] = {"busqueda": busqueda, "autor": (v.get("user") or {}).get("name", ""),
                         "autor_url": (v.get("user") or {}).get("url", ""), "url": v.get("url", ""), "licencia": LICENCIA}
        out.append(destino)
    _guardar_creditos(creditos)
    return out


def credito(clip: Path) -> dict:
    if clip.parent == CACHE:
        return {**_creditos().get(clip.stem, {}), "fuente": "Pexels"}
    return {"fuente": "propio", "archivo": clip.name}


def elegir(n: int, semilla: str, por_escena: list[str | None] | None = None) -> tuple[list[Path], str]:
    """n clips para n tramos. Devuelve (clips, motivo). Lista vacía = usar el fondo gráfico."""
    busquedas = _conf().get("busquedas") or ["Miami beach"]
    rng = random.Random(semilla)  # variación por pieza, pero reproducible
    pedidas = list(por_escena or [None] * n)
    clips: list[Path] = []
    motivo = ""
    if env("PEXELS_API_KEY") or any(CACHE.glob("*.mp4")):
        try:
            pool: dict[str, list[Path]] = {}
            orden = busquedas[:]
            rng.shuffle(orden)
            for i in range(n):
                q = pedidas[i] if i < len(pedidas) and pedidas[i] else orden[i % len(orden)]
                if q not in pool:
                    pool[q] = buscar_pexels(q, 4)
                    rng.shuffle(pool[q])
                if pool[q]:
                    clips.append(pool[q][i % len(pool[q])])
        except requests.RequestException as e:
            motivo = f"Pexels no respondió ({e.__class__.__name__}); "
            clips = []
    if not clips:
        propios = sorted(p for p in CARPETA.glob("*.mp4") if not excluido(p.name))
        if propios:
            rng.shuffle(propios)
            clips = [propios[i % len(propios)] for i in range(n)]
    if not clips:
        return [], motivo + "sin PEXELS_API_KEY ni clips en assets/broll/: se usa el fondo gráfico"
    return clips, motivo + "vídeo real de fondo"


def preparar_fondo(clips: list[Path], duraciones: list[float], salida: Path) -> Path:
    """Une los clips en una pista vertical 1080×1920 de la duración exacta, un poco oscurecida y con un leve zoom."""
    cmd = ["ffmpeg", "-y", "-v", "error"]
    fc = []
    for i, (c, d) in enumerate(zip(clips, duraciones)):
        d = max(0.4, d)
        cmd += ["-stream_loop", "-1", "-t", f"{d:.3f}", "-i", str(c)]
        fc.append(f"[{i}:v]scale=1188:2112:force_original_aspect_ratio=increase,crop=1188:2112,"
                  f"zoompan=z='min(1.0+0.0006*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
                  f"trim=duration={d:.3f},setpts=PTS-STARTPTS,eq=brightness=-0.07:saturation=1.08,setsar=1[c{i}]")
    fc.append("".join(f"[c{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[v]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "22", "-pix_fmt", "yuv420p", "-r", "30", str(salida)]
    subprocess.run(cmd, check=True)
    return salida

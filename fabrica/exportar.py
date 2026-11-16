"""Exporta las piezas a la carpeta del día, una subcarpeta por plataforma (plan v2, H1).

~/Movies/Punto de Control/2026-11-19/
├── TikTok/NN_slug.mp4 · NN_slug.txt · NN_slug_portada.jpg
├── YouTube Shorts/NN_slug.mp4 · NN_slug.txt
└── _revisar.md
El mismo número NN en las carpetas es la misma idea.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

from estudio.ideas import slug
from podcast.publicar import HASHTAGS_TIKTOK, HORA
from radar.config import cfg

CARPETAS = {"tiktok": "TikTok", "shorts": "YouTube Shorts"}
AVISO = "Este video usa voces sintéticas. Cada dato lleva su fuente; los rumores se indican como tales."


def carpeta_dia() -> Path:
    base = Path(cfg().get("fabrica", {}).get("carpeta_base", "~/Movies/Punto de Control")).expanduser()
    d = base / datetime.now().strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def siguiente_numero(dia: Path) -> int:
    nums = [int(m.group(1)) for sub in CARPETAS.values() for f in (dia / sub).glob("**/*.mp4")
            if (m := re.match(r"(\d+)_", f.name))]
    return max(nums, default=0) + 1


def _fuentes(g: dict) -> str:
    return "\n".join(f"• {f.get('titulo', '')}: {f['url']}" for f in g.get("fuentes", []) if f.get("url"))


def _txt_tiktok(g: dict) -> str:
    t = g.get("textos", {})
    texto = (t.get("tiktok") or g["gancho"]).strip()
    return (f"TEXTO PARA TIKTOK (copiar y pegar)\n\n{texto} {HASHTAGS_TIKTOK}\n\n"
            f"COMENTARIO FIJADO\n{t.get('comentario_fijado') or '¿Tú qué opinas? Te leo 👇'}\n\n"
            f"ANTES DE PUBLICAR\n- Activa «Contenido generado por IA» (voces sintéticas).\n- Mejor hora: {HORA}.\n\n"
            f"FUENTES (para responder dudas)\n{_fuentes(g)}\n")


def _txt_shorts(g: dict) -> str:
    t = g.get("textos", {})
    titulo = (t.get("youtube_titulo") or g["titulo"]).strip()
    if "gta 6" not in titulo.lower() and "gta vi" not in titulo.lower():
        titulo = f"GTA 6: {titulo}"
    titulo = titulo[:90] + ("" if "#shorts" in titulo.lower() else " #Shorts")
    desc = (t.get("youtube_descripcion") or g["titulo"]).strip()
    return (f"TÍTULO\n{titulo}\n\nDESCRIPCIÓN\n{desc}\n\nFuentes:\n{_fuentes(g)}\n\n{AVISO}\n\n#GTA6 #Shorts\n\n"
            f"COMENTARIO FIJADO\n{t.get('comentario_fijado') or '¿Tú qué opinas?'}\n\n"
            f"ANTES DE PUBLICAR\n- Marca «Contenido alterado o sintético» en YouTube Studio.\n- Mejor hora: {HORA}.\n")


def exportar(video: Path, portada: Path, g: dict, plataformas: list[str], calidad: dict[str, dict], encargo: str) -> dict:
    """Copia el vídeo a cada plataforma con su .txt y añade la pieza a _revisar.md. Devuelve {plataforma: ruta}."""
    dia = carpeta_dia()
    nn = f"{siguiente_numero(dia):02d}_{slug(g['titulo'], 36)}"
    rutas = {}
    for p in plataformas:
        sub = dia / CARPETAS[p]
        sub.mkdir(exist_ok=True)
        dst = sub / f"{nn}.mp4"
        shutil.copy2(video, dst)
        (sub / f"{nn}.txt").write_text(_txt_tiktok(g) if p == "tiktok" else _txt_shorts(g), encoding="utf-8")
        if p == "tiktok":
            shutil.copy2(portada, sub / f"{nn}_portada.jpg")
        rutas[p] = dst
    # checklist del día
    rev = dia / "_revisar.md"
    if not rev.exists():
        rev.write_text(f"# Revisar antes de publicar · {dia.name}\n\nVe cada vídeo una vez entero y marca la lista.\n",
                       encoding="utf-8")
    lineas = [f"\n## {nn} — {g['titulo']}  (encargo {encargo})",
              f"Formato: {g['formato']} · Etiqueta: **{g['etiqueta']}**" + (f" · Veredicto: {g['veredicto']}" if g.get("veredicto") else "")]
    for p, q in calidad.items():
        estado = "✅ calidad OK" if q["ok"] else "🔴 REVISAR: " + "; ".join(q["fallos"])
        lineas.append(f"- {CARPETAS[p]}: {q['duracion']:.0f} s · {q['lufs']} LUFS · {estado}")
    lineas += ["- [ ] Los datos coinciden con las fuentes y el RUMOR se dice como rumor",
               "- [ ] El título cumple lo que promete",
               "- [ ] Sin spoilers del final ni de giros de la historia",
               "- [ ] Etiqueta de contenido con IA activada al subir",
               "Fuentes:", _fuentes(g)]
    with rev.open("a", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    return rutas

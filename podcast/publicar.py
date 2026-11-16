"""Pack para publicar: deja en output/<fecha>/publicar/ cada vídeo con el nombre de su plataforma
y un publicar.md con los textos listos para copiar y pegar en YouTube y TikTok.

TikTok no permite subir por API sin auditoría, así que esos vídeos se suben a mano (1 minuto cada uno).
"""
from __future__ import annotations

import shutil
from pathlib import Path

HASHTAGS_TIKTOK = "#GTA6 #GTAVI #GrandTheftAutoVI #videojuegos #gamer"
HORA = "18:00–20:00 hora de Ciudad de México (01:00–03:00 en España): la tarde-noche de Latinoamérica"


def pieza(tipo: str, video: Path, titulo: str, descripcion: str, etiquetas: list[str] | None = None,
          miniatura: Path | None = None, gancho: str = "") -> dict:
    """Describe un vídeo del pack. tipo: 'episodio' (horizontal) o 'short' (vertical)."""
    return {"tipo": tipo, "video": video, "titulo": titulo, "descripcion": descripcion,
            "etiquetas": etiquetas or [], "miniatura": miniatura, "gancho": gancho}


def _texto_tiktok(p: dict) -> str:
    # TikTok: texto corto que engancha + 3-5 hashtags (más hashtags no ayudan)
    base = (p["gancho"] or p["titulo"]).replace("#Shorts", "").strip()
    return f"{base} 👀 ¿Tú qué opinas? {HASHTAGS_TIKTOK}"


def crear_pack(work: Path, piezas: list[dict], aviso_sintetico: str) -> Path:
    out = work / "publicar"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    md = ["# Pack para publicar", "",
          f"**Mejor hora para publicar:** {HORA}. En YouTube Studio y en TikTok puedes programarlo.", "",
          "**Antes de publicar:** revisa que los datos marcados como RUMOR se digan como rumor y que el título no prometa "
          "algo que el vídeo no cuenta.", ""]
    n_short = 0
    for p in piezas:
        if p["tipo"] == "episodio":
            dst = out / "youtube_episodio.mp4"
            shutil.copy2(p["video"], dst)
            md += ["---", "## 🎙️ Episodio (YouTube, horizontal)", f"Archivo: `{dst.name}`"]
            if p.get("miniatura") and Path(p["miniatura"]).exists():
                shutil.copy2(p["miniatura"], out / "youtube_miniatura.jpg")
                md.append("Miniatura: `youtube_miniatura.jpg`")
            md += ["", "**Título**", "```", p["titulo"], "```", "**Descripción**", "```", p["descripcion"], "```",
                   "**Etiquetas**", "```", ", ".join(p["etiquetas"]), "```", ""]
            continue
        n_short += 1
        yt, tk = out / f"youtube_short_{n_short}.mp4", out / f"tiktok_{n_short}.mp4"
        shutil.copy2(p["video"], yt)
        shutil.copy2(p["video"], tk)
        titulo_yt = p["titulo"] if "#Shorts" in p["titulo"] else f"{p['titulo'][:90]} #Shorts"
        md += ["---", f"## 📱 Short {n_short}", f"Archivos: `{yt.name}` (YouTube Shorts) · `{tk.name}` (TikTok)", "",
               "### YouTube Shorts", "**Título**", "```", titulo_yt, "```", "**Descripción**", "```", p["descripcion"],
               "```", "### TikTok", "**Texto**", "```", _texto_tiktok(p), "```",
               "Activa en TikTok **«Contenido generado por IA»** (voces sintéticas) antes de publicar.", ""]
    md += ["---", "**Aviso de contenido sintético** (ya incluido en las descripciones de YouTube):", "", aviso_sintetico, ""]
    (out / "publicar.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  [pack] {out} · {n_short} Shorts listos para YouTube y TikTok")
    return out

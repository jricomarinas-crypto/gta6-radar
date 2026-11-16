"""Los 3 formatos de lanzamiento (plan v2, H2): fotogramas verticales 1080×1920 y montaje.

1  Lista por país   → filas «país → valor»; la fila de la que se habla se resalta.
2  Verdad o bulo    → la afirmación y un sello VERDAD / BULO / A MEDIAS que aparece al revelarlo.
11 Última hora      → franja roja «ÚLTIMA HORA» + tarjeta con la etiqueta y la fuente.

Zona segura: el texto importante va entre x=60 y x=940 (a la derecha están los botones de TikTok)
y por encima de y≈1450 (abajo va el texto de la publicación).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

from podcast import render
from podcast.render import (CYAN, F_BLACK, F_BOLD, F_REG, GOLD, PINK, STATUS, base_background, fit, font, pill, rgb,
                            rounded, text_h)
from radar.config import cfg

W, H = 1080, 1920
X0, X1 = 60, 940                      # zona segura horizontal
BODY = (X0, 540, X1, 1170)            # zona del contenido de cada formato
WAVE = (140, 1468, 800, 60)
VEREDICTOS = {"VERDAD": "#22C55E", "BULO": "#EF4444", "A MEDIAS": "#F59E0B", "SIN CONFIRMAR": "#A1A1AA"}
RED = "#EF4444"
_FONDO = None


def _fondo() -> Image.Image:
    global _FONDO
    if _FONDO is None:
        _FONDO = base_background(W, H, sun_alpha=0.22)
    return _FONDO.copy()


def _cabecera(img, guion: dict) -> None:
    d = ImageDraw.Draw(img)
    d.text((X0, 80), cfg()["canal"]["nombre"], font=font(F_BLACK, 34), fill=(255, 255, 255, 235))
    x = X0
    _, _, x, _ = pill(img, (x, 150), "GTA 6", font(F_BOLD, 26), (255, 255, 255, 255), rgb(PINK, 210), pad=(16, 8))
    st = (guion.get("etiqueta") or "").upper()
    if st:
        col = STATUS.get(st, "#A1A1AA")
        pill(img, (x + 12, 150), "● " + st, font(F_BOLD, 26), rgb(col), rgb(col, 46), pad=(16, 8), outline=rgb(col, 140))
    f, lines = fit(d, (guion.get("gancho") or guion.get("titulo", "")).upper(), F_BLACK, X1 - X0, 3, 100, 62)
    y = 236
    for i, ln in enumerate(lines):
        col = rgb(GOLD) if i == len(lines) - 1 and len(lines) > 1 else (255, 255, 255, 255)
        d.text((X0, y), ln, font=f, fill=col, stroke_width=5, stroke_fill=(0, 0, 0, 255))
        y += int(text_h(f) * 0.98)


def _hablante(img, speaker: str) -> None:
    host = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}[speaker]
    pill(img, (X0, 1215), f"{host['nombre'].upper()} · {host['rol']}", font(F_BOLD, 28), (255, 255, 255, 255),
         rgb(host["color"], 200), pad=(18, 9))


def _caja(img, box, fill=(12, 12, 22, 215), outline=(255, 255, 255, 34)):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rounded(ImageDraw.Draw(layer), box, 28, fill=fill, outline=outline, width=2)
    img.alpha_composite(layer)


# ------------------------------------------------------------------ 1 · lista por país
def _lista(img, guion: dict, activo: int | None) -> None:
    items = guion.get("lista") or []
    x0, y0, x1, y1 = BODY
    _caja(img, BODY)
    d = ImageDraw.Draw(img)
    nota = (guion.get("nota") or "").strip()      # p. ej. «Hora del centro de México»
    if nota:
        d.text((x0 + 40, y1 - 30), nota, font=font(F_BOLD, 26), fill=(161, 161, 176, 255), anchor="lb")
        y1 -= 50
    n = max(1, len(items))
    pad = 26
    row = min(118, (y1 - y0 - 2 * pad) // n)
    fs = max(30, min(48, int(row * 0.42)))
    for i, it in enumerate(items):
        ry = y0 + pad + i * row
        on = activo == i
        if on:
            _caja(img, (x0 + 14, ry + 4, x1 - 14, ry + row - 4), fill=rgb(CYAN, 60), outline=rgb(CYAN, 200))
            d = ImageDraw.Draw(img)
        a = 255 if on or activo is None else 150
        fn = font(F_BLACK if on else F_BOLD, fs + (4 if on else 0))
        fv = font(F_BLACK, fs + (4 if on else 0))
        cy = ry + row / 2
        nombre = (it.get("nombre") or "")[:22]
        valor = (it.get("valor") or "")[:20]
        d.text((x0 + 40, cy), nombre, font=fn, fill=(255, 255, 255, a), anchor="lm")
        d.text((x1 - 40, cy), valor, font=fv, fill=rgb(GOLD, a) if on else (220, 220, 232, a), anchor="rm")
        if i < len(items) - 1 and not on and activo != i + 1:
            d.line([(x0 + 40, ry + row), (x1 - 40, ry + row)], fill=(255, 255, 255, 28), width=2)


# ------------------------------------------------------------------ 2 · verdad o bulo
def _verdad_bulo(img, guion: dict, revelado: bool) -> None:
    x0, y0, x1, y1 = BODY
    _caja(img, BODY)
    d = ImageDraw.Draw(img)
    d.text((x0 + 44, y0 + 40), "¿VERDAD O BULO?", font=font(F_BLACK, 36), fill=rgb(GOLD))
    f, lines = fit(d, f"«{guion.get('afirmacion', '')}»", F_BLACK, x1 - x0 - 88, 4, 64, 40)
    y = y0 + 110
    for ln in lines:
        d.text((x0 + 44, y), ln, font=f, fill=(255, 255, 255, 255))
        y += int(text_h(f) * 1.0)
    fuente = (guion.get("fuente") or "").strip()
    if fuente:
        d.text((x0 + 44, y1 - 36), "Fuente: " + fuente, font=font(F_REG, 26), fill=(161, 161, 176, 255), anchor="lb")
    if not revelado:
        d.text(((x0 + x1) / 2, y1 - 140), "?", font=font(F_BLACK, 150), fill=(255, 255, 255, 60), anchor="mm")
        return
    v = (guion.get("veredicto") or "SIN CONFIRMAR").upper()
    col = VEREDICTOS.get(v, "#A1A1AA")
    sello = Image.new("RGBA", (760, 220), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sello)
    rounded(sd, (10, 10, 750, 210), 26, fill=rgb(col, 70), outline=rgb(col), width=10)
    fs, sl = fit(sd, v, F_BLACK, 680, 1, 130, 60)
    sd.text((380, 112), sl[0], font=fs, fill=rgb(col), anchor="mm")
    sello = sello.rotate(-8, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(sello, (int((x0 + x1) / 2 - sello.width / 2), int(y1 - 175 - sello.height / 2)))


# ------------------------------------------------------------------ 11 · última hora
def _ultima_hora(img, guion: dict) -> None:
    x0, y0, x1, _ = BODY
    banda = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rounded(ImageDraw.Draw(banda), (x0, y0, x1, y0 + 96), 22, fill=rgb(RED, 235))
    img.alpha_composite(banda)
    d = ImageDraw.Draw(img)
    d.text((x0 + 36, y0 + 48), "● ÚLTIMA HORA", font=font(F_BLACK, 46), fill=(255, 255, 255, 255), anchor="lm")
    hora = guion.get("hora") or datetime.now().strftime("%d/%m")
    d.text((x1 - 36, y0 + 48), hora, font=font(F_BOLD, 32), fill=(255, 255, 255, 230), anchor="rm")
    card = {"estado": guion.get("etiqueta", ""), "titular": guion.get("titular", ""), "detalle": guion.get("detalle", ""),
            "fuente": guion.get("fuente", "")}
    render._fact_card(img, (x0, y0 + 124, x1, BODY[3]), card, max_head_lines=3, head_size=74, detail_size=36)


# ------------------------------------------------------------------ fotograma y montaje
def fotograma(guion: dict, speaker: str, item: int | None = None, revelado: bool = False) -> Image.Image:
    img = _fondo()
    _cabecera(img, guion)
    f = guion["formato"]
    if f == "lista_pais":
        _lista(img, guion, item)
    elif f == "verdad_bulo":
        _verdad_bulo(img, guion, revelado)
    else:
        _ultima_hora(img, guion)
    _hablante(img, speaker)
    return img.convert("RGB")


def _revela_desde(guion: dict) -> int:
    lineas = guion["lineas"]
    for i, ln in enumerate(lineas):
        if ln.get("revela"):
            return i
    return len(lineas) // 2


def montar(guion: dict, lines: list[dict], audio: Path, total: float, workdir: Path) -> tuple[Path, Path]:
    """lines: las de tts.build_timeline (en el mismo orden que guion['lineas']). Devuelve (vídeo, portada)."""
    workdir.mkdir(parents=True, exist_ok=True)
    revela = _revela_desde(guion)
    cache, items, prev = {}, [], 0.0
    for i, ln in enumerate(lines):
        src = guion["lineas"][i]
        item = src.get("item") if isinstance(src.get("item"), int) else None
        key = (ln["speaker"], item, i >= revela)
        if key not in cache:
            p = workdir / f"f{len(cache):02d}.png"
            fotograma(guion, ln["speaker"], item, i >= revela).save(p)
            cache[key] = p
        end = lines[i + 1]["start"] if i + 1 < len(lines) else total
        items.append((cache[key], end - prev))
        prev = end
    portada = workdir / "portada.jpg"
    fotograma(guion, lines[0]["speaker"], None, False).save(portada, quality=92)
    ass = render.write_ass(lines, workdir / "subs.ass", W, H, 78, 480, 100, 3, True)
    lufs = float(cfg().get("fabrica", {}).get("volumen_lufs", -14))
    out = workdir / "video.mp4"
    bar = {"verdad_bulo": GOLD, "ultima_hora": RED}.get(guion["formato"], CYAN)
    render.ffmpeg_compose(items, audio, ass, out, W, H, WAVE, total, bar_color=bar, fade=True, lufs=lufs)
    return out, portada

"""Montaje de vídeo: fotogramas con Pillow + FFmpeg (ondas de audio, subtítulos palabra a palabra, barra de progreso)."""
from __future__ import annotations

import math
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from radar.config import ROOT, cfg

FONTS = ROOT / "assets" / "fonts"
F_BLACK, F_XBOLD = FONTS / "InterDisplay-Black.otf", FONTS / "InterDisplay-ExtraBold.otf"
F_BOLD, F_SEMI, F_MED, F_REG = (FONTS / f"Inter-{w}.otf" for w in ("Bold", "SemiBold", "Medium", "Regular"))
STATUS = {"CONFIRMADO": "#22C55E", "REPORTADO": "#3B82F6", "RUMOR": "#F59E0B", "OPINIÓN": "#A1A1AA", "HOY": "#FF3D8B"}
PINK, CYAN, GOLD = "#FF3D8B", "#19D3DA", "#FFD23F"


# ------------------------------------------------------------------ utilidades de dibujo
@lru_cache(maxsize=256)
def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def rgb(h: str, a: int = 255) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def wrap(draw, text, fnt, max_w) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, path, max_w, max_lines, size, min_size):
    while True:
        f = font(path, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines or size <= min_size:
            return f, lines[:max_lines]
        size -= 4


def text_h(f) -> int:
    a, d = f.getmetrics()
    return a + d


def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def pill(img, xy, text, fnt, fg, bg, pad=(18, 9), anchor="l", outline=None):
    d = ImageDraw.Draw(img)
    tw = d.textlength(text, font=fnt)
    a, de = fnt.getmetrics()
    w, h = tw + 2 * pad[0], a + de + 2 * pad[1] - 6
    x, y = xy
    if anchor == "c":
        x -= w / 2
    elif anchor == "r":
        x -= w
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    rounded(ld, (x, y, x + w, y + h), h / 2, fill=bg, outline=outline, width=2 if outline else 1)
    ld.text((x + pad[0], y + pad[1] - 4), text, font=fnt, fill=fg)
    img.alpha_composite(layer)
    return x, y, x + w, y + h


# ------------------------------------------------------------------ fondo
@lru_cache(maxsize=4)
def base_background(w: int, h: int, sun_alpha: float = 0.30) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    top, bot = rgb("#07070F"), rgb("#1A0A2B")
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    # sol synthwave
    horizon = int(h * (0.70 if w > h else 0.62))
    r = int(min(w, h) * (0.36 if w > h else 0.42))
    cx = w // 2
    sun = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sun)
    c1, c2 = rgb("#FFB347"), rgb(PINK)
    for yy in range(horizon - r, horizon + 1):
        t = (yy - (horizon - r)) / max(r, 1)
        dx = int(math.sqrt(max(0, r * r - (yy - horizon) ** 2)))
        col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (int(255 * sun_alpha),)
        band = (yy - (horizon - r)) / r
        if band > 0.45 and int((yy - horizon) / (6 + 10 * band)) % 2 == 0:
            continue  # franjas
        sd.line([(cx - dx, yy), (cx + dx, yy)], fill=col)
    glow = sun.filter(ImageFilter.GaussianBlur(60))
    img.alpha_composite(glow)
    img.alpha_composite(sun)
    # rejilla en perspectiva
    grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    gcol = rgb(PINK, 70)
    for i in range(-14, 15):
        gd.line([(cx + i * w * 0.012, horizon), (cx + i * w * 0.16, h)], fill=gcol, width=2)
    y, step = horizon, 6
    while y < h:
        gd.line([(0, y), (w, y)], fill=gcol, width=2)
        step *= 1.32
        y += step
    img.alpha_composite(grid)
    # viñeta
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse((-w * 0.25, -h * 0.35, w * 1.25, h * 1.25), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 170))
    dark.putalpha(Image.eval(vig, lambda v: 170 - int(v * 170 / 255)))
    img.alpha_composite(dark)
    return img


# ------------------------------------------------------------------ avatares
@lru_cache(maxsize=16)
def avatar(host_id: str, size: int, active: bool) -> Image.Image:
    host = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}[host_id]
    col = rgb(host["color"])
    pad = 40
    S = size + 2 * pad
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    pic_path = ROOT / host.get("avatar", "")
    if host.get("avatar") and pic_path.exists():
        pic = Image.open(pic_path).convert("RGBA")
        side = min(pic.size)
        pic = pic.crop(((pic.width - side) // 2, (pic.height - side) // 2, (pic.width + side) // 2,
                        (pic.height + side) // 2)).resize((size, size), Image.LANCZOS)
    else:
        pic = Image.new("RGBA", (size, size))
        pd = ImageDraw.Draw(pic)
        dark = tuple(int(c * 0.35) for c in col[:3])
        for y in range(size):
            t = y / size
            pd.line([(0, y), (size, y)], fill=tuple(int(col[i] * (1 - t) + dark[i] * t) for i in range(3)) + (255,))
        f = font(F_BLACK, int(size * 0.5))
        pd.text((size / 2, size / 2 + size * 0.02), host["nombre"][0].upper(), font=f, fill=(255, 255, 255, 240), anchor="mm")
    out.paste(pic, (pad, pad), mask)
    d = ImageDraw.Draw(out)
    if active:
        ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((pad - 10, pad - 10, pad + size + 10, pad + size + 10), outline=col, width=10)
        out.alpha_composite(ring.filter(ImageFilter.GaussianBlur(14)))
        out.alpha_composite(ring)
    else:
        d.ellipse((pad - 4, pad - 4, pad + size + 4, pad + size + 4), outline=(255, 255, 255, 60), width=3)
        r_, g_, b_, a_ = out.split()
        dim = lambda ch: ch.point(lambda v: int(v * 0.42))  # noqa: E731 — oscurece sin transparentar
        out = Image.merge("RGBA", (dim(r_), dim(g_), dim(b_), a_))
    return out


def _host_block(img, host, cx, cy, size, active, name_size=36, show_live=True):
    av = avatar(host["id"], size, active)
    img.alpha_composite(av, (int(cx - av.width / 2), int(cy - av.height / 2)))
    d = ImageDraw.Draw(img)
    y = cy + size / 2 + 22
    a = 255 if active else 140
    d.text((cx, y), host["nombre"], font=font(F_BLACK, name_size), fill=(255, 255, 255, a), anchor="mt")
    d.text((cx, y + name_size + 8), host["rol"], font=font(F_SEMI, int(name_size * 0.6)), fill=(200, 200, 215, a), anchor="mt")
    if active and show_live:
        pill(img, (cx, y + name_size + 8 + name_size * 0.6 + 18), "● AL AIRE", font(F_BOLD, int(name_size * 0.55)),
             (255, 255, 255, 255), rgb(host["color"], 210), pad=(14, 8), anchor="c")


def _fact_card(img, box, card: dict, max_head_lines=2, head_size=70, detail_size=34):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    rounded(ld, box, 30, fill=(12, 12, 22, 215), outline=(255, 255, 255, 34), width=2)
    img.alpha_composite(layer)
    d = ImageDraw.Draw(img)
    pad, inner = 44, x1 - x0 - 88
    st = (card.get("estado") or "").upper().strip()
    head = (card.get("titular") or "").strip()
    det = (card.get("detalle") or "").strip()
    src = (card.get("fuente") or "").strip()
    y = y0 + pad - 6
    if st:
        col = STATUS.get(st, "#A1A1AA")
        _, _, _, by = pill(img, (x0 + pad, y), ("● " + st), font(F_BOLD, 24), rgb(col), rgb(col, 46), pad=(16, 8),
                           outline=rgb(col, 140))
        y = by + 16
    bottom = y1 - pad - (40 if src else 0)
    avail = bottom - y
    # busca el tamaño mayor en el que titular + detalle caben sin pisar la fuente
    for hs in range(head_size, 35, -4):
        fh = font(F_BLACK, hs)
        hl = wrap(d, head, fh, inner) if head else []
        if len(hl) > max_head_lines:
            continue
        ds = min(detail_size, max(24, int(hs * 0.5)))
        fd = font(F_MED, ds)
        dl = wrap(d, det, fd, inner)[:2] if det else []
        hh = int(text_h(fh) * 0.98) * len(hl)
        dh = int(text_h(fd) * 1.05) * len(dl)
        if hh + (8 if dl else 0) + dh <= avail:
            break
        if hs <= 40 and len(dl) > 1:
            dl = dl[:1]
            break
    for ln in hl:
        d.text((x0 + pad, y), ln, font=fh, fill=(255, 255, 255, 255))
        y += int(text_h(fh) * 0.98)
    y += 8
    for ln in dl:
        d.text((x0 + pad, y), ln, font=fd, fill=(212, 212, 222, 255))
        y += int(text_h(fd) * 1.05)
    if src:
        d.text((x0 + pad, y1 - pad + 4), "Fuente: " + src, font=font(F_REG, 24), fill=(161, 161, 176, 255), anchor="lb")


# ------------------------------------------------------------------ fotogramas
def frame_horizontal(meta: dict, seg: dict, speaker: str, seg_idx: int) -> Image.Image:
    W, H = 1920, 1080
    img = base_background(W, H).copy()
    d = ImageDraw.Draw(img)
    ch = cfg()["canal"]
    d.text((64, 44), ch["nombre"], font=font(F_BLACK, 40), fill=(255, 255, 255, 255))
    d.text((66, 94), ch["subtitulo"], font=font(F_SEMI, 22), fill=(200, 190, 235, 255))
    pill(img, (1856, 48), meta["badge"], font(F_BOLD, 22), (255, 255, 255, 255), (255, 255, 255, 26), anchor="r",
         outline=(255, 255, 255, 50))
    chapter = (seg.get("capitulo") or "").upper() if seg_idx > 0 else "HOY EN EL PODCAST"
    pill(img, (W / 2, 140), chapter, font(F_XBOLD, 32), (255, 255, 255, 255), rgb(PINK, 60), pad=(26, 12), anchor="c",
         outline=rgb(PINK, 170))
    card = dict(seg.get("tarjeta") or {})
    if seg_idx == 0:
        card = {"titular": meta["title"], "detalle": card.get("detalle") or card.get("titular", ""), "estado": "HOY",
                "fuente": card.get("fuente", "")}
    _fact_card(img, (380, 228, 1540, 588), card)
    hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
    _host_block(img, hosts["A"], 190, 400, 210, speaker == "A")
    _host_block(img, hosts["B"], 1730, 400, 210, speaker == "B")
    return img.convert("RGB")


def frame_vertical(meta: dict, seg: dict, speaker: str, hook: str) -> Image.Image:
    W, H = 1080, 1920
    img = base_background(W, H).copy()
    d = ImageDraw.Draw(img)
    ch = cfg()["canal"]
    d.text((W / 2, 96), ch["nombre"], font=font(F_BLACK, 36), fill=(255, 255, 255, 230), anchor="mt")
    pill(img, (W / 2, 150), "GTA 6", font(F_BOLD, 26), (255, 255, 255, 255), rgb(PINK, 200), pad=(18, 8), anchor="c")
    f, lines = fit(d, hook.upper(), F_BLACK, 960, 3, 104, 64)
    y = 240
    for i, ln in enumerate(lines):
        col = rgb(GOLD) if i == len(lines) - 1 and len(lines) > 1 else (255, 255, 255, 255)
        d.text((W / 2, y), ln, font=f, fill=col, anchor="mt", stroke_width=5, stroke_fill=(0, 0, 0, 255))
        y += int(text_h(f) * 0.98)
    _fact_card(img, (60, 640, 1020, 990), seg.get("tarjeta") or {}, max_head_lines=2, head_size=62, detail_size=32)
    hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
    _host_block(img, hosts["A"], 330, 1150, 180, speaker == "A", name_size=32, show_live=False)
    _host_block(img, hosts["B"], 750, 1150, 180, speaker == "B", name_size=32, show_live=False)
    d.text((W / 2, 1790), meta.get("pie") or "Episodio completo en el canal  ▶", font=font(F_BOLD, 32), fill=(220, 220, 235, 230), anchor="mt")
    return img.convert("RGB")


def thumbnail(meta: dict, ep: dict, out: Path) -> Path:
    W, H = 1280, 720
    img = base_background(W, H, sun_alpha=0.55).copy()
    d = ImageDraw.Draw(img)
    hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
    a = avatar("A", 250, True)
    b = avatar("B", 250, True)
    img.alpha_composite(b, (W - b.width + 10, 250))
    img.alpha_composite(a, (W - a.width - 230, 300))
    pill(img, (48, 44), "GTA 6", font(F_BLACK, 38), (255, 255, 255, 255), rgb(PINK, 235), pad=(22, 10))
    txt = (ep.get("titulo_miniatura") or ep["titulo"]).upper()
    f, lines = fit(d, txt, F_BLACK, 760, 3, 136, 72)
    y = 140
    for i, ln in enumerate(lines):
        col = rgb(GOLD) if i == len(lines) - 1 and len(lines) > 1 else (255, 255, 255, 255)
        d.text((52, y), ln, font=f, fill=col, stroke_width=8, stroke_fill=(0, 0, 0, 255))
        y += int(text_h(f) * 0.95)
    sub = (ep.get("subtitulo_miniatura") or "").strip()
    if sub:
        pill(img, (52, y + 18), sub, font(F_BOLD, 38), (15, 15, 25, 255), rgb(CYAN, 240), pad=(20, 10))
    d.text((52, H - 40), cfg()["canal"]["nombre"], font=font(F_BLACK, 30), fill=(255, 255, 255, 220), anchor="lb")
    _ = hosts
    img.convert("RGB").save(out, quality=92)
    return out


# ------------------------------------------------------------------ subtítulos ASS
def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t - h * 3600 - m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_color(hexc: str) -> str:
    r, g, b, _ = rgb(hexc)
    return f"&H00{b:02X}{g:02X}{r:02X}&"


def write_ass(lines: list[dict], path: Path, W: int, H: int, size: int, margin_v: int, margin_lr: int,
              max_words: int, upper: bool, offset: float = 0.0, t0: float = 0.0, t1: float = 1e9):
    hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Inter Display Black,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,{max(3, size // 16)},2,2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for ln in lines:
        words = [(w, s, e) for w, s, e in ln["abs_words"] if s >= t0 - 0.01 and e <= t1 + 0.5]
        if not words:
            continue
        hi = _ass_color(hosts[ln["speaker"]]["color"])
        chunks, cur = [], []
        for w in words:
            cur.append(w)
            if len(cur) >= max_words or (len(cur) >= 3 and w[0][-1:] in ".,;:?!…"):
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        for ci, ch in enumerate(chunks):
            nxt = chunks[ci + 1][0][1] if ci + 1 < len(chunks) else ch[-1][2] + 0.35
            for wi, (w, s, e) in enumerate(ch):
                start = ch[0][1] if wi == 0 else s
                end = ch[wi + 1][1] if wi + 1 < len(ch) else min(nxt, ch[-1][2] + 0.35)
                if end <= start:
                    end = start + 0.05
                parts = []
                for wj, (w2, _, _) in enumerate(ch):
                    t = (w2.upper() if upper else w2).replace("{", "(").replace("}", ")")
                    parts.append(f"{{\\c{hi}}}{t}{{\\c&H00FFFFFF&}}" if wj == wi else t)
                events.append(f"Dialogue: 0,{_ass_time(start - offset)},{_ass_time(end - offset)},Main,,0,0,0,,{' '.join(parts)}")
    path.write_text(head + "\n".join(events) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------ FFmpeg
def _concat_file(items: list[tuple[Path, float]], path: Path) -> Path:
    out = []
    for p, dur in items:
        out.append(f"file '{p.as_posix()}'\nduration {max(dur, 0.04):.3f}")
    out.append(f"file '{items[-1][0].as_posix()}'")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def ffmpeg_compose(items, audio: Path, ass: Path, out: Path, W: int, H: int, wave_box: tuple, duration: float,
                   bar_color: str = PINK, audio_ss: float = 0.0, fade: bool = False):
    work = out.parent
    lst = _concat_file(items, work / (out.stem + "_frames.txt"))
    music = ROOT / (cfg()["podcast"].get("musica_fondo") or "_none_")
    has_music = music.is_file()
    wx, wy, ww, wh = wave_box
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
    cmd += ["-ss", f"{audio_ss:.3f}", "-t", f"{duration:.3f}", "-i", str(audio)]
    cmd += ["-f", "lavfi", "-i", f"color=c=0x{bar_color.lstrip('#')}:s={W}x8:r=30:d={duration:.3f}"]
    if has_music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
    afade = f",afade=t=in:d=0.25,afade=t=out:st={max(0, duration - 0.6):.2f}:d=0.6" if fade else ""
    fc = [
        "[0:v]fps=30,format=rgba[bg]",
        f"[1:a]aresample=48000{afade},asplit=3[voice][sc][aw]",
        f"[aw]showwaves=s={ww}x{wh}:mode=cline:rate=30:scale=sqrt:draw=full:colors=0xFFFFFF,format=rgba,colorchannelmixer=aa=0.8[wv]",
        f"[bg][wv]overlay={wx}:{wy}[v1]",
        f"[v1]ass='{ass.as_posix()}':fontsdir='{FONTS.as_posix()}'[v2]",
        f"[v2][2:v]overlay=x='-w+w*t/{duration:.3f}':y={H - 8}:shortest=1,format=yuv420p[v]",
    ]
    if has_music:
        db = cfg()["podcast"].get("musica_volumen_db", -24)
        fc += [f"[3:a]aresample=48000,volume={db}dB[mus]",
               "[mus][sc]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=500[duck]",
               "[voice][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=11[a]"]
    else:
        fc += ["[sc]anullsink", "[voice]loudnorm=I=-15:TP=-1.5:LRA=11[a]"]
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out


def render_episode(ep: dict, lines: list[dict], audio: Path, total: float, workdir: Path, meta: dict) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    cache, items = {}, []
    # cada línea muestra su fotograma desde el final de la anterior
    prev_end = 0.0
    for i, ln in enumerate(lines):
        key = (ln["seg"], ln["speaker"])
        if key not in cache:
            p = workdir / f"h_{ln['seg']:02d}_{ln['speaker']}.png"
            frame_horizontal(meta, ep["segmentos"][ln["seg"]], ln["speaker"], ln["seg"]).save(p)
            cache[key] = p
        end = lines[i + 1]["start"] if i + 1 < len(lines) else total
        items.append((cache[key], end - prev_end))
        prev_end = end
    ass = write_ass(lines, workdir / "episodio.ass", 1920, 1080, 58, 200, 300, 7, False)
    out = workdir / "episodio.mp4"
    print("  [vídeo] renderizando episodio…")
    return ffmpeg_compose(items, audio, ass, out, 1920, 1080, (460, 948, 1000, 84), total)


def render_short(ep: dict, lines: list[dict], audio: Path, short: dict, workdir: Path, meta: dict, idx: int) -> Path | None:
    seg_i = short["segmento"]
    seg_lines = [ln for ln in lines if ln["seg"] == seg_i]
    if not seg_lines:
        return None
    maxd = float(cfg()["podcast"].get("shorts_duracion_max", 75))
    t0 = max(0.0, seg_lines[0]["start"] - 0.15)
    kept = [ln for ln in seg_lines if ln["end"] - t0 <= maxd] or seg_lines[:1]
    t1 = kept[-1]["end"] + 0.5
    dur = t1 - t0
    seg = ep["segmentos"][seg_i]
    hook = short.get("gancho") or seg.get("capitulo") or ep["titulo"]
    items, prev = [], t0
    cache = {}
    for i, ln in enumerate(kept):
        if ln["speaker"] not in cache:
            p = workdir / f"v{idx}_{ln['speaker']}.png"
            frame_vertical(meta, seg, ln["speaker"], hook).save(p)
            cache[ln["speaker"]] = p
        end = kept[i + 1]["start"] if i + 1 < len(kept) else t1
        items.append((cache[ln["speaker"]], end - prev))
        prev = end
    ass = write_ass(kept, workdir / f"short{idx}.ass", 1080, 1920, 86, 420, 70, 3, True, offset=t0, t0=t0, t1=t1)
    out = workdir / f"short_{idx + 1}.mp4"
    print(f"  [vídeo] renderizando Short {idx + 1} ({dur:.0f}s)…")
    return ffmpeg_compose(items, audio, ass, out, 1080, 1920, (110, 1565, 860, 110), dur, audio_ss=t0, fade=True)


def chapters(ep: dict, lines: list[dict]) -> str:
    starts = {}
    for ln in lines:
        starts.setdefault(ln["seg"], ln["start"])
    out = []
    for si, seg in enumerate(ep["segmentos"]):
        if si not in starts:
            continue
        t = 0 if si == 0 else int(starts[si] - 0.4)
        name = "Intro" if si == 0 else seg.get("capitulo", f"Parte {si}")
        out.append(f"{t // 60}:{t % 60:02d} {name}")
    return "\n".join(out)

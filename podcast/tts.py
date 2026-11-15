"""Voces: Edge (gratis), ElevenLabs (premium) u offline (espeak, solo pruebas).

Devuelve, por cada línea del guion, un WAV y los tiempos de cada palabra (para subtítulos).
"""
from __future__ import annotations

import asyncio
import base64
import re
import shutil
import subprocess
import wave
from pathlib import Path

import requests

from radar.config import cfg, env

SR = 24000  # Hz, mono


def pronounce(text: str) -> str:
    rep = cfg()["podcast"].get("pronunciacion") or {}
    for k in sorted(rep, key=len, reverse=True):
        text = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", rep[k], text)
    return text


def _to_wav(src: Path, dst: Path) -> float:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(SR),
                    "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                           "silenceremove=start_periods=1:start_threshold=-50dB,areverse",
                    "-c:a", "pcm_s16le", str(dst)], check=True)
    with wave.open(str(dst)) as w:
        return w.getnframes() / w.getframerate()


# ------------------------------------------------------------------ proveedores
async def _edge_async(text, voice, rate, mp3_path):
    import edge_tts

    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                st = chunk["offset"] / 1e7
                words.append((chunk["text"], st, st + chunk["duration"] / 1e7))
    return words


def _edge(text, host, mp3_path):
    voice = host["voz_edge"]
    rate = cfg()["podcast"]["voz"].get("velocidad", "+0%")
    for attempt in range(4):
        try:
            return asyncio.run(_edge_async(text, voice, rate, mp3_path))
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f"  [voz] reintento Edge ({e.__class__.__name__})")
    return []


def _elevenlabs(text, host, mp3_path):
    key = env("ELEVENLABS_API_KEY", required=True)
    vid = host.get("voz_elevenlabs") or ""
    if not vid:
        raise SystemExit(f"Falta voz_elevenlabs para {host['nombre']} en config.yaml")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": text, "model_id": cfg()["podcast"]["voz"].get("elevenlabs_modelo", "eleven_multilingual_v2"),
              "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35}},
        timeout=180)
    r.raise_for_status()
    data = r.json()
    Path(mp3_path).write_bytes(base64.b64decode(data["audio_base64"]))
    al = data.get("alignment") or {}
    chars, starts, ends = al.get("characters", []), al.get("character_start_times_seconds", []), al.get("character_end_times_seconds", [])
    words, cur, ws, last_e = [], "", None, 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append((cur, ws, last_e))
            cur, ws = "", None
            continue
        if not cur:
            ws = s
        cur += ch
        last_e = e
    if cur:
        words.append((cur, ws, last_e))
    return words


def _offline(text, host, out_path):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise SystemExit("Proveedor 'offline' necesita espeak-ng instalado")
    variant = "+m3" if host["id"] == "A" else "+f3"
    subprocess.run([exe, "-v", "es-419" + variant, "-s", "168", "-w", str(out_path), text], check=True,
                   stdout=subprocess.DEVNULL)
    return []


# ------------------------------------------------------------------ alineación
def _align(display: str, tts_words: list, duration: float) -> list[tuple[str, float, float]]:
    """Tiempos para las palabras que se muestran (texto original, no el pronunciado)."""
    disp = display.split()
    if not disp:
        return []
    if tts_words and len(tts_words) == len(disp):
        return [(d, s, e) for d, (_, s, e) in zip(disp, tts_words)]
    start = tts_words[0][1] if tts_words else 0.05
    end = tts_words[-1][2] if tts_words else max(0.1, duration - 0.05)
    end = min(end, duration)
    weights = [len(w) + 2 for w in disp]
    total, t, out = sum(weights), start, []
    for w, wt in zip(disp, weights):
        d = (end - start) * wt / total
        out.append((w, t, t + d))
        t += d
    return out


def synthesize(lines: list[dict], hosts: dict, workdir: Path) -> list[dict]:
    """lines: [{speaker, text, seg}] → añade wav, duration, words (relativos a la línea)."""
    provider = env("VOZ_PROVEEDOR") or cfg()["podcast"]["voz"].get("proveedor", "edge")
    workdir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, ln in enumerate(lines):
        host = hosts[ln["speaker"]]
        say = pronounce(ln["text"])
        raw = workdir / f"l{i:03d}.{'wav' if provider == 'offline' else 'mp3'}"
        wav = workdir / f"l{i:03d}_24k.wav"
        if provider == "edge":
            tw = _edge(say, host, raw)
        elif provider == "elevenlabs":
            tw = _elevenlabs(say, host, raw)
        else:
            tw = _offline(say, host, raw)
        # el recorte de silencios desplaza los tiempos: medimos el silencio inicial antes
        lead = _leading_silence(raw)
        dur = _to_wav(raw, wav)
        tw = [(w, max(0.0, s - lead), max(0.0, e - lead)) for w, s, e in tw]
        out.append({**ln, "wav": str(wav), "duration": dur, "words": _align(ln["text"], tw, dur)})
        print(f"  [voz] {i + 1}/{len(lines)} {host['nombre']}: {dur:.1f}s")
    return out


def _leading_silence(path: Path) -> float:
    p = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "silencedetect=n=-50dB:d=0.02", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"silence_start: (-?[\d.]+)\s*\n.*?silence_end: ([\d.]+)", p.stderr, re.S)
    if m and float(m.group(1)) <= 0.01:
        return float(m.group(2))
    return 0.0


def build_timeline(lines: list[dict], out_wav: Path) -> tuple[list[dict], float]:
    """Une las líneas con pausas naturales. Devuelve líneas con start/end absolutos y la duración total."""
    gaps = []
    for i, ln in enumerate(lines):
        if i == 0:
            gaps.append(0.25)
        elif ln["seg"] != lines[i - 1]["seg"]:
            gaps.append(0.65)
        elif ln["speaker"] != lines[i - 1]["speaker"]:
            gaps.append(0.28)
        else:
            gaps.append(0.15)
    t = 0.0
    with wave.open(str(out_wav), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SR)
        for ln, gap in zip(lines, gaps):
            out.writeframes(b"\x00\x00" * int(gap * SR))
            t += gap
            with wave.open(ln["wav"]) as w:
                frames = w.readframes(w.getnframes())
            out.writeframes(frames)
            ln["start"], ln["end"] = t, t + ln["duration"]
            ln["abs_words"] = [(w, t + s, t + e) for w, s, e in ln["words"]]
            t += ln["duration"]
        tail = 1.2
        out.writeframes(b"\x00\x00" * int(tail * SR))
        t += tail
    return lines, t

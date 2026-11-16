"""Voces de Leo y Sofi con caché: cada frase se genera una sola vez.

Si falla el montaje, al reintentar no se vuelven a pedir las voces. Si cambia una frase del guion,
solo se regenera esa frase. La caché vive en la carpeta de la pieza (output/fabrica/<encargo>/voces/).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from podcast import tts
from radar.config import cfg, env


class FalloVoz(RuntimeError):
    """El proveedor de voz no respondió. Se puede reintentar sin rehacer el guion."""


def _clave(linea: dict, host: dict) -> str:
    voz = cfg()["podcast"]["voz"]
    proveedor = env("VOZ_PROVEEDOR") or voz.get("proveedor", "edge")
    base = json.dumps([linea["text"], host.get("voz_edge"), host.get("voz_elevenlabs"), proveedor,
                       voz.get("velocidad"), cfg()["podcast"].get("pronunciacion")], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def sintetizar(lineas: list[dict], cache: Path) -> list[dict]:
    """lineas: [{seg, speaker, text}] → las mismas con wav, duration y words (como podcast.tts.synthesize)."""
    hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for ln in lineas:
        k = _clave(ln, hosts[ln["speaker"]])
        wav, meta = cache / f"{k}.wav", cache / f"{k}.json"
        if not (wav.exists() and meta.exists()):
            tmp = cache / f"_tmp_{k}"
            try:
                hecho = tts.synthesize([ln], hosts, tmp)[0]
                shutil.copy2(hecho["wav"], wav)
                meta.write_text(json.dumps({"duration": hecho["duration"], "words": hecho["words"]}), encoding="utf-8")
            except (Exception, SystemExit) as e:  # noqa: BLE001 — red, proveedor caído, cuota…
                raise FalloVoz(f"No pudimos generar la voz ({e.__class__.__name__}: {e}). "
                               "Puedes reintentar sin rehacer el guion.") from e
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        m = json.loads(meta.read_text(encoding="utf-8"))
        out.append({**ln, "wav": str(wav), "duration": m["duration"], "words": [tuple(w) for w in m["words"]]})
    return out

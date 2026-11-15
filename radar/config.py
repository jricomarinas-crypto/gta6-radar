"""Carga de configuración (config.yaml) y variables de entorno (.env / Secrets)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DB_PATH = DATA_DIR / "radar.db"


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


@lru_cache(maxsize=1)
def cfg() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, required: bool = False) -> str | None:
    val = os.environ.get(name) or None
    if required and not val:
        raise SystemExit(
            f"Falta la variable {name}. Añádela en GitHub → Settings → Secrets → Actions "
            f"(o en el archivo .env si lo ejecutas en tu ordenador)."
        )
    return val

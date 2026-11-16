"""Rutas del Estudio en un solo sitio.

Las pruebas (tests/) ponen PC_RAIZ_PRUEBAS=/carpeta/temporal y todo se guarda ahí:
así nunca tocan tu base de datos ni tu carpeta de Películas.
"""
from __future__ import annotations

import os
from pathlib import Path

from radar.config import DATA_DIR, OUTPUT_DIR, ROOT, cfg


def _raiz_pruebas() -> Path | None:
    r = os.environ.get("PC_RAIZ_PRUEBAS")
    return Path(r) if r else None


def db_path() -> Path:
    r = _raiz_pruebas()
    return (r / "estudio.db") if r else DATA_DIR / "estudio.db"


def ideas_dir() -> Path:
    r = _raiz_pruebas()
    return (r / "ideas") if r else ROOT / "estudio" / "ideas"


def guiones_dir() -> Path:
    r = _raiz_pruebas()
    return (r / "guiones") if r else ROOT / "estudio" / "guiones"


def trabajo_dir(tid: str) -> Path:
    r = _raiz_pruebas()
    return ((r / "render") if r else OUTPUT_DIR / "fabrica") / tid


def carpeta_base() -> Path:
    r = _raiz_pruebas()
    if r:
        return r / "Punto de Control"
    return Path(cfg().get("fabrica", {}).get("carpeta_base", "~/Movies/Punto de Control")).expanduser()

"""Descarga a tu ordenador la base de datos del Radar (rama "data" del repositorio)
para usar el chat (python -m radar.chat) o abrir el panel en local.

    python tools/descargar_datos.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
(ROOT / "data").mkdir(exist_ok=True)
try:
    subprocess.run(["git", "fetch", "--depth", "1", "origin", "data"], cwd=ROOT, check=True)
    db = subprocess.run(["git", "show", "FETCH_HEAD:data/radar.db"], cwd=ROOT, check=True, capture_output=True).stdout
except subprocess.CalledProcessError:
    sys.exit("No pude descargar la rama 'data'. ¿Se ha ejecutado ya el Radar en GitHub Actions al menos una vez?")
(ROOT / "data" / "radar.db").write_bytes(db)
print(f"✅ Base de datos descargada ({len(db) / 1e6:.1f} MB) en data/radar.db")
subprocess.run([sys.executable, "-m", "radar.run", "--solo-panel"], cwd=ROOT)
print("Abre site/index.html en el navegador para ver el panel, o usa: python -m radar.chat")

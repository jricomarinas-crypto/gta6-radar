"""Muestra un encargo de la Fábrica: la idea, el formato y la plantilla del guion que hay que escribir.

    python -m fabrica.encargo            → lista los encargos que esperan guion
    python -m fabrica.encargo a1b2c3     → detalle de uno

Después de escribir el guion (JSON) en output/guiones/<id>.json:
    python -m fabrica.producir a1b2c3 output/guiones/a1b2c3.json
"""
from __future__ import annotations

import json
import sys

from estudio import db

from .guion import PLANTILLA

REGLAS = """REGLAS DEL GUION
- Contenido 100 % propio: nada copiado de otros creadores ni de Rockstar. Sin spoilers del final ni de giros.
- Cada dato verificado en fuente primaria (Rockstar, PlayStation, Xbox) o medio fiable, con su URL en «fuentes».
- Etiqueta honesta: CONFIRMADO (oficial), REPORTADO (medio fiable), RUMOR (sin verificar, y la voz lo dice), OPINIÓN.
- Estructura: gancho (0-2 s) → promesa (2-5 s) → desarrollo con un giro a mitad → cierre con pregunta.
- 6-10 líneas alternando A (Leo, analista) y B (Sofi, fan). Frases de < 12 palabras. Español neutro latinoamericano.
- Duración objetivo: 25-45 s (unas 70-110 palabras)."""


def main():
    con = db.connect()
    if len(sys.argv) < 2:
        pend = [t for t in db.trabajos(con, 50) if t["estado"] == "esperando_guion"]
        if not pend:
            print("No hay encargos esperando guion.")
        for t in pend:
            print(f"{t['id']}  ·  {t['formato']}  ·  {'+'.join(t['plataformas'])}  ·  {t['idea'].get('titulo')}")
        return
    t = db.trabajo(con, sys.argv[1])
    if not t:
        raise SystemExit(f"No existe el encargo {sys.argv[1]}")
    print(f"ENCARGO {t['id']} · estado: {t['estado']}")
    print(f"Idea: {t['idea'].get('titulo')}\nPor qué ahora: {t['idea'].get('por_que')}\nOrigen: {t['idea'].get('origen')}")
    print(f"Formato: {t['formato']} · Plataformas: {', '.join(t['plataformas'])}")
    for f in t["idea"].get("fuentes", []):
        print(f"Pista (no copiar, solo contexto): {f.get('titulo')} {f.get('url')}")
    print("\n" + REGLAS + "\n\nPLANTILLA DEL GUION (JSON):")
    print(json.dumps({**PLANTILLA, "formato": t["formato"]}, ensure_ascii=False, indent=2))
    print(f"\nGuárdalo en output/guiones/{t['id']}.json y ejecuta:\n  python -m fabrica.producir {t['id']} output/guiones/{t['id']}.json")


if __name__ == "__main__":
    main()

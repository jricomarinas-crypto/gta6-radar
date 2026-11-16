"""Encargos que esperan guion (modo suscripción).

    python -m fabrica.encargo            → lista las piezas en la etapa Guion, con la ruta donde va su guion
    python -m fabrica.encargo a1b2c3     → detalle: idea, formato, reglas, esquema y dónde guardar el JSON
    python -m fabrica.encargo --validar ruta.json   → valida un guion sin guardarlo en ningún sitio
"""
from __future__ import annotations

import json
import sys

from estudio import db, flujo

from . import guion

REGLAS = """REGLAS DEL GUION (megaprompt §9)
- Contenido 100 % propio: nada de otros creadores ni de Rockstar. Cero spoilers del final o de giros.
- Cada afirmación con etiqueta, fuente (URL) y fecha de consulta. Fuente oficial = CONFIRMADO; medio fiable = REPORTADO;
  sin confirmar = RUMOR (y la voz lo dice); interpretación = OPINIÓN. Muchas copias de lo mismo no son confirmaciones.
- 3 ganchos de tipos distintos (pregunta al país, dato con número, «esto no lo sabías», conflicto, cuenta atrás, error común).
- Estructura: gancho (0-2 s) → promesa (2-5 s) → desarrollo con un giro a mitad → cierre con pregunta.
- 6-10 escenas alternando leo (analista) y sofi (fan). Frases < 12 palabras. Español neutro latinoamericano. 25-45 s."""


def main():
    args = sys.argv[1:]
    if args[:1] == ["--validar"]:
        try:
            g, avisos = guion.validar(json.loads(open(args[1], encoding="utf-8").read()))
        except guion.GuionNoValido as e:
            raise SystemExit(str(e))
        print(f"✔ Guion válido · hash {guion.hash_guion(g)}" + ("\nAvisos: " + "; ".join(avisos) if avisos else ""))
        return
    con = db.connect()
    if not args:
        pend = [flujo.estado(con, t["id"]) for t in db.trabajos(con)]
        pend = [p for p in pend if p["etapa"] == "Guion"]
        if not pend:
            print("No hay piezas esperando guion. (Aprueba la idea en el Estudio para pedirlo.)")
        for p in pend:
            print(f"{p['id']} · {p['formato']} {p['variante']} · {p['idea'].get('titulo')}\n   → {p['guion']['ruta']}"
                  + (f"\n   errores: {p['guion']['errores']}" if p["guion"]["errores"] else ""))
        return
    t = db.trabajo(con, args[0])
    if not t:
        raise SystemExit(f"No existe el encargo {args[0]}")
    st = flujo.estado(con, t["id"])
    print(f"ENCARGO {t['id']} · etapa: {st['etapa']} · {st['siguiente']}")
    print(f"Idea: {t['idea'].get('titulo')}\nPor qué ahora: {t['idea'].get('por_que')}\nOrigen: {t['idea'].get('origen')}")
    print(f"Formato: {t['formato']} · variante: {st['variante']} · plataformas: {', '.join(t['plataformas'])}")
    for f in t["idea"].get("fuentes", []):
        print(f"Señal (solo contexto, no es una fuente de hechos): {f.get('titulo')} {f.get('url')}")
    print("\n" + REGLAS + "\n\nESQUEMA: ver la cabecera de fabrica/guion.py")
    print(f"\nGuárdalo en:\n  {flujo.ruta_guion(t)}\nY compruébalo con:\n  python -m fabrica.encargo --validar {flujo.ruta_guion(t)}")


if __name__ == "__main__":
    main()

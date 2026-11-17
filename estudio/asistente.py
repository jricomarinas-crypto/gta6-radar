"""Contexto de una investigación para el asistente en el chat (fase 3, 0 €). Lo usa el comando /investigar.

    python -m estudio.asistente            → investigaciones abiertas
    python -m estudio.asistente <id>       → todo lo de esa investigación, numerado para citarlo: [F1] [A1] [N1]

Solo LEE: no modifica nada. Todo sale de tu Mac (data/estudio.db y el Radar local).
"""
from __future__ import annotations

import sys
from contextlib import closing

from . import db, ideas, seguimiento
from . import verificacion as ver
from .investigacion import ESTADOS_NOMBRE, inv, lista_inv


def _f(v) -> str:
    return (v or "")[:10] or "fecha desconocida"


def contexto(con, iid: str, radar=None, demo: bool = False) -> str:
    i = inv(con, iid, completa=True)
    if not i:
        return f"No existe la investigación {iid}. Ejecuta `python -m estudio.asistente` para ver la lista."
    L = [f"# Investigación {i['id']}: {i['titulo']}", f"Estado: {ESTADOS_NOMBRE.get(i['estado'], i['estado'])} · creada {_f(i['creada_en'])} · "
         f"última actividad {_f(i['actividad_en'])}", ""]
    for k, t in (("pregunta", "Pregunta"), ("descripcion", "Descripción"), ("que_se", "Qué sé"), ("que_falta", "Qué falta"),
                 ("conclusion", "Conclusión provisional")):
        L.append(f"## {t}\n{i[k] or '(vacío)'}\n")
    num = {}
    L.append("## Fuentes")
    for n, f in enumerate(i["fuentes"], 1):
        num[f["id"]] = f"F{n}"
        L.append(f"[F{n}] {f['titulo']} — {f['fuente'] or '—'} · publicado {_f(f['publicado_en'])} · consultado {_f(f['consultada_en'])}"
                 f" · {f['url']}" + (f"\n     aporta: {f['aporte']}" if f["aporte"] else ""))
    if not i["fuentes"]:
        L.append("(sin fuentes)")
    L.append("\n## Afirmaciones")
    afs = ver.lista_afirm(con, inv_id=iid)
    for n, a in enumerate(afs, 1):
        c = a["cuentas"]
        L.append(f"[A{n}] «{a['texto']}» — {a['estado_nombre']} (etiqueta {a['etiqueta']}) · quién primero: {a['quien_primero'] or 'desconocido'}"
                 f" ({_f(a['fecha_origen'])}) · {c['independientes']} independiente(s), {c['a_favor']} a favor, {c['en_contra']} en contra, "
                 f"{c['repite']} solo repiten · revisada {_f(a['revisada_en'])}" + (" · REVISIÓN ANTIGUA" if a["revision_antigua"] else ""))
        for e in a["evidencias"]:
            ref = num.get(e["ref_id"], f"biblioteca #{e['ref_id']}")
            L.append(f"     {ver.RELACIONES[e['relacion']]}{' (independiente)' if e['independiente'] else ''}: [{ref}] {e['titulo']}")
    if not afs:
        L.append("(sin afirmaciones)")
    L.append("\n## Notas (de Javier: no se modifican)")
    for n, x in enumerate(i["notas"], 1):
        L.append(f"[N{n}] ({x['tipo']}, {_f(x['actualizada_en'] or x['creada_en'])}) {x['texto']}")
    if not i["notas"]:
        L.append("(sin notas)")
    L.append("\n## Cronología (más reciente primero)")
    for e in ver.cronologia(con, inv_id=iid)[:40]:
        L.append(f"- {_f(e['ocurrio_en'] or e['publicado_en'] or e['detectado_en'] or e['creado_en'])} ({e['fecha_usada']}) "
                 f"{e['tipo_nombre']}: {e['titulo']}")
    s = seguimiento.estado(con, iid)
    L.append("\n## Seguimiento")
    if s and s["activo"] and radar is not None:
        nov = seguimiento.novedades(radar, con, iid, demo)
        L.append(f"Consultas: {' | '.join(s['consultas'])} · revisado {_f(s['revisado_en'])} · {len(nov)} novedad(es) del Radar sin revisar:")
        L += [f"- [{x['tipo_nombre']}] {x['titulo']} — {x['fuente'] or '—'} · detectado {_f(x['detectado'])} · {x['url']}" for x in nov[:20]]
    else:
        L.append("(no se sigue)")
    L.append("\nAlcance de estos datos: esta investigación + el Radar local. No incluye búsquedas en internet.")
    return "\n".join(L)


def main():
    con = db.connect()
    if len(sys.argv) < 2:
        for i in lista_inv(con):
            print(f"{i['id']} · {i['titulo']} · {ESTADOS_NOMBRE.get(i['estado'])} · {i['n_fuentes']} fuentes · {i['n_notas']} notas")
        return
    with closing(ideas.radar_db()) as radar:
        print(contexto(con, sys.argv[1].strip(), radar, ideas.es_demo(radar)))


if __name__ == "__main__":
    main()

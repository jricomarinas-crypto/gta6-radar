"""Agente Editor: revisa el guion contra el dossier antes de grabar y corrige lo que no se sostiene."""
from __future__ import annotations

from radar.config import cfg
from radar.db import jdump
from radar.llm import ask_json

SYSTEM = """Eres el AGENTE EDITOR de un podcast de YouTube sobre GTA 6 para público hispano de Latinoamérica.
Tu trabajo es proteger la credibilidad del canal y su monetización. Revisas el guion ANTES de grabarlo.

Busca, línea a línea:
- dato_no_respaldado: cifras, fechas, nombres o afirmaciones que NO están en el dossier
- rumor_como_hecho: algo marcado como [RUMOR]/[REPORTADO] en el dossier que el guion presenta como seguro
- titulo_enganoso: el título o la miniatura prometen algo que el episodio no da (clickbait falso)
- politica: copiar contenido de otros creadores, describir material filtrado con detalle, lenguaje ofensivo,
  pedir suscripción más de una vez, decir que es una IA o hablar del "guion"
- tono: expresiones de España en vez de español neutro latinoamericano, frases demasiado largas para oírse bien
- repeticion: ideas repetidas que alargan sin aportar

Reglas:
- Solo marca problemas reales; no reescribas por gusto.
- En "propuesta" da SOLO el texto hablado COMPLETO de la línea corregida (sin poner el nombre de quien habla),
  o "" si hay que borrarla.
- Gravedad alta = no se puede publicar así; media = conviene corregir; baja = detalle."""


def review(ep: dict, dossier: str) -> dict:
    numbered = [{"segmento": si, "capitulo": s.get("capitulo"), "tarjeta": s.get("tarjeta"),
                 "lineas": [{"linea": li, "habla": ln["habla"], "texto": ln["texto"]} for li, ln in enumerate(s["lineas"])]}
                for si, s in enumerate(ep["segmentos"])]
    prompt = f"""DOSSIER VERIFICADO:
{dossier[:20000]}

GUION A REVISAR:
título: {ep.get('titulo')}
miniatura: {ep.get('titulo_miniatura')} / {ep.get('subtitulo_miniatura')}
{jdump(numbered)}

Devuelve SOLO JSON:
{{"veredicto": "aprobado|corregir", "nota": 0-10, "resumen": "1-2 frases",
  "titulo_sugerido": "solo si el título es engañoso, si no vacío",
  "problemas": [{{"segmento": 0, "linea": 0, "tipo": "...", "gravedad": "alta|media|baja",
                  "detalle": "qué falla", "propuesta": "línea corregida completa o vacío para borrarla"}}]}}"""
    return ask_json(prompt, system=SYSTEM, model=cfg()["ia"]["modelo_principal"], max_tokens=8000)


def apply(ep: dict, rev: dict) -> tuple[dict, int]:
    changes = 0
    to_delete = []
    for p in rev.get("problemas", []):
        if p.get("gravedad") not in ("alta", "media"):
            continue
        si, li = p.get("segmento"), p.get("linea")
        if not isinstance(si, int) or not isinstance(li, int):
            continue
        if not (0 <= si < len(ep["segmentos"])) or not (0 <= li < len(ep["segmentos"][si]["lineas"])):
            continue
        new = (p.get("propuesta") or "").strip()
        if new:
            ep["segmentos"][si]["lineas"][li]["texto"] = new
        else:
            to_delete.append((si, li))
        changes += 1
    for si, li in sorted(to_delete, reverse=True):
        if len(ep["segmentos"][si]["lineas"]) > 1:
            del ep["segmentos"][si]["lineas"][li]
    if (rev.get("titulo_sugerido") or "").strip():
        ep["titulo"] = rev["titulo_sugerido"].strip()[:100]
        changes += 1
    return ep, changes


def report_md(rev: dict, changes: int) -> str:
    lines = ["# Informe del Agente Editor", "",
             f"Veredicto: **{rev.get('veredicto', '?')}** · nota {rev.get('nota', '?')}/10 · {changes} cambios aplicados", "",
             rev.get("resumen", ""), ""]
    for p in rev.get("problemas", []):
        lines.append(f"- [{p.get('gravedad')}] {p.get('tipo')} (seg. {p.get('segmento')}, línea {p.get('linea')}): "
                     f"{p.get('detalle')}\n  → {p.get('propuesta') or '(borrar línea)'}")
    return "\n".join(lines)

"""Ideas para el Estudio, sin IA: kits del calendario, temas con hueco, alertas e ideas del día (si las hay).

Cada idea: {id, titulo, por_que, variante, formato, plataformas, fuentes, origen}.
No hay «score de viralidad» a la vista (megaprompt §8): el orden es interno y se explica con el porqué y el origen.
La prioridad explicable de verdad llega en el corte 2.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from radar import oportunidades
from radar.config import DATA_DIR, cfg
from radar.db import connect as radar_connect
from radar.db import hours_ago, jload, kv_get

from . import rutas

# Formatos de arranque del corte 1 (megaprompt §10): A novedad verificada, B explicación/comparación, C guía breve
VARIANTES = {
    "lista_pais": ("A", "Lista por país"),
    "ultima_hora": ("A", "Última hora"),
    "verdad_bulo": ("B", "Verdad o bulo"),
    "comparacion": ("B", "GTA 5 frente a GTA 6"),
    "guia": ("C", "Guía breve"),
}
FORMATOS = {"A": "Novedad verificada", "B": "Explicación o comparación", "C": "Descubrimiento o guía breve"}
PLATAFORMAS = {"tiktok": "TikTok", "shorts": "YouTube Shorts"}
VARIANTE_POR_TEMA = {
    "lanzamiento": "lista_pais", "precio_ediciones": "lista_pais", "plataformas_pc": "verdad_bulo",
    "filtraciones_rumores": "verdad_bulo", "polemica": "verdad_bulo", "historia": "verdad_bulo",
    "comparativa_gta5": "comparacion", "guias_trucos": "guia", "gameplay": "guia",
}
MADRID = ZoneInfo("Europe/Madrid")


def slug(texto: str, n: int = 40) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n].strip("-") or "idea"


def radar_db() -> sqlite3.Connection:
    """La base de datos real del Radar si tiene vídeos; si no, la de demostración (marcada como demo)."""
    real = DATA_DIR / "radar.db"
    if real.exists():
        con = radar_connect(real)
        if con.execute("SELECT COUNT(*) FROM videos").fetchone()[0] > 0:
            return con
        con.close()
    demo = DATA_DIR / "demo.db"
    if not demo.exists():
        raise SystemExit("No hay datos del Radar. Ejecuta: python tools/descargar_datos.py  (o python tools/datos_demo.py)")
    return radar_connect(demo)


def es_demo(con) -> bool:
    return con.execute("PRAGMA database_list").fetchone()["file"].endswith("demo.db")


def _kits(ahora: datetime) -> list[dict]:
    out = []
    for k in cfg().get("fabrica", {}).get("kits", []) or []:
        try:
            desde = datetime.strptime(k["desde"], "%Y-%m-%d %H:%M").replace(tzinfo=MADRID)
            hasta = datetime.strptime(k["hasta"], "%Y-%m-%d %H:%M").replace(tzinfo=MADRID)
        except (KeyError, ValueError):
            continue
        if desde <= ahora <= hasta:
            out.append({"id": k["id"], "titulo": k["titulo"], "por_que": k.get("por_que", ""),
                        "variante": k.get("formato", "ultima_hora"), "fuentes": [], "origen": "calendario", "_orden": 100})
    return out


def listar(con_radar, descartadas: set[str] | None = None) -> list[dict]:
    descartadas = descartadas or set()
    demo = es_demo(con_radar)
    ideas = _kits(datetime.now(MADRID))

    for i in (jload(kv_get(con_radar, "ideas_hoy"), {}) or {}).get("ideas", []):
        if i.get("titulo"):
            ideas.append({"id": "ia-" + slug(i["titulo"]), "titulo": i["titulo"], "por_que": i.get("por_que", ""),
                          "variante": VARIANTE_POR_TEMA.get(i.get("tema"), "ultima_hora"), "fuentes": [],
                          "origen": "ideas del día" + (" (demo)" if demo else ""), "_orden": 90})

    for t in oportunidades.calcular(con_radar).get("temas", [])[:8]:
        ideas.append({"id": "tema-" + t["topic"], "titulo": f"GTA 6: {t['label']}",
                      "por_que": (f"Mucha demanda ({t['demanda']:,} vistas/h en 48 h) y solo {t['videos_es']} vídeos "
                                  f"en español").replace(",", "."),
                      "variante": VARIANTE_POR_TEMA.get(t["topic"], "ultima_hora"),
                      "fuentes": [{"titulo": t["ejemplo"], "url": t["url"]}] if t.get("url") else [],
                      "origen": "tema con hueco" + (" (demo)" if demo else ""), "_orden": 40 + t["hueco"] * 0.45})

    for a in con_radar.execute("""SELECT * FROM alerts WHERE created_at>=? AND severity IN ('high','critical')
                                  ORDER BY id DESC LIMIT 10""", (hours_ago(24),)):
        tipo = a["type"] or ""
        variante = "verdad_bulo" if tipo in ("misinformation", "rumor_spike", "copyright_risk") else "ultima_hora"
        ideas.append({"id": "alerta-" + str(a["id"]), "titulo": a["title"], "por_que": a["message"] or "",
                      "variante": variante, "fuentes": [{"titulo": a["title"], "url": a["url"]}] if a["url"] else [],
                      "origen": "alerta" + (" (demo)" if demo else ""), "_orden": 80 if a["severity"] == "critical" else 60})

    vistos, out = set(), []
    defecto = cfg().get("fabrica", {}).get("plataformas_por_defecto", ["tiktok", "shorts"])
    for i in sorted(ideas, key=lambda x: -x["_orden"]):
        if i["id"] in vistos or i["id"] in descartadas:
            continue
        vistos.add(i["id"])
        i.pop("_orden", None)
        i["formato"] = VARIANTES.get(i["variante"], ("A", ""))[0]
        i["variante_nombre"] = VARIANTES.get(i["variante"], ("", i["variante"]))[1]
        i["plataformas"] = [p for p in defecto if p in PLATAFORMAS]
        i["demo"] = demo and i["origen"] != "calendario"
        out.append(i)
    return out


def exportar_dia(ideas: list[dict], piezas: list[dict]) -> str:
    """Escribe estudio/ideas/AAAA-MM-DD.json para que Claude escriba los guiones (modo suscripción, megaprompt §9)."""
    hoy = datetime.now(MADRID).strftime("%Y-%m-%d")
    d = rutas.ideas_dir()
    d.mkdir(parents=True, exist_ok=True)
    ruta = d / f"{hoy}.json"
    ruta.write_text(json.dumps({"fecha": hoy, "ideas": ideas, "piezas_esperando_guion": piezas},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    return str(ruta)

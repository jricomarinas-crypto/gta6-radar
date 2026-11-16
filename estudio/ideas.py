"""Ideas para la Fábrica, sin IA: kits del calendario, temas con hueco, alertas e ideas del día (si las hay).

Cada idea: {id, titulo, por_que, formato, plataformas, fuentes, origen, score}.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

from radar import oportunidades
from radar.config import DATA_DIR, cfg
from radar.db import connect as radar_connect
from radar.db import hours_ago, jload, kv_get

FORMATOS = {
    "lista_pais": "Lista por país",
    "verdad_bulo": "Verdad o bulo",
    "ultima_hora": "Última hora",
}
PLATAFORMAS = {"tiktok": "TikTok", "shorts": "YouTube Shorts"}
FORMATO_POR_TEMA = {
    "lanzamiento": "lista_pais", "precio_ediciones": "lista_pais", "plataformas_pc": "lista_pais",
    "filtraciones_rumores": "verdad_bulo", "polemica": "verdad_bulo", "historia": "verdad_bulo",
}
MADRID = ZoneInfo("Europe/Madrid")


def slug(texto: str, n: int = 40) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n].strip("-") or "idea"


def radar_db() -> sqlite3.Connection:
    """La base de datos real del Radar si tiene vídeos; si no, la de demostración."""
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
                        "formato": k.get("formato", "ultima_hora"), "fuentes": [], "origen": "calendario", "score": 100})
    return out


def listar(con_radar, descartadas: set[str] | None = None) -> list[dict]:
    descartadas = descartadas or set()
    ahora = datetime.now(MADRID)
    ideas = _kits(ahora)

    # ideas del día generadas con IA (solo si alguna vez hubo clave de API)
    for i in (jload(kv_get(con_radar, "ideas_hoy"), {}) or {}).get("ideas", []):
        if i.get("titulo"):
            ideas.append({"id": "ia-" + slug(i["titulo"]), "titulo": i["titulo"], "por_que": i.get("por_que", ""),
                          "formato": FORMATO_POR_TEMA.get(i.get("tema"), "ultima_hora"), "fuentes": [],
                          "origen": "ideas del día", "score": 90})

    # temas con hueco: mucha demanda y poca oferta en español
    for t in oportunidades.calcular(con_radar).get("temas", [])[:8]:
        ideas.append({"id": "tema-" + t["topic"], "titulo": f"GTA 6: {t['label']}",
                      "por_que": f"Hueco {t['hueco']}/100 · {t['demanda']:,} vistas/h · solo {t['videos_es']} vídeos en español"
                      .replace(",", "."),
                      "formato": FORMATO_POR_TEMA.get(t["topic"], "ultima_hora"),
                      "fuentes": [{"titulo": t["ejemplo"], "url": t["url"]}] if t.get("url") else [],
                      "origen": "tema con hueco", "score": 40 + t["hueco"] * 0.45})

    # alertas altas o críticas de las últimas 24 h
    for a in con_radar.execute("""SELECT * FROM alerts WHERE created_at>=? AND severity IN ('high','critical')
                                  ORDER BY id DESC LIMIT 10""", (hours_ago(24),)):
        tipo = a["type"] or ""
        formato = "verdad_bulo" if tipo in ("misinformation", "rumor_spike", "copyright_risk") else "ultima_hora"
        ideas.append({"id": "alerta-" + str(a["id"]), "titulo": a["title"], "por_que": a["message"] or "",
                      "formato": formato, "fuentes": [{"titulo": a["title"], "url": a["url"]}] if a["url"] else [],
                      "origen": "alerta", "score": 80 if a["severity"] == "critical" else 60})

    vistos, out = set(), []
    defecto = cfg().get("fabrica", {}).get("plataformas_por_defecto", ["tiktok", "shorts"])
    for i in sorted(ideas, key=lambda x: -x["score"]):
        if i["id"] in vistos or i["id"] in descartadas:
            continue
        vistos.add(i["id"])
        i["score"] = round(i["score"])
        i["plataformas"] = [p for p in defecto if p in PLATAFORMAS]
        i["formato_nombre"] = FORMATOS.get(i["formato"], i["formato"])
        out.append(i)
    return out

"""Shorts sueltos del día: 2-3 Shorts propios (Leo y Sofi) sobre lo más caliente del Radar.

    python -m podcast.shorts_diarios                # investiga, escribe, pone voces, monta y sube (privado)
    python -m podcast.shorts_diarios --sin-subir    # todo menos la subida
    python -m podcast.shorts_diarios --demo         # usa examples/short_demo.json (no necesita Claude)

Contenido 100 % propio: nada de clips de otros creadores ni de Rockstar.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

from radar.config import OUTPUT_DIR, ROOT, cfg
from radar.db import connect, jdump, jload, kv_get, kv_set
from radar.llm import extract_json, research_with_web
from radar.notify import send

from . import publicar, render, script, tts, upload

AVISO = "Este video usa voces sintéticas. Los datos llevan su fuente; los rumores se indican como tales."
ESTADOS = ("CONFIRMADO", "REPORTADO", "RUMOR", "OPINIÓN")


def validar(shorts: list[dict]) -> list[dict]:
    ok = []
    for s in shorts:
        lineas = [ln for ln in s.get("lineas", []) if ln.get("habla") in ("A", "B") and ln.get("texto", "").strip()]
        if len(lineas) < 3:
            continue
        tarjeta = s.get("tarjeta") or {}
        if tarjeta.get("estado") not in ESTADOS:
            tarjeta["estado"] = "REPORTADO"
        ok.append({**s, "lineas": lineas, "tarjeta": tarjeta, "titulo": (s.get("titulo") or "GTA 6")[:90],
                   "gancho": s.get("gancho") or s.get("titulo") or "GTA 6"})
    return ok


def escribir(con, n: int) -> tuple[list[dict], list[dict]]:
    """Claude elige los temas, verifica con búsqueda web y escribe los Shorts."""
    p = cfg()["podcast"]
    a, b = ({h["id"]: h for h in p["presentadores"]}[k] for k in ("A", "B"))
    hechos = jload(kv_get(con, "shorts_hechos"), [])[-15:]
    hoy = [{"titulo": r["title"], "temas": jload(r["topic_keys"])}
           for r in con.execute("SELECT * FROM episodes ORDER BY date DESC LIMIT 2")]
    prompt = f"""Hoy es {script.today_str()}. Escribes Shorts verticales (35-50 segundos) para «{cfg()['canal']['nombre']}»,
canal de YouTube y TikTok sobre GTA 6 para público hispano de Latinoamérica. Español neutro latinoamericano.

Presentadores (voces sintéticas):
- A = {a['nombre']} ({a['rol']}): {a['personalidad']}
- B = {b['nombre']} ({b['rol']}): {b['personalidad']}

LO QUE DETECTA NUESTRO RADAR (últimas 48 h):
{jdump(script.radar_context(con))}

YA CUBIERTO (no repitas el mismo ángulo):
- Episodios recientes: {jdump(hoy)}
- Shorts recientes: {jdump(hechos)}

Tu trabajo:
1. Elige los {n} temas con más tirón AHORA (momentum, alertas, temas en alza con poca cobertura en español)
   y que se puedan contar bien en 40 segundos.
2. Verifica cada dato clave con búsqueda web en fuentes primarias o medios fiables. Nunca uses a otros creadores como fuente.
3. Escribe cada Short:
   - Primera línea = GANCHO que se entiende sin contexto en menos de 2 segundos (pregunta o dato fuerte).
   - 5-8 líneas en total, alternando A y B, frases cortas, sin relleno. Unas 100-130 palabras.
   - Última línea = pregunta a la audiencia para que comente.
   - Cada dato con su grado: si es rumor, se dice como rumor. No inventes cifras, fechas ni citas.
   - Sin emojis, sin acotaciones, sin markdown en los textos.

Devuelve SOLO este JSON:
{{"shorts": [{{
  "tema": "slug corto, p. ej. precio-ediciones",
  "titulo": "título ≤ 60 caracteres, honesto, con 'GTA 6'",
  "gancho": "≤ 6 palabras para el texto grande",
  "tarjeta": {{"titular": "≤ 40 caracteres", "detalle": "≤ 70 caracteres",
              "estado": "CONFIRMADO|REPORTADO|RUMOR|OPINIÓN", "fuente": "medio u organismo (≤ 40 caracteres)"}},
  "lineas": [{{"habla": "A|B", "texto": "..."}}],
  "fuentes": [{{"titulo": "...", "url": "https://..."}}]
}}]}}"""
    text, sources = research_with_web(prompt, max_uses=4, max_tokens=8000)
    return validar(extract_json(text).get("shorts", [])), sources


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--sin-subir", action="store_true")
    args = ap.parse_args()

    conf = cfg()["podcast"].get("shorts_diarios", {})
    if not conf.get("activar", True) and not args.demo:
        print("Shorts diarios desactivados en config.yaml (podcast.shorts_diarios.activar)")
        return
    n = int(conf.get("por_ejecucion", 2))
    con = connect()
    now = datetime.now(ZoneInfo(cfg()["canal"].get("zona_horaria", "UTC")))
    work = OUTPUT_DIR / now.strftime("%Y-%m-%d") / f"shorts_{now.strftime('%H%M')}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    # 1) guiones
    if args.demo:
        shorts = validar(json.loads((ROOT / "examples/short_demo.json").read_text(encoding="utf-8"))["shorts"])
    else:
        print("▶ Eligiendo temas y verificando datos…")
        shorts, _ = escribir(con, n)
    shorts = shorts[:n]
    if not shorts:
        raise SystemExit("La IA no devolvió ningún Short válido")
    (work / "guiones.json").write_text(json.dumps(shorts, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) voces + vídeo vertical (cada Short es un mini episodio de 1 segmento)
    hosts = {h["id"]: h for h in cfg()["podcast"]["presentadores"]}
    piezas = []
    (work / "render").mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(shorts):
        print(f"▶ Short {i + 1}: {s['titulo']}")
        ep = {"titulo": s["titulo"], "segmentos": [{"capitulo": s["gancho"], "tarjeta": s["tarjeta"], "lineas": s["lineas"]}]}
        lines = tts.synthesize(script.flatten(ep), hosts, work / f"voces_{i + 1}")
        lines, _ = tts.build_timeline(lines, work / f"audio_{i + 1}.wav")
        meta = {"title": s["titulo"], "badge": "GTA 6", "pie": "Sigue el canal para más  ▶"}
        p = render.render_short(ep, lines, work / f"audio_{i + 1}.wav", {"segmento": 0, "gancho": s["gancho"]},
                                work / "render", meta, i)
        if not p:
            continue
        dst = work / p.name
        shutil.move(p, dst)
        fuentes = "\n".join(f"• {f.get('titulo')}: {f['url']}" for f in s.get("fuentes", [])[:5] if f.get("url"))
        bloque_fuentes = "Fuentes:\n" + fuentes + "\n\n" if fuentes else ""
        desc = f"{s['titulo']}\n\n{bloque_fuentes}{AVISO}\n\n#GTA6 #Shorts"
        piezas.append(publicar.pieza("short", dst, s["titulo"], desc, ["GTA 6", "GTA VI", "Grand Theft Auto VI"],
                                     gancho=s["gancho"]))

    # 3) pack para publicar + subida en privado
    publicar.crear_pack(work, piezas, AVISO)
    ids = []
    up = cfg()["podcast"]["subida"]
    if up.get("activar", True) and up.get("subir_shorts", True) and not args.sin_subir and upload.available():
        print("▶ Subiendo a YouTube (privado)…")
        for pz in piezas:
            ids.append(upload.upload(pz["video"], f"{pz['titulo'][:90]} #Shorts", pz["descripcion"], pz["etiquetas"]))

    if not args.demo:
        hechos = jload(kv_get(con, "shorts_hechos"), []) + [{"fecha": now.strftime("%Y-%m-%d"), "tema": s.get("tema"),
                                                              "titulo": s["titulo"]} for s in shorts]
        kv_set(con, "shorts_hechos", jdump(hechos[-40:]))
        con.commit()

    msg = [f"📱 {len(piezas)} Shorts nuevos listos"] + [f"• {pz['titulo']}" for pz in piezas]
    msg += [f"Revísalo: https://studio.youtube.com/video/{v}/edit" for v in ids]
    msg.append("TikTok: descarga la carpeta publicar/ del artifact y súbelos a mano.")
    if cfg()["avisos"].get("enviar_aviso_episodio", True) and not args.demo:
        send("\n".join(msg))
    print("\n".join(msg))
    print(f"✔ Archivos en {work}")


if __name__ == "__main__":
    main()

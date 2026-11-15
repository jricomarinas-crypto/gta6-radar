"""Agente de Operaciones: vigila que todo funcione, diagnostica fallos y te dice cómo arreglarlos.

    python -m agentes.operaciones            # informe diario de salud
    python -m agentes.operaciones --fallo    # se lanza solo cuando falla el Radar o el Podcast

Revisa: ejecuciones de GitHub Actions, errores y cuota del Radar, frescura de los datos y último episodio.
Si algo falla, lee el log, la IA diagnostica la causa y abre (o actualiza) un issue en GitHub con la solución.
"""
from __future__ import annotations

import argparse
from datetime import timedelta

from radar.config import cfg, env
from radar.db import connect, hours_ago, jdump, jload, now, parse_iso
from radar.llm import ask_json
from radar.notify import send

from . import github

SYSTEM = """Eres el AGENTE DE OPERACIONES de un sistema automático (Radar de GTA 6 + podcast diario en YouTube)
que corre en GitHub Actions. Escribes para el dueño del canal, que no es programador experto.
Diagnostica con los datos que te doy, sin inventar. Para cada problema: causa más probable y solución en pasos
concretos (qué secret revisar, qué valor de config.yaml cambiar, qué comando ejecutar). Español de España, breve."""

KNOWN = """Fallos típicos y su arreglo:
- "Falta la variable X" → añadir el secret X en GitHub → Settings → Secrets and variables → Actions.
- invalid_grant / Token has been expired or revoked (YouTube) → la app OAuth está en modo "Prueba" (caduca a los 7 días)
  o se revocó: publicar la app en Google Cloud y repetir tools/get_youtube_token.py; actualizar YT_REFRESH_TOKEN.
- quotaExceeded / cupo de búsquedas agotado → bajar radar.busquedas_por_ejecucion en config.yaml o el cron del Radar.
- uploadLimitExceeded → YouTube limita subidas en canales nuevos: subir_shorts: false unos días.
- 401/403 de api.anthropic.com → ANTHROPIC_API_KEY mal copiada o sin saldo; 529 overloaded → reintentar más tarde.
- Edge TTS 403 / WSServerHandshakeError → Microsoft cambió el servicio: actualizar edge-tts en requirements.txt o
  cambiar podcast.voz.proveedor a elevenlabs.
- "La IA no devolvió JSON válido" → fallo puntual; si se repite, subir max_tokens o cambiar ia.modelo_principal.
- Pages: "Get Pages site failed" → activar Settings → Pages → Source: GitHub Actions o quitar la variable PUBLICAR_PANEL.
- ffmpeg / ass / fontsdir → revisar que assets/fonts esté en el repo."""


def collect(con) -> dict:
    data: dict = {"fecha": now().strftime("%Y-%m-%d %H:%M UTC")}
    # 1) GitHub Actions
    if github.available():
        try:
            rs = [r for r in github.runs(60) if parse_iso(r.get("created_at")) and parse_iso(r["created_at"]) >= now() - timedelta(hours=26)]
            by_wf: dict = {}
            for r in rs:
                w = by_wf.setdefault(r["name"], {"ok": 0, "fallos": 0, "ultima": None, "fallidas": []})
                if r.get("conclusion") == "success":
                    w["ok"] += 1
                elif r.get("conclusion") in ("failure", "timed_out", "startup_failure"):
                    w["fallos"] += 1
                    w["fallidas"].append({"id": r["id"], "url": r["html_url"], "cuando": r["created_at"]})
                if not w["ultima"]:
                    w["ultima"] = {"estado": r.get("conclusion") or r.get("status"), "cuando": r["created_at"], "url": r["html_url"]}
            data["github_actions"] = by_wf
        except Exception as e:  # noqa: BLE001
            data["github_actions"] = f"no disponible: {e}"
    # 2) Radar
    last = con.execute("SELECT * FROM runs WHERE kind='radar' ORDER BY id DESC LIMIT 1").fetchone()
    errs = [dict(r) for r in con.execute("SELECT started_at, error FROM runs WHERE error IS NOT NULL AND started_at>=? "
                                         "ORDER BY id DESC LIMIT 8", (hours_ago(24),))]
    stats24 = [jload(r["stats"], {}) for r in con.execute("SELECT stats FROM runs WHERE started_at>=?", (hours_ago(24),))]
    data["radar"] = {
        "ultima_ejecucion": last["started_at"] if last else None,
        "horas_desde_ultima": round((now() - parse_iso(last["started_at"])).total_seconds() / 3600, 1) if last else None,
        "ejecuciones_24h": len(stats24),
        "errores_24h": errs,
        "busquedas_youtube_24h": sum(int(s.get("busquedas_api", 0) or 0) for s in stats24),
        "unidades_youtube_24h": sum(int(s.get("unidades_api", 0) or 0) for s in stats24),
        "videos_nuevos_24h": con.execute("SELECT COUNT(*) FROM videos WHERE first_seen_at>=?", (hours_ago(24),)).fetchone()[0],
        "noticias_nuevas_24h": con.execute("SELECT COUNT(*) FROM news WHERE first_seen_at>=?", (hours_ago(24),)).fetchone()[0],
        "sin_clasificar": con.execute("SELECT COUNT(*) FROM videos WHERE classified_at IS NULL").fetchone()[0],
    }
    ep = con.execute("SELECT * FROM episodes ORDER BY date DESC LIMIT 1").fetchone()
    data["ultimo_episodio"] = dict(date=ep["date"], titulo=ep["title"], youtube_id=ep["youtube_id"]) if ep else None
    data["config"] = {"secrets_presentes": [k for k in ("ANTHROPIC_API_KEY", "YOUTUBE_API_KEY", "YT_REFRESH_TOKEN",
                                                         "TELEGRAM_BOT_TOKEN") if env(k)]}
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fallo", action="store_true", help="modo diagnóstico tras un fallo")
    args = ap.parse_args()
    con = connect()
    data = collect(con)

    logs = ""
    gha = data.get("github_actions")
    if isinstance(gha, dict):
        for wf, info in gha.items():
            for f in info["fallidas"][:1]:
                try:
                    logs += f"\n\n## {wf} ({f['url']})\n" + github.failed_log_tail(f["id"])
                except Exception as e:  # noqa: BLE001
                    logs += f"\n\n## {wf}: no pude leer el log ({e})"

    if not env("ANTHROPIC_API_KEY"):
        send("🛠️ Operaciones (sin IA): " + jdump(data)[:3500])
        return

    res = ask_json(
        f"ESTADO DEL SISTEMA:\n{jdump(data)}\n\nLOGS DE FALLOS RECIENTES:\n{logs or '(ninguno)'}\n\n{KNOWN}\n\n"
        "Devuelve SOLO JSON: {\"estado\": \"verde|amarillo|rojo\", \"resumen\": \"1-2 frases\", "
        "\"problemas\": [{\"titulo\": \"...\", \"causa\": \"...\", \"solucion\": [\"paso 1\", \"paso 2\"], "
        "\"urgente\": true}], \"metricas\": \"1 línea con lo más relevante del día\"}",
        system=SYSTEM, model=cfg()["ia"]["modelo_principal"], max_tokens=3000)

    icon = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}.get(res.get("estado"), "⚪")
    lines = [f"{icon} OPERACIONES — {res.get('resumen', '')}", res.get("metricas", "")]
    body = [f"**Estado:** {icon} {res.get('estado')}", "", res.get("resumen", ""), ""]
    for p in res.get("problemas", []):
        steps = p.get("solucion") or []
        lines.append(f"\n• {p.get('titulo')}\n  Causa: {p.get('causa')}\n  Solución: " + " → ".join(steps))
        body += [f"### {p.get('titulo')}", f"**Causa probable:** {p.get('causa')}", "",
                 "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)), ""]
    if res.get("estado") in ("amarillo", "rojo") and res.get("problemas") and github.available():
        body += ["---", "Informe generado por el Agente de Operaciones. Datos:", "```json", jdump(data)[:6000], "```"]
        url = github.open_or_update_issue(f"[Operaciones] {res['problemas'][0].get('titulo', 'Problema detectado')}"[:120],
                                          "\n".join(body))
        if url:
            lines.append(f"\nIssue con el diagnóstico: {url}")
    if args.fallo or res.get("estado") != "verde" or cfg()["avisos"].get("enviar_informe_operaciones", True):  # noqa: E501
        send("\n".join(x for x in lines if x))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

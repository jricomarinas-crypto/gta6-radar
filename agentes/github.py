"""Acceso mínimo a la API de GitHub (ejecuciones, logs, issues) con el token de Actions."""
from __future__ import annotations

import requests

from radar.config import env

API = "https://api.github.com"


def _h():
    tok = env("GITHUB_TOKEN") or env("GH_TOKEN")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def repo() -> str | None:
    return env("GITHUB_REPOSITORY")


def available() -> bool:
    return bool(repo() and (env("GITHUB_TOKEN") or env("GH_TOKEN")))


def get(path: str, **params):
    r = requests.get(f"{API}/repos/{repo()}{path}", headers=_h(), params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def runs(limit: int = 40) -> list[dict]:
    return get("/actions/runs", per_page=limit).get("workflow_runs", [])


def failed_log_tail(run_id: int, lines: int = 120) -> str:
    """Últimas líneas (y las de error) de los jobs fallidos de una ejecución."""
    out = []
    for job in get(f"/actions/runs/{run_id}/jobs").get("jobs", []):
        if job.get("conclusion") != "failure":
            continue
        failed_steps = [s["name"] for s in job.get("steps", []) if s.get("conclusion") == "failure"]
        r = requests.get(f"{API}/repos/{repo()}/actions/jobs/{job['id']}/logs", headers=_h(), timeout=60)
        text = r.text if r.ok else f"(no pude leer el log: HTTP {r.status_code})"
        all_lines = text.splitlines()
        errs = [ln for ln in all_lines if any(k in ln for k in ("Error", "error:", "Traceback", "Exception", "Falta", "⚠"))]
        out.append(f"### Job {job['name']} · pasos fallidos: {', '.join(failed_steps) or '?'}\n"
                   + "\n".join(errs[-40:]) + "\n--- final del log ---\n" + "\n".join(all_lines[-lines:]))
    return "\n\n".join(out)[:30000]


def open_or_update_issue(title: str, body: str, label: str = "agente-operaciones") -> str | None:
    h = _h()
    base = f"{API}/repos/{repo()}"
    try:
        existing = requests.get(f"{base}/issues", headers=h, params={"state": "open", "labels": label}, timeout=30).json()
        for it in existing if isinstance(existing, list) else []:
            if it.get("title") == title:
                requests.post(f"{base}/issues/{it['number']}/comments", headers=h, json={"body": body}, timeout=30)
                return it.get("html_url")
        r = requests.post(f"{base}/issues", headers=h, json={"title": title, "body": body, "labels": [label]}, timeout=30)
        return r.json().get("html_url") if r.ok else None
    except requests.RequestException as e:
        print(f"  [GitHub] no pude crear el issue: {e}")
        return None

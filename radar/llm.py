"""Llamadas a Claude: JSON robusto, reintentos y búsqueda web con citas."""
from __future__ import annotations

import json
import re
import time

from .config import cfg, env

_client = None


class ModoSuscripcion(RuntimeError):
    """ia.modo = suscripcion: la app no llama a la IA (0 €). Los guiones los escribe Claude Code en la sesión."""


def modo() -> str:
    return (cfg().get("ia", {}).get("modo") or "suscripcion").lower()


def disponible() -> bool:
    """¿Se puede llamar a la API? Solo con ia.modo=api y clave puesta."""
    return modo() == "api" and bool(env("ANTHROPIC_API_KEY"))


def client():
    global _client
    if modo() != "api":
        raise ModoSuscripcion("La IA de pago está desactivada (ia.modo: suscripcion en config.yaml). "
                              "Pide los guiones a Claude Code en la sesión, o cambia ia.modo a 'api' si quieres pagar la API.")
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY", required=True))
    return _client


def _text_of(resp) -> str:
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def ask(prompt: str, *, system: str = "", model: str | None = None, max_tokens: int = 4000,
        temperature: float | None = None) -> str:
    model = model or cfg()["ia"]["modelo_principal"]
    kwargs = dict(model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    if system:
        kwargs["system"] = system
    if temperature is not None:
        kwargs["temperature"] = temperature
    for attempt in range(4):
        try:
            return _text_of(client().messages.create(**kwargs))
        except Exception as e:  # red, 429, 529…
            if attempt == 3:
                raise
            wait = 5 * (attempt + 1)
            print(f"  [IA] error ({e.__class__.__name__}); reintento en {wait}s")
            time.sleep(wait)
    return ""


def extract_json(text: str):
    """Saca el primer bloque JSON válido de una respuesta."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    candidates = [m.group(1)] if m else []
    candidates.append(text)
    for c in candidates:
        c = c.strip()
        for opener, closer in (("{", "}"), ("[", "]")):
            i, j = c.find(opener), c.rfind(closer)
            if i != -1 and j > i:
                try:
                    return json.loads(c[i : j + 1])
                except json.JSONDecodeError:
                    continue
    raise ValueError("La IA no devolvió JSON válido")


def ask_json(prompt: str, *, system: str = "", model: str | None = None, max_tokens: int = 8000):
    last_err = None
    for _ in range(2):
        txt = ask(prompt, system=system, model=model, max_tokens=max_tokens)
        try:
            return extract_json(txt)
        except ValueError as e:
            last_err = e
            prompt += "\n\nIMPORTANTE: responde SOLO con JSON válido, sin texto alrededor."
    raise last_err


def research_with_web(prompt: str, *, system: str = "", max_uses: int = 6, model: str | None = None,
                      max_tokens: int = 6000) -> tuple[str, list[dict]]:
    """Claude busca en la web (herramienta del servidor) y devuelve (texto, fuentes citadas)."""
    model = model or cfg()["ia"]["modelo_principal"]
    messages = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}]
    text_parts, sources, seen = [], [], set()
    for _ in range(6):  # pause_turn → continuar
        kwargs = dict(model=model, max_tokens=max_tokens, messages=messages, tools=tools)
        if system:
            kwargs["system"] = system
        resp = client().messages.create(**kwargs)
        for b in resp.content:
            if getattr(b, "type", "") == "text":
                text_parts.append(b.text)
                for c in getattr(b, "citations", None) or []:
                    url = getattr(c, "url", None)
                    if url and url not in seen:
                        seen.add(url)
                        sources.append({"title": getattr(c, "title", "") or url, "url": url})
        if resp.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": resp.content}]
            continue
        break
    return "".join(text_parts).strip(), sources

"""Avisos opcionales a Telegram y/o Discord."""
from __future__ import annotations

import requests

from .config import env


def send(text: str) -> None:
    """Envía un mensaje (Markdown sencillo). Si no hay canales configurados, solo lo imprime."""
    sent = False
    tok, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
    if tok and chat:
        for chunk in _chunks(text, 3800):
            try:
                requests.post(
                    f"https://api.telegram.org/bot{tok}/sendMessage",
                    json={"chat_id": chat, "text": chunk, "disable_web_page_preview": True},
                    timeout=20,
                )
                sent = True
            except requests.RequestException as e:
                print(f"  [aviso] Telegram falló: {e}")
    hook = env("DISCORD_WEBHOOK_URL")
    if hook:
        for chunk in _chunks(text, 1900):
            try:
                requests.post(hook, json={"content": chunk}, timeout=20)
                sent = True
            except requests.RequestException as e:
                print(f"  [aviso] Discord falló: {e}")
    if not sent:
        print("  [aviso] (sin Telegram/Discord configurado)\n" + text[:1500])


def _chunks(text: str, n: int):
    while text:
        if len(text) <= n:
            yield text
            return
        cut = text.rfind("\n", 0, n)
        cut = cut if cut > n // 2 else n
        yield text[:cut]
        text = text[cut:].lstrip("\n")

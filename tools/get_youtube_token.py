"""Paso único (en TU ordenador): autoriza al bot a subir vídeos a tu canal y obtiene el refresh token.

1. Descarga de Google Cloud el JSON del "ID de cliente OAuth" (tipo App de escritorio)
   y guárdalo junto a este archivo como  tools/client_secret.json
2. pip install google-auth-oauthlib
3. python tools/get_youtube_token.py
4. Se abre el navegador: entra con la cuenta del canal y acepta.
5. Copia los 3 valores que salen en pantalla a los Secrets de GitHub.
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
secret = Path(__file__).with_name("client_secret.json")
if not secret.exists():
    raise SystemExit(f"No encuentro {secret}. Descárgalo de Google Cloud → Credenciales → ID de cliente OAuth.")

flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
info = json.loads(secret.read_text())
cli = info.get("installed") or info.get("web") or {}
print("\n✅ Listo. Copia estos valores en GitHub → Settings → Secrets and variables → Actions:\n")
print(f"YT_CLIENT_ID      = {cli.get('client_id')}")
print(f"YT_CLIENT_SECRET  = {cli.get('client_secret')}")
print(f"YT_REFRESH_TOKEN  = {creds.refresh_token}")
print("\nNo compartas estos valores con nadie.")

"""Subida a YouTube con la API oficial (OAuth con refresh token)."""
from __future__ import annotations

from pathlib import Path

from radar.config import cfg, env

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def available() -> bool:
    return all(env(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def _service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(None, refresh_token=env("YT_REFRESH_TOKEN", True), client_id=env("YT_CLIENT_ID", True),
                        client_secret=env("YT_CLIENT_SECRET", True), token_uri="https://oauth2.googleapis.com/token",
                        scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(video: Path, title: str, description: str, tags: list[str], thumb: Path | None = None,
           sintetico: bool | None = None) -> str:
    """sintetico: si el vídeo tiene voz o imagen sintética realista. None = valor de config.yaml (subida.contenido_sintetico)."""
    from googleapiclient.http import MediaFileUpload

    up = cfg()["podcast"]["subida"]
    lang = cfg()["canal"].get("idioma", "es-419")
    body = {
        "snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:30],
                    "categoryId": str(up.get("categoria_id", "20")), "defaultLanguage": lang,
                    "defaultAudioLanguage": lang},
        "status": {"privacyStatus": up.get("privacidad", "private"), "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(up.get("contenido_sintetico", True) if sintetico is None else sintetico)},
    }
    yt = _service()
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True,
                                                        mimetype="video/mp4"))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  [YouTube] subiendo {video.name}: {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"  [YouTube] subido: https://youtu.be/{vid}")
    if thumb and thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
        except Exception as e:  # noqa: BLE001 — requiere canal verificado por teléfono
            print(f"  [YouTube] no pude poner la miniatura ({e}). Verifica tu canal en youtube.com/verify")
    return vid

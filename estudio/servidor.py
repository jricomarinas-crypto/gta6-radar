"""Servidor local del Estudio: el panel del Radar + la pestaña Estudio y su API.

    python -m estudio               → http://localhost:8080
    python -m estudio --puerto 8090 → si el 8080 está ocupado

Solo escucha en tu Mac (127.0.0.1). Sin dependencias nuevas (librería estándar de Python):
el proyecto ya usa Python y no hace falta un framework para unas pocas rutas.
"""
from __future__ import annotations

import json
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fabrica import cola
from radar import dashboard
from radar.config import DATA_DIR, cfg

from . import api_investigar, db, flujo, ideas, rutas

SITE = DATA_DIR / "estudio_site"
RE_ID = re.compile(r"^[0-9a-f]{6}$")
RE_VERSION = re.compile(r"^([0-9a-f]{6})-v(\d{1,3})$")


def _ideas() -> tuple[list[dict], bool]:
    con_r, con_e = ideas.radar_db(), db.connect()
    try:
        lista = ideas.listar(con_r, db.descartadas(con_e))
        esperando = [{"encargo": e["id"], "idea": e["idea"], "variante": e["variante"],
                      "guion_en": e["guion"]["ruta"], "errores": e["guion"]["errores"]}
                     for e in (flujo.estado(con_e, t["id"]) for t in db.trabajos(con_e))
                     if e["etapa"] == "Guion"]
        ideas.exportar_dia(lista, esperando)  # estudio/ideas/AAAA-MM-DD.json para /guiones-del-dia
        return lista, ideas.es_demo(con_r)
    finally:
        con_r.close()
        con_e.close()


def _panel() -> bytes:
    con = ideas.radar_db()
    try:
        return dashboard.build(con, out_dir=SITE, demo=ideas.es_demo(con)).read_bytes()
    finally:
        con.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "Estudio/2.0"

    def log_message(self, fmt, *args):
        if args and str(args[1]).startswith("5"):
            super().log_message(fmt, *args)

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code: int = 200):
        self._send(code, json.dumps(data, ensure_ascii=False, default=str).encode(), "application/json; charset=utf-8")

    def _body(self) -> dict:
        n = min(int(self.headers.get("Content-Length") or 0), 64_000)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def _media(self, vid: str):
        """Vídeo de una versión, buscado en la base de datos (nunca una ruta que venga del navegador)."""
        m = RE_VERSION.match(vid)
        v = db.version(db.connect(), vid) if m else None
        if not v or not v.get("video_ruta") or not Path(v["video_ruta"]).exists():
            return self._json({"error": "Vídeo no disponible"}, 404)
        ruta = Path(v["video_ruta"])
        tam = ruta.stat().st_size
        rango = re.match(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
        a, b = (int(rango.group(1)), int(rango.group(2) or tam - 1)) if rango else (0, tam - 1)
        b = min(b, tam - 1, a + 8 * 1024 * 1024)  # trozos de 8 MB para que Safari pueda saltar
        with open(ruta, "rb") as f:
            f.seek(a)
            datos = f.read(b - a + 1)
        cab = {"Accept-Ranges": "bytes", "Content-Range": f"bytes {a}-{b}/{tam}"}
        self._send(206 if rango else 200, datos, "video/mp4", cab)

    # ---------------------------------------------------------- GET
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html"):
                return self._send(200, _panel(), "text/html; charset=utf-8")
            if path == "/api/ideas":
                lista, demo = _ideas()
                return self._json({"ideas": lista, "demo": demo, "variantes": ideas.VARIANTES, "formatos": ideas.FORMATOS,
                                   "plataformas": ideas.PLATAFORMAS, "carpeta": str(rutas.carpeta_base())})
            if path == "/api/series":
                from . import series
                return self._json(series.produccion(db.connect(), 90))
            if path == "/api/series/dia":
                from urllib.parse import parse_qs, urlparse
                from . import series
                fecha = (parse_qs(urlparse(self.path).query).get("fecha") or [""])[0]
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
                    return self._json({"error": "Fecha no válida"}, 400)
                return self._json({"fecha": fecha, "eventos": series.eventos_del_dia(db.connect(), fecha)})
            if path == "/api/estado-datos":
                from radar.config import env
                from radar.llm import modo
                return self._json({"conexiones": [
                    {"nombre": "YouTube (lectura)", "ok": bool(env("YOUTUBE_API_KEY")), "como": "YOUTUBE_API_KEY en .env o GitHub Secrets"},
                    {"nombre": "Pexels (vídeo de fondo)", "ok": bool(env("PEXELS_API_KEY")), "como": "PEXELS_API_KEY en .env"},
                    {"nombre": "IA de pago (Anthropic)", "ok": modo() == "api" and bool(env("ANTHROPIC_API_KEY")),
                     "como": f"desactivada a propósito (ia.modo: {modo()})"},
                    {"nombre": "Subida a YouTube (OAuth)", "ok": bool(env("YT_REFRESH_TOKEN")), "como": "tools/get_youtube_token.py"},
                ]})
            if path == "/api/piezas":
                con = db.connect()
                return self._json({"piezas": [flujo.estado(con, t["id"]) for t in db.trabajos(con)]})
            m = re.match(r"^/api/piezas/([0-9a-f]{6})$", path)
            if m:
                con = db.connect()
                st = flujo.estado(con, m.group(1))
                gi = flujo.leer_guion(db.trabajo(con, m.group(1)))
                st["guion"]["contenido"] = gi.get("guion")
                return self._json(st)
            res = api_investigar.get(path, self.path.partition("?")[2])
            if res:
                return self._json(res[1], res[0])
            m = re.match(r"^/media/toma/([0-9a-f]{6})/(\d{1,2})\.wav$", path)
            if m:
                fila = db.connect().execute("SELECT ruta FROM tomas WHERE trabajo_id=? AND escena=?",
                                            (m.group(1), int(m.group(2)))).fetchone()
                if not fila or not Path(fila["ruta"]).exists():
                    return self._json({"error": "Toma no disponible"}, 404)
                return self._send(200, Path(fila["ruta"]).read_bytes(), "audio/wav")
            m = re.match(r"^/media/([0-9a-f]{6}-v\d{1,3})\.mp4$", path)
            if m:
                return self._media(m.group(1))
            return self._json({"error": "No encontrado"}, 404)
        except flujo.Bloqueado as e:
            return self._json({"error": str(e)}, 404)
        except SystemExit as e:  # sin datos del Radar
            return self._json({"error": str(e)}, 503)

    # ---------------------------------------------------------- POST
    def do_POST(self):
        path = self.path.split("?")[0]
        con = db.connect()
        m = re.match(r"^/api/piezas/([0-9a-f]{6})/voz/(\d{1,2})$", path)
        if m:  # toma de voz: audio crudo del micrófono (no JSON)
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > 25 * 1024 * 1024:
                return self._json({"error": "La grabación está vacía o es demasiado grande (máx. 25 MB)."}, 413)
            datos = self.rfile.read(n)
            try:
                return self._json(flujo.guardar_toma(con, m.group(1), int(m.group(2)), datos,
                                                     self.headers.get("Content-Type", "")))
            except flujo.Bloqueado as e:
                return self._json({"error": str(e)}, 409)
        body = self._body()
        res = api_investigar.post(path, body)
        if res:
            return self._json(res[1], res[0])
        try:
            if path == "/api/enviar":
                if body.get("a_mano"):
                    idea = flujo.idea_a_mano(body.get("titulo"), body.get("por_que"))
                else:
                    idea = {i["id"]: i for i in _ideas()[0]}.get(str(body.get("idea_id", "")))
                    if not idea:
                        raise flujo.Bloqueado("Esa idea ya no está en la lista. Recarga la página.")
                variante = body.get("variante") or idea.get("variante", "ultima_hora")
                plats = body.get("plataformas") if isinstance(body.get("plataformas"), list) else idea.get("plataformas", [])
                t = flujo.enviar_al_estudio(con, idea, variante, plats)
                return self._json(flujo.estado(con, t["id"]))
            if path == "/api/descartar-idea":
                iid, motivo = str(body.get("idea_id", ""))[:80], str(body.get("motivo", "")).strip()
                if not iid or not motivo:
                    raise flujo.Bloqueado("Di por qué la descartas: el motivo sirve para aprender.")
                db.descartar(con, iid, motivo[:300])
                return self._json({"ok": True})
            if path == "/api/abrir-carpeta":
                destino = rutas.carpeta_base()
                tid = str(body.get("pieza", ""))
                if RE_ID.match(tid):
                    exp = flujo.estado(con, tid)["exportacion"]
                    ruta = next((e["ruta"] for e in exp.values() if e.get("ruta")), None)
                    if ruta:
                        destino = Path(ruta).parent.parent
                destino.mkdir(parents=True, exist_ok=True)
                subprocess.run(["open", str(destino)], check=False)
                return self._json({"ok": True})
            m = re.match(r"^/api/piezas/([0-9a-f]{6})/(aprobar|cambios|crear|reintentar|cancelar|exportar|subido|descartar|opciones)$", path)
            if not m:
                return self._json({"error": "No encontrado"}, 404)
            tid, accion = m.groups()
            if accion == "opciones":
                return self._json(flujo.poner_opciones(con, tid, body.get("fondo"), body.get("voz")))
            if accion == "aprobar":
                return self._json(flujo.aprobar(con, tid, str(body.get("tipo", ""))))
            if accion == "cambios":
                return self._json(flujo.pedir_cambios(con, tid, body.get("nota", "")))
            if accion == "crear":
                flujo.crear_video(con, tid)
            elif accion == "reintentar":
                flujo.reintentar(con, tid)
            elif accion == "cancelar":
                flujo.cancelar(con, tid)
            elif accion == "exportar":
                res = flujo.exportar(con, tid)
                if cfg().get("estudio", {}).get("abrir_finder_al_terminar", True) and \
                        any("ya exportado" not in r["estado"] for r in res.values()):
                    subprocess.run(["osascript", "-e", 'display notification "Disponible en el Mac" with title '
                                    '"Punto de Control" sound name "Glass"'], check=False, capture_output=True)
            elif accion == "subido":
                return self._json(flujo.marcar_subido(con, tid, str(body.get("plataforma", "")), str(body.get("url", ""))))
            elif accion == "descartar":
                return self._json(flujo.descartar_pieza(con, tid, body.get("motivo", "")))
            return self._json(flujo.estado(con, tid))
        except flujo.Bloqueado as e:
            return self._json({"error": str(e)}, 409)


def usar_ffmpeg_completo() -> None:
    """El ffmpeg normal de Homebrew no trae subtítulos (libass); si está ffmpeg-full, se usa ese."""
    import os
    full = "/opt/homebrew/opt/ffmpeg-full/bin"
    if Path(full).exists() and not os.environ.get("PATH", "").startswith(full):
        os.environ["PATH"] = full + os.pathsep + os.environ.get("PATH", "")


def main():
    import argparse
    usar_ffmpeg_completo()
    ap = argparse.ArgumentParser(description="Estudio de Punto de Control")
    ap.add_argument("--puerto", type=int, default=int(cfg().get("estudio", {}).get("puerto", 8080)))
    puerto = ap.parse_args().puerto
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", puerto), Handler)
    except OSError:
        raise SystemExit(f"El puerto {puerto} está ocupado. Cierra lo que lo usa (p. ej. otro «python -m http.server») "
                         f"o usa: python -m estudio --puerto 8090")
    cola.arrancar_hilo()
    print(f"🎬 Estudio en http://localhost:{puerto}  (Ctrl+C para cerrar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nEstudio cerrado.")


if __name__ == "__main__":
    main()

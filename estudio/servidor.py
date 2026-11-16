"""Servidor local del Estudio: el panel del Radar + la pestaña Fábrica y su API.

    python -m estudio            → http://localhost:8080

Solo escucha en tu Mac (127.0.0.1). Sin dependencias nuevas: librería estándar de Python.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from radar import dashboard
from radar.config import DATA_DIR, cfg

from . import db, ideas

SITE = DATA_DIR / "estudio_site"


def carpeta_base() -> Path:
    return Path(cfg().get("fabrica", {}).get("carpeta_base", "~/Movies/Punto de Control")).expanduser()


def _ideas() -> list[dict]:
    con_r, con_e = ideas.radar_db(), db.connect()
    try:
        return ideas.listar(con_r, db.descartadas(con_e))
    finally:
        con_r.close()
        con_e.close()


def _panel() -> bytes:
    con = ideas.radar_db()
    try:
        demo = Path(con.execute("PRAGMA database_list").fetchone()["file"]).name == "demo.db"
        return dashboard.build(con, out_dir=SITE, demo=demo).read_bytes()
    finally:
        con.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "Estudio/1.0"

    def log_message(self, fmt, *args):  # sin ruido en la terminal salvo errores
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)

    # ---------------------------------------------------------- utilidades
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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

    # ---------------------------------------------------------- rutas
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html"):
                return self._send(200, _panel(), "text/html; charset=utf-8")
            if path == "/api/ideas":
                return self._json({"ideas": _ideas(), "formatos": ideas.FORMATOS, "plataformas": ideas.PLATAFORMAS,
                                   "carpeta": str(carpeta_base())})
            if path == "/api/trabajos":
                con = db.connect()
                return self._json({"trabajos": db.trabajos(con)})
            if path.startswith("/api/trabajos/"):
                t = db.trabajo(db.connect(), path.rsplit("/", 1)[1])
                return self._json(t) if t else self._json({"error": "No existe ese encargo"}, 404)
            return self._json({"error": "No encontrado"}, 404)
        except SystemExit as e:  # sin datos del Radar
            return self._json({"error": str(e)}, 503)

    def do_POST(self):
        path, body = self.path.split("?")[0], self._body()
        con = db.connect()
        if path in ("/api/crear", "/api/crear-pack"):
            todas = {i["id"]: i for i in _ideas()}
            if path == "/api/crear":
                idea = todas.get(str(body.get("idea_id", "")))
                if not idea:
                    return self._json({"error": "Esa idea ya no está en la lista"}, 400)
                elegidas = [(idea, body.get("formato"), body.get("plataformas"))]
            else:
                n = int(cfg().get("fabrica", {}).get("pack_del_dia", 5))
                elegidas = [(i, None, None) for i in list(todas.values())[:n]]
            creados = []
            for idea, formato, plats in elegidas:
                formato = formato if formato in ideas.FORMATOS else idea["formato"]
                plats = [p for p in (plats if isinstance(plats, list) else idea["plataformas"]) if p in ideas.PLATAFORMAS]
                if not plats:
                    return self._json({"error": "Marca al menos una plataforma"}, 400)
                creados.append(db.crear_trabajo(con, idea, formato, plats))
            return self._json({"trabajos": creados})
        if path == "/api/descartar":
            iid = str(body.get("idea_id", ""))[:80]
            if not iid:
                return self._json({"error": "Falta la idea"}, 400)
            db.descartar(con, iid)
            return self._json({"ok": True})
        if path == "/api/abrir-carpeta":
            base = carpeta_base()
            t = db.trabajo(con, str(body.get("trabajo_id", ""))) if body.get("trabajo_id") else None
            destino = Path(t["piezas"][0]["ruta"]).parent.parent if t and t["piezas"] else base
            destino.mkdir(parents=True, exist_ok=True)
            subprocess.run(["open", str(destino)], check=False)
            return self._json({"ok": True})
        if path == "/api/subido":
            pieza = con.execute("SELECT * FROM piezas WHERE id=?", (str(body.get("pieza_id", "")),)).fetchone()
            if not pieza:
                return self._json({"error": "No existe esa pieza"}, 404)
            ruta = Path(pieza["ruta"])
            subidos = ruta.parent / "subidos"
            subidos.mkdir(exist_ok=True)
            for f in ruta.parent.glob(ruta.stem + "*"):  # vídeo, .txt y portada
                shutil.move(str(f), subidos / f.name)
            con.execute("UPDATE piezas SET subida_en=datetime('now'), ruta=? WHERE id=?", (str(subidos / ruta.name), pieza["id"]))
            con.commit()
            return self._json({"ok": True})
        return self._json({"error": "No encontrado"}, 404)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Estudio de Punto de Control")
    ap.add_argument("--puerto", type=int, default=int(cfg().get("estudio", {}).get("puerto", 8080)))
    puerto = ap.parse_args().puerto
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", puerto), Handler)
    except OSError:
        raise SystemExit(f"El puerto {puerto} está ocupado. Cierra lo que lo usa (p. ej. otro «python -m http.server») "
                         f"o cambia estudio.puerto en config.yaml.")
    print(f"🎬 Estudio en http://localhost:{puerto}  (Ctrl+C para cerrar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nEstudio cerrado.")


if __name__ == "__main__":
    main()

"""Cola de render: un vídeo a la vez (configurable), reintentos limitados, cancelación y recuperación.

- El Estudio arranca un hilo que procesa las versiones «pendiente» de una en una.
- Al arrancar, lo que estaba «en curso» (el Estudio se cerró a mitad) pasa a «fallido: interrumpido».
- Cada fallo dice en qué etapa fue y qué hacer; el guion nunca se pierde (está guardado en la versión).
"""
from __future__ import annotations

import threading
import time

from estudio import db

from .producir import render_version

MAX_INTENTOS = 3
_cerrojo = threading.Lock()


def recuperar(con) -> int:
    n = con.execute("""UPDATE versiones SET estado_produccion='fallido', etapa='Interrumpido',
                       error='El Estudio se cerró mientras se fabricaba. Puedes reintentar sin rehacer el guion.'
                       WHERE estado_produccion='en_curso'""").rowcount
    con.commit()
    return n


def procesar_una(con) -> bool:
    """Procesa la versión pendiente más antigua. Devuelve False si no había ninguna."""
    with _cerrojo:  # un render a la vez
        r = con.execute("SELECT id FROM versiones WHERE estado_produccion='pendiente' ORDER BY creada_en LIMIT 1").fetchone()
        if not r:
            return False
        vid = r["id"]
        con.execute("UPDATE versiones SET intentos=intentos+1 WHERE id=?", (vid,))
        con.commit()
        try:
            render_version(con, vid)
        except Exception as e:  # noqa: BLE001 — se guarda el motivo y la etapa para reintentar
            v = db.version(con, vid)
            db.actualizar_version(con, vid, estado_produccion="fallido", error=str(e)[:500],
                                  etapa=f"Falló en: {v['etapa'] or 'inicio'}")
        return True


def procesar_pendientes(con) -> None:
    while procesar_una(con):
        pass


def arrancar_hilo() -> threading.Thread:
    def bucle():
        con = db.connect()
        recuperar(con)
        while True:
            try:
                if not procesar_una(con):
                    time.sleep(1.5)
            except Exception as e:  # noqa: BLE001 — el hilo nunca muere
                print(f"[cola] error inesperado: {e}")
                time.sleep(5)

    h = threading.Thread(target=bucle, name="cola-render", daemon=True)
    h.start()
    return h

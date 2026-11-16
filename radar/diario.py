"""Resumen diario del Radar (para la gráfica «Radar» de Hoy).

Por qué hace falta: las capturas se borran a los 14 días y los vídeos a los 45, así que sin este
resumen no habría histórico de 90 días. Cada ejecución del Radar actualiza el día de hoy (y ayer).

Definiciones (días en panel.zona_horaria, por defecto Europe/Madrid):
- publicados       = vídeos de GTA 6 cuya FECHA DE PUBLICACIÓN cae ese día (entre los que el Radar ha visto).
- detectados       = vídeos que el Radar vio POR PRIMERA VEZ ese día (first_seen_at).
- max_vistas_hora  = mayor velocidad (vistas/hora) medida ese día entre los vídeos que se actualizaron ese día.
                     Solo existe desde que se guarda este resumen: los días anteriores quedan sin dato (null).
Un día sin ninguna ejecución del Radar no tiene fila: es «sin datos», no cero.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import cfg
from .db import iso, parse_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS radar_diario (
    fecha TEXT PRIMARY KEY,             -- AAAA-MM-DD en la zona del panel
    publicados INTEGER, detectados INTEGER, max_vistas_hora REAL,
    origen TEXT,                        -- 'ejecucion' | 'reconstruido' | 'demo'
    actualizado_en TEXT
);
"""


def zona() -> ZoneInfo:
    return ZoneInfo(cfg().get("panel", {}).get("zona_horaria", "Europe/Madrid"))


def dia_local(valor: str | None) -> str | None:
    dt = parse_iso(valor) if valor else None
    return dt.astimezone(zona()).date().isoformat() if dt else None


def hoy() -> date:
    return datetime.now(zona()).date()


def actualizar(con) -> int:
    """Recalcula hoy y ayer; rellena días anteriores que aún no tengan fila (sin el máximo de vistas/hora)."""
    con.executescript(SCHEMA)
    publicados, detectados, dias_con_datos = {}, {}, set()
    for r in con.execute("SELECT published_at, first_seen_at FROM videos WHERE COALESCE(is_related,1)=1"):
        p, d = dia_local(r["published_at"]), dia_local(r["first_seen_at"])
        if p:
            publicados[p] = publicados.get(p, 0) + 1
        if d:
            detectados[d] = detectados.get(d, 0) + 1
            dias_con_datos.add(d)
    for r in con.execute("SELECT started_at FROM runs WHERE kind='radar'"):
        if dia_local(r["started_at"]):
            dias_con_datos.add(dia_local(r["started_at"]))
    h = hoy()
    recientes = {h.isoformat(), (h - timedelta(days=1)).isoformat()}
    # máximo de vistas/hora de los vídeos actualizados hoy
    max_hoy = None
    for r in con.execute("SELECT velocity, last_scraped_at FROM videos WHERE COALESCE(is_related,1)=1"):
        if dia_local(r["last_scraped_at"]) == h.isoformat() and r["velocity"] is not None:
            max_hoy = max(max_hoy or 0.0, float(r["velocity"]))
    n = 0
    ahora = iso()
    for d in sorted(dias_con_datos):
        if d > h.isoformat():
            continue
        fila = con.execute("SELECT * FROM radar_diario WHERE fecha=?", (d,)).fetchone()
        if fila and d not in recientes:
            continue  # días cerrados: no se tocan (los vídeos viejos se borran y el recuento bajaría)
        mvh = fila["max_vistas_hora"] if fila else None
        if d == h.isoformat() and max_hoy is not None:
            mvh = max(mvh or 0.0, max_hoy)
        origen = "ejecucion" if d in recientes else "reconstruido"
        con.execute("""INSERT OR REPLACE INTO radar_diario(fecha,publicados,detectados,max_vistas_hora,origen,actualizado_en)
                       VALUES(?,?,?,?,?,?)""", (d, publicados.get(d, 0), detectados.get(d, 0), mvh,
                                               fila["origen"] if fila and fila["origen"] == "demo" else origen, ahora))
        n += 1
    con.commit()
    return n


def serie(con, dias: int = 90) -> list[dict]:
    """Últimos `dias` días, del más antiguo al de hoy. Día sin fila → valores None (sin datos)."""
    con.executescript(SCHEMA)
    filas = {r["fecha"]: dict(r) for r in con.execute("SELECT * FROM radar_diario")}
    h = hoy()
    out = []
    for i in range(dias - 1, -1, -1):
        d = (h - timedelta(days=i)).isoformat()
        f = filas.get(d)
        out.append({"fecha": d, "publicados": f["publicados"] if f else None, "detectados": f["detectados"] if f else None,
                    "max_vistas_hora": f["max_vistas_hora"] if f else None, "origen": f["origen"] if f else None})
    return out

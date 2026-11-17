"""Pruebas de las series diarias de Hoy (rediseño fase 1A).

    python -m unittest tests.test_series -v

Comprueba que un día sin datos queda en None (nunca 0), que un día con ejecución y sin vídeos es un 0 real,
que la producción antes del primer evento es None, y que el panel generado incluye todas sus piezas.
"""
from __future__ import annotations

import sqlite3
import unittest
from datetime import timedelta

from tests.test_corte1 import RAIZ, nueva_pieza  # carpeta temporal

from estudio import db, series  # noqa: E402
from radar import dashboard, diario  # noqa: E402
from radar.db import connect, iso  # noqa: E402


def radar_vacio() -> sqlite3.Connection:
    ruta = RAIZ / "radar_prueba.db"
    ruta.unlink(missing_ok=True)
    return connect(ruta)  # con migraciones, como el Radar real


class SeriesDiarias(unittest.TestCase):
    def test_1_dia_sin_ejecucion_es_none_y_con_ejecucion_sin_videos_es_cero(self):
        con = radar_vacio()
        con.execute("INSERT INTO runs(kind,started_at) VALUES('radar',?)", (iso(),))  # hoy hubo ejecución, sin vídeos
        con.commit()
        diario.actualizar(con)
        s = diario.serie(con, 3)
        self.assertEqual([x["fecha"] for x in s][-1], diario.hoy().isoformat())
        self.assertEqual(s[-1]["publicados"], 0)        # cero real: el Radar corrió y no encontró nada
        self.assertIsNone(s[-1]["max_vistas_hora"])     # sin vídeos medidos no hay máximo: None, no 0
        self.assertIsNone(s[0]["publicados"])           # hace 2 días no hubo ejecución: sin datos

    def test_2_dias_cerrados_no_se_recalculan(self):
        con = radar_vacio()
        viejo = (diario.hoy() - timedelta(days=5)).isoformat()
        con.executescript(diario.SCHEMA)
        con.execute("INSERT OR REPLACE INTO radar_diario(fecha,publicados,detectados,max_vistas_hora,origen,actualizado_en) "
                    "VALUES(?,7,7,100,'ejecucion',?)", (viejo, iso()))
        con.commit()
        diario.actualizar(con)
        fila = con.execute("SELECT publicados FROM radar_diario WHERE fecha=?", (viejo,)).fetchone()
        self.assertEqual(fila["publicados"], 7)  # aunque ya no queden vídeos de ese día en la base, no baja a 0

    def test_3_produccion_none_antes_del_primer_evento_y_cero_despues(self):
        con = db.connect()
        nueva_pieza(con, "Serie de producción")
        p = series.produccion(con, 10)
        hoy = p["dias"][-1]
        self.assertEqual(hoy["fabricados"], hoy["fabricados"] or 0)
        primero = p["desde"]
        antes = [d for d in p["dias"] if d["fecha"] < primero]
        despues = [d for d in p["dias"] if d["fecha"] >= primero]
        self.assertTrue(all(d["fabricados"] is None for d in antes))
        self.assertTrue(all(isinstance(d["fabricados"], int) for d in despues))
        ev = series.eventos_del_dia(con, primero)
        self.assertTrue(any(e["tipo"] == "pieza_creada" for e in ev))

    def test_4_panel_generado_incluye_todo_y_sin_marcadores(self):
        con = radar_vacio()
        out = dashboard.build(con, out_dir=RAIZ / "site", demo=False)
        html = out.read_text()
        for marca in ("/*__CSS__*/", "/*__JS__*/", "/*__DATA__*/"):
            self.assertNotIn(marca, html)
        for pieza in ("const MENU", "const Grafica", "const Hoy", "const guardado", "function arrancarPanel"):
            self.assertIn(pieza, html)
        self.assertNotIn("canal_demo\": [", html)  # en datos reales no viajan series demo


if __name__ == "__main__":
    unittest.main()

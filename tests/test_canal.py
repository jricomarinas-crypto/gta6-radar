"""Pruebas de Mi canal (fase 2B): mediciones, cálculos diarios, ventana de 48 h, índice, retención y colaboradores.

    python -m unittest tests.test_canal -v

Carpeta temporal (PC_RAIZ_PRUEBAS): no toca tus datos.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from tests.test_corte1 import nueva_pieza  # carpeta temporal

from estudio import canal, colaboradores as col, db  # noqa: E402
from radar.diario import dia_local, zona  # noqa: E402

BASE = datetime.now(zona()).replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=20)


def t(dias=0, horas=0) -> str:
    """Hora local de Madrid sin zona, como la manda el formulario (datetime-local)."""
    return (BASE + timedelta(days=dias, hours=horas)).strftime("%Y-%m-%dT%H:%M")


class Canal(unittest.TestCase):
    def setUp(self):
        self.con = db.connect()
        for x in ("mediciones", "medicion_log", "mis_videos", "colaboradores"):
            self.con.execute(f"DELETE FROM {x}")
        self.con.commit()

    def video(self, n=0, plataforma="tiktok", dias=0, **kw):
        v = canal.crear_video(self.con, plataforma, f"https://www.tiktok.com/@pc/video/{n}", f"Vídeo {n}", t(dias))
        return canal.editar_video(self.con, v["id"], **kw) if kw else v

    def test_1_vacio_no_es_cero_duplicados_y_bajadas(self):
        v = self.video()
        m = canal.medir(self.con, v["id"], t(1), {"vistas": "", "compartidos": "0", "likes": "1.234"})
        self.assertIsNone(m["vistas"])
        self.assertEqual(m["compartidos"], 0)
        self.assertEqual(m["likes"], 1234)
        with self.assertRaises(canal.Errores) as e:
            canal.medir(self.con, v["id"], t(1), {"vistas": "10"})
        self.assertIn("medido_en", e.exception.errores)
        with self.assertRaises(canal.Errores) as e:
            canal.medir(self.con, v["id"], t(2), {"vistas": "abc", "pct_completo": "120"})
        self.assertEqual(set(e.exception.errores), {"vistas", "pct_completo"})
        canal.medir(self.con, v["id"], t(2), {"vistas": "500"})
        with self.assertRaises(canal.Errores) as e:  # un acumulado que baja: pide confirmación
            canal.medir(self.con, v["id"], t(3), {"vistas": "400"})
        self.assertTrue(e.exception.confirmar)
        canal.medir(self.con, v["id"], t(3), {"vistas": "400"}, confirmar_bajada=True)
        with self.assertRaises(canal.Errores):  # sin ninguna métrica
            canal.medir(self.con, v["id"], t(4), {})

    def test_2_diario_es_diferencia_y_marca_huecos(self):
        v = self.video()
        canal.medir(self.con, v["id"], t(1), {"vistas": "100"})
        canal.medir(self.con, v["id"], t(2), {"vistas": "250"})
        canal.medir(self.con, v["id"], t(5), {"vistas": "400"})
        d = {f["fecha"]: f for f in canal.diario(self.con, 30)}
        dia = lambda n: (BASE + timedelta(days=n)).date().isoformat()  # noqa: E731
        self.assertEqual(d[dia(1)]["tiktok"], 100)
        self.assertIn("desde la publicación", d[dia(1)]["notas"][0])
        self.assertEqual(d[dia(2)]["tiktok"], 150)         # 250 − 100, no 350
        self.assertIsNone(d[dia(3)]["tiktok"])             # sin medición: sin dato, no cero
        self.assertEqual(d[dia(5)]["tiktok"], 150)         # todo al día de la medición…
        self.assertIn("acumula 3 días", d[dia(5)]["notas"][0])  # …y avisado
        self.assertIsNone(d[dia(5)]["shorts"])
        self.assertEqual(sum(f["tiktok"] or 0 for f in d.values()), 400)  # nunca la suma de acumulados

    def test_3_ventana_48h_sin_interpolar(self):
        v = self.video()
        canal.medir(self.con, v["id"], t(0, 30), {"vistas": "300"})
        canal.medir(self.con, v["id"], t(0, 70), {"vistas": "700"})
        self.assertEqual(canal.vistas_48(self.con, canal._video(self.con, v["id"]))["estado"], "sin_ventana")
        canal.medir(self.con, v["id"], t(0, 47), {"vistas": "480"})
        r = canal.vistas_48(self.con, canal._video(self.con, v["id"]))
        self.assertEqual((r["estado"], r["vistas"]), ("ok", 480))

    def test_4_indice_48h_necesita_20_piezas(self):
        for i in range(20):
            v = self.video(i, dias=i * 0.1)
            canal.medir(self.con, v["id"], t(i * 0.1, 48), {"vistas": str((i + 1) * 100)})
        ultimo = self.video(99, dias=3)
        canal.medir(self.con, ultimo["id"], t(3, 48), {"vistas": "2100"})
        r = canal.indice_48(self.con, canal._video(self.con, ultimo["id"]))
        self.assertEqual(r["estado"], "ok")
        self.assertEqual(r["mediana"], 1050)  # mediana de 100…2000
        self.assertAlmostEqual(r["valor"], 2.0, places=2)
        quinto = canal._video(self.con, self.con.execute("SELECT id FROM mis_videos WHERE url LIKE '%/5'").fetchone()[0])
        r = canal.indice_48(self.con, quinto)
        self.assertEqual((r["estado"], r["n"]), ("historial_insuficiente", 5))

    def test_5_retencion_y_grupos_pequenos(self):
        a = self.video(1, duracion_s="30", serie="Lista")
        b = self.video(2, duracion_s="60", serie="Lista")
        canal.medir(self.con, a["id"], t(1), {"pct_completo": "40"})
        canal.medir(self.con, b["id"], t(1), {"pct_completo": "20"})
        g = canal.rinde(self.con, "serie")["grupos"][0]
        self.assertEqual(g["retencion"]["estado"], "no_comparable")
        self.assertTrue(g["pocos_datos"])
        canal.editar_video(self.con, b["id"], duracion_s="32")
        g = canal.rinde(self.con, "serie")["grupos"][0]
        self.assertEqual((g["retencion"]["estado"], g["retencion"]["valor"]), ("ok", 30.0))
        self.assertIsNone(g["vistas_total"])  # sin vistas registradas: sin dato, no 0

    def test_6_log_de_correcciones_y_borrados(self):
        v = self.video()
        m = canal.medir(self.con, v["id"], t(1), {"vistas": "100"})
        canal.medir(self.con, v["id"], t(1), {"vistas": "110"}, mid=m["id"])
        canal.borrar_medicion(self.con, m["id"])
        acciones = [r[0] for r in self.con.execute("SELECT accion FROM medicion_log ORDER BY id")]
        self.assertEqual(acciones, ["alta", "corregida", "borrada"])

    def test_7_pieza_subida_crea_el_video_una_vez(self):
        p = nueva_pieza(self.con, "Pieza para Mi canal")
        a = canal.video_desde_pieza(self.con, p["id"], "tiktok", "https://www.tiktok.com/@pc/video/777")
        b = canal.video_desde_pieza(self.con, p["id"], "tiktok", "https://www.tiktok.com/@pc/video/777")
        self.assertEqual(a["id"], b["id"])
        self.assertEqual((a["pieza_id"], a["origen"]), (p["id"], "fabrica"))

    def test_8_dias_en_hora_de_madrid(self):
        v = self.video(dias=-1)
        manana = (BASE + timedelta(days=5)).replace(hour=0, minute=30)
        m = canal.medir(self.con, v["id"], manana.strftime("%Y-%m-%dT%H:%M"), {"vistas": "5"})
        self.assertEqual(dia_local(m["medido_en"]), manana.date().isoformat())  # 00:30 de Madrid = ese día

    def test_9_colaboradores_sin_acciones_externas(self):
        c = col.guardar(self.con, None, None, "Creador de prueba", "youtube", "https://youtube.com/@x")
        self.assertEqual(c["estado"], "por_revisar")
        c = col.actualizar(self.con, c["id"], "contactar", "le escribiré yo")
        self.assertEqual(c["estado_nombre"], "Contactar")
        with self.assertRaises(canal.NoValido):
            col.actualizar(self.con, c["id"], "inventado")
        self.assertFalse(hasattr(col, "enviar"))


if __name__ == "__main__":
    unittest.main()

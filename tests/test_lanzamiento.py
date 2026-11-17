"""Pruebas de la versión de lanzamiento: base real sin vídeos, avisos honestos e identidad visual en el panel.

    python -m unittest tests.test_lanzamiento -v
"""
from __future__ import annotations

import unittest
from unittest import mock

from tests.test_corte1 import RAIZ  # carpeta temporal

from estudio import ideas  # noqa: E402
from radar import dashboard  # noqa: E402
from radar.db import connect, iso  # noqa: E402


def base(nombre: str, noticias: int = 0):
    d = RAIZ / "lanz"
    d.mkdir(exist_ok=True)
    (d / nombre).unlink(missing_ok=True)
    con = connect(d / nombre)
    for i in range(noticias):
        con.execute("INSERT INTO news(id,title,url,source,published_at,first_seen_at) VALUES(?,?,?,?,?,?)",
                    (f"n{i}", f"Noticia {i}", "https://ejemplo.com", "Medio", iso(), iso()))
    con.commit()
    return d, con


class Lanzamiento(unittest.TestCase):
    def test_1_real_con_noticias_aunque_no_haya_videos(self):
        d, con = base("radar.db", noticias=3)
        con.close()
        base("demo.db")[1].close()
        with mock.patch.object(ideas, "DATA_DIR", d):
            r = ideas.radar_db()
            self.assertFalse(ideas.es_demo(r))   # 3 noticias y 0 vídeos: es real, no demo
            r.close()
            base("radar.db")[1].close()        # vacía del todo → demo
            r = ideas.radar_db()
            self.assertTrue(ideas.es_demo(r))
            r.close()

    def test_2_aviso_honesto_y_marca_en_el_panel(self):
        d, con = base("panel.db", noticias=2)
        dashboard.build(con, out_dir=d, demo=False)
        html = (d / "index.html").read_text(encoding="utf-8")
        self.assertIn("falta YOUTUBE_API_KEY", html)          # se dice lo que falta, no se rellena
        self.assertIn("@font-face{font-family:'Inter'", html)  # tipografía dentro del HTML (sin CDN)
        self.assertNotIn("fonts.googleapis", html)
        self.assertIn("PUNTO DE CONTROL", html)
        dashboard.build(con, out_dir=d, demo=True)
        self.assertNotIn("falta YOUTUBE_API_KEY", (d / "index.html").read_text(encoding="utf-8"))  # en demo no se avisa


if __name__ == "__main__":
    unittest.main()

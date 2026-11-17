"""Pruebas del Centro de investigación (fase 1B).

    python -m unittest tests.test_investigacion -v

Todo ocurre en una carpeta temporal (PC_RAIZ_PRUEBAS): no toca data/estudio.db ni el Radar real.
"""
from __future__ import annotations

import unittest

from tests.test_corte1 import RAIZ  # carpeta temporal

from estudio import api_investigar, busqueda, db  # noqa: E402
from estudio import investigacion as inv  # noqa: E402
from radar.db import connect, iso  # noqa: E402


def radar_con_noticia():
    ruta = RAIZ / "radar_inv.db"
    ruta.unlink(missing_ok=True)
    con = connect(ruta)
    con.execute("""INSERT INTO news(id,title,url,source,published_at,first_seen_at,summary,language,topics,verification)
                   VALUES('n1','El precio de GTA 6 en México','https://ejemplo.com/precio','Medio Uno',?,?,
                          'Tiendas filtran un precio de 80 dólares','es','[\"price\"]','reported')""", (iso(), iso()))
    con.commit()
    return con


class Investigacion(unittest.TestCase):
    def setUp(self):
        self.con = db.connect()
        for t in ("inv_refs", "notas", "investigaciones", "referencias"):
            self.con.execute(f"DELETE FROM {t}")
        self.con.commit()
        self.radar = radar_con_noticia()

    def test_1_referencia_no_se_duplica_y_guarda_copia(self):
        a = inv.crear_ref(self.con, "noticia", "n1", radar=self.radar)
        b = inv.crear_ref(self.con, "noticia", "n1", radar=self.radar)
        self.assertEqual(a["id"], b["id"])
        self.radar.execute("DELETE FROM news")  # el Radar borra el original…
        self.radar.commit()
        r = inv.ref(self.con, a["id"])          # …y la copia sigue completa
        self.assertEqual(r["titulo"], "El precio de GTA 6 en México")
        self.assertEqual(r["datos"]["verificacion"], "reported")

    def test_2_quitar_de_investigacion_no_borra_de_biblioteca(self):
        r = inv.crear_ref(self.con, "noticia", "n1", radar=self.radar)
        i = inv.crear_inv(self.con, "Precio en Latinoamérica")
        inv.anadir_ref(self.con, i["id"], r["id"], "dato de precio")
        inv.anadir_ref(self.con, i["id"], r["id"])  # dos veces: sin duplicar
        self.assertEqual(inv.inv(self.con, i["id"])["n_fuentes"], 1)
        inv.quitar_ref(self.con, i["id"], r["id"])
        self.assertEqual(inv.inv(self.con, i["id"])["n_fuentes"], 0)
        self.assertIsNotNone(inv.ref(self.con, r["id"]))
        inv.anadir_ref(self.con, i["id"], r["id"])
        self.assertEqual(inv.eliminar_ref(self.con, r["id"]), 1)  # eliminar sí la quita de todas
        self.assertEqual(inv.inv(self.con, i["id"])["n_fuentes"], 0)

    def test_3_validaciones(self):
        with self.assertRaises(inv.NoValido):
            inv.crear_ref(self.con, "enlace", url="javascript:alert(1)", titulo="x")
        with self.assertRaises(inv.NoValido):
            inv.crear_inv(self.con, "ab")
        i = inv.crear_inv(self.con, "Prueba de estados")
        with self.assertRaises(inv.NoValido):
            inv.actualizar_inv(self.con, i["id"], estado="inventado")
        with self.assertRaises(inv.NoValido):
            inv.nota(self.con, i["id"], "   ")
        code, data = api_investigar.post("/api/investigaciones", {"titulo": "x"})
        self.assertEqual(code, 409)
        self.assertIn("error", data)

    def test_4_buscador_sin_tildes_con_notas_privadas_y_marcas(self):
        i = inv.crear_inv(self.con, "Lanzamiento en PC")
        inv.nota(self.con, i["id"], "Revisar el rumor del puerto para ordenadores", "pregunta")
        busqueda.reconstruir(self.radar, self.con)
        r = busqueda.buscar(self.radar, self.con, "précio méxico")
        self.assertEqual(r["total"], 1)
        self.assertIn("\u0001precio\u0002", r["resultados"][0]["titulo_marcado"])
        self.assertIn("\u0001precio\u0002", r["resultados"][0]["extracto"])
        notas = busqueda.buscar(self.radar, self.con, "ordenadores", tipos=["nota"])
        self.assertEqual(notas["total"], 1)
        self.assertEqual(notas["resultados"][0]["privado"], 1)
        self.assertIn("aviso", busqueda.buscar(self.radar, self.con, "(("))
        self.assertEqual(busqueda.buscar(self.radar, self.con, "precio", fuente="Otro medio")["total"], 0)


if __name__ == "__main__":
    unittest.main()

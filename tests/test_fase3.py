"""Pruebas de la fase 3: asistente (contexto), Google News (sin conexión), seguimiento, Revisión, Calendario e
ideas creadas con «Crear vídeo de esto».

    python -m unittest tests.test_fase3 -v
"""
from __future__ import annotations

import unittest

from tests.test_corte1 import nueva_pieza
from tests.test_investigacion import radar_con_noticia

from estudio import asistente, busqueda, db, externo, flujo, seguimiento  # noqa: E402
from estudio import investigacion as inv  # noqa: E402
from estudio import verificacion as ver  # noqa: E402

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>
<item><title>GTA 6 costara 80 dolares - Medio Dos</title><link>https://news.google.com/rss/articles/abc</link>
<pubDate>Mon, 16 Nov 2026 10:00:00 GMT</pubDate><source url="https://medio2.com">Medio Dos</source></item>
<item><title>Otra noticia sin fecha</title><link>https://news.google.com/rss/articles/def</link></item>
</channel></rss>"""


class Fase3(unittest.TestCase):
    def setUp(self):
        self.con = db.connect()
        for t in ("inv_refs", "notas", "investigaciones", "referencias", "afirmaciones", "afirm_evidencias", "afirm_historial",
                  "inv_afirm", "cronologia", "seguimientos", "trabajos", "aprobaciones"):
            self.con.execute(f"DELETE FROM {t}")
        self.con.commit()
        self.radar = radar_con_noticia()
        self.radar.execute("""INSERT INTO news(id,title,url,source,published_at,first_seen_at,summary,language,topics)
                              VALUES('n2','Nuevo rumor del precio en Argentina','https://ejemplo.com/ar','Medio Tres',
                              '2026-01-01T00:00:00Z','2026-01-01T00:00:00Z','precio filtrado','es','[]')""")
        self.radar.commit()
        self.i = inv.crear_inv(self.con, "Precio en Latinoamérica", pregunta="¿Cuánto costará?")
        r = inv.crear_ref(self.con, "noticia", "n1", radar=self.radar)
        inv.anadir_ref(self.con, self.i["id"], r["id"], "dice 80 dólares")
        ver.crear_afirm(self.con, "GTA 6 costará 80 dólares en México", self.i["id"])
        inv.nota(self.con, self.i["id"], "Buscar la fuente original", "pregunta")

    def test_1_seguimiento_y_asistente(self):
        seguimiento.seguir(self.con, self.i["id"], "precio\n\n")
        self.con.execute("UPDATE seguimientos SET revisado_en='2025-01-01T00:00:00Z'")
        busqueda.reconstruir(self.radar, self.con)
        nov = seguimiento.novedades(self.radar, self.con, self.i["id"])
        self.assertEqual([x["clave"] for x in nov], ["n2"])  # n1 ya está en la investigación: no es novedad
        txt = asistente.contexto(self.con, self.i["id"], self.radar)
        for s in ("[F1] El precio de GTA 6 en México", "[A1] «GTA 6 costará 80 dólares en México»", "[N1]",
                  "1 novedad(es)", "Nuevo rumor del precio en Argentina", "No incluye búsquedas en internet"):
            self.assertIn(s, txt)
        seguimiento.revisado(self.con, self.i["id"])
        self.assertEqual(seguimiento.novedades(self.radar, self.con, self.i["id"]), [])
        self.assertIn("No existe", asistente.contexto(self.con, "zzzzzz"))

    def test_2_google_news_sin_conexion_y_limite(self):
        externo._historial.clear()
        d = externo.google_news("GTA 6 precio", "latam", descargar=lambda url: RSS, ahora=1000)
        r = d["resultados"][0]
        self.assertEqual((r["titulo"], r["medio"], r["publicado_en"]), ("GTA 6 costara 80 dolares", "Medio Dos", "2026-11-16T10:00:00Z"))
        self.assertIsNone(d["resultados"][1]["publicado_en"])  # sin fecha: no se inventa
        with self.assertRaises(inv.NoValido):  # menos de 5 s
            externo.google_news("otra", descargar=lambda url: RSS, ahora=1002)
        for k in range(29):
            externo.google_news("x" + str(k), descargar=lambda url: RSS, ahora=1010 + k * 10)
        with self.assertRaises(inv.NoValido):  # 30 en la última hora
            externo.google_news("una más", descargar=lambda url: RSS, ahora=1400)
        ref = inv.crear_ref(self.con, "enlace", url=r["url"], titulo=r["titulo"], fuente=r["medio"], publicado_en=r["publicado_en"],
                            datos={"externo": "Google News"})
        self.assertEqual((ref["fuente"], ref["publicado_en"], ref["datos"]["externo"]), ("Medio Dos", "2026-11-16T10:00:00Z", "Google News"))

    def test_3_revision_y_calendario(self):
        p = nueva_pieza(self.con, "Pieza para revisar y programar")
        self.assertTrue(flujo.estado(self.con, p["id"])["espera_a_javier"])   # idea por aprobar
        flujo.aprobar(self.con, p["id"], "idea")
        self.assertFalse(flujo.estado(self.con, p["id"])["espera_a_javier"])  # ahora espera el guion (no a Javier)
        self.assertEqual(flujo.programar(self.con, p["id"], "2026-11-19")["fecha_prevista"], "2026-11-19")
        for mala in ("19/11/2026", "2026-02-30"):
            with self.assertRaises(flujo.Bloqueado):
                flujo.programar(self.con, p["id"], mala)
        self.assertIsNone(flujo.programar(self.con, p["id"], "")["fecha_prevista"])

    def test_4_crear_video_de_esto(self):
        idea = flujo.idea_a_mano("Precio de GTA 6 en Argentina", "", [{"titulo": "Nota", "url": "https://ejemplo.com/ar"},
                                                                     {"titulo": "mala", "url": "javascript:alert(1)"}], "Noticias")
        self.assertEqual(idea["fuentes"], [{"titulo": "Nota", "url": "https://ejemplo.com/ar"}])
        a = flujo.enviar_al_estudio(self.con, idea, "ultima_hora", ["tiktok"])
        b = flujo.enviar_al_estudio(self.con, idea, "ultima_hora", ["tiktok"])
        self.assertEqual(a["id"], b["id"])
        self.assertFalse(self.con.execute("SELECT COUNT(*) FROM aprobaciones WHERE trabajo_id=?", (a["id"],)).fetchone()[0])
        self.assertEqual(flujo.estado(self.con, a["id"])["etapa"], "Brief")


if __name__ == "__main__":
    unittest.main()

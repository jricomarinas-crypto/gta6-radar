"""Pruebas de verificación, cronología, dossier y paso a la Fábrica (fase 2A).

    python -m unittest tests.test_verificacion -v

Carpeta temporal (PC_RAIZ_PRUEBAS): no toca tus datos.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest

from tests.test_investigacion import radar_con_noticia  # carpeta temporal + Radar con una noticia

from estudio import db, dossier, ideas  # noqa: E402
from estudio import investigacion as inv  # noqa: E402
from estudio import verificacion as ver  # noqa: E402
from fabrica import encargo  # noqa: E402


class Verificacion(unittest.TestCase):
    def setUp(self):
        self.con = db.connect()
        for t in ("inv_refs", "notas", "investigaciones", "referencias", "afirmaciones", "afirm_evidencias",
                  "afirm_historial", "inv_afirm", "cronologia", "dossiers", "trabajos"):
            self.con.execute(f"DELETE FROM {t}")
        self.con.commit()
        self.radar = radar_con_noticia()
        self.i = inv.crear_inv(self.con, "Precio en Latinoamérica", pregunta="¿Cuánto costará?")
        self.noticia = inv.crear_ref(self.con, "noticia", "n1", radar=self.radar)
        self.oficial = inv.crear_ref(self.con, "enlace", url="https://www.rockstargames.com/newswire/x", titulo="Newswire")
        self.copia = inv.crear_ref(self.con, "enlace", url="https://blog.ejemplo.com/copia", titulo="Blog que repite")
        for r in (self.noticia, self.oficial, self.copia):
            inv.anadir_ref(self.con, self.i["id"], r["id"])

    def test_1_historial_y_regla_de_confirmado(self):
        a = ver.crear_afirm(self.con, "GTA 6 costará 80 dólares", self.i["id"], "Medio Uno", "", self.noticia["id"])
        self.assertIsNone(a["fecha_origen"])  # no se inventa
        for _ in range(5):  # cinco copias no confirman nada
            ver.evidencia(self.con, a["id"], self.copia["id"], "repite", independiente=True)
        a = ver.afirm(self.con, a["id"])
        self.assertEqual(a["cuentas"]["independientes"], 0)
        with self.assertRaises(inv.NoValido):
            ver.cambiar_estado(self.con, a["id"], "confirmado", "lo dicen todos")
        with self.assertRaises(inv.NoValido):  # sin nota tampoco
            ver.cambiar_estado(self.con, a["id"], "confirmado", "")
        ver.evidencia(self.con, a["id"], self.oficial["id"], "a_favor", independiente=True)
        a = ver.cambiar_estado(self.con, a["id"], "confirmado", "Lo publica Rockstar")
        self.assertEqual(a["etiqueta"], "CONFIRMADO")
        cambios = [h for h in a["historial"] if h["campo"] == "estado"]
        self.assertEqual((cambios[0]["antes"], cambios[0]["despues"]), ("pendiente", "confirmado"))
        self.assertTrue(any(h["campo"] == "creada" for h in a["historial"]))

    def test_2_cronologia_automatica_y_tres_fechas(self):
        a = ver.crear_afirm(self.con, "Saldrá también en PC en 2027", self.i["id"])
        ver.evidencia(self.con, a["id"], self.noticia["id"], "en_contra")
        ver.cambiar_estado(self.con, a["id"], "contradicho", "Rockstar no lo ha dicho")
        ev = ver.cronologia(self.con, inv_id=self.i["id"])
        tipos = [e["tipo"] for e in ev]
        self.assertEqual(tipos.count("publicacion"), 3)   # una por fuente, sin duplicar
        self.assertIn("rumor", tipos)
        self.assertIn("desmentido", tipos)
        pub = next(e for e in ev if e["ref_id"] == self.noticia["id"])
        self.assertIsNone(pub["ocurrio_en"])               # «ocurrió» desconocido: vacío
        self.assertTrue(pub["publicado_en"] and pub["detectado_en"])
        self.assertEqual(pub["fecha_usada"], "publicado")
        with self.assertRaises(inv.NoValido):              # los automáticos no se borran…
            ver.borrar_evento(self.con, pub["id"])
        ver.editar_evento(self.con, pub["id"], oculto=True)  # …se ocultan
        self.assertNotIn(pub["id"], [e["id"] for e in ver.cronologia(self.con, inv_id=self.i["id"])])
        with self.assertRaises(inv.NoValido):
            ver.evento(self.con, "anuncio", "Tráiler 3", self.i["id"], ocurrio_en="ayer")
        m = ver.evento(self.con, "anuncio", "Tráiler 3", self.i["id"], ocurrio_en="2026-11-01")
        ver.borrar_evento(self.con, m["id"])

    def test_3_dossier_congelado_con_incertidumbres_y_etiquetas(self):
        conf = ver.crear_afirm(self.con, "GTA 6 sale el 19 de noviembre", self.i["id"])
        ver.evidencia(self.con, conf["id"], self.oficial["id"], "a_favor", independiente=True)
        ver.cambiar_estado(self.con, conf["id"], "confirmado", "Fecha oficial")
        ver.crear_afirm(self.con, "Costará 80 dólares en México", self.i["id"])
        bulo = ver.crear_afirm(self.con, "Habrá demo gratuita antes", self.i["id"])
        ver.evidencia(self.con, bulo["id"], self.oficial["id"], "en_contra")
        ver.cambiar_estado(self.con, bulo["id"], "contradicho", "No hay demo")
        d1 = dossier.guardar(self.con, self.i["id"])
        c = d1["contenido"]["afirmaciones"]
        self.assertEqual([a["etiqueta"] for a in c["confirmadas"]], ["CONFIRMADO"])
        self.assertEqual([a["etiqueta"] for a in c["incertidumbres"]], ["RUMOR"])
        self.assertEqual(len(c["contradichas"]), 1)
        self.assertIn("Incertidumbres", d1["markdown"])
        self.assertTrue(set(ver.ETIQUETA.values()) - {"DESMENTIDO"} <= {"CONFIRMADO", "REPORTADO", "RUMOR", "OPINIÓN"})
        ver.crear_afirm(self.con, "Una afirmación posterior al dossier", self.i["id"])
        self.assertEqual(len(dossier.obtener(self.con, d1["id"])["contenido"]["afirmaciones"]["incertidumbres"]), 1)  # congelado
        self.assertEqual(dossier.guardar(self.con, self.i["id"])["n"], 2)

    def test_4_idea_en_la_fabrica_sin_duplicar_y_encargo(self):
        a = ver.crear_afirm(self.con, "Habrá demo gratuita antes", self.i["id"])
        ver.evidencia(self.con, a["id"], self.oficial["id"], "en_contra")
        ver.cambiar_estado(self.con, a["id"], "contradicho", "No hay demo")
        d = dossier.guardar(self.con, self.i["id"])
        with self.assertRaises(inv.NoValido):
            dossier.crear_idea(self.con, d["id"], "lista_pais", [])
        p1 = dossier.crear_idea(self.con, d["id"], "lista_pais", ["tiktok"])
        p2 = dossier.crear_idea(self.con, d["id"], "lista_pais", ["tiktok"])
        self.assertEqual(p1["id"], p2["id"])
        idea = db.trabajo(self.con, p1["id"])["idea"]
        self.assertEqual((idea["investigacion_id"], idea["dossier_id"], idea["dossier_n"]), (self.i["id"], d["id"], 1))
        self.assertEqual(idea["no_afirmar"], ["Habrá demo gratuita antes"])  # contradicha: no se afirma
        self.assertNotIn("verdad", ideas.VARIANTES["lista_pais"][1].lower())
        self.assertFalse(self.con.execute("SELECT COUNT(*) FROM aprobaciones WHERE trabajo_id=?", (p1["id"],)).fetchone()[0])
        self.assertEqual(dossier.obtener(self.con, d["id"])["piezas"][0]["id"], p1["id"])
        out = io.StringIO()
        argv = sys.argv
        try:
            sys.argv = ["encargo", p1["id"]]
            with contextlib.redirect_stdout(out):
                encargo.main()
        finally:
            sys.argv = argv
        self.assertIn("NO AFIRMAR", out.getvalue())
        self.assertIn(f"DOSSIER v1 de la investigación {self.i['id']}", out.getvalue())


if __name__ == "__main__":
    unittest.main()

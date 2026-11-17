"""Pruebas del vídeo de fondo real y de tu voz grabada.

    python -m unittest tests.test_broll_voz -v

Sin internet: los «clips de Miami» son clips generados con ffmpeg y las «tomas» son tonos.
Todo pasa en una carpeta temporal (PC_RAIZ_PRUEBAS).
"""
from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from tests.test_corte1 import RAIZ, DEMO, nueva_pieza, poner_guion, voz_simulada  # prepara PATH y carpeta temporal

from estudio import db, flujo  # noqa: E402
from fabrica import broll, cola, exportar  # noqa: E402
from podcast import tts  # noqa: E402


def tono_wav(segundos: float = 1.6) -> bytes:
    f = RAIZ / "tono.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=220:duration={segundos}",
                    "-ac", "1", "-ar", "24000", str(f)], check=True)
    return f.read_bytes()


def grabar_todo(con, tid: str) -> None:
    for i in range(len(DEMO["escenas"])):
        flujo.guardar_toma(con, tid, i, tono_wav(), "audio/wav")


class FondoYVoz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tts.synthesize = voz_simulada
        os.environ.pop("PEXELS_API_KEY", None)
        cls.clips = RAIZ / "broll"
        cls.clips.mkdir(parents=True, exist_ok=True)
        broll.CARPETA, broll.CACHE = cls.clips, cls.clips / "_pexels"
        for i, fuente in enumerate(["testsrc2=size=720x1280:rate=30:duration=3", "smptebars=size=720x1280:rate=30:duration=3"]):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", fuente, "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", str(cls.clips / f"miami_{i}.mp4")], check=True)
        cls.con = db.connect()

    def test_1_filtro_excluye_material_de_terceros(self):
        self.assertTrue(broll.excluido("https://www.pexels.com/video/gta-6-gameplay-trailer-123/"))
        self.assertTrue(broll.excluido("Rockstar logo"))
        self.assertFalse(broll.excluido("https://www.pexels.com/video/miami-beach-at-sunset-456/"))

    def test_2_sin_clips_usa_fondo_grafico_y_lo_explica(self):
        vacia = RAIZ / "vacia"
        vacia.mkdir(exist_ok=True)
        antes = broll.CARPETA, broll.CACHE
        broll.CARPETA, broll.CACHE = vacia, vacia / "_pexels"
        try:
            clips, motivo = broll.elegir(3, "x")
        finally:
            broll.CARPETA, broll.CACHE = antes
        self.assertEqual(clips, [])
        self.assertIn("fondo gráfico", motivo)

    def test_3_tu_voz_y_fondo_real_de_punta_a_punta(self):
        con = self.con
        t = nueva_pieza(con, "Fondo real y mi voz", fondo="video", voz="propia")
        flujo.aprobar(con, t["id"], "idea")
        poner_guion(t)
        flujo.aprobar(con, t["id"], "guion")
        with self.assertRaises(flujo.Bloqueado) as ctx:  # faltan las tomas
            flujo.crear_video(con, t["id"])
        self.assertIn("escena", str(ctx.exception))
        grabar_todo(con, t["id"])
        st = flujo.estado(con, t["id"])
        self.assertTrue(all(x["valida"] for x in st["tomas"]))
        v = flujo.crear_video(con, t["id"])
        cola.procesar_pendientes(con)
        v = db.version(con, v["id"])
        self.assertEqual(v["estado_produccion"], "listo", v["error"])
        self.assertEqual(v["opciones"]["fondo_usado"], "video")
        self.assertEqual(v["opciones"]["voz"], "propia")
        info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                               "-of", "csv=p=0", v["video_ruta"]], capture_output=True, text=True).stdout.strip()
        self.assertEqual(info, "1080,1920")
        flujo.aprobar(con, t["id"], "video")
        res = flujo.exportar(con, t["id"])
        txt = Path(str(Path(res["tiktok"]["ruta"]).with_suffix("")) + ".txt").read_text()
        self.assertNotIn("voces sintéticas", txt)
        shorts = Path(str(Path(res["shorts"]["ruta"]).with_suffix("")) + ".txt").read_text()
        self.assertIn(exportar.AVISO_PROPIA, shorts)
        man = json.loads(Path(str(Path(res["shorts"]["ruta"]).with_suffix("")) + ".manifiesto.json").read_text())
        self.assertEqual((man["voz"], man["fondo"]), ("propia", "video"))

    def test_4_regrabar_o_cambiar_el_texto_anula_lo_aprobado(self):
        con = self.con
        t = nueva_pieza(con, "Regrabar tras aprobar", fondo="grafico", voz="propia")
        flujo.aprobar(con, t["id"], "idea")
        poner_guion(t)
        flujo.aprobar(con, t["id"], "guion")
        grabar_todo(con, t["id"])
        flujo.crear_video(con, t["id"])
        cola.procesar_pendientes(con)
        flujo.aprobar(con, t["id"], "video")
        self.assertTrue(flujo.estado(con, t["id"])["aprobado"]["video"])
        flujo.guardar_toma(con, t["id"], 2, tono_wav(2.0), "audio/wav")  # nueva toma de la escena 3
        st = flujo.estado(con, t["id"])
        self.assertFalse(st["aprobado"]["video"])
        self.assertEqual(st["etapa"], "Montaje")
        g = json.loads(json.dumps(DEMO))
        g["escenas"][1]["texto"] = "Texto distinto: hay que volver a grabar."
        poner_guion(t, g)
        st = flujo.estado(con, t["id"])
        self.assertFalse(st["tomas"][1]["valida"])
        self.assertIn("vuelve a grabarla", st["tomas"][1]["aviso"])

    def test_5_toma_vacia_o_formato_raro_se_rechaza(self):
        con = self.con
        t = nueva_pieza(con, "Tomas no válidas", voz="propia")
        flujo.aprobar(con, t["id"], "idea")
        poner_guion(t)
        with self.assertRaises(flujo.Bloqueado):
            flujo.guardar_toma(con, t["id"], 0, b"", "audio/wav")
        with self.assertRaises(flujo.Bloqueado):
            flujo.guardar_toma(con, t["id"], 0, b"hola", "text/html")
        with self.assertRaises(flujo.Bloqueado):
            flujo.guardar_toma(con, t["id"], 99, tono_wav(), "audio/wav")


if __name__ == "__main__":
    unittest.main()

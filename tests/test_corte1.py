"""Pruebas del corte 1 (criterios de aceptación del megaprompt §14).

    python -m unittest tests.test_corte1 -v

Todo pasa en una carpeta temporal (PC_RAIZ_PRUEBAS): no toca tu base de datos ni tu carpeta de Películas.
La voz es un tono simulado (sin internet); el montaje con ffmpeg es real.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

RAIZ = Path(tempfile.mkdtemp(prefix="pc_pruebas_"))
os.environ["PC_RAIZ_PRUEBAS"] = str(RAIZ)
for p in ("/opt/homebrew/bin", "/opt/homebrew/opt/ffmpeg-full/bin"):  # el último queda primero: ffmpeg con libass
    if Path(p).exists():
        os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

from estudio import db, flujo  # noqa: E402
from fabrica import cola  # noqa: E402
from podcast import tts  # noqa: E402

DEMO = json.loads((Path(__file__).resolve().parent.parent / "examples" / "guion_escenas_demo.json").read_text())
SINTESIS_REAL = tts.synthesize


def voz_simulada(lines, hosts, workdir):
    """Sustituye a Edge TTS: un tono por frase, con la duración proporcional a las palabras."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, ln in enumerate(lines):
        dur = 0.32 * len(ln["text"].split()) + 0.3
        wav = workdir / f"l{i:03d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={dur:.2f}",
                        "-ac", "1", "-ar", str(tts.SR), "-c:a", "pcm_s16le", str(wav)], check=True)
        with wave.open(str(wav)) as w:
            d = w.getnframes() / w.getframerate()
        out.append({**ln, "wav": str(wav), "duration": d, "words": tts._align(ln["text"], [], d)})
    return out


def voz_caida(lines, hosts, workdir):
    raise ConnectionError("proveedor de voz caído (simulado)")


def nueva_pieza(con, titulo="Pieza de prueba del corte 1") -> dict:
    return flujo.enviar_al_estudio(con, flujo.idea_a_mano(titulo, "prueba"), "guia", ["tiktok", "shorts"])


def poner_guion(t: dict, g: dict | None = None) -> Path:
    ruta = flujo.ruta_guion(t)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(g or DEMO, ensure_ascii=False), encoding="utf-8")
    return ruta


def hasta_video_aprobado(con, titulo) -> dict:
    t = nueva_pieza(con, titulo)
    flujo.aprobar(con, t["id"], "idea")
    poner_guion(t)
    flujo.aprobar(con, t["id"], "guion")
    flujo.crear_video(con, t["id"])
    cola.procesar_pendientes(con)
    flujo.aprobar(con, t["id"], "video")
    return t


class Corte1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tts.synthesize = voz_simulada
        cls.con = db.connect()

    @classmethod
    def tearDownClass(cls):
        tts.synthesize = SINTESIS_REAL
        shutil.rmtree(RAIZ, ignore_errors=True)

    def test_1_recorrido_completo(self):
        con = self.con
        t = nueva_pieza(con, "Recorrido completo")
        self.assertEqual(flujo.estado(con, t["id"])["etapa"], "Brief")
        flujo.aprobar(con, t["id"], "idea")
        self.assertEqual(flujo.estado(con, t["id"])["guion"]["estado"], "falta")
        poner_guion(t)
        st = flujo.aprobar(con, t["id"], "guion")
        self.assertTrue(st["aprobado"]["guion"])
        v = flujo.crear_video(con, t["id"])
        self.assertEqual(v["estado_produccion"], "pendiente")
        cola.procesar_pendientes(con)
        v = db.version(con, v["id"])
        self.assertEqual(v["estado_produccion"], "listo", v["error"])
        info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                          "stream=width,height", "-of", "json", v["video_ruta"]],
                                         capture_output=True, text=True, check=True).stdout)["streams"][0]
        self.assertEqual((info["width"], info["height"]), (1080, 1920))
        self.assertTrue(Path(v["srt_ruta"]).read_text().startswith("1\n00:00:"))
        self.assertEqual(flujo.estado(con, t["id"])["etapa"], "Revisión")
        flujo.aprobar(con, t["id"], "video")
        res = flujo.exportar(con, t["id"])
        self.assertEqual(set(res), {"tiktok", "shorts"})
        st = flujo.estado(con, t["id"])
        for pl in ("tiktok", "shorts"):
            self.assertTrue(st["exportacion"][pl]["disponible"], st["exportacion"][pl])
            base = Path(res[pl]["ruta"]).with_suffix("")
            for ext in (".mp4", ".txt", ".srt", ".manifiesto.json"):
                self.assertTrue(Path(str(base) + ext).exists(), ext)
        self.assertTrue(Path(str(Path(res["tiktok"]["ruta"]).with_suffix("")) + "_portada.jpg").exists())
        man = json.loads(Path(str(Path(res["shorts"]["ruta"]).with_suffix("")) + ".manifiesto.json").read_text())
        self.assertEqual(man["version"], 1)
        self.assertIn("video", man["aprobaciones"])

    def test_2_exportar_dos_veces_no_duplica(self):
        con = self.con
        t = hasta_video_aprobado(con, "Exportar dos veces")
        flujo.exportar(con, t["id"])
        carpeta = rutas_dia()
        antes = sorted(p.name for p in carpeta.rglob("*") if p.is_file())
        res = flujo.exportar(con, t["id"])
        despues = sorted(p.name for p in carpeta.rglob("*") if p.is_file())
        self.assertEqual(antes, despues)
        self.assertTrue(all("ya exportado" in r["estado"] for r in res.values()))

    def test_3_editar_guion_invalida_aprobaciones(self):
        con = self.con
        t = hasta_video_aprobado(con, "Editar tras aprobar")
        g = json.loads(json.dumps(DEMO))
        g["escenas"][2]["texto"] = "Primer paso cambiado después de aprobar."
        poner_guion(t, g)
        st = flujo.estado(con, t["id"])
        self.assertFalse(st["aprobado"]["guion"])
        self.assertFalse(st["aprobado"]["video"])
        self.assertIn("cambió", st["siguiente"])
        with self.assertRaises(flujo.Bloqueado):
            flujo.exportar(con, t["id"])

    def test_4_fallo_de_voz_se_reintenta_sin_perder_el_guion(self):
        con = self.con
        t = nueva_pieza(con, "Fallo de voz")
        flujo.aprobar(con, t["id"], "idea")
        g = json.loads(json.dumps(DEMO))
        g["escenas"][0]["texto"] = "Frase nueva que no está en la caché de voces."
        poner_guion(t, g)
        flujo.aprobar(con, t["id"], "guion")
        tts.synthesize = voz_caida
        try:
            v = flujo.crear_video(con, t["id"])
            cola.procesar_pendientes(con)
        finally:
            tts.synthesize = voz_simulada
        v = db.version(con, v["id"])
        self.assertEqual(v["estado_produccion"], "fallido")
        self.assertIn("No pudimos generar la voz", v["error"])
        self.assertEqual(v["guion"]["escenas"][0]["texto"], g["escenas"][0]["texto"])  # el guion sigue ahí
        flujo.reintentar(con, t["id"])
        cola.procesar_pendientes(con)
        self.assertEqual(db.version(con, v["id"])["estado_produccion"], "listo")

    def test_5_crear_no_duplica(self):
        con = self.con
        idea = flujo.idea_a_mano("Idea repetida dos veces", "")
        a = flujo.enviar_al_estudio(con, idea, "guia", ["tiktok"])
        b = flujo.enviar_al_estudio(con, idea, "guia", ["tiktok"])
        self.assertEqual(a["id"], b["id"])
        flujo.aprobar(con, a["id"], "idea")
        poner_guion(a)
        flujo.aprobar(con, a["id"], "guion")
        v1 = flujo.crear_video(con, a["id"])
        v2 = flujo.crear_video(con, a["id"])
        self.assertEqual(v1["id"], v2["id"])
        flujo.cancelar(con, a["id"])
        self.assertEqual(db.version(con, v1["id"])["etapa"], "Cancelado")

    def test_6_sin_guion_o_sin_aprobar_se_bloquea(self):
        con = self.con
        t = nueva_pieza(con, "Sin guion todavía")
        with self.assertRaises(flujo.Bloqueado):
            flujo.aprobar(con, t["id"], "guion")  # falta aprobar la idea
        flujo.aprobar(con, t["id"], "idea")
        with self.assertRaises(flujo.Bloqueado):
            flujo.aprobar(con, t["id"], "guion")  # no hay archivo de guion
        with self.assertRaises(flujo.Bloqueado):
            flujo.crear_video(con, t["id"])
        with self.assertRaises(flujo.Bloqueado):
            flujo.exportar(con, t["id"])

    def test_7_guion_no_valido_explica_los_errores(self):
        con = self.con
        t = nueva_pieza(con, "Guion con errores")
        flujo.aprobar(con, t["id"], "idea")
        g = json.loads(json.dumps(DEMO))
        g["escenas"][1]["afirmaciones"][0]["fuente"] = "sin-url"
        g["escenas"][1]["afirmaciones"][0]["etiqueta"] = "RUMOR"
        poner_guion(t, g)
        st = flujo.estado(con, t["id"])
        self.assertEqual(st["guion"]["estado"], "no_valido")
        self.assertTrue(any("fuente" in e for e in st["guion"]["errores"]))
        self.assertTrue(any("rumor" in e.lower() for e in st["guion"]["errores"]))

    def test_8_exportacion_fallida_no_dice_disponible(self):
        con = self.con
        t = hasta_video_aprobado(con, "Exportación fallida")
        base = RAIZ / "Punto de Control"
        base.mkdir(parents=True, exist_ok=True)
        carpetas = [base, *[p for p in base.rglob("*") if p.is_dir()]]
        for c in carpetas:
            os.chmod(c, 0o500)  # sin permiso de escritura
        try:
            with self.assertRaises(flujo.Bloqueado) as ctx:
                flujo.exportar(con, t["id"])
            self.assertIn("carpeta del Mac", str(ctx.exception))
        finally:
            for c in carpetas:
                os.chmod(c, 0o755)
        st = flujo.estado(con, t["id"])
        self.assertFalse(any(e.get("disponible") for e in st["exportacion"].values()))
        flujo.exportar(con, t["id"])  # con permisos, ahora sí
        self.assertTrue(all(e["disponible"] for e in flujo.estado(con, t["id"])["exportacion"].values()))


def rutas_dia() -> Path:
    from estudio import rutas
    return rutas.carpeta_base()


if __name__ == "__main__":
    unittest.main()

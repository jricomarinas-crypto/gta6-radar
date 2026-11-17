"""Crea una base de datos de DEMOSTRACIÓN (datos inventados) para ver el panel sin claves.

    python tools/datos_demo.py      → data/demo.db y site/index.html
"""
from __future__ import annotations

import random
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar import dashboard, scoring, trends, vigilancia  # noqa: E402
from radar.config import DATA_DIR  # noqa: E402
from radar.db import connect, iso, jdump, kv_set, now  # noqa: E402

random.seed(19)
CREATORS = [("Canal Demo Noticias", 1_200_000, "es"), ("Canal Demo Análisis", 380_000, "es"),
            ("Demo Gaming MX", 2_400_000, "es"), ("Demo Leaks", 95_000, "en"), ("Pequeño Canal Demo", 8_000, "es"),
            ("Demo Tech", 640_000, "en"), ("Demo Clips", 22_000, "es"), ("Demo Reacciones", 150_000, "es")]
VIDEOS = [
    ("¿A cuántos FPS irá GTA 6 en PS5 y PS5 Pro? Lo que se sabe", "analysis", ["rendimiento_fps"], "low", "reported", 0.6),
    ("GTA 6: todo lo que llega el 19 de noviembre (horarios y precarga)", "news", ["lanzamiento"], "low", "official", 0.7),
    ("FILTRADO: supuesta lista de armas de GTA 6", "leak", ["filtraciones_rumores"], "high", "unverified", 0.5),
    ("GTA 5 vs GTA 6: 20 cambios que vas a notar", "comparison", ["comparativa_gta5", "gameplay"], "low", "opinion", 0.4),
    ("El mapa de Leonida, comparado con Los Santos", "analysis", ["mapa"], "low", "reported", 0.5),
    ("¿GTA 6 en PC? Lo que dijo Take-Two", "news", ["plataformas_pc"], "low", "reported", 0.6),
    ("Reacción a la última noticia de GTA 6", "reaction", ["reacciones"], "low", "opinion", 0.2),
    ("Teoría: el final de Lucía y Jason", "theory", ["historia", "personajes"], "medium", "unverified", 0.3),
    ("GTA 6 meme compilation", "meme", ["humor_memes"], "low", "n/a", 0.1),
    ("Rumor: ¿retraso de GTA 6 en algunas regiones?", "rumor", ["filtraciones_rumores", "lanzamiento"], "high", "unverified", 0.4),
    ("Precio de GTA 6: ediciones y lo que incluye cada una", "news", ["precio_ediciones"], "low", "reported", 0.5),
    ("Probé a contar los coches del tráiler de GTA 6", "analysis", ["vehiculos"], "low", "opinion", 0.4),
]


def series_demo(con) -> None:
    """Series de 90 días para las gráficas de Hoy (DEMO, reproducibles). Incluyen a propósito los casos difíciles:
    un día a cero, un día sin datos, métricas que empiezan más tarde y una plataforma sin datos al principio."""
    from radar import diario
    rng = random.Random(7)
    h = diario.hoy()
    dia = lambda i: (h - timedelta(days=i)).isoformat()  # noqa: E731
    con.executescript(diario.SCHEMA)
    for i in range(89, -1, -1):
        if i == 5:
            continue  # día sin ninguna ejecución del Radar → «sin datos», no cero
        crece = 1 + (89 - i) / 30
        pub = 0 if i == 9 else int(rng.uniform(18, 40) * crece)
        det = 0 if i == 9 else int(pub * rng.uniform(0.8, 1.2))
        mvh = round(rng.uniform(4000, 22000) * crece) if i <= 20 else None  # el máximo solo se guarda desde hace 20 días
        con.execute("INSERT OR REPLACE INTO radar_diario(fecha,publicados,detectados,max_vistas_hora,origen,actualizado_en) "
                    "VALUES(?,?,?,?,'demo',?)", (dia(i), pub, det, mvh, iso()))
    canal, prod = [], []
    for i in range(89, -1, -1):
        canal.append({"fecha": dia(i),
                      "tiktok": None if i > 60 or i == 3 else int(rng.uniform(800, 6000) * (1 + (60 - i) / 25)),
                      "shorts": None if i > 45 else (0 if i == 12 else int(rng.uniform(300, 2500) * (1 + (45 - i) / 30))),
                      "largo": None if i > 20 else int(rng.uniform(100, 900))})
        prod.append({"fecha": dia(i), **({"fabricados": None, "aprobados": None, "publicados": None} if i > 25 else
                                          {"fabricados": rng.choice([0, 1, 2, 3]), "aprobados": rng.choice([0, 0, 1, 2]),
                                           "publicados": rng.choice([0, 0, 1, 2])})})
    kv_set(con, "demo_canal", jdump(canal))
    kv_set(con, "demo_produccion", jdump(prod))
    con.commit()


def main():
    path = DATA_DIR / "demo.db"
    path.unlink(missing_ok=True)
    con = connect(path)
    t = now()
    for i, (name, subs, lang) in enumerate(CREATORS):
        con.execute("""INSERT INTO creators(id,platform,external_id,name,subscribers,language,first_seen_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?)""", (f"youtube:DEMO{i}", "youtube", f"DEMO{i}", name, subs, lang, iso(), iso()))
    n = 0
    for rep in range(5):
        for j, (title, ctype, topics, risk, ver, nov) in enumerate(VIDEOS):
            ci = random.randrange(len(CREATORS))
            name, subs, lang = CREATORS[ci]
            age_h = random.uniform(0.5, 46)
            vel = max(50, random.lognormvariate(7.2, 1.3) * (subs / 400_000) ** 0.35)
            if ci == 4 and rep == 0:
                vel = 2500  # creador pequeño que despunta
            views = int(vel * age_h * random.uniform(0.7, 1.3))
            vid = f"youtube:demo{n}"
            pub = t - timedelta(hours=age_h)
            con.execute(
                """INSERT INTO videos(id,platform,external_id,creator_id,title,description,url,published_at,duration_s,
                   is_short,language,found_via,views,likes,comments,velocity,is_related,content_type,topics,entities,
                   sentiment,risk_level,novelty,summary,key_claims,verification,classified_at,first_seen_at,last_scraped_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (vid, "youtube", f"demo{n}", f"youtube:DEMO{ci}", title + (f" #{rep + 1}" if rep else ""), "",
                 "https://www.youtube.com/results?search_query=" + quote_plus(title), iso(pub), random.choice([45, 58, 480, 720, 1260]), int(rep % 3 == 0), lang,
                 random.choice(["búsqueda", "tendencias MX", "canal vigilado"]), views, int(views * random.uniform(.02, .06)),
                 int(views * random.uniform(.002, .01)), vel, 1, ctype, jdump(topics), jdump(["Rockstar Games"]),
                 "neutral", risk, nov, "Resumen de demostración del vídeo.", jdump(["Afirmación de ejemplo"]), ver,
                 iso(), iso(pub), iso()))
            con.execute("INSERT INTO snapshots(video_id,captured_at,views,likes,comments) VALUES(?,?,?,?,?)",
                        (vid, iso(), views, 0, 0))
            n += 1
    for k, (src, title, ver, off) in enumerate([
        ("Medio Demo", "Rockstar confirma la hora de desbloqueo (demo)", "official", 1),
        ("Otro Medio Demo", "Análisis técnico del rendimiento en consolas (demo)", "reported", 0),
        ("Medio Demo EN", "Rumour roundup ahead of launch (demo)", "unverified", 0)]):
        con.execute("""INSERT INTO news(id,source,title,url,published_at,language,is_official,is_related,topics,verification,
                       novelty,ai_summary,classified_at,first_seen_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (f"n{k}", src, title, "https://example.com/", iso(t - timedelta(hours=3 + k * 5)),
                     "en" if "EN" in src else "es", off, 1, jdump(["lanzamiento"]), ver, 0.8, "Resumen de demostración.", iso(), iso()))
    kv_set(con, "community_questions", jdump({"preguntas": [
        {"pregunta": "¿A qué hora se desbloquea en mi país?", "frecuencia": "alta"},
        {"pregunta": "¿Tendrá modo 60 FPS en PS5 Pro?", "frecuencia": "alta"},
        {"pregunta": "¿Cuándo sale en PC?", "frecuencia": "media"}], "opiniones": ["Opinión de ejemplo"]}))
    kv_set(con, "ideas_hoy", jdump({"fecha": t.strftime("%Y-%m-%d"), "ideas": [
        {"titulo": "GTA 6: a qué hora se desbloquea en cada país de Latinoamérica", "formato": "short",
         "tema": "lanzamiento", "por_que": "Ejemplo: el tema con más demanda y casi sin vídeos en español."},
        {"titulo": "GTA 6 en PS5 Pro: ¿vale la pena para 60 FPS?", "formato": "episodio",
         "tema": "rendimiento_fps", "por_que": "Ejemplo: los análisis rinden x3 sobre lo normal esta semana."},
        {"titulo": "Precio de GTA 6 en pesos: qué edición conviene", "formato": "short",
         "tema": "precio_ediciones", "por_que": "Ejemplo: pregunta repetida en comentarios y poca oferta en español."}]}))
    con.execute("INSERT INTO runs(kind,started_at,finished_at,stats) VALUES('radar',?,?,'{}')", (iso(), iso()))
    con.commit()
    scoring.score_videos(con)
    vigilancia.actualizar_lista(con)
    series_demo(con)
    trends.detect_alerts(con)
    out = dashboard.build(con, demo=True)
    print("Panel de demostración:", out)


if __name__ == "__main__":
    main()

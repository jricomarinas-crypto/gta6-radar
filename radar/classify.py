"""Clasificación con IA (fase ligera): tema, tipo, entidades, riesgo, novedad y resumen."""
from __future__ import annotations

from .config import cfg
from .db import iso, jdump
from .llm import ask_json

TOPICS = [
    "lanzamiento", "precio_ediciones", "plataformas_pc", "rendimiento_fps", "mapa", "personajes",
    "historia", "gameplay", "vehiculos", "online", "trailer", "filtraciones_rumores", "comparativa_gta5",
    "graficos_tecnologia", "polemica", "humor_memes", "reacciones", "guias_trucos", "ventas_negocio", "otros",
]
CONTENT_TYPES = [
    "trailer", "gameplay", "leak", "rumor", "news", "analysis", "theory", "reaction", "review",
    "comparison", "meme", "interview", "stream", "short", "podcast", "guide", "other",
]

SYSTEM = f"""Eres el clasificador del radar de contenido sobre GTA 6 (Grand Theft Auto VI, de Rockstar Games).
Recibes una lista de piezas (vídeos de YouTube o noticias) con título, descripción y metadatos.
Para cada una devuelve un objeto con:
- id: el mismo id recibido
- is_related: true si trata realmente sobre GTA 6 (no GTA 5 Online, no clickbait sin relación)
- content_type: uno de {CONTENT_TYPES}
- topics: 1-3 de {TOPICS}
- entities: personas, personajes, lugares, plataformas o empresas mencionadas (máx. 6)
- language: código de idioma (es, en, pt…)
- sentiment: positive | neutral | negative | mixed
- risk_level: low | medium | high | critical  (riesgo de desinformación, filtración no verificada,
  copyright, contenido sexualizado, polémica o clickbait engañoso)
- novelty: 0-1 (¿aporta información nueva: anuncio oficial, dato inédito, análisis original?)
- summary: 1 frase en español, neutral, sin exagerar
- key_claims: lista de afirmaciones concretas que hace (máx. 3), en español
- verification: official (fuente Rockstar/Take-Two) | reported (medio fiable citando fuente) |
  unverified (rumor/filtración) | opinion | n/a
No inventes nada que no esté en el texto. Responde SOLO con un array JSON."""


def _payload(rows, kind):
    items = []
    for r in rows:
        if kind == "video":
            items.append({
                "id": r["id"], "tipo": "video", "titulo": r["title"], "canal": r["cname"],
                "descripcion": (r["description"] or "")[:500], "duracion_s": r["duration_s"],
                "vistas": r["views"], "publicado": r["published_at"],
            })
        else:
            items.append({
                "id": r["id"], "tipo": "noticia", "titulo": r["title"], "medio": r["source"],
                "resumen": (r["summary"] or "")[:400], "publicado": r["published_at"],
            })
    return items


def classify_pending(con) -> int:
    limit = int(cfg()["radar"].get("clasificar_max_por_ejecucion", 120))
    vids = con.execute(
        """SELECT v.*, c.name AS cname FROM videos v LEFT JOIN creators c ON c.id=v.creator_id
           WHERE v.classified_at IS NULL ORDER BY v.views DESC LIMIT ?""", (limit,)).fetchall()
    news = con.execute("SELECT * FROM news WHERE classified_at IS NULL ORDER BY published_at DESC LIMIT ?",
                       (max(20, limit // 3),)).fetchall()
    done = 0
    model = cfg()["ia"]["modelo_rapido"]
    for kind, rows in (("video", vids), ("news", news)):
        for i in range(0, len(rows), 25):
            batch = rows[i : i + 25]
            try:
                res = ask_json(jdump(_payload(batch, kind)), system=SYSTEM, model=model, max_tokens=8000)
            except Exception as e:  # noqa: BLE001
                print(f"  [IA] clasificación falló: {e}")
                continue
            by_id = {str(x.get("id")): x for x in res if isinstance(x, dict)}
            for r in batch:
                x = by_id.get(r["id"])
                if not x:
                    continue
                vals = (
                    1 if x.get("is_related", True) else 0, x.get("content_type"), jdump(x.get("topics") or []),
                    jdump(x.get("entities") or []), x.get("sentiment"), x.get("risk_level"),
                    float(x.get("novelty") or 0), x.get("summary"), jdump(x.get("key_claims") or []),
                    x.get("verification"), iso(), r["id"],
                )
                if kind == "video":
                    con.execute("""UPDATE videos SET is_related=?,content_type=?,topics=?,entities=?,sentiment=?,
                        risk_level=?,novelty=?,summary=?,key_claims=?,verification=?,classified_at=? WHERE id=?""", vals)
                    lang = x.get("language")
                    if lang:
                        con.execute("UPDATE videos SET language=COALESCE(NULLIF(language,''),?) WHERE id=?", (lang, r["id"]))
                else:
                    con.execute("""UPDATE news SET is_related=?,content_type=?,topics=?,entities=?,sentiment=?,
                        risk_level=?,novelty=?,ai_summary=?,key_claims=?,verification=?,classified_at=? WHERE id=?""", vals)
                done += 1
            con.commit()
    print(f"  [IA] clasificadas {done} piezas")
    return done

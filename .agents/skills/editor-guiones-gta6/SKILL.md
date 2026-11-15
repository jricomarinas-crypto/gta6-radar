---
name: editor-guiones-gta6
description: Revisar o editar un episodio del podcast de GTA 6 (guion.json, dossier.md, editor.md, título, miniatura, Shorts, presentadores, formatos). Úsala cuando Javier quiera revisar el episodio de hoy, cambiar un título, reescribir un guion o crear un formato nuevo.
---

# Editor de guiones — podcast de GTA 6

## Archivos de un episodio (`output/<fecha>/` o el artifact `episodio-N` de GitHub)
- `dossier.md`: hechos verificados con etiqueta y URL (la única fuente válida de datos)
- `guion.json`: el episodio (esquema abajo)
- `editor.md`: informe del Agente Editor (problemas encontrados y correcciones aplicadas)
- `episodio.mp4`, `short_N.mp4`, `miniatura.jpg`, `descripcion.txt`

## Esquema de `guion.json`
```json
{"formato": "noticias|a_fondo|verdad_o_bulo|debate|comunidad|gta5_vs_gta6",
 "titulo": "≤70", "titulo_miniatura": "2-4 PALABRAS", "subtitulo_miniatura": "≤5 palabras",
 "descripcion": "...", "etiquetas": [], "temas_clave": [],
 "segmentos": [{"capitulo": "≤32", "tarjeta": {"titular": "≤40", "detalle": "≤70",
   "estado": "CONFIRMADO|REPORTADO|RUMOR|OPINIÓN", "fuente": "≤40"},
   "lineas": [{"habla": "A|B", "texto": "..."}]}],
 "shorts": [{"segmento": 2, "titulo": "≤60", "gancho": "≤6 palabras"}],
 "fuentes": [{"titulo": "...", "url": "https://..."}]}
```
A = Leo (analista, datos, tranquilo) · B = Sofi (fan desde Vice City, energía, preguntas de la comunidad). Definidos en `config.yaml → podcast.presentadores`.

## Criterios editoriales
1. **Cada dato sale del dossier.** Si no está, fuera. Un rumor se dice como rumor ("se rumorea", "según un filtrador, sin confirmar").
2. **Título honesto**: promete exactamente lo que da el episodio, incluye "GTA 6", ≤ 70 caracteres. Nada de "CONFIRMADO" si es rumor.
3. **Miniatura**: 2-4 palabras grandes; la pregunta o el dato clave. Sin logos ni arte de Rockstar.
4. **Gancho** en los primeros 15-25 s con el dato más fuerte; presentación después.
5. **Shorts**: segmentos de 120-180 palabras que se entiendan solos; el gancho funciona sin contexto.
6. **Español neutro latinoamericano**: "ustedes", nada de "vosotros", "mola" o "tío".
7. **Voz**: frases cortas (se van a oír, no a leer). Siglas que suenan mal → añadirlas a `podcast.pronunciacion` en `config.yaml`.
8. **Política de YouTube**: no copiar ni narrar vídeos de otros creadores; no describir con detalle material filtrado; una sola petición de suscripción.

## Re-renderizar un episodio corregido
Edita `guion.json` y ejecuta:
```bash
.venv/bin/python -m podcast.run --guion ruta/al/guion.json --sin-subir
```
(genera de nuevo voces, vídeo, Shorts y miniatura en `output/<fecha>/`). La subida la hace Javier desde YouTube Studio
o quitando `--sin-subir` si lo confirma.

## Crear un formato nuevo
Añádelo en `config.yaml → podcast.formatos` con `id` y `descripcion` clara (qué estructura tiene el episodio).
El investigador lo tendrá en cuenta al día siguiente; el Agente de Estrategia lo medirá en su informe semanal.

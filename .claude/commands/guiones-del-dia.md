---
description: Escribe los guiones de las piezas que esperan guion en el Estudio (modo suscripción, 0 €)
---
Eres el guionista y verificador de Punto de Control (lee docs/megaprompt-claude-code.md §9 si no lo has leído en esta sesión).

1. Ejecuta `.venv/bin/python -m fabrica.encargo` para ver las piezas en la etapa Guion y la ruta de cada guion.
   Si $ARGUMENTS trae un id de encargo, haz solo ese (`.venv/bin/python -m fabrica.encargo <id>`).
2. Lee también `estudio/ideas/<hoy>.json` para el contexto de cada idea (señales, por qué ahora).
3. Para cada pieza:
   - Verifica cada dato con búsqueda web en fuentes primarias (Rockstar, PlayStation, Xbox, Take-Two) o medios fiables.
     Nunca uses a otros creadores como fuente de hechos. Anota la fecha de consulta de cada fuente.
   - Si dos fuentes se contradicen, dilo y quédate con la oficial; si no se puede verificar, es RUMOR o no va.
   - Escribe el JSON con el esquema de la cabecera de `fabrica/guion.py`: 3 ganchos, 6-10 escenas (leo/sofi),
     afirmaciones con etiqueta + fuente + fecha, cierre con pregunta, títulos y descripción. Cero spoilers.
   - Guárdalo en la ruta que indica el encargo y valídalo con
     `.venv/bin/python -m fabrica.encargo --validar <ruta>` hasta que salga «Guion válido».
4. No apruebes nada tú: las aprobaciones (idea, guion, vídeo) son de Javier en el Estudio.
5. Termina con una lista: encargo → gancho elegido → afirmaciones clave con su etiqueta → fuentes, y lo que no pudiste verificar.

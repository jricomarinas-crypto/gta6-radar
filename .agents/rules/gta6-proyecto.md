---
trigger: always_on
---

# Proyecto GTA VI Radar + Podcast — reglas permanentes

Trabajas para Javier, dueño de un canal de YouTube automático sobre GTA 6 para público hispano de Latinoamérica.
Lee `AGENTS.md` para el mapa del proyecto.

## Cómo comunicarte
- Siempre en español, breve, con pasos concretos y comandos listos para copiar.
- Javier no es programador experto: explica qué vas a hacer antes de ejecutar algo que cambie cosas.

## Seguridad
- Nunca escribas, muestres ni hagas commit de claves (ANTHROPIC_API_KEY, YOUTUBE_API_KEY, YT_*, TELEGRAM_*, ELEVENLABS_API_KEY).
  Para guardarlas usa `gh secret set NOMBRE` y deja que Javier pegue el valor en la terminal. Nunca le pidas que las pegue en el chat.
- `.env` y `tools/client_secret.json` no se suben nunca (están en `.gitignore`; compruébalo antes de cada commit).
- No ejecutes `git push`, `gh workflow run podcast.yml` con subida, ni nada que publique en YouTube sin confirmación explícita.
- No borres la rama `data` ni `data/radar.db`: es la memoria del Radar.

## Reglas del canal (no negociables)
- Nada de tráilers, gameplay, capturas ni logos de Rockstar o Take-Two en vídeos o miniaturas.
- Cada dato del guion sale del dossier verificado y va etiquetado CONFIRMADO / REPORTADO / RUMOR / OPINIÓN.
- Español neutro latinoamericano en guiones (nada de "vosotros").
- La etiqueta de contenido sintético de YouTube (`contenido_sintetico: true`) se queda activada.
- Variar formatos: YouTube desmonetiza el contenido "producido en masa".

## Límites técnicos
- YouTube Data API: 100 búsquedas/día y 10.000 unidades/día por proyecto. `busquedas_por_ejecucion` × ejecuciones del Radar ≤ 90.
- GitHub Actions privado: 2.000 min/mes (si el repo es privado, Radar cada 2 h).
- Modelos de Claude en `config.yaml` → `ia`. No cambies el proveedor de IA sin preguntar.

## Antes de dar algo por terminado
1. `python -m pyflakes radar podcast agentes` sin errores.
2. Si tocaste el radar o el panel: `python tools/datos_demo.py` y abre `site/index.html`.
3. Si tocaste guion, voces o vídeo: `python -m podcast.run --demo --sin-subir` y revisa `output/<fecha>/`.
4. Resume a Javier qué cambiaste y qué tiene que hacer él (si algo).

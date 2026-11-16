# GTA VI Radar + Podcast automático

Dos piezas que trabajan juntas, gratis en GitHub:

| | Qué hace | Cuándo |
|---|---|---|
| **Radar** | Vigila YouTube (búsquedas, tendencias de Gaming por país, canales que tú elijas) y medios (Google News, VGC, Eurogamer). La IA clasifica cada pieza por tema, tipo, riesgo y verificación, la puntúa y salta una alerta si algo explota. Genera un panel web y un briefing diario. | Cada hora |
| **Podcast** | Coge lo que detecta el Radar, verifica los datos con búsqueda web, escribe un episodio con dos presentadores (Leo y Sofi), genera las voces y monta el vídeo horizontal, 3 Shorts verticales y la miniatura. Lo sube a YouTube **en privado** para que lo revises. | Una vez al día |

```
Radar (cada hora) ──► base de datos ──► panel + alertas a Telegram
                              │
Podcast (diario) ─────────────┴──► investigación web ──► guion ──► voces ──► vídeo + Shorts ──► YouTube (privado)
```

---

## Puesta en marcha (unos 45 minutos, una sola vez)

### 1. Crea el repositorio en GitHub
1. En github.com → **New repository**. Nombre: `gta6-radar`.
2. **Público** (recomendado): minutos de GitHub Actions ilimitados y panel web gratis. El código es público, pero tus claves no (van en Secrets).
   Si lo haces **privado** tienes 2.000 min/mes: abre `.github/workflows/radar.yml` y cambia `"17 * * * *"` por `"17 */2 * * *"` (cada 2 h).
3. Sube todos los archivos de esta carpeta (lo más fácil: **GitHub Desktop** → Add existing repository → Publish).
   Asegúrate de que se sube la carpeta oculta `.github`.

### 2. Clave de Claude (guiones, clasificación, briefing)
1. console.anthropic.com → **API Keys** → Create key.
2. En la consola, activa la **búsqueda web** para tu organización (Settings → Privacy). Sin esto, el podcast no puede verificar datos.
3. Pon un **límite de gasto mensual** en Billing. El Radar usa el modelo barato para clasificar; el guion usa el principal.

### 3. Clave de YouTube para leer datos
1. console.cloud.google.com → crea un proyecto (`gta6-radar`).
2. **APIs y servicios → Biblioteca → YouTube Data API v3 → Habilitar**.
3. **Credenciales → Crear credenciales → Clave de API**. Restríngela a "YouTube Data API v3".

Cuota gratis por proyecto: 100 búsquedas/día + 100 subidas/día + 10.000 unidades para lo demás. El Radar usa ~72 búsquedas/día; no subas `busquedas_por_ejecucion` en `config.yaml` por encima de 4.

### 4. Permiso para subir vídeos a tu canal
En el mismo proyecto de Google Cloud:
1. **Pantalla de consentimiento OAuth** → Externo → rellena nombre y tu email → en "Usuarios de prueba" añade la cuenta del canal.
2. Pulsa **Publicar aplicación** (pasar a "En producción"). Si la dejas en "Prueba", el permiso caduca a los 7 días.
3. **Credenciales → Crear credenciales → ID de cliente OAuth → App de escritorio** → descarga el JSON y guárdalo como `tools/client_secret.json`.
4. En tu ordenador (con Python instalado):
   ```bash
   pip install google-auth-oauthlib
   python tools/get_youtube_token.py
   ```
   Se abre el navegador → elige el canal → verás "Google no ha verificado esta aplicación" → *Configuración avanzada → Ir a…* (es tu propia app) → Permitir.
   Copia los 3 valores que salen.
5. Verifica tu canal por teléfono en youtube.com/verify (necesario para miniaturas personalizadas).

> **Importante:** Google sube en **privado** todo lo que llega por la API desde proyectos no auditados. Por eso el bot sube en privado y tú publicas desde YouTube Studio (revisas en 2 minutos y evitas publicar un error). Cuando quieras publicar automáticamente, pide la auditoría: formulario "YouTube API Services – Audit and Quota Extension".

### 5. Avisos al móvil (opcional, recomendado)
**Telegram:** habla con @BotFather → `/newbot` → copia el token. Escribe algo a tu bot y luego habla con @userinfobot para saber tu `chat id`.
(O un webhook de Discord.)

### 6. Guarda las claves en GitHub
Repositorio → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Obligatorio |
|---|---|
| `ANTHROPIC_API_KEY` | Sí |
| `YOUTUBE_API_KEY` | Sí |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | Para subir a YouTube |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Opcional |
| `DISCORD_WEBHOOK_URL` | Opcional |
| `ELEVENLABS_API_KEY` | Solo si usas voces de ElevenLabs |

### 7. Panel web (opcional)
**Settings → Pages → Source: GitHub Actions**, y en **Settings → Secrets and variables → Actions → Variables** crea `PUBLICAR_PANEL` = `si`.
El panel quedará en `https://TU_USUARIO.github.io/gta6-radar/` (es público, aunque nadie lo encontrará si no le das el enlace).
Sin Pages: el panel se descarga en cada ejecución del Radar (Actions → ejecución → Artifacts → `panel`).

### 8. Primera prueba
1. **Actions → Radar GTA 6 → Run workflow**. Tarda 1-3 min. Ejecútalo 2 veces seguidas con una hora de diferencia para que haya velocidades (vistas/hora).
2. **Actions → Podcast diario GTA 6 → Run workflow** (desmarca "Subir a YouTube" la primera vez). Tarda ~15 min.
3. Descarga el resultado en **Artifacts → episodio-N**: episodio, Shorts, miniatura, guion y dossier con fuentes.

A partir de ahí funciona solo: Radar cada hora y episodio cada día a las 14:41 (hora de España).

---

## Día a día
- **Telegram** te avisa de las alertas importantes, te manda el briefing y te dice cuándo hay episodio nuevo con el enlace a YouTube Studio.
- **Revisa** el episodio en Studio (título, datos marcados como rumor, miniatura) y publícalo. Programa la publicación para la tarde de Latinoamérica.
- **TikTok:** descarga los Shorts de Artifacts y súbelos a mano (la API de TikTok exige auditoría).
- **Preguntar al Radar** desde tu ordenador:
  ```bash
  pip install -r requirements.txt
  cp .env.example .env        # pon tu ANTHROPIC_API_KEY
  python tools/descargar_datos.py
  python -m radar.chat "¿qué vídeos de GTA 6 crecen más rápido ahora?"
  ```

## Estudio y Fábrica (en tu Mac, gratis)
```bash
python -m estudio        # abre http://localhost:8080 → pestaña Fábrica
```
1. En **Fábrica** ves las mejores ideas del momento (kits del lanzamiento, temas con hueco, alertas).
2. Elige formato (Lista por país, Verdad o bulo, Última hora) y plataformas, y pulsa **Crear**.
3. Copia la frase «Escribe el guion del encargo X» y pégala en Claude Code: Claude verifica los datos, escribe el guion y fabrica el vídeo.
4. Los vídeos aparecen en `~/Movies/Punto de Control/<fecha>/TikTok/` y `YouTube Shorts/`, con un `.txt` de textos listos y `_revisar.md`.

El plan completo y los hitos siguientes están en `docs/plan-v2.md`.

## Agentes que gestionan el canal (automáticos)
| Agente | Cuándo | Qué hace |
|---|---|---|
| **Editor** | Cada episodio, antes de grabar | Revisa el guion línea a línea contra el dossier: datos sin fuente, rumores contados como hechos, título engañoso, tono. Corrige y deja `editor.md`. |
| **Operaciones** | Cada día a las 08:23 y siempre que falle algo | Revisa ejecuciones, errores, cuota y datos. Si algo falla, lee el log, diagnostica la causa, te avisa por Telegram y abre un *issue* en GitHub con la solución paso a paso. |
| **Estrategia** | Cada lunes | Mide tus episodios y Shorts publicados (vistas/hora, likes, comentarios), lee los comentarios de tu audiencia y las tendencias del Radar. Prioriza formatos y temas para la semana, añade búsquedas al Radar y te propone respuestas a comentarios. |

Se lanzan a mano en **Actions → Agentes (operaciones y estrategia) → Run workflow**.

## Trabajar desde Antigravity
Abre la carpeta del proyecto en Antigravity. Ya trae:
- **Reglas** (`.agents/rules/`) que el agente sigue siempre: español, nunca tocar claves, no publicar sin tu OK, reglas del canal.
- **Skills** (`.agents/skills/`) que se activan solas: `operar-canal-gta6` (fallos, cuotas, horarios) y `editor-guiones-gta6` (revisar episodios).
- **Comandos** (`.agents/workflows/`), escríbelos en el chat del agente:

| Comando | Para qué |
|---|---|
| `/puesta-en-marcha` | Te guía para dejarlo todo funcionando: GitHub, claves, primera ejecución |
| `/probar-local` | Prueba en tu Mac sin gastar cuota (panel y episodio de demostración) |
| `/estado` | Parte de situación: ejecuciones, errores, último episodio |
| `/arreglar` | Diagnostica el último fallo y lo arregla (te pide OK antes de subir cambios) |
| `/episodio` | Descarga y revisa el episodio de hoy antes de publicarlo |
| `/estrategia` | Lee el informe semanal y propone cambios en `config.yaml` |

En el **Agent Manager** puedes tener varios a la vez, por ejemplo uno con `/episodio` y otro con `/estado`.

## Personalizar (`config.yaml`)
- **Canal:** nombre, subtítulo, zona horaria.
- **Presentadores:** nombre, personalidad, voz y color. Pon fotos/ilustraciones propias en `assets/hosts/leo.png` y `assets/hosts/sofi.png` (si no, se dibujan avatares).
- **Voces:** `edge` (gratis, voces neuronales de Microsoft), `elevenlabs` (más naturales, de pago; pega los `voice_id`) u `offline` (robótica, solo pruebas). Ajusta la pronunciación de siglas en `pronunciacion`.
- **Formatos** que se alternan: noticias, a fondo, verdad o bulo, debate, comunidad, GTA 5 vs GTA 6.
- **Radar:** palabras clave, canales a vigilar (`creadores_prioritarios` con su @), medios RSS, umbrales de alertas y pesos del score.
- **Música:** deja un MP3 sin copyright en `assets/music/fondo.mp3` (p. ej. de la Biblioteca de audio de YouTube). Baja sola cuando hablan.

## Probar sin claves
```bash
pip install -r requirements.txt          # + ffmpeg instalado
python tools/datos_demo.py               # panel con datos inventados → site/index.html
python -m podcast.run --demo --sin-subir # episodio de ejemplo → output/<fecha>/
```

## Reglas para no perder el canal
- **No uses tráilers ni gameplay de Rockstar**: Take-Two reclama con Content ID. El bot usa solo gráficos propios.
- **YouTube no monetiza contenido "producido en masa"** (política de "contenido no auténtico", que YouTube detalló aún más en julio de 2026). Por eso el bot alterna formatos, se basa en lo que pasa cada día, cita fuentes y responde a la comunidad. Revisa los episodios, cambia títulos cuando haga falta y, si puedes, graba de vez en cuando una intro con tu voz.
- **Etiqueta de contenido sintético**: el bot la marca al subir (`containsSyntheticMedia`) y lo indica en la descripción.
- **Rumores**: el guion separa CONFIRMADO / REPORTADO / RUMOR / OPINIÓN; la tarjeta de cada capítulo lo muestra.

## Limitaciones conocidas
- **Reddit** cerró su API a desarrolladores nuevos en 2025. Solo funciona si ya tienes credenciales aprobadas (`REDDIT_CLIENT_ID/SECRET`).
- **X/Twitter** y **TikTok** no están incluidos: sus APIs son de pago o requieren aprobación.
- **Edge TTS** es un servicio gratuito no oficial de Microsoft; si un día deja de funcionar, cambia `proveedor` a `elevenlabs`.
- Los datos se guardan en la rama `data` del repositorio (un solo commit que se reescribe; el repo no crece).

## Estructura
```
radar/        ingesta (youtube.py, news.py), IA (classify.py), score (scoring.py),
              alertas y tendencias (trends.py), briefing.py, panel (dashboard*.py), chat.py, run.py
podcast/      guion (script.py), voces (tts.py), vídeo/Shorts/miniatura (render.py), upload.py, run.py
agentes/      Agente de Operaciones y Agente de Estrategia (el Editor está en podcast/editor.py)
tools/        token de YouTube, datos demo, descarga de datos, guardado en Git
.github/      automatizaciones (radar cada hora, podcast diario, agentes)
.agents/      reglas, skills y comandos para Antigravity · AGENTS.md: guía para cualquier agente
config.yaml   todo lo configurable
```

Fuentes tipográficas: Inter (© The Inter Project Authors, SIL Open Font License 1.1).

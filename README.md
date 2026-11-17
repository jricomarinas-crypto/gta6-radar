# GTA VI Radar + Podcast automático

Centro de control para detectar noticias y tendencias sobre GTA 6, convertirlas en contenido y gestionar un canal con revisión humana antes de publicar.

El proyecto combina dos procesos: un Radar que recopila y organiza información y una cadena de producción que prepara episodios y clips para revisión.

> Estado del proyecto: comprueba las funciones disponibles en la versión instalada. La sección «Evolución del panel» describe mejoras previstas, no funcionalidades que deban darse por implementadas. El estado detallado (hecho, probado, pendiente) está en `docs/ESTADO.md`.

---

## Qué hace

| Componente | Función | Frecuencia configurada |
|---|---|---|
| Radar | Consulta YouTube y medios, clasifica contenido, calcula indicadores de crecimiento y genera alertas, panel y briefing. | Cada hora, según el workflow. |
| Podcast | Utiliza las referencias del Radar para investigar, preparar el guion, generar voces y montar un episodio con clips y miniatura. | Una vez al día, según el workflow. |
| Editor | Revisa el guion frente al dossier y señala problemas de fuentes, verificación y tono. | Antes de generar el episodio. |
| Operaciones | Comprueba ejecuciones y diagnostica incidencias según sus permisos y configuración. | De forma programada o ante fallos. |
| Estrategia | Analiza el rendimiento disponible y propone temas, formatos y mejoras. | Semanalmente. |
| Estudio y Fábrica | En tu Mac: ideas, aprobaciones, vídeos verticales con tu voz y vídeo de fondo, exportación verificada. Ver «Estudio: crear vídeos en tu Mac». | Cuando lo usas. |

Las salidas, los horarios y las acciones disponibles dependen de los workflows y de `config.yaml`.

### Flujo general

    Fuentes de YouTube y medios
                 │
                 ▼
          RADAR PROGRAMADO
                 │
       Recopilación y snapshots
                 │
       Clasificación y puntuación
                 │
        ┌────────┼─────────┐
        ▼        ▼         ▼
      Panel   Briefing   Alertas
                 │
                 ▼
        PRODUCCIÓN DEL PODCAST
                 │
      Investigación y dossier
                 │
       Guion de Leo y Sofi
                 │
         Revisión editorial
                 │
       Voces y montaje de vídeo
                 │
      Episodio + clips + miniatura
                 │
       Subida privada, si se activa
                 │
          REVISIÓN HUMANA
                 │
       Publicación desde Studio

La revisión automática ayuda a detectar errores, pero no sustituye la comprobación humana de datos, derechos y contenido final.

---

## Costes y servicios necesarios

El proyecto está diseñado para aprovechar herramientas y cuotas gratuitas cuando sea posible, pero no debe considerarse completamente gratuito.

Los costes y límites dependen de:

- El plan y las condiciones de GitHub.
- La frecuencia y duración de las ejecuciones.
- Las llamadas a la API de Anthropic y a sus herramientas.
- Las cuotas de YouTube.
- El proveedor de voz elegido.
- El almacenamiento y la conservación de artefactos.
- Otros servicios que decidas conectar.

Antes de activar la automatización:

1. Configura los controles de gasto disponibles en cada proveedor.
2. Revisa las cuotas de las APIs.
3. Ejecuta primero las pruebas de demostración.
4. Activa los procesos reales de forma gradual.

No guardes claves ni credenciales dentro del repositorio.

> Modo actual: `ia.modo: suscripcion` en `config.yaml`. La app no llama a ninguna IA de pago; los guiones se escriben con Claude Code en la sesión. El modo `api` solo se activa si lo decides.

---

## Requisitos

Para ejecutar las herramientas locales necesitarás:

- Python compatible con las dependencias del proyecto.
- FFmpeg para generar los vídeos (en Mac, `ffmpeg-full` de Homebrew: el normal no trae subtítulos).
- Git.
- Una cuenta de GitHub para las automatizaciones.
- Credenciales de los servicios que quieras utilizar.

Servicios principales:

| Servicio | Para qué se utiliza |
|---|---|
| Anthropic | Clasificación, briefing, investigación y guiones, según la configuración. |
| YouTube Data API | Consulta de vídeos, canales y métricas disponibles. |
| OAuth de Google | Acceso autorizado a las funciones del canal, incluida la subida. |
| Telegram o Discord | Avisos opcionales. |
| Proveedor de voz | Generación de las voces del episodio. |
| Pexels (opcional) | Vídeo de fondo real con licencia que permite uso comercial. |

El acceso a métricas de tu propio canal puede requerir permisos o integraciones adicionales a los utilizados para consultar vídeos públicos.

---

## 1. Probar el proyecto sin claves

Empieza por la demostración local:

    pip install -r requirements.txt
    python tools/datos_demo.py
    python -m podcast.run --demo --sin-subir

Necesitarás FFmpeg instalado para las operaciones de vídeo.

Resultados esperados:

- Panel de demostración en `site/index.html`.
- Episodio de ejemplo y materiales en `output/<fecha>/`.

Los datos generados en este modo son ficticios y deben aparecer identificados como demostración.

> El modo demo sirve para comprobar la interfaz y el flujo de producción. No acredita que las integraciones externas estén configuradas correctamente.

Pruebas automáticas (no tocan tus datos ni tu carpeta de Películas):

    python -m unittest tests.test_corte1 tests.test_broll_voz -v

---

## 2. Crear el repositorio en GitHub

1. Crea un repositorio, por ejemplo `gta6-radar`.
2. Elige su visibilidad después de revisar qué archivos y datos se publicarán.
3. Sube el proyecto completo.
4. Comprueba que se incluye la carpeta `.github`.
5. Revisa `.gitignore` antes del primer commit.

No subas:

- Archivos `.env` con valores reales.
- Credenciales OAuth.
- Tokens.
- Claves de API.
- Archivos privados del canal.
- Datos personales que no quieras hacer públicos.

### Repositorio público o privado

Un repositorio público facilita compartir el proyecto, pero también hace visibles sus archivos y cualquier rama pública de datos.

Un repositorio privado restringe el acceso al código, aunque la disponibilidad de Actions y Pages depende del plan y de la configuración.

Revisa las condiciones actuales de GitHub antes de decidir. No presupongas minutos ilimitados ni una cuota fija para todos los planes.

### Frecuencia del Radar

El horario se configura en:

    .github/workflows/radar.yml

Ejemplos de expresiones cron:

    17 * * * *       # Cada hora, en el minuto 17
    17 */2 * * *     # Cada dos horas, en el minuto 17

Confirma la zona horaria aplicada por el workflow. No des por hecho que una expresión cron representa siempre la hora de España.

---

## 3. Configurar Anthropic

1. Accede a la consola de Anthropic.
2. Crea una clave de API.
3. Configura los controles de gasto disponibles.
4. Guarda la clave como secreto de GitHub:

    ANTHROPIC_API_KEY

El proyecto puede utilizar distintos modelos para clasificación, briefing y guion.

Comprueba que los modelos configurados existen y están disponibles para tu cuenta.

### Investigación web

Si la producción del podcast utiliza búsqueda web:

- Revisa los requisitos de la herramienta utilizada.
- Comprueba que el código la habilita correctamente.
- Verifica los permisos y la disponibilidad en tu cuenta.
- Ten en cuenta su posible coste.

No confundas el acceso a un modelo con la disponibilidad automática de todas sus herramientas.

---

## 4. Configurar YouTube para consultar datos

1. Crea un proyecto en Google Cloud.
2. Habilita YouTube Data API v3.
3. Genera una clave de API.
4. Restríngela a la API y a los usos compatibles con tu despliegue.
5. Guárdala en GitHub como:

    YOUTUBE_API_KEY

### Control de cuota

El consumo depende de las operaciones realizadas:

- Búsquedas.
- Consulta de vídeos.
- Consulta de canales.
- Paginación.
- Reintentos.
- Otras llamadas del proyecto.

Comprueba la cuota asignada a tu proyecto en Google Cloud.

No aumentes `busquedas_por_ejecucion` sin revisar el consumo real. El número de búsquedas configuradas no siempre equivale al número total de llamadas.

Si te acercas al límite:

1. Reduce la frecuencia.
2. Reduce búsquedas o paginación.
3. Prioriza fuentes relevantes.
4. Reutiliza datos ya obtenidos cuando sea apropiado.
5. Revisa errores y reintentos.

---

## 5. Autorizar las subidas a YouTube

La clave de API utilizada para consultar datos no autoriza por sí sola a subir vídeos a tu canal.

Para la subida se utiliza OAuth.

### Preparación

En el proyecto de Google Cloud:

1. Configura la pantalla de consentimiento.
2. Selecciona el tipo de aplicación y usuarios que corresponda.
3. Añade tu cuenta de prueba si el proyecto está en ese estado.
4. Crea un cliente OAuth de tipo aplicación de escritorio.
5. Descarga el archivo de credenciales.

Guárdalo localmente en:

    tools/client_secret.json

Comprueba que está excluido de Git.

### Obtener el token

    pip install google-auth-oauthlib
    python tools/get_youtube_token.py

Completa la autorización en el navegador y guarda los valores generados como secretos:

    YT_CLIENT_ID
    YT_CLIENT_SECRET
    YT_REFRESH_TOKEN

Autoriza únicamente un cliente creado y controlado por ti. No ignores avisos de seguridad de aplicaciones desconocidas.

### Duración y permisos

El comportamiento de los tokens puede depender del estado de la aplicación, los permisos solicitados y las políticas de Google.

Pasar una aplicación a producción no equivale automáticamente a verificarla ni a superar una auditoría de YouTube.

Si una subida falla por autorización, revisa el error concreto antes de regenerar credenciales.

### Revisión antes de publicar

El flujo previsto es subir el episodio en privado y revisarlo desde YouTube Studio.

Además, pueden existir restricciones de visibilidad para proyectos API no auditados. Comprueba las condiciones aplicables a tu proyecto.

No actives la publicación automática sin una revisión específica del flujo y de los permisos.

---

## 6. Configurar avisos

### Telegram

1. Crea un bot con `@BotFather`.
2. Guarda su token.
3. Inicia una conversación con el bot.
4. Obtén el identificador del chat de destino.
5. Configura:

    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID

No compartas el token ni lo incluyas en capturas o registros públicos.

### Discord

Si utilizas la integración por webhook:

    DISCORD_WEBHOOK_URL

Trata la URL como una credencial.

Los avisos disponibles dependen de la configuración: alertas del Radar, briefing, episodios e incidencias.

---

## 7. Guardar los secretos en GitHub

En el repositorio:

Settings → Secrets and variables → Actions → New repository secret

| Secreto | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | Funciones de IA configuradas. |
| `YOUTUBE_API_KEY` | Consulta de YouTube. |
| `YT_CLIENT_ID` | Subida autorizada mediante OAuth. |
| `YT_CLIENT_SECRET` | Subida autorizada mediante OAuth. |
| `YT_REFRESH_TOKEN` | Renovación de autorización. |
| `TELEGRAM_BOT_TOKEN` | Avisos por Telegram. |
| `TELEGRAM_CHAT_ID` | Destino de los avisos. |
| `DISCORD_WEBHOOK_URL` | Avisos por Discord. |
| `ELEVENLABS_API_KEY` | Voces de ElevenLabs, si se utiliza. |

Configura solo los secretos necesarios para las funciones que vayas a activar.

Los secretos no deben imprimirse en logs ni incorporarse al HTML, los artefactos o los archivos generados.

`PEXELS_API_KEY` (vídeo de fondo) se usa en el Estudio de tu Mac: va en tu archivo `.env`, no en GitHub.

---

## 8. Publicar el panel web

Si el repositorio y el plan permiten utilizar GitHub Pages:

1. Abre Settings → Pages.
2. Selecciona GitHub Actions como fuente.
3. Crea la variable de Actions:

    PUBLICAR_PANEL = si

4. Ejecuta el workflow correspondiente.

La dirección habitual tendrá esta forma:

    https://TU_USUARIO.github.io/gta6-radar/

### Privacidad del panel

Una URL poco conocida no es un mecanismo de privacidad.

Antes de publicarlo, revisa que no incluya:

- Notas privadas.
- Datos de colaboradores.
- Rutas locales.
- Credenciales.
- Información económica sensible.
- Material pendiente que no quieras difundir.

Si necesitas una zona privada de gestión, no presupongas que queda protegida por publicar el panel con un enlace difícil de adivinar.

El Estudio (piezas, guiones, tomas de voz) solo existe en tu Mac: no se publica en GitHub Pages.

### Sin publicación web

Puedes consultar los artefactos generados desde la ejecución de Actions, según la configuración del workflow y los permisos del repositorio.

El artefacto del panel se identifica como `panel` en el flujo descrito.

---

## 9. Primera ejecución real

### Probar el Radar

En GitHub:

Actions → Radar GTA 6 → Run workflow

Después:

1. Revisa el resultado de la ejecución.
2. Comprueba las fuentes consultadas.
3. Abre el panel generado.
4. Confirma que los avisos llegan al destino correcto.
5. Revisa el consumo de cuota.

Para calcular crecimiento entre mediciones hacen falta al menos dos observaciones comparables.

Una primera ejecución puede mostrar información válida sin disponer todavía de vistas/hora.

### Probar el podcast

En GitHub:

Actions → Podcast diario GTA 6 → Run workflow

En la primera prueba, desactiva la subida a YouTube.

Revisa los materiales generados:

- Episodio horizontal.
- Clips verticales.
- Miniatura.
- Guion.
- Dossier con fuentes.
- Informe editorial, si se ha generado.

La duración de la ejecución dependerá del episodio, el proveedor de voz y el entorno.

Activa la subida privada solo después de comprobar el resultado.

En modo suscripción (`ia.modo: suscripcion`), el podcast y los Shorts automáticos se saltan con un aviso: los vídeos se hacen desde el Estudio.

---

## Estudio: crear vídeos en tu Mac

    python -m estudio            # http://localhost:8080 (si está ocupado: --puerto 8090)

Cada pieza avanza por etapas: Brief → Guion → Montaje → Revisión → Exportación. Nada se publica sin tu aprobación.

1. **Idea.** En «Ideas para hoy», pulsa «Enviar al Estudio» y «Aprobar idea». Pide el guion a Claude Code con la frase que aparece («Escribe el guion del encargo X») o con `/guiones-del-dia`. Cada afirmación del guion lleva etiqueta, fuente y fecha.
2. **Guion.** Léelo («Ver el guion completo») y pulsa «Aprobar guion».
3. **Fondo y voz.** Elige:
   - Fondo: «Vídeo real (Miami / Florida)» o «Gráfico». El vídeo real viene de Pexels si pones `PEXELS_API_KEY` en `.env`, o de tus propios clips en `assets/broll/`. Si no hay ninguno, se usa el gráfico y se avisa. Se descarta cualquier clip con «GTA», «Rockstar», «gameplay»… en su título.
   - Voz: «La mía» (grabas cada escena con el micrófono desde el navegador; puedes escucharla y repetirla) o «Leo y Sofi» (voz sintética).
4. **Vídeo.** «Crear vídeo» se activa cuando está todo listo. Mira el resultado y pulsa «Aprobar vídeo» o «Pedir cambios».
5. **Exportar.** Deja en `~/Movies/Punto de Control/<fecha>/TikTok/` y `YouTube Shorts/` el vídeo, el texto para copiar, los subtítulos `.srt`, la portada y un manifiesto con la huella de cada archivo. Solo pone «Disponible en el Mac» tras comprobarla.

Si cambias el guion, el fondo, la voz o una toma después de aprobar, la aprobación del vídeo se anula y hay que crear otro. Si falla la voz o el montaje, «Reintentar» no rehace el guion.

Limitación conocida: con tu voz, los subtítulos reparten el tiempo de cada palabra de forma proporcional dentro de la toma; quedan aproximados, no exactos a la sílaba.

Contenido sintético: con tu voz y vídeo real, los textos ya no piden la etiqueta de IA; con Leo y Sofi, sí. Revísalo igualmente en cada pieza.

---

## Uso diario

### 1. Revisar el Radar

Comprueba:

- Noticias y vídeos nuevos.
- Temas con mayor crecimiento.
- Alertas.
- Antigüedad de los datos.
- Fuentes y estado de verificación.

Una puntuación alta indica prioridad según las reglas configuradas, no que una noticia sea verdadera.

### 2. Revisar el episodio

Antes de publicar:

- Comprueba nombres, fechas y cifras.
- Abre las fuentes de las afirmaciones importantes.
- Distingue hechos, información atribuida y rumores.
- Revisa pronunciación y montaje.
- Confirma que título y miniatura representan el contenido.
- Comprueba derechos de música, imágenes y otros materiales.
- Revisa la configuración de contenido sintético cuando corresponda.

### 3. Publicar

Publica o programa desde YouTube Studio tras la revisión.

Elige el horario según tu audiencia y tus datos, no solo por una recomendación genérica.

### 4. Distribuir clips

Si no existe una integración aprobada para la plataforma de destino, descarga los clips y súbelos manualmente.

Comprueba formato, subtítulos, portada y texto antes de publicarlos.

---

## Preguntar al Radar desde el ordenador

Instala las dependencias y prepara el entorno:

    pip install -r requirements.txt
    cp .env.example .env

Completa las variables necesarias sin compartir el archivo `.env`.

Descarga los datos y realiza una consulta:

    python tools/descargar_datos.py
    python -m radar.chat "¿Qué vídeos de GTA 6 crecen más rápido ahora?"

Las respuestas dependen de los datos disponibles y de su última actualización. “Ahora” no implica información en tiempo real si la última captura es anterior.

---

## Agentes del canal

### Editor

Revisa el guion frente al dossier para detectar:

- Afirmaciones sin respaldo.
- Rumores presentados como hechos.
- Contradicciones.
- Títulos engañosos.
- Problemas de tono.

Puede generar `editor.md` como registro de revisión.

Su evaluación no garantiza que todas las afirmaciones sean correctas.

### Operaciones

Comprueba, según la implementación:

- Estado de workflows.
- Errores recientes.
- Disponibilidad de datos.
- Cuotas observables.
- Incidencias de producción.

Puede enviar avisos y abrir issues si dispone de permisos.

No debe exponer secretos en diagnósticos ni realizar cambios destructivos sin autorización.

### Estrategia

Utiliza las métricas disponibles y las tendencias del Radar para proponer:

- Temas prioritarios.
- Formatos.
- Series.
- Ajustes de búsquedas.
- Respuestas a comentarios para revisión.

Debe distinguir recomendaciones de cambios aplicados.

Cualquier modificación automática de configuración debe estar documentada y contar con el mecanismo de aprobación que corresponda.

### Ejecución manual

Actions → Agentes (operaciones y estrategia) → Run workflow

Los horarios reales se consultan en los archivos de `.github/workflows/`.

---

## Trabajar desde Antigravity u otro agente de código

El proyecto incluye instrucciones y herramientas en:

- `AGENTS.md`
- `.agents/rules/`
- `.agents/skills/`
- `.agents/workflows/`
- `docs/megaprompt-claude-code.md` y `docs/megaprompt-2.0.md` (documentos maestros), `docs/ESTADO.md`
- `.claude/commands/guiones-del-dia.md` (comando `/guiones-del-dia` de Claude Code)

La carga automática de reglas o skills depende de la herramienta utilizada. Comprueba que el agente las haya leído.

### Comandos previstos

| Comando | Objetivo |
|---|---|
| `/puesta-en-marcha` | Revisar la configuración y guiar la primera ejecución. |
| `/probar-local` | Probar panel y episodio demo. |
| `/estado` | Consultar ejecuciones, errores y último episodio. |
| `/arreglar` | Diagnosticar una incidencia y proponer su corrección. |
| `/episodio` | Descargar y revisar el episodio. |
| `/estrategia` | Consultar el informe y proponer ajustes. |
| `/guiones-del-dia` | (Claude Code) Escribir y verificar los guiones que esperan en el Estudio. |

### Trabajo en paralelo

Puedes repartir tareas entre agentes, pero evita que modifiquen simultáneamente los mismos archivos.

Antes de editar:

1. Revisar el estado de Git.
2. Identificar cambios pendientes.
3. Acordar el alcance de cada agente.
4. Utilizar ramas o entornos de trabajo separados cuando corresponda.
5. Revisar los cambios antes de integrarlos.

Ningún agente debe publicar contenido, hacer push o desplegar sin la autorización establecida para esa acción.

---

## Personalización

La configuración principal está en:

    config.yaml

### Canal

- Nombre.
- Subtítulo.
- Zona horaria.
- Preferencias editoriales.

### Presentadores

- Nombre.
- Personalidad.
- Voz.
- Color.
- Recursos visuales.

Imágenes previstas:

    assets/hosts/leo.png
    assets/hosts/sofi.png

Utiliza imágenes propias o con permisos adecuados.

### Voces

Proveedores descritos por el proyecto:

| Proveedor | Uso previsto |
|---|---|
| `edge` | Voz mediante la integración configurada; depende de un servicio externo. |
| `elevenlabs` | Voz mediante API y plan contratado. |
| `offline` | Pruebas sin depender del proveedor de voz en línea, según disponibilidad local. |
| Tu voz | Grabada por escena en el Estudio (`fabrica.voz_por_defecto: propia`). |

Revisa las condiciones de uso y las dependencias de cada proveedor.

Configura la pronunciación de siglas y nombres en el apartado correspondiente.

### Vídeo de fondo

`config.yaml → fabrica.broll`: búsquedas (por defecto, Miami y Florida) y palabras excluidas. Instrucciones en `assets/broll/LEEME.md`. Cada clip de Pexels guarda su autor, enlace y licencia, que aparecen en los textos y el manifiesto.

### Formatos editoriales

Ejemplos:

- Noticias.
- A fondo.
- Verdad o bulo.
- Debate.
- Comunidad.
- GTA 5 frente a GTA 6.

En el Estudio: A (novedad verificada: lista por país, última hora), B (explicación: verdad o bulo, GTA 5 frente a GTA 6) y C (guía breve).

Alternar formatos no sustituye aportar contenido original y valor editorial.

### Radar

- Palabras clave.
- Canales prioritarios.
- Fuentes RSS.
- Umbrales de alerta.
- Pesos de puntuación.

### Música

Recurso previsto:

    assets/music/fondo.mp3

Utiliza música con una licencia compatible con la publicación y monetización previstas.

Conserva la licencia o justificante y cumple cualquier requisito de atribución. “Sin copyright” no debe utilizarse como sustituto de comprobar los derechos.

---

## Evolución del panel: centro de control interactivo

Esta sección define el objetivo de producto. No implica que todas las funciones estén implementadas.

### Navegación lateral

    Hoy

    Estadísticas
      Por día
      Por plataforma
      Por formato
      Registro manual

    Lo que más rinde
      Temas
      Formatos
      Series
      Colaboraciones

    Vídeos más virales
      Mis vídeos
      Vídeos del Radar
      Guardados

    Creadores y colaboradores
      Destacados
      Emergentes
      Posibles colaboradores
      Guardados

    Creación de vídeo
      Fábrica
      En curso
      Revisión
      Calendario
      Carpeta y archivos

    Radar
      Contenido
      Oportunidades
      Medios
      Briefing

### Tres gráficas diarias

1. Radar: vídeos detectados y velocidad máxima observada, con unidades diferenciadas.
2. Mi canal: vistas diarias por plataforma, cuando existan datos suficientes.
3. Producción: piezas creadas, aprobadas y publicadas.

Requisitos:

- Periodos de 7, 30 y 90 días.
- Consulta de valores exactos.
- Detalle al seleccionar un día.
- Comparación con ayer cuando sea válida.
- Diferencia entre cero y dato ausente.
- Estados vacíos explicativos.
- Datos demo claramente identificados.

Estado: ya se guardan los datos diarios del Radar y los eventos de producción; la barra lateral y las gráficas están pendientes (ver `docs/ESTADO.md`).

### Interactividad

- Búsqueda y tablas ordenables.
- Filtros combinables y visibles.
- Fichas de vídeos y creadores.
- Guardado de referencias.
- Acción “Crear vídeo de esto”.
- Flujo de producción conectado con el Estudio.
- Navegación accesible en escritorio y móvil.

### Criterios de datos

- No sumar mediciones acumuladas como si fueran incrementos diarios.
- No mezclar datos reales y demo.
- No inventar métricas ausentes.
- Documentar las fórmulas.
- Distinguir rendimiento de rentabilidad.
- Mantener la referencia original de cada idea.

---

## Seguridad editorial y derechos

### Verificación

Separa de forma visible:

- CONFIRMADO: respaldado por una fuente adecuada.
- REPORTADO: atribuido a un medio o fuente identificada.
- RUMOR: no confirmado.
- OPINIÓN: interpretación editorial.

La clasificación debe acompañarse de referencias, no sustituirlas.

### Recursos audiovisuales

El flujo predeterminado debe priorizar gráficos propios y materiales con derechos revisados.

No presupongas que puedes reutilizar tráilers, gameplay, música, imágenes o clips de terceros por estar disponibles públicamente.

Tampoco presentes una reclamación de derechos como una consecuencia idéntica e inevitable para cualquier uso: revisa cada material y sus condiciones.

### Originalidad y monetización

La automatización no garantiza que un canal cumpla los requisitos de monetización.

Revisa las políticas vigentes de YouTube y aporta trabajo editorial reconocible:

- Investigación.
- Contexto.
- Análisis.
- Narrativa propia.
- Revisión.
- Aportaciones originales.

No bases la estrategia únicamente en producir más vídeos o alternar plantillas.

### Contenido sintético

Comprueba si corresponde declarar contenido alterado o sintético y cómo lo gestiona la versión actual del uploader.

Si se utiliza `containsSyntheticMedia`, verifica su integración y su aplicación al contenido concreto.

No des por cumplida una obligación solo por añadir una frase a la descripción.

---

## Datos, almacenamiento y privacidad

El diseño descrito guarda datos en una rama `data`.

Comprueba en la implementación:

- Qué archivos contiene.
- Si conserva históricos o solo el último estado.
- Cómo resuelve ejecuciones simultáneas.
- Qué ocurre si falla una escritura.
- Cómo se recupera una copia anterior.

Si el proceso reescribe commits, no lo consideres una copia de seguridad completa.

La rama de datos tendrá la visibilidad y los permisos que correspondan al repositorio.

No guardes ahí información privada sin revisar antes sus implicaciones.

El Estudio guarda sus datos en tu Mac (`data/estudio.db`, guiones en `estudio/guiones/`, tomas de voz en `output/fabrica/`), fuera de git y de la rama `data`.

---

## Limitaciones

- La cobertura depende de las fuentes configuradas y de sus condiciones de acceso.
- Las APIs pueden cambiar, limitar solicitudes o requerir aprobación.
- Reddit, X y TikTok no deben darse por integrados sin comprobar los conectores y permisos de esta versión.
- Las métricas públicas no equivalen a todas las estadísticas privadas de un canal.
- Las tareas programadas no deben tratarse como un servicio con puntualidad garantizada.
- La consulta sin conexión requiere disponer previamente de los recursos y datos necesarios.
- La investigación, las voces y la actualización de fuentes pueden depender de internet.
- Los proveedores de voz pueden cambiar su disponibilidad o condiciones.
- La clasificación automática y la revisión editorial pueden cometer errores.
- La generación del vídeo no implica que se haya subido.
- La subida privada no implica publicación.
- Las mejoras del panel no están disponibles hasta implementarse y probarse.

---

## Resolución rápida de problemas

| Síntoma | Qué revisar |
|---|---|
| El Radar no se ejecuta | Workflow habilitado, programación, permisos y errores de Actions. |
| Falla YouTube | API habilitada, restricciones de clave, cuota y respuesta exacta del servicio. |
| No aparece crecimiento | Existencia de dos mediciones comparables y tiempo transcurrido. |
| Falla Anthropic | Clave, saldo o límites, modelo y herramientas solicitadas. |
| Falla la voz | Proveedor, credenciales, disponibilidad y formato de salida. |
| Falla el montaje | FFmpeg, recursos necesarios y logs de renderizado. |
| Falla la subida | OAuth, permisos, token, restricciones y respuesta de YouTube. |
| No llegan avisos | Token, destino configurado y errores del envío. |
| El panel está vacío | Fuentes sin datos, filtros activos, generación o sincronización. |
| El panel no se actualiza | Última ejecución correcta y publicación del artefacto generado. |
| El vídeo sale con fondo gráfico | `PEXELS_API_KEY` en `.env` o clips en `assets/broll/`; el motivo aparece en la revisión. |
| No graba la voz | Permiso de micrófono del navegador para `localhost`. |

No pegues credenciales en issues ni compartas logs sin revisarlos.

---

## Estructura del proyecto

    radar/
      youtube.py          Consulta de YouTube
      news.py             Ingesta de medios
      classify.py         Clasificación
      scoring.py          Puntuación
      trends.py           Tendencias y alertas
      briefing.py         Briefing
      dashboard*.py       Generación del panel
      diario.py           Resumen diario para las gráficas
      chat.py             Consulta del Radar
      run.py              Ejecución principal

    podcast/
      script.py           Guion
      editor.py           Revisión editorial
      tts.py              Voces
      render.py           Vídeo, clips y miniatura
      upload.py           Subida
      run.py              Orquestación

    estudio/              Estudio local: servidor, flujo de aprobaciones, base de datos
    fabrica/              Guion por escenas, voces, tu voz, vídeo de fondo, montaje, calidad, exportación
    tests/                Pruebas automáticas

    agentes/
      Operaciones y estrategia

    tools/
      Autorización de YouTube
      Datos demo
      Descarga y persistencia de datos

    .github/
      Workflows de automatización

    .agents/
      Reglas, skills y comandos de agentes

    assets/
      Recursos visuales y sonoros (incluido broll/)

    docs/                 Megaprompts, principios, plan v2 y ESTADO
    config.yaml           Configuración
    AGENTS.md             Instrucciones para agentes

La estructura real del repositorio es la referencia si difiere de este resumen.

---

## Lista de comprobación antes de automatizar

- [ ] He probado el panel demo.
- [ ] He generado un episodio demo.
- [ ] He comprobado que las credenciales están excluidas de Git.
- [ ] He configurado límites y revisado cuotas.
- [ ] He ejecutado el Radar manualmente.
- [ ] He comprobado las fuentes y la fecha de actualización.
- [ ] He revisado un episodio completo sin subirlo.
- [ ] He probado la subida privada, si voy a utilizarla.
- [ ] He revisado qué información expone el panel.
- [ ] He confirmado los horarios y la zona horaria.
- [ ] He comprobado cómo se conservan y recuperan los datos.
- [ ] He mantenido la revisión humana antes de publicar.

---

## Licencias y atribuciones

Fuentes tipográficas:

- Inter — © The Inter Project Authors.
- Licencia SIL Open Font License 1.1.

Vídeo de fondo: clips de Pexels bajo la Pexels License; el autor y el enlace de cada clip se guardan en `assets/broll/_pexels/creditos.json` y en el manifiesto de cada pieza.

Conserva los avisos exigidos por las licencias de las fuentes y de cualquier otro recurso incluido.

La licencia del código del proyecto debe indicarse por separado en el archivo `LICENSE`.

---

## Principio del proyecto

Automatizar la recopilación y la producción sin perder el control editorial.

El Radar ayuda a detectar.
Los agentes ayudan a preparar y revisar.
Tú decides qué se publica.

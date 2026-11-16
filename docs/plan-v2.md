# PUNTO DE CONTROL 2.0 — Fábrica de vídeos virales de GTA 6

16-nov-2026 · @Rico

> Reconstruido a partir del PDF «PUNTO DE CONTROL 2.0» (27 páginas) el 16-nov-2026, después de que Claude Code
> sobrescribiera por error la versión anterior de este archivo. Mismo contenido que el PDF.
> El estado de cada hito está en `docs/ESTADO.md`.

## Resumen ejecutivo

Punto de Control 2.0 convierte el Radar en una fábrica de vídeos virales: detecta cada hora lo que va a explotar sobre GTA 6, elige las mejores ideas y, con un botón, deja en el Mac los vídeos listos para TikTok, YouTube Shorts y YouTube.

El plan v1 era un canal de noticias con podcast diario. La v2 tiene un solo objetivo: que cada pieza que sale tenga la máxima probabilidad de hacerse viral. Todo lo que no sirve para eso sale del Radar.

**Lo que no cambia.** Contenido 100 % propio, cada dato con su etiqueta (CONFIRMADO, REPORTADO, RUMOR u OPINIÓN) y Javier decide qué se publica.

**Por qué hay prisa.** GTA 6 se desbloquea el 19 de noviembre a las 0:00 en la hora local de cada país, y México y Centroamérica están entre los últimos en jugar (Vandal). Esas horas de espera son la mayor ventana de atención del año para un canal hispano.

| | Plan v1 | Plan v2 |
|---|---|---|
| Para qué sirve el Radar | Vigilar y alimentar un podcast diario | Encontrar lo que más se va a ver y convertirlo en vídeos |
| Producto principal | Podcast de 9 min + 3 Shorts al día | Piezas verticales por tema para TikTok y Shorts, y vídeo largo solo cuando el tema lo merece |
| Fuentes | YouTube y 12 medios | Más de 30 fuentes en 6 familias, externas e internas |
| Filtro | La IA clasifica y puntúa | 7 capas y un comité de 6 agentes que votan cada idea |
| Momento | Reacciona a lo que ya pasó | Anticipa: señales tempranas y calendario de eventos |
| Salida | Archivos en GitHub | Botón Crear: carpeta del Mac con TikTok, YouTube Shorts y YouTube |
| Aprendizaje | Informe semanal | Cada vídeo publicado reajusta el score |

**Orden de construcción.** Antes del 19 de noviembre: el botón, la carpeta y 3 formatos rápidos con lo que ya funciona. En las 4 semanas siguientes: las fuentes nuevas, el comité, la anticipación y el aprendizaje.

## Objetivo y métricas de viralidad

El objetivo es la **tasa de acierto viral**: el porcentaje de piezas que, en 48 horas, multiplican por 5 las vistas medianas de las últimas 20 piezas del canal en esa misma plataforma.

Se mide contra el propio canal y no contra una cifra fija, porque 10.000 vistas son un éxito el primer mes y un fracaso el tercero. Cada pieza queda en una de tres bandas:
- **Viral:** 5× la mediana o más.
- **Acierto:** entre 2× y 5×.
- **Normal o fallo:** menos de 2×. Alimenta el aprendizaje igual que los éxitos.

Objetivos propuestos para empezar (se recalibran a las 2 semanas con datos reales):
- Semanas 1–4: al menos 1 de cada 10 piezas en la banda viral y 3 de cada 10 en acierto.
- Mes 2 en adelante: subir la tasa de acierto cada mes; la viral depende de la ola de GTA 6.

**Monetización, que condiciona el formato.** El programa Creator Rewards de TikTok exige 18 años, 10.000 seguidores, 100.000 vistas en los últimos 30 días y solo paga vídeos de al menos 1 minuto (requisitos 2026). Por eso parte de las piezas de TikTok se diseñan para durar más de 60 segundos sin perder ritmo.

| Plataforma | Qué dice si la pieza funciona | Métricas que se guardan por pieza |
|---|---|---|
| TikTok | Que no se desliza y que se comparte | Vistas 48 h, % que ve más de 3 s, retención media, compartidos y guardados por 1.000 vistas, seguidores ganados |
| YouTube Shorts | Que se elige ver en lugar de deslizar | Vistas 48 h, % visto frente a deslizado, retención media, suscriptores ganados |
| YouTube largo | Que la miniatura atrae y el vídeo retiene | CTR de la miniatura, retención a los 30 s, duración media vista, suscriptores ganados |

## Cómo funciona de punta a punta

El sistema hace solo 7 de los 9 pasos; Javier interviene para elegir qué se crea y para publicar.

Lo que Javier publica vuelve al paso 9 y reajusta el score, así que el sistema acierta más cuanto más se usa. Los pasos 1–4 corren cada hora en GitHub; del 5 al 7, en el Mac al pulsar Crear.

## Fuentes: dónde se escucha la conversación

El Radar pasa de 2 tipos de fuente a 6 familias. Las que no tienen API abierta entran por la **Bandeja**: Javier pega cualquier enlace (TikTok, X, Reddit, Instagram) y el sistema lo analiza igual que lo demás.

| Familia | Fuente | Qué aporta | Cómo se lee | Coste |
|---|---|---|---|---|
| Vídeo | YouTube Data API: búsquedas, estadísticas y comentarios | Qué vídeos crecen y qué pregunta la gente | API, cada hora, dentro de la cuota | 0 € |
| Vídeo | RSS de 200+ canales de YouTube | Lo nuevo de cada creador vigilado, sin gastar cuota | RSS, cada hora | 0 € |
| Vídeo | Tendencias de Gaming por país (MX, AR, CO, CL, PE, ES, US) | Qué entra en tendencias y en qué país primero | API, cada hora | 0 € |
| Vídeo | Autocompletado de búsqueda de YouTube | Qué escribe la gente justo ahora («gta 6 + …») | Consulta ligera, cada 3 h | 0 € |
| Vídeo | TikTok Creative Center (hashtags, sonidos y creadores en tendencia) | Formatos y sonidos que suben en TikTok | Lectura semiautomática o manual, 2 veces al día | 0 € |
| Vídeo | Twitch (categoría GTA VI: espectadores y clips más vistos) | Qué momentos generan reacción en directo | API gratuita, cada hora | 0 € |
| Búsqueda | Google Trends por país | Consultas en ascenso y dónde suben primero | Consulta diaria y en alertas | 0 € |
| Búsqueda | Wikipedia Pageviews API (es y en) | Picos de interés en personajes, lugares y el juego | API, cada hora | 0 € |
| Búsqueda | Autocompletado de Google | Preguntas nuevas antes de que haya vídeos | Consulta ligera, cada 3 h | 0 € |
| Oficial y medios | Rockstar Newswire, Soporte de Rockstar, PlayStation Blog, Xbox Wire | Lo CONFIRMADO, de primera mano | RSS o página, cada hora | 0 € |
| Oficial y medios | PS Store y Xbox Store | Precio por país, rankings, horas de desbloqueo | Página, diaria | 0 € |
| Oficial y medios | Los 12 medios actuales + medios latinoamericanos y en inglés | Noticias y lo REPORTADO | RSS, cada hora | 0 € |
| Comunidad | Reddit (r/GTA6 y similares) | Memes, quejas y teorías antes que en YouTube | RSS público si sigue disponible; si no, Bandeja | 0 € |
| Comunidad | GTAForums y wikis de fans | Datos finos, mapas, filtraciones con historial | RSS o página, diaria | 0 € |
| Comunidad | Know Your Meme e Imgflip | Qué memes existen y cuáles suben | Página, diaria | 0 € |
| Comunidad | X/Twitter e Instagram | Filtradores y reacciones al minuto | Sin API: lista curada que Javier revisa y pega en la Bandeja | 0 € |
| Mercado (tras el lanzamiento) | Rareza de trofeos y logros (PSNProfiles, TrueAchievements) | Qué está haciendo la gente en el juego y dónde se atasca | Página, diaria | 0 € |
| Mercado (tras el lanzamiento) | Metacritic y OpenCritic | Notas y polémicas de la prensa | Página, diaria | 0 € |
| Internas | YouTube Analytics API | Retención, CTR, búsquedas que traen vistas, fuentes de tráfico | API, diaria | 0 € |
| Internas | Comentarios en los vídeos propios | Preguntas y peticiones de tu audiencia | API, cada 3 h | 0 € |
| Internas | TikTok Studio | Rendimiento de cada pieza en TikTok | Javier pega las cifras en el Estudio (1 min al día) | 0 € |
| Internas | Historial de ideas, piezas y resultados | Qué funcionó y qué no, por tema y formato | Base de datos propia | 0 € |
| Internas | Notas de Javier y encuestas a la comunidad | Intuición y lo que pide tu gente | Botón «Idea» en el Estudio y encuestas de Telegram o Comunidad | 0 € |

**Regla de uso:** las fuentes sirven para decidir de qué hacer el vídeo, nunca para copiar su material. Ningún vídeo, imagen o audio de otro creador ni de Rockstar entra en las piezas.

## El filtro en capas y el comité que decide

De miles de piezas al día solo pasan a producción las 5–10 mejores ideas. Cada capa descarta algo distinto, y la última palabra la tiene un comité de agentes con puntos de vista opuestos, como si fuera un equipo de personas.

La unidad de decisión es la **historia** (un tema concreto, p. ej. «hora de desbloqueo en México»), no el vídeo o la noticia suelta. Una historia agrupa todo lo que se dice de ella en todas las fuentes.

1. **Limpieza** (sin IA): quita duplicados, resubidas, spam, idiomas que no interesan y cuentas recién creadas sin historial.
2. **Relevancia** (modelo barato): ¿es de GTA 6? ¿de qué tema? Lo de GTA 5 o roleplay solo pasa si se compara con GTA 6.
3. **Agrupación en historias:** une piezas de distintas fuentes que hablan de lo mismo y cuenta en cuántas familias aparece.
4. **Verificación:** busca la fuente primaria y cruza fuentes. Etiqueta CONFIRMADO, REPORTADO, RUMOR, OPINIÓN o BULO. Los filtradores se ponderan por su historial de aciertos.
5. **Potencial viral:** calcula el score de la sección de score.
6. **Hueco en español:** compara la demanda (búsquedas, vistas) con la oferta en español de las últimas 24 h. Mucha demanda y poca oferta suben la idea.
7. **Riesgo:** copyright, spoilers del final o de giros de la historia, temas sensibles, afirmaciones que no se pueden sostener. Un riesgo alto bloquea la idea aunque sea muy viral.
8. **Comité:** las 30 mejores historias pasan a votación.

### El comité

Cada agente puntúa de 1 a 10 y lo justifica en una frase. El Director suma los votos ponderados, aplica el veto del Verificador y ordena. Dos reglas de diversidad: máximo 2 ideas del mismo tema en el top 10, y al menos 1 idea de humor o meme si la hay.

| Agente | Pregunta que responde | Peso |
|---|---|---|
| El Analista | ¿Los datos dicen que esto está subiendo de verdad? | 1,0 |
| El Fan latino de 17 años | ¿Lo vería entero y se lo mandaría a un amigo? | 1,5 |
| El Editor de TikTok | ¿Hay un gancho de 1 segundo y ritmo para 30–70 s? | 1,0 |
| El Productor de YouTube | ¿Hay título, miniatura y búsqueda para un vídeo largo? | 1,0 |
| El Abogado del diablo | ¿Por qué va a fracasar? ¿Ya está quemado? | 1,0 |
| El Verificador | ¿Se sostiene sin inventar? | Veto |

Salida del comité por idea, en el formato que lee el Estudio:

```json
{
  "historia_id": "desbloqueo-mexico",
  "titulo_idea": "A qué hora se juega GTA 6 en tu país",
  "por_que_ahora": "Búsquedas en ascenso en MX y AR; en español solo hay 3 vídeos de las últimas 24 h",
  "etiqueta": "CONFIRMADO",
  "fuentes": ["https://..."],
  "ganchos": ["¿Eres de México? Vas a jugar de los últimos", "...", "..."],
  "formatos": {"tiktok": "lista-por-pais", "shorts": "lista-por-pais", "youtube": null},
  "score": 87,
  "votos": {"analista": 9, "fan": 8, "tiktok": 9, "youtube": 5, "diablo": 6, "verificador": "ok"},
  "riesgo": "bajo"
}
```

El último filtro es Javier. El Estudio le enseña el top con su porqué y él decide qué se crea.

**Control de coste:** las capas 1–7 usan el modelo barato o ninguno; solo el comité, con 30 historias al día como máximo, usa el modelo principal.

## Anticipación: llegar antes que la ola

Un vídeo viral casi siempre llega en las primeras horas de un tema. El Radar busca señales de que algo va a explotar y prepara el vídeo antes de que lo hagan los demás.

### Señales tempranas

Los umbrales son una propuesta inicial; el aprendizaje los ajusta cada semana.

| Señal | Qué indica | Umbral inicial |
|---|---|---|
| Aceleración | Las vistas por hora crecen hora tras hora, no solo son altas | 3 horas seguidas subiendo |
| Canal pequeño desbocado | Un creador pequeño supera con mucho su media: el tema tira por sí solo | Vistas/suscriptores 3× su mediana |
| Salto entre plataformas | El tema aparece en varias familias de fuentes a la vez | 2 o más familias en menos de 6 h |
| Inglés antes que español | Crece en inglés y aún no hay oferta en español | Menos de 5 vídeos en español en 24 h |
| Preguntas que se repiten | Comentarios con la misma duda («¿cuándo…?», «¿cómo…?», «¿en PC?») | La misma pregunta en 20+ comentarios en 6 h |
| Búsqueda nueva | Sube en Google Trends o Wikipedia, o aparece en el autocompletado | Pico 2× sobre su media de 7 días |
| Filtrador fiable | Publica alguien con buen historial de aciertos | Historial de aciertos alto en el Radar |
| Calendario | Evento conocido que va a pasar | Ver tabla de eventos |

**Probabilidad de ola.** Las primeras semanas, una regla simple: si coinciden 3 señales, la historia salta a alerta y se crea un vídeo en menos de 3 horas. Con 2–3 semanas de datos propios, se entrena un modelo sencillo que estima la probabilidad de que la historia multiplique sus vistas en las 12 horas siguientes.

### Calendario de eventos

GTA 6 se desbloquea a las 0:00 del 19 de noviembre en la hora local de cada país, según la PS Store; Nueva Zelanda es de los primeros y México y Centroamérica de los últimos (Vandal). Pasado a hora de España, Nueva Zelanda empieza hacia las 12:00 del 18 y Ciudad de México hacia las 7:00 del 19: unas 19 horas en las que medio mundo juega y Latinoamérica espera.

Cada kit son guiones y gráficos listos con huecos. Cuando el evento ocurre, el Radar rellena los datos y el vídeo sale en minutos.

| Cuándo (hora de España) | Evento | Estado | Kit de vídeos preparado de antemano |
|---|---|---|---|
| 16–18 nov | Cuenta atrás | Confirmado | Hora de desbloqueo por país, qué hacer la noche del lanzamiento, 5 cosas que ya sabemos |
| 18 nov, desde 12:00 | Juegan los primeros países | Confirmado | Lo que cuentan los primeros jugadores sin spoilers, actualizado cada pocas horas |
| 19 nov, 0:00 | Desbloqueo en España | Confirmado | Primeras impresiones, primeros problemas técnicos |
| 19 nov, 7:00 | Desbloqueo en Ciudad de México | Confirmado | «Ya puedes jugar»: qué hacer en la primera hora |
| 19–22 nov | Primer fin de semana | Previsible | Secretos sin spoilers, errores graciosos contados, dudas más buscadas |
| 27 nov | Black Friday | Fecha fija | Precio y ofertas por país |
| Sin fecha | Primer parche | Previsible | Plantilla «qué arregla el parche» lista para rellenar |
| Sin fecha | GTA Online | Sin confirmar | Plantilla «todo lo que sabemos de GTA Online» |
| Sin fecha | Versión de PC | Sin confirmar (El Comercio) | Plantilla «GTA 6 en PC: qué se sabe» |
| 24 dic – 6 ene | Navidad y Reyes | Fecha fija | Regalo, ediciones, consolas |

## Score de potencial viral

Cada historia recibe un score de 0 a 100 por plataforma, porque lo que explota en TikTok no es lo mismo que lo que se busca en YouTube. El score combina 7 componentes y se multiplica por el riesgo.

```
SPV_plataforma = 100 × (Σ_{i=1..7} w_i · c_i) × (1 − riesgo) × (1 − repetición)
```

Cada componente c va de 0 a 1 y los pesos w de cada plataforma suman 1.

| Componente | Qué mide | TikTok | Shorts | YouTube |
|---|---|---|---|---|
| Demanda | Vistas/hora del tema, búsquedas y comentarios | 0,15 | 0,20 | 0,25 |
| Aceleración | Cuánto crece ahora frente a hace 3 h | 0,20 | 0,20 | 0,10 |
| Hueco en español | Demanda frente a oferta en español en 24 h | 0,15 | 0,15 | 0,20 |
| Emoción | Sorpresa, polémica, humor o nostalgia que detecta la IA | 0,25 | 0,15 | 0,10 |
| Encaje del formato | Si hay un formato ganador para contarlo en esa plataforma | 0,10 | 0,15 | 0,15 |
| Frescura | Horas desde que nació la historia | 0,10 | 0,10 | 0,05 |
| Solidez | Etiqueta y fuentes: CONFIRMADO puntúa más que RUMOR | 0,05 | 0,05 | 0,15 |

**Penalizaciones.** Riesgo (0 a 1) sale de la capa de riesgo; con 0,7 o más la idea se bloquea. Repetición sube si el canal ya publicó algo del mismo tema en las últimas 24 h, para no parecer un canal en serie.

**Cómo aprende.** Cada lunes, o cada 20 piezas publicadas, el Agente de Estrategia compara el score que tuvo cada pieza con su resultado real (el multiplicador sobre la mediana del canal) y reajusta los pesos:
- Cada peso cambia como mucho un 20 % por semana, para no dar bandazos por un solo vídeo.
- El 10 % de las ideas que se producen son de exploración: temas o formatos con poca historia, para descubrir lo que todavía no se sabe que funciona.
- Cada cambio de pesos queda registrado con su motivo, y Javier puede volver atrás desde el Estudio.

## Radar de memes y ranking de creadores

Los memes y los creadores son dos pestañas nuevas del panel. Sirven para saber de qué se ríe la gente y qué formatos están funcionando, y se convierten en vídeos propios, nunca en copias.

### Memes

**Cómo se detectan.** Frases que se repiten en títulos y comentarios de muchas fuentes a la vez, sonidos en ascenso en TikTok, entradas nuevas de Know Your Meme y lo más votado de Reddit. Un meme existe cuando aparece en 2 o más familias de fuentes.

Ficha de cada meme (lo que ve Javier en el panel):
- Qué es en una frase y de dónde salió, con enlaces de ejemplo.
- Fase: naciendo, en pico o quemado. Los memes duran días, no semanas: o se hace el vídeo en menos de 24 h o se descarta.
- Cómo adaptarlo con material propio (Leo y Sofi, texto en pantalla, gráficos y voz).
- Riesgo: si depende de una imagen de Rockstar o de otro creador, no se puede hacer tal cual.

Plantillas de humor propias que la fábrica sabe montar:

| Plantilla | Ejemplo |
|---|---|
| «Nadie: / GTA 6:» | Nadie: / La gente de México esperando 19 horas más que Nueva Zelanda: |
| Expectativa frente a realidad | Lo que crees que harás el primer día frente a lo que harás |
| POV | POV: llevas 13 años esperando y se te olvida la precarga |
| Tier list | Ranking de cosas que harás antes de la primera misión |
| Leo contra Sofi | Discusión de 20 segundos sobre un tema que divide |
| Reacción a comentarios | Leo y Sofi leen los comentarios más graciosos de tu canal |

### Creadores

El ranking se actualiza cada día y tiene 4 listas:

| Lista | Quién entra | Para qué sirve |
|---|---|---|
| Top en español | Los que más vistas suman sobre GTA 6 en 7 días | Saber qué temas ya están cubiertos |
| Emergentes | Canales pequeños con vídeos muy por encima de su media | Detectar formatos nuevos que funcionan y posibles colaboraciones |
| Referentes en inglés | Los que primero publican cada tema | Anticipar lo que llegará al español |
| Colaboradores posibles | Emergentes de tu tamaño con audiencia parecida | 2–3 contactos por semana |

De cada creador se guarda: tamaño, vistas/hora medias, mejor vídeo de la semana y por qué funcionó (gancho, título, duración, formato), país e idioma. La IA resume cada lunes qué patrones se repiten en los vídeos que ganan; esos patrones alimentan el catálogo de formatos.

## Catálogo de formatos virales

La fábrica sabe montar 15 formatos, cada uno con su versión para cada plataforma. El comité elige el formato; Javier puede cambiarlo antes de pulsar Crear.

### Especificaciones por plataforma

| | TikTok | YouTube Shorts | YouTube |
|---|---|---|---|
| Imagen | 1080 × 1920 (9:16) | 1080 × 1920 (9:16) | 1920 × 1080 (16:9) |
| Duración | 25–45 s para alcance; 61–75 s para cobrar en Creator Rewards | 25–60 s; el máximo son 3 min (YouTube, oct. 2024) | 8–12 min con capítulos |
| Primer segundo | Texto grande y voz a la vez | Texto grande y voz a la vez | Promesa del vídeo en 10 s |
| Subtítulos | Palabra a palabra, centro de la pantalla | Palabra a palabra, centro de la pantalla | Opcionales |
| Final | Pregunta para comentarios | Bucle: el final enlaza con el principio | Tarjeta al siguiente vídeo |
| Extras | Texto de 1–2 líneas y 3–5 hashtags | Título con «GTA 6» y enlace al vídeo largo | Miniatura 1280 × 720, descripción con fuentes |

### Los 15 formatos

| # | Formato | Dónde | Gancho tipo |
|---|---|---|---|
| 1 | Lista por país (hora, precio, edición) | TikTok, Shorts | «¿Eres de Argentina? Esto te afecta» |
| 2 | Verdad o bulo en 30 s | TikTok, Shorts | «Todo el mundo dice X. Es mentira» |
| 3 | Lo que nadie te contó de… | TikTok, Shorts | «Esto lo descubrí en la letra pequeña» |
| 4 | Top 5 (armas, coches, lugares, animales) | Los tres | «El número 1 no te lo esperas» |
| 5 | GTA 5 frente a GTA 6 | Shorts, YouTube | «13 años después, esto es lo que cambia» |
| 6 | Mapa de Leonida explicado (mapa dibujado por nosotros) | Shorts, YouTube | «Así de grande es el mapa comparado con…» |
| 7 | Personaje explicado sin spoilers | Shorts, YouTube | «Quién es de verdad Lucía» |
| 8 | Respuesta a la pregunta más repetida | TikTok, Shorts | Se abre con el comentario en pantalla |
| 9 | Meme del día | TikTok | La plantilla de humor que toque |
| 10 | Leo contra Sofi | TikTok, Shorts | Una frase polémica de cada uno |
| 11 | Última hora | TikTok, Shorts | «Acaba de pasar» + etiqueta en pantalla |
| 12 | Resumen de la semana | YouTube | Las 5 noticias que importan |
| 13 | Guía rápida (tras el lanzamiento) | Los tres | «Haz esto en tu primera hora» |
| 14 | Teoría (siempre etiquetada OPINIÓN o RUMOR) | Shorts, YouTube | «Esta teoría tiene más sentido de lo que crees» |
| 15 | Versión larga de TikTok (61+ s) de los formatos 1, 4 y 13 | TikTok | El mismo gancho, con más desarrollo |

### Banco de ganchos

Cada guion sale con 3 ganchos de tipos distintos y el comité elige uno: pregunta directa al país, dato con número, «esto no lo sabías», conflicto, cuenta atrás y error común. Los ganchos que ganan se guardan y se reutilizan con otras palabras, nunca iguales.

### Decisión pendiente: gameplay propio

Tras el lanzamiento, lo más visto será el gameplay. La política de Rockstar dice que le gusta que los fans suban su gameplay (Rockstar), pero la plantea para uso no comercial, es decir, sin ganar dinero con el material del juego (Rockstar). También retira los spoilers, como el final o los grandes giros de la historia (Rockstar).
- **Opción A, sin gameplay:** la regla actual. Es lo más seguro y limita el alcance.
- **Opción B, gameplay grabado por Javier** en pocos segundos y dentro de un vídeo comentado: más alcance, con el riesgo de reclamaciones que la política deja abierto. Sin spoilers ni música de las radios del juego.
- **Opción C, esperar 2 semanas** a ver cómo trata Rockstar a los canales que lo hacen.

## La fábrica: de la idea al vídeo terminado

Cuando Javier pulsa Crear, la fábrica hace 10 pasos sin intervención y, si algo no pasa el control de calidad, lo rehace o avisa. La mayoría de las piezas ya existen en `podcast/` (guion, voces, montaje, miniatura) y se reorganizan por plataforma.

1. **Guion por plataforma.** Estructura fija: gancho (0–2 s), promesa (2–5 s), desarrollo con un giro a mitad, cierre con pregunta. 3 ganchos para elegir. Lenguaje de Latinoamérica neutro, frases de menos de 12 palabras.
2. **Revisión del Editor.** El Agente Editor comprueba cada dato contra el dossier y pone la etiqueta en pantalla y en la voz.
3. **Voz.** Leo y Sofi, con su personalidad fija. En TikTok la voz va un 10 % más rápida. Las voces gratuitas sirven para empezar; las de pago se activan si la retención cae en los primeros segundos.
4. **Visuales propios.** Biblioteca de recursos hechos para el canal: mapa de Leonida dibujado por nosotros, iconos de armas y coches, tarjetas CONFIRMADO / RUMOR, avatares de Leo y Sofi, fondos de estilo Vice City sin marcas de Rockstar.
5. **Subtítulos** palabra a palabra, sincronizados con la voz, con la palabra clave resaltada en color.
6. **Música y efectos** de bibliotecas sin copyright, con la música bajando sola cuando hablan.
7. **Montaje.** Una plantilla por formato y plataforma con variación obligatoria: color, disposición, transiciones y ritmo salen de un conjunto amplio, para que dos vídeos nunca parezcan hechos en serie.
8. **Portada y miniatura.** 3 propuestas por pieza; la mejor según el comité va primero.
9. **Textos.** 3 títulos, descripción con fuentes, hashtags, comentario fijado y aviso de contenido hecho con IA.
10. **Control de calidad automático** (tabla de abajo). Si falla algo arreglable, se rehace; si no, la pieza llega marcada en rojo.

| Comprobación | Regla |
|---|---|
| Duración | Dentro del rango del formato y la plataforma |
| Imagen | Resolución y proporción correctas, sin bandas negras |
| Volumen | Normalizado a -14 LUFS, sin picos |
| Zona segura | Texto y subtítulos fuera de la zona que tapan los botones de la app |
| Primer segundo | Hay texto y voz desde el fotograma 1 |
| Etiquetas | Todo dato lleva su etiqueta; un RUMOR se dice como rumor |
| Fuentes | La descripción incluye al menos una fuente por dato |
| Material ajeno | Ningún logo, imagen ni audio de Rockstar o de otros creadores |
| Repetición | Se parece poco a lo publicado en los últimos 7 días (guion, plantilla y título) |
| Texto | Ortografía y nombres propios revisados; pronunciación de siglas correcta |

**Por qué tanta variación.** En julio de 2026 YouTube aclaró que no monetiza los vídeos genéricos, repetitivos o hechos con plantillas que apenas cambian de uno a otro, se hagan con IA o no (The Desk). Una fábrica de vídeos es justo lo que esa política vigila, así que cada pieza tiene que aportar algo distinto: un dato nuevo, una respuesta a la audiencia, una opinión o la voz de Javier.

## El botón Crear: de la idea a la carpeta del Mac

El panel del Radar se convierte en el **Estudio**, una app que corre en el propio Mac (en `localhost:8080`, la misma dirección que ya usas). Su pestaña principal, **Fábrica**, enseña las mejores ideas del momento, y un botón deja los vídeos en una carpeta separados por plataforma.

### Lo que ve Javier

Cada idea es una tarjeta con su score por plataforma, el porqué de ahora, la etiqueta, los 3 ganchos y las casillas ☐ TikTok ☐ YouTube Shorts ☐ YouTube ya marcadas según el comité.
- **Crear:** fabrica esa idea en las plataformas marcadas.
- **Crear el pack del día:** fabrica las 5 primeras ideas de una vez.
- **Otro gancho:** rehace solo el guion con otro gancho.
- **Descartar:** la quita y enseña al sistema que no le interesa.

Barra de progreso por vídeo. Al terminar, aviso de macOS y se abre la carpeta en el Finder.

### La carpeta

Una carpeta por día y, dentro, una por plataforma, para que al subir a TikTok solo haya que abrir la de TikTok:

```
~/Movies/Punto de Control/
└── 2026-11-19/
    ├── TikTok/
    │   ├── 01_hora-por-pais.mp4
    │   ├── 01_hora-por-pais.txt        ← texto, hashtags y comentario fijado
    │   ├── 01_hora-por-pais_portada.jpg
    │   └── 02_meme-19-horas.mp4 …
    ├── YouTube Shorts/
    │   ├── 01_hora-por-pais.mp4
    │   └── 01_hora-por-pais.txt        ← título y descripción con fuentes
    ├── YouTube/
    │   ├── 01_todo-sobre-el-lanzamiento.mp4
    │   ├── 01_todo-sobre-el-lanzamiento_miniatura-A.jpg (B, C)
    │   └── 01_todo-sobre-el-lanzamiento.txt  ← 3 títulos, descripción, capítulos
    └── _revisar.md                     ← checklist y fuentes de todo el día
```

El mismo número en las tres carpetas es la misma idea. Cuando Javier sube un vídeo, lo marca como subido en el Estudio y el archivo pasa a una subcarpeta `subidos/`.

**Opción móvil:** si la carpeta base se pone dentro de iCloud Drive, los vídeos aparecen en el iPhone y se suben a TikTok desde la app del móvil.

### Cómo funciona por dentro

- **Modo local** (por defecto): el Estudio es un servidor pequeño en Python que arranca solo al encender el Mac. Al pulsar Crear, pone el trabajo en una cola y la fábrica lo procesa en el Mac con `ffmpeg`. Es gratis y rápido, y el Radar sigue corriendo cada hora en GitHub.
- **Modo nube** (opcional): el botón encarga el trabajo a GitHub Actions y un sincronizador del Mac descarga el resultado a la misma carpeta cada 10 minutos. Sirve si el Mac está apagado o se quiere producir de madrugada.

| Llamada del Estudio | Qué hace |
|---|---|
| `GET /api/ideas` | Lista de ideas con score, porqué, etiqueta y formatos |
| `POST /api/crear` | Crea una idea: `{idea_id, plataformas, gancho}` y devuelve un id de trabajo |
| `POST /api/crear-pack` | Crea las N mejores ideas del día |
| `GET /api/trabajos/{id}` | Progreso y resultado de un trabajo |
| `POST /api/abrir-carpeta` | Abre la carpeta del día en el Finder |
| `POST /api/subido` | Marca una pieza como subida y la mueve a `subidos/` |
| `POST /api/bandeja` | Recibe un enlace pegado por Javier para analizarlo |

## Publicación: cuánto, cuándo y cómo

La fábrica produce más de lo que se publica: Javier elige lo mejor y lo sube él. Más piezas no es mejor si se parecen entre sí; el volumen sube solo cuando la tasa de acierto aguanta.

| Fase | TikTok | YouTube Shorts | YouTube largo |
|---|---|---|---|
| Semana del lanzamiento (17–23 nov) | 4–6 al día | 3–4 al día | 1 cada 1–2 días |
| Semanas 2–4 | 3–4 al día | 2–3 al día | 3 por semana |
| Desde el mes 2 | Lo que diga el aprendizaje | Lo que diga el aprendizaje | 2–3 por semana |

**Horarios.** Se mantiene la franja del plan v1: 18:00–20:00 de Ciudad de México (01:00–03:00 en España), programado. La excepción son las alertas: un tema que explota se publica en cuanto esté listo, sin esperar a la franja.

**Cómo se sube.**
- **TikTok:** a mano desde la carpeta `TikTok/`, con el texto del `.txt` y la etiqueta de contenido de IA activada. Un minuto por vídeo.
- **YouTube Shorts y YouTube:** el Estudio puede subirlos en privado por la API con título, descripción y miniatura; Javier los revisa y programa en YouTube Studio. También se pueden subir a mano desde la carpeta.
- **Instagram Reels:** los mismos archivos de `YouTube Shorts/`, sin coste extra.

### La rutina de Javier (30–45 min al día)
1. Abrir la pestaña Fábrica y revisar el top de ideas (5 min).
2. Pulsar Crear en las elegidas o en el pack del día.
3. Ver cada vídeo una vez con la checklist de `_revisar.md` (10–20 min).
4. Subir TikTok y programar YouTube (10 min).
5. Responder comentarios en la primera hora tras publicar.
6. Pegar en el Estudio las cifras de TikTok de ayer (1 min).

**Lo que aporta Javier y la máquina no.** Su voz o su cara de vez en cuando, las respuestas a comentarios y los contactos con otros creadores. Es lo que hace que el canal parezca de una persona y no una fábrica, que es lo que YouTube premia.

## Aprender de cada vídeo

Cada pieza publicada vuelve al sistema con sus resultados a las 2, 24 y 48 horas, y eso decide qué se fabrica después. Es lo que hace que el acierto suba con el tiempo.

**Qué se registra de cada pieza:** la idea, el formato, el gancho elegido, la plantilla y su variación, la duración, la hora de publicación, el score que tuvo y las métricas reales de la sección de objetivos.

**De dónde salen los datos:** YouTube y Shorts por la API de YouTube Analytics, a diario. TikTok, a mano: Javier pega en el Estudio vistas, retención y compartidos de las piezas de ayer.

**Pruebas A/B.**
- **YouTube:** la herramienta de A/B de YouTube Studio prueba hasta 3 títulos y miniaturas en el mismo vídeo y deja la combinación con más tiempo de visualización (Ayuda de YouTube). Cada vídeo largo sale con 3 miniaturas y 3 títulos preparados para eso.
- **TikTok y Shorts:** no se publica dos veces lo mismo. Se aprende entre piezas: qué tipo de gancho, duración y formato rinden más a igualdad de tema.

**El ciclo semanal** (lunes, Agente de Estrategia):
1. Calcula la tasa de acierto por plataforma, formato, tipo de gancho y franja horaria.
2. Reajusta los pesos del score dentro del límite del 20 %.
3. Actualiza el Salón de la fama (las piezas virales y por qué funcionaron) y la lista negra (lo que falló 3 veces seguidas).
4. Añade o quita palabras clave y canales vigilados.
5. Escribe un informe de una página con 3 decisiones propuestas para la semana. Javier las acepta o las rechaza desde el Estudio.

**Análisis de cada viral.** Cuando una pieza entra en la banda viral, el sistema escribe en 5 líneas por qué cree que funcionó y propone 2 continuaciones (una segunda parte o el mismo enfoque con otro tema) para publicar en las 24 horas siguientes.

## Arquitectura técnica y plan de implementación

La v2 se construye encima del código que ya existe, en 10 hitos pequeños que Claude Code puede implementar uno a uno. Cada hito termina con una prueba que Javier puede hacer él mismo.

**Cómo pedirlo:** abre Claude Code en la carpeta `gta6-radar-podcast` y escribe «Implementa el hito H1 de docs/plan-v2.md. Pruébalo en modo demo y enséñame el resultado».

### Mapa de módulos

| Ruta | Estado | Qué hace |
|---|---|---|
| `radar/youtube.py`, `news.py`, `vigilancia.py` | Existe | Ingesta de YouTube, medios y 200 canales por RSS |
| `radar/classify.py`, `scoring.py`, `trends.py`, `oportunidades.py` | Existe, se amplía | Clasificación, score, alertas y huecos en español |
| `radar/fuentes/` | Nuevo | Twitch, Wikipedia, Google Trends, autocompletado, TikTok Creative Center, Reddit, tiendas, memes |
| `radar/historias.py` | Nuevo | Agrupa piezas de todas las fuentes en historias |
| `radar/verificar.py` | Nuevo | Fuente primaria, cruce y etiqueta |
| `radar/score_viral.py` | Nuevo | Score por plataforma con pesos aprendidos |
| `radar/anticipar.py` | Nuevo | Señales tempranas, probabilidad de ola y calendario |
| `radar/comite.py` | Nuevo | Los 6 agentes, el Director y las reglas de diversidad |
| `radar/creadores.py`, `radar/memes.py` | Nuevo | Rankings de creadores y radar de memes |
| `podcast/script.py`, `editor.py`, `tts.py`, `render.py`, `shorts_diarios.py` | Existe | Guion, revisión, voces y montaje: la fábrica los reutiliza |
| `fabrica/formatos/` | Nuevo | Un archivo por formato con su guion y su montaje por plataforma |
| `fabrica/variacion.py` | Nuevo | Elige colores, disposición y ritmo para que no haya dos vídeos iguales |
| `fabrica/calidad.py` | Nuevo | Control de calidad automático |
| `fabrica/exportar.py` | Nuevo | Escribe la carpeta del día por plataforma y `_revisar.md` |
| `estudio/` | Nuevo | Servidor local, cola de trabajos y pestañas Fábrica, Memes, Creadores y Bandeja |
| `aprendizaje/` | Nuevo | Métricas por pieza, ajuste de pesos, Salón de la fama |
| `agentes/estrategia.py` | Existe, se amplía | Ciclo semanal sobre los datos de aprendizaje |
| `tools/instalar_estudio.sh` | Nuevo | Instala `ffmpeg`, el entorno de Python y el arranque automático en el Mac |

### Datos nuevos

```sql
CREATE TABLE historias (id TEXT PRIMARY KEY, titulo TEXT, tema TEXT, etiqueta TEXT,
  familias INTEGER, primera_vez TEXT, ultima_vez TEXT, fuentes TEXT, estado TEXT);
CREATE TABLE items_historia (historia_id TEXT, item_id TEXT, tipo TEXT, PRIMARY KEY (historia_id, item_id));
CREATE TABLE senales (historia_id TEXT, tipo TEXT, valor REAL, medido_en TEXT);
CREATE TABLE ideas (id TEXT PRIMARY KEY, historia_id TEXT, creada_en TEXT, score_tiktok REAL,
  score_shorts REAL, score_youtube REAL, por_que TEXT, ganchos TEXT, formatos TEXT, riesgo TEXT, estado TEXT);
CREATE TABLE votos (idea_id TEXT, agente TEXT, nota REAL, motivo TEXT);
CREATE TABLE trabajos (id TEXT PRIMARY KEY, idea_id TEXT, plataformas TEXT, gancho INTEGER,
  estado TEXT, progreso REAL, error TEXT, creado_en TEXT, terminado_en TEXT);
CREATE TABLE piezas (id TEXT PRIMARY KEY, trabajo_id TEXT, plataforma TEXT, formato TEXT,
  ruta TEXT, duracion REAL, variacion TEXT, calidad TEXT, subida_en TEXT, url TEXT);
CREATE TABLE metricas_pieza (pieza_id TEXT, horas INTEGER, vistas INTEGER, retencion REAL,
  compartidos INTEGER, seguidores INTEGER, ctr REAL, PRIMARY KEY (pieza_id, horas));
CREATE TABLE pesos_score (semana TEXT, plataforma TEXT, pesos TEXT, motivo TEXT);
CREATE TABLE memes (id TEXT PRIMARY KEY, nombre TEXT, fase TEXT, ejemplos TEXT, adaptacion TEXT, visto_en TEXT);
CREATE TABLE bandeja (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, nota TEXT, recibido_en TEXT, historia_id TEXT);
```

### Configuración nueva en `config.yaml`

```yaml
fabrica:
  carpeta_base: "~/Movies/Punto de Control"   # o una carpeta de iCloud Drive
  modo: "local"                               # local | nube
  pack_del_dia: 5
  plataformas_por_defecto: ["tiktok", "shorts"]
  duraciones:
    tiktok: [25, 45]
    tiktok_larga: [61, 75]
    shorts: [25, 60]
    youtube: [480, 720]
estudio:
  puerto: 8080
  abrir_finder_al_terminar: true
comite:
  historias_a_votar: 30
  max_mismo_tema_en_top10: 2
score:
  cambio_max_semanal: 0.20
  exploracion: 0.10
  bloqueo_por_riesgo: 0.70
```

### Hitos

- **H1 — Botón y carpeta.** Estudio local con pestaña Fábrica que lista las ideas de `oportunidades.py`; Crear llama a la producción de Shorts que ya existe y exporta a `TikTok/` y `YouTube Shorts/`. *Prueba:* pulsar Crear en modo demo y ver el MP4 y el TXT en la carpeta del día.
- **H2 — Formatos de lanzamiento.** Formatos 1, 2 y 11, subtítulos palabra a palabra, control de calidad básico (duración, imagen, volumen) y kits del calendario de lanzamiento. *Prueba:* los 3 formatos salen bien en TikTok y Shorts.
- **H3 — Historias y score viral.** Agrupación en historias, capas 1–7 y score por plataforma. *Prueba:* el top del Estudio enseña historias, no vídeos sueltos, con su score por plataforma.
- **H4 — Fuentes nuevas.** Twitch, Wikipedia, autocompletado, Google Trends y Bandeja. *Prueba:* una historia muestra señales de 3 familias.
- **H5 — Comité.** Los 6 agentes, el Director y las reglas de diversidad. *Prueba:* cada idea muestra sus 6 votos y sus motivos.
- **H6 — Anticipación.** Señales tempranas, alerta de ola y kits por evento. *Prueba:* con datos demo de una historia en aceleración salta la alerta.
- **H7 — Memes y creadores.** Las dos pestañas y las plantillas de humor. *Prueba:* el formato 9 se fabrica desde una ficha de meme.
- **H8 — Aprendizaje.** Métricas a 2, 24 y 48 h, pegado de cifras de TikTok, ajuste de pesos y Salón de la fama. *Prueba:* el informe del lunes propone pesos nuevos con su motivo.
- **H9 — Los 15 formatos y la variación.** Catálogo completo, vídeo largo con 3 miniaturas y control de calidad completo. *Prueba:* 10 piezas seguidas del mismo formato no se parecen entre sí.
- **H10 — Modo nube y móvil.** Encargar a GitHub Actions, sincronizador y opción iCloud. *Prueba:* con el Mac cerrado, el pack aparece en la carpeta al abrirlo.

## Reglas, riesgos y costes

El mayor riesgo de una fábrica de vídeos virales es que YouTube la trate como contenido en serie y no la monetice. Las reglas de abajo existen para que cada pieza parezca, y sea, trabajo de un canal con criterio.

### Reglas que no se rompen
1. Nada se publica sin que Javier lo vea. La fábrica deja los vídeos en la carpeta; publicar es siempre una decisión suya.
2. Contenido 100 % propio: ningún vídeo, imagen, audio ni logo de Rockstar o de otros creadores, salvo lo que decida Javier sobre el gameplay propio.
3. Todo dato lleva su etiqueta y su fuente. Un rumor se dice como rumor, en pantalla y en la voz.
4. Nada de spoilers del final ni de los grandes giros de la historia.
5. Etiqueta de contenido hecho con IA activada en YouTube y en TikTok.
6. Las claves solo van en GitHub Secrets o en `.env`, nunca en el código ni en el chat.

### Riesgos

| Riesgo | Qué pasaría | Cómo se evita |
|---|---|---|
| Contenido en serie | YouTube no monetiza el canal: desde julio de 2026 nombra expresamente los vídeos con plantillas que apenas cambian (Media Copilot) | Variación obligatoria, límite por tema, control de repetición, voz y respuestas de Javier |
| Copyright (Content ID) | Vídeos bloqueados; con 3 avisos, canal cerrado | Solo material propio; control de material ajeno en la calidad |
| Gameplay y política de Rockstar | Retiradas o reclamaciones si se usa su material con fines comerciales o con spoilers | Decisión explícita de Javier (opciones A, B o C) |
| Publicar un bulo | Pérdida de confianza y suscriptores | Capa de verificación, veto del Verificador, revisión de Javier |
| Perseguir lo viral a cualquier precio | Títulos engañosos que hunden la retención y la confianza | El título cumple lo que promete; las pruebas A/B premian el tiempo visto, no el clic |
| Javier se quema | Se deja de publicar | Rutina de 30–45 min, pack del día, volumen que baja tras el lanzamiento |
| La ola de GTA 6 baja | Menos vistas a partir de unos meses | Ampliar a GTA Online, PC y guías; segundo canal con el mismo sistema |
| Cuotas y claves | El Radar o la fábrica se paran un día | Límite de 100 búsquedas diarias de YouTube, límite de gasto en la IA, aviso del Agente de Operaciones |

### Costes aproximados al mes

Las cifras son estimaciones: el gasto real se ve en la consola de Anthropic desde la primera semana.

| Concepto | Plan v1 | Plan v2 | Comentario |
|---|---|---|---|
| IA de Claude (API) | 20–40 € | 30–60 € | El comité añade llamadas; se usa el modelo barato en las capas y se fija un límite de gasto |
| GitHub, YouTube API, Twitch, Wikipedia, Telegram | 0 € | 0 € | Gratis dentro de sus cuotas |
| Producción en el Mac | — | 0 € | Usa el ordenador de Javier |
| Voces de pago (opcional) | 5–22 € | 5–22 € | Solo si la voz gratuita frena la retención |
| **Total** | **20–40 €** | **30–60 € (hasta ~80 € con voces de pago)** | Se ajusta con el primer mes real |

## Hoja de ruta

Antes del 19 de noviembre solo se construye lo que llega a tiempo para el lanzamiento: el botón, la carpeta y 3 formatos. Lo demás entra en las 4 semanas siguientes, un hito cada pocos días, sin parar la producción.

Cada fase tiene una prueba que hay que pasar para empezar la siguiente. Las fases de negocio del plan v1 (crecimiento, monetización y estabilidad hasta noviembre de 2027) siguen igual.

### Próximos pasos (esta semana)
- Activar las claves de Claude y YouTube en GitHub, con límite de gasto (pendiente del plan v1).
- Pedir a Claude Code el hito H1 y probar el botón en modo demo.
- Pedir el hito H2 y dejar listos los kits del 18 y 19 de noviembre.
- Decidir la opción de gameplay propio (A, B o C).
- Elegir la carpeta base: Películas del Mac o iCloud Drive.
- Publicar las primeras piezas en la ventana de 19 horas del 18 al 19 de noviembre.

## Anexo: lo que se mantiene del plan v1

La parte de negocio del plan del 16 de noviembre sigue vigente; la v2 solo cambia cómo se detecta y se fabrica el contenido.

| Tema | Lo que dice el plan v1 |
|---|---|
| Audiencia | Hispanohablantes de 14 a 35 años, foco en México, Argentina, Colombia, Chile y Perú; España secundaria. Consumen en móvil, por la tarde y la noche, en Shorts y TikTok |
| Posicionamiento | El canal en español que separa hechos de rumores sobre GTA 6, todos los días y antes que nadie |
| Diferencias | Rigor visible (etiquetas y fuentes), velocidad, huecos en español y los presentadores Leo y Sofi |
| Marketing | Descubrimiento con Shorts y TikTok, fidelidad con el vídeo largo, SEO con las preguntas que se buscan, 2–3 contactos con creadores por semana, remezclas con la voz o la cara de Javier; Telegram o WhatsApp a partir de 1.000 suscriptores; Instagram Reels sin coste extra |
| Fases de negocio | Arranque (16 nov – 15 dic 2026), Crecimiento (16 dic – feb 2027), Monetización (mar – may 2027), Estabilidad (jun – nov 2027). Se pasa de fase con 30 días seguidos publicando, con los requisitos de YouTube cumplidos y con ingresos de al menos 2 veces el coste |
| Ingresos | Programa de Socios de YouTube (comprobar requisitos en YouTube Studio), Creator Rewards de TikTok, patrocinios de periféricos y tiendas, enlaces de afiliado |
| Estabilidad | Ampliar a GTA Online, PC, mods y guías; un segundo canal con el mismo sistema; ofrecer el sistema como servicio a otros creadores o marcas |
| Equipo | Javier (30–45 min al día de revisión y publicación, 20 min de comunidad, 1–2 h a la semana de mantenimiento con Claude Code) y los agentes. Se contrata un editor o community manager cuando el canal ingrese al menos el doble del coste del puesto durante 2 meses seguidos |

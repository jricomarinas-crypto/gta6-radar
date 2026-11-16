# Estado del proyecto — Punto de Control

Última actualización: 16-nov-2026 (Claude Code). Documentos de referencia: `docs/megaprompt-claude-code.md`,
`docs/principios-producto.md`, `docs/plan-v2.md`.

## Incidencia de esta sesión
- `docs/plan-v2.md` se sobrescribió por error con un resumen. **Se ha reconstruido entero a partir del PDF**
  «PUNTO DE CONTROL 2.0» (27 páginas). Si la versión anterior tenía cambios que no estaban en el PDF, se han perdido
  (no estaba en git).

## Corte 1 (H1 + H2) — qué hay

### Hecho y probado (modo demo, 16-nov)
- `python -m estudio` sirve el panel con la pestaña **Fábrica** (ideas: kits del calendario, temas con hueco, alertas, ideas del día).
  La pestaña solo aparece en el Estudio; en GitHub Pages queda oculta (comprobado).
- **Crear** crea un encargo en `data/estudio.db` (estado «esperando guion») con la frase para pedírselo a Claude.
- `python -m fabrica.encargo <id>` muestra la idea, las reglas y la plantilla del guion.
- `python -m fabrica.producir <id> <guion.json>`: valida el guion → voces (Edge TTS) → montaje vertical 1080×1920 con
  subtítulos palabra a palabra y etiqueta en pantalla → control de calidad → copia a
  `~/Movies/Punto de Control/<fecha>/TikTok/` y `YouTube Shorts/` con `.txt`, portada y `_revisar.md` → aviso de macOS.
- Formatos: `lista_pais` (1), `verdad_bulo` (2), `ultima_hora` (11). Probados los 3 con guiones de demo.
- Calidad: resolución, duración por plataforma, −14 LUFS (ebur128), gancho, etiqueta, fuente con URL, «RUMOR dicho en voz».
- El podcast (`python -m podcast.run --demo --sin-subir`) sigue funcionando tras el cambio en `render.py`.

### Simulado / demo
- Las ideas salen de `data/demo.db` mientras `data/radar.db` no tenga vídeos (el Radar de GitHub aún no tiene clave de YouTube).
- Los 3 guiones de `examples/guion_fabrica_demo_*.json` tienen datos inventados marcados como demo.

### Diferencias con los criterios de aceptación del corte 1 (megaprompt §14) — PENDIENTE
1. **Aprobaciones separadas** (idea / guion / vídeo): no existen. Hoy Crear → guion → vídeo exportado directamente.
2. **Ver el guion en el Estudio** antes de fabricar: no existe.
3. **Exportar como paso aparte** y solo de la versión aprobada: hoy `producir` exporta al terminar.
4. **`.srt` y `manifiesto.json`** (versión, hash por archivo, aprobación, fuentes); exportar dos veces no duplica;
   «Disponible en el Mac» solo tras comprobar el hash: no existen.
5. **Editar el guion invalida la aprobación del vídeo**: no existe (no hay versiones).
6. **Reintentar voz o render sin perder el guion**: el guion se guarda en `output/fabrica/<id>/guion.json` y se puede
   relanzar `producir`, pero no hay botón «Reintentar» en el Estudio.
7. **Progreso como etapa, sin porcentajes inventados** (megaprompt §6 y §16): hoy se muestra una barra con porcentaje fijo
   por etapa → hay que cambiarla por la etapa.
8. **Rutas del modo suscripción** (§9): ideas en `estudio/ideas/AAAA-MM-DD.json`, guiones en
   `estudio/guiones/AAAA-MM-DD/<id>.json` y comando `/guiones-del-dia`: hoy los guiones van en `output/guiones/<id>.json`.
9. **`ia.modo: suscripcion | api`** en `config.yaml`: no existe todavía.
10. **Esquema del guion por escenas** (§9: `escenas` con `en_pantalla`, `visual`, `afirmaciones` con fecha; 3 ganchos):
    el guion actual es por líneas, con un solo gancho y las fuentes a nivel de pieza.
11. **Formato C (descubrimiento o guía breve)**: no existe; A (novedad verificada) y B (verdad o bulo) sí.
12. **Robustez** (§5): un render a la vez, cancelación y recuperación tras reinicio: no existen.

### Fuera del corte 1 (más adelante)
Navegación Hoy · Radar · Estudio · Biblioteca · Resultados; voz un 10 % más rápida en TikTok; 3 portadas; variación;
H3–H10 de `docs/plan-v2.md`.

## Supuestos tomados
- Puerto de pruebas 8090 (`python -m estudio --puerto 8090`) porque el 8080 lo ocupa un `python -m http.server`
  que sirve `site/` (lanzado desde Antigravity). El Estudio usa el 8080 por defecto cuando esté libre.
- `data/estudio.db` va aparte de `radar.db` para que descargar los datos del Radar no la pise.

## Siguiente paso
Esperando el OK de Javier para ajustar el corte 1 a los criterios del megaprompt (puntos 1–12) o usar ya lo que hay
para las piezas del 18-19 nov.

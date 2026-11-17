// ===== Utilidades comunes del panel (se cargan antes que graficas.js, hoy.js y nav.js) =====
// Memoria del navegador SOLO para preferencias (grupos abiertos, periodo, series visibles).
// Si el navegador no deja guardar (modo privado), el panel funciona igual con los valores por defecto.
const guardado = {
  leer(k, def) { try { const v = localStorage.getItem('pc.' + k); return v == null ? def : JSON.parse(v); } catch { return def; } },
  poner(k, v) { try { localStorage.setItem('pc.' + k, JSON.stringify(v)); } catch { /* sin almacenamiento: no pasa nada */ } },
};

// Piezas del panel. Lo general (el, icono, aviso, confirmar, contar) viene de ../js/interfaz.js y se comparte con el formulario.
import { el, icono } from "../js/interfaz.js";
export { $, aviso, confirmar, contar, el, icono } from "../js/interfaz.js";

const SVG = "http://www.w3.org/2000/svg";
export const num = (n) => Number(n).toLocaleString("es-EC");
export const NOMBRE_ESTADO = { aceptar: "Aceptado", revisar: "Por revisar", descartar: "Descartado", sin_calcular: "Sin calcular" };
export const NOMBRE_DIMENSION = { completitud: "Completo", validez: "Con sentido", exactitud: "Ubicación", consistencia: "Fecha", unicidad: "No repetido", oportunidad: "Rapidez" };

export function nombreCategoria(config, id) {
  const c = config && config.categorias.find((x) => x.id === id);
  return c ? c.nombre : id;
}

export const hora = (iso) => new Date(iso).toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" });
export const fechaLarga = (iso) => new Date(iso).toLocaleString("es-EC", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).replace(".", "");

// "hace 5 min", "hace 3 h", "ayer 14:05" o "12 dic"
export function hace(iso) {
  const segundos = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (segundos < 45) return "hace un momento";
  if (segundos < 3600) return "hace " + Math.round(segundos / 60) + " min";
  if (segundos < 86400) return "hace " + Math.round(segundos / 3600) + " h";
  if (segundos < 172800) return "ayer " + hora(iso);
  return new Date(iso).toLocaleDateString("es-EC", { day: "numeric", month: "short" }).replace(".", "");
}

export function pildora(estado, puntaje) {
  const clave = estado || "sin_calcular";
  return el("span", { class: "pildora p-" + clave }, el("i"), puntaje != null ? Math.round(puntaje) + " · " + NOMBRE_ESTADO[clave] : NOMBRE_ESTADO[clave]);
}

export const colorDeNota = (p) => (p >= 80 ? "ok" : p >= 50 ? "aviso" : "malo");

// anillo de progreso (SVG) que se llena solo
export function anillo(porcentaje, centro, subtitulo, clase = "") {
  const r = 52, c = 2 * Math.PI * r;
  const dibujo = document.createElementNS(SVG, "svg");
  dibujo.setAttribute("viewBox", "0 0 140 140");
  dibujo.setAttribute("class", "anillo-progreso " + clase);
  dibujo.setAttribute("role", "img");
  dibujo.setAttribute("aria-label", centro + " " + subtitulo);
  const circulo = (clase2) => { const e = document.createElementNS(SVG, "circle"); e.setAttribute("class", clase2); e.setAttribute("cx", 70); e.setAttribute("cy", 70); e.setAttribute("r", r); return e; };
  const fondo = circulo("fondo"), valor = circulo("valor");
  valor.setAttribute("stroke-dasharray", c.toFixed(1));
  valor.setAttribute("stroke-dashoffset", c.toFixed(1));
  requestAnimationFrame(() => requestAnimationFrame(() => valor.setAttribute("stroke-dashoffset", (c * (1 - Math.min(1, Math.max(0, porcentaje) / 100))).toFixed(1))));
  const texto = (y, clase2, contenido) => { const t = document.createElementNS(SVG, "text"); t.setAttribute("x", 70); t.setAttribute("y", y); if (clase2) t.setAttribute("class", clase2); t.textContent = contenido; return t; };
  dibujo.append(fondo, valor, texto(74, "", centro), texto(91, "sub", subtitulo));
  return dibujo;
}

// tarjeta con titulo (la unidad basica de todas las pestañas)
export function tarjeta(titulo, ...contenido) {
  return el("section", { class: "tarjeta" }, titulo ? el("h2", { text: titulo }) : null, ...contenido);
}
export { icono as iconoPanel };

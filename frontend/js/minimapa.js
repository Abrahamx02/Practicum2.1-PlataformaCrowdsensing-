// Mini mapa del paso "Donde": muestra tu punto GPS con su circulo de precision y deja corregirlo moviendo el mapa
// (el pin queda fijo al centro, como en las apps de transporte). Lo corregido se marca como "ubicacion puesta a mano".
import { aGeo, aMundo, dibujarMosaicos, limpiarMosaicos, metrosPorPixel } from "./geomapa.js";
import { el, icono } from "./interfaz.js";

const MAXIMO_AJUSTE_M = 150;

export function crearMinimapa(contenedor, alCambiar) {
  const mosaicos = new Map();
  const vista = { z: 18, lon: 0, lat: 0, w: 0, h: 0 };
  let gps = null, arrastre = null;
  const capaMosaicos = el("div", { class: "mini-mosaicos" });
  const circulo = el("div", { class: "mini-circulo" });
  const aviso = el("div", { class: "mini-aviso", text: "Mueve el mapa si el pin no está justo donde estás." });
  const volver = el("button", { type: "button", class: "boton-vidrio", "aria-label": "Volver a mi ubicación GPS", hidden: true, onclick: () => { vista.lon = gps.lon; vista.lat = gps.lat; avisar(false); dibujar(); } }, icono("centrar"));
  contenedor.replaceChildren(capaMosaicos, el("div", { class: "mini-capa" }, circulo),
    el("div", { class: "mini-pin" }, icono("pin")),
    el("div", { class: "mini-controles" },
      el("button", { type: "button", class: "boton-vidrio", "aria-label": "Acercar", onclick: () => zoom(1) }, icono("mas")),
      el("button", { type: "button", class: "boton-vidrio", "aria-label": "Alejar", onclick: () => zoom(-1) }, icono("menos")), volver), aviso);

  function medir() { vista.w = contenedor.clientWidth; vista.h = contenedor.clientHeight; }
  function distanciaAlGps() {
    return Math.hypot((vista.lat - gps.lat) * 111320, (vista.lon - gps.lon) * 111320 * Math.cos(gps.lat * Math.PI / 180));
  }
  function avisar(movido) { volver.hidden = !movido; aviso.textContent = movido ? "Punto corregido a mano. Toca ⌖ para volver al GPS." : "Mueve el mapa si el pin no está justo donde estás."; }
  function dibujar() {
    if (!gps) return;
    if (!vista.w) medir();
    dibujarMosaicos(capaMosaicos, mosaicos, vista);
    const [cx, cy] = aMundo(vista.lon, vista.lat, vista.z), [gx, gy] = aMundo(gps.lon, gps.lat, vista.z);
    const radio = Math.max(8, gps.precision / metrosPorPixel(gps.lat, vista.z));
    circulo.style.width = circulo.style.height = radio * 2 + "px";
    circulo.style.left = vista.w / 2 + (gx - cx) + "px";
    circulo.style.top = vista.h / 2 + (gy - cy) + "px";
  }
  function zoom(paso) { vista.z = Math.max(15, Math.min(19, vista.z + paso)); dibujar(); }
  function terminar() {
    if (!arrastre) return;
    arrastre = null;
    contenedor.classList.remove("moviendo");
    if (distanciaAlGps() > MAXIMO_AJUSTE_M) {            // no se permite alejar el punto mas de 150 m del GPS
      vista.lon = gps.lon; vista.lat = gps.lat;
      aviso.textContent = "Solo puedes corregir hasta " + MAXIMO_AJUSTE_M + " m de tu GPS.";
      dibujar();
    }
    const movido = distanciaAlGps() > 5;
    avisar(movido && distanciaAlGps() <= MAXIMO_AJUSTE_M);
    alCambiar({ lat: vista.lat, lon: vista.lon, ajustada: movido });
  }
  contenedor.addEventListener("pointerdown", (e) => { if (e.target.closest(".mini-controles") || !gps) return; arrastre = { x: e.clientX, y: e.clientY }; contenedor.classList.add("moviendo"); });
  window.addEventListener("pointermove", (e) => {
    if (!arrastre) return;
    const [cx, cy] = aMundo(vista.lon, vista.lat, vista.z);
    [vista.lon, vista.lat] = aGeo(cx - (e.clientX - arrastre.x), cy - (e.clientY - arrastre.y), vista.z);
    arrastre = { x: e.clientX, y: e.clientY };
    dibujar();
  });
  window.addEventListener("pointerup", terminar);
  window.addEventListener("pointercancel", terminar);
  document.addEventListener("mcs-tema", () => { limpiarMosaicos(mosaicos); dibujar(); });

  return {
    mostrar(punto) { gps = { lat: punto.lat, lon: punto.lon, precision: punto.precision }; vista.lat = punto.lat; vista.lon = punto.lon; vista.z = punto.precision > 60 ? 17 : 18; contenedor.hidden = false; medir(); avisar(false); dibujar(); },
    ocultar() { gps = null; contenedor.hidden = true; limpiarMosaicos(mosaicos); },
  };
}

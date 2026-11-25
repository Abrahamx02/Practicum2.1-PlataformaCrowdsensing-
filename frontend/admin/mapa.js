// Pestaña "Mapa": un mapa propio y liviano (mosaicos CARTO/OpenStreetMap + puntos). No usa librerías externas.
import { aGeo, aMundo, dibujarMosaicos, limpiarMosaicos } from "../js/geomapa.js";
import { $, el, icono, nombreCategoria, NOMBRE_ESTADO } from "./ui.js";
import { alCambiar, estado } from "./datos.js";
import { abrirHoja } from "./reportes.js";

const ZMIN = 11, ZMAX = 19;
const vista = { z: 15, lon: -79.2, lat: -3.99, w: 0, h: 0 };
const mosaicos = new Map(), marcas = new Map(), punteros = new Map();
let caja, capaMosaicos, capaMarcas, lienzo, cuadroZona, activo = false, ajustado = false, calor = false, filtroEstado = "todos";
let arrastrado = false, distanciaInicial = 0, ultimaRueda = 0;

export function iniciarMapa() {
  const filtros = el("div", { class: "segmentos segmentos-mapa", id: "chips-mapa", role: "group", "aria-label": "Estado" });
  capaMosaicos = el("div", { class: "capa-mosaicos" });
  capaMarcas = el("div", { class: "capa-marcas" });
  lienzo = el("canvas", { class: "capa-calor", "aria-hidden": "true" });
  cuadroZona = el("div", { class: "zona-mapa", title: "Zona del piloto" });
  caja = el("div", { class: "mapa", id: "mapa" }, capaMosaicos, cuadroZona, lienzo, capaMarcas,
    el("div", { class: "mapa-arriba" }, filtros,
      el("label", { class: "interruptor" }, el("input", { type: "checkbox", onchange: (e) => { calor = e.target.checked; caja.classList.toggle("con-calor", calor); dibujar(); } }), el("span", { text: "Calor" }))),
    el("div", { class: "mapa-controles" },
      el("button", { type: "button", class: "boton-vidrio", "aria-label": "Acercar", onclick: () => zoomEn(1, vista.w / 2, vista.h / 2) }, icono("mas")),
      el("button", { type: "button", class: "boton-vidrio", "aria-label": "Alejar", onclick: () => zoomEn(-1, vista.w / 2, vista.h / 2) }, icono("menos")),
      el("button", { type: "button", class: "boton-vidrio", "aria-label": "Centrar en la zona", onclick: () => { ajustar(); dibujar(); } }, icono("centrar"))),
    el("div", { class: "mapa-pie" },
      el("span", { class: "leyenda-mapa" }, ...["aceptar", "revisar", "descartar"].map((e) => el("span", { class: "m-" + e }, el("i"), NOMBRE_ESTADO[e]))),
      el("span", { class: "atribucion", text: "© OpenStreetMap · © CARTO" })));
  $("vista-mapa").append(el("div", { class: "encabezado-vista" }, el("h2", { text: "Mapa" }), el("span", { class: "cuenta", id: "mapa-cuenta" })), caja);
  dibujarChips();

  caja.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".mapa-arriba, .mapa-controles")) return;
    punteros.set(e.pointerId, { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY });
    arrastrado = false;
    if (punteros.size === 2) distanciaInicial = distanciaEntrePunteros();
  });
  window.addEventListener("pointermove", (e) => {
    const p = punteros.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    if (Math.hypot(e.clientX - p.x0, e.clientY - p.y0) > 5) arrastrado = true;
    if (punteros.size === 1) {
      const [cx, cy] = aMundo(vista.lon, vista.lat, vista.z);
      [vista.lon, vista.lat] = aGeo(cx - dx, cy - dy, vista.z);
      vista.lat = Math.max(-84, Math.min(84, vista.lat));
      dibujar();
    } else if (punteros.size === 2 && distanciaInicial) {
      const razon = distanciaEntrePunteros() / distanciaInicial;
      if (razon > 1.5 || razon < 0.67) {
        const [a, b] = [...punteros.values()], c = caja.getBoundingClientRect();
        zoomEn(razon > 1 ? 1 : -1, (a.x + b.x) / 2 - c.left, (a.y + b.y) / 2 - c.top);
        distanciaInicial = distanciaEntrePunteros();
      }
    }
  });
  const soltar = (e) => { punteros.delete(e.pointerId); distanciaInicial = 0; setTimeout(() => { arrastrado = false; }, 0); };
  window.addEventListener("pointerup", soltar);
  window.addEventListener("pointercancel", soltar);
  caja.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (Date.now() - ultimaRueda < 260) return;
    ultimaRueda = Date.now();
    const c = caja.getBoundingClientRect();
    zoomEn(e.deltaY < 0 ? 1 : -1, e.clientX - c.left, e.clientY - c.top);
  }, { passive: false });
  caja.addEventListener("dblclick", (e) => { const c = caja.getBoundingClientRect(); zoomEn(1, e.clientX - c.left, e.clientY - c.top); });
  capaMarcas.addEventListener("click", (e) => {
    const marca = e.target.closest(".marcador");
    if (marca && !arrastrado) abrirHoja(Number(marca.dataset.id));
  });
  new ResizeObserver(() => { medir(); if (activo) dibujar(); }).observe(caja);
  document.addEventListener("mcs-tema", () => { limpiarMosaicos(mosaicos); if (activo) dibujar(); });
  alCambiar(() => { if (activo) dibujar(); });
}

const distanciaEntrePunteros = () => { const [a, b] = [...punteros.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
function medir() { vista.w = caja.clientWidth; vista.h = caja.clientHeight; }

export function mostrarMapa(visible) {
  activo = visible;
  if (!visible) return;
  medir();
  if (!ajustado && vista.w) { ajustar(); ajustado = true; }
  dibujar();
}

export function centrarEn(lat, lon) {
  vista.lat = lat; vista.lon = lon; vista.z = 18;
}

function dibujarChips() {
  $("chips-mapa").replaceChildren(...[["todos", "Todos"], ["aceptar", "Aceptados"], ["revisar", "Revisar"], ["descartar", "Descartados"]].map(([clave, texto]) =>
    el("button", { type: "button", "aria-pressed": String(filtroEstado === clave), text: texto, onclick: () => { filtroEstado = clave; dibujarChips(); dibujar(); } })));
}

function ajustar() {
  const z = estado.config.zona;
  let [lonMin, lonMax, latMin, latMax] = [z.lon_min, z.lon_max, z.lat_min, z.lat_max];
  for (const r of estado.reportes) {          // se incluyen los puntos pegados a la zona; uno lejano no debe alejar todo el mapa (se llega a el con el zoom)
    if (r.lon > z.lon_min - 0.004 && r.lon < z.lon_max + 0.004 && r.lat > z.lat_min - 0.004 && r.lat < z.lat_max + 0.004) {
      lonMin = Math.min(lonMin, r.lon); lonMax = Math.max(lonMax, r.lon); latMin = Math.min(latMin, r.lat); latMax = Math.max(latMax, r.lat);
    }
  }
  vista.lon = (lonMin + lonMax) / 2; vista.lat = (latMin + latMax) / 2; vista.z = ZMIN;
  for (let zoom = ZMAX; zoom >= ZMIN; zoom--) {
    const [x1, y1] = aMundo(lonMin, latMax, zoom), [x2, y2] = aMundo(lonMax, latMin, zoom);
    if (x2 - x1 <= vista.w * 0.88 && y2 - y1 <= vista.h * 0.88) { vista.z = zoom; break; }
  }
}

function zoomEn(paso, px, py) {
  const nuevo = Math.max(ZMIN, Math.min(ZMAX, vista.z + paso));
  if (nuevo === vista.z) return;
  const [cx, cy] = aMundo(vista.lon, vista.lat, vista.z), escala = 2 ** (nuevo - vista.z);
  const wx = (cx - vista.w / 2 + px) * escala, wy = (cy - vista.h / 2 + py) * escala;
  [vista.lon, vista.lat] = aGeo(wx - px + vista.w / 2, wy - py + vista.h / 2, nuevo);
  vista.z = nuevo;
  dibujar();
}

function dibujar() {
  if (!vista.w || !estado.config) return;
  const [ox, oy] = dibujarMosaicos(capaMosaicos, mosaicos, vista);

  const z = estado.config.zona, [x1, y1] = aMundo(z.lon_min, z.lat_max, vista.z), [x2, y2] = aMundo(z.lon_max, z.lat_min, vista.z);
  Object.assign(cuadroZona.style, { left: x1 - ox + "px", top: y1 - oy + "px", width: x2 - x1 + "px", height: y2 - y1 + "px" });

  const visibles = estado.reportes.filter((r) => filtroEstado === "todos" || (r.estado_calidad || "sin_calcular") === filtroEstado);
  $("mapa-cuenta").textContent = visibles.length + (visibles.length === 1 ? " punto" : " puntos");
  const usados = new Set(), puntos = [];
  for (const r of visibles) {
    const [x, y] = aMundo(r.lon, r.lat, vista.z), px = x - ox, py = y - oy;
    if (px < -30 || py < -30 || px > vista.w + 30 || py > vista.h + 30) continue;
    puntos.push([px, py]);
    usados.add(r.id);
    let marca = marcas.get(r.id);
    if (!marca) {
      marca = el("button", { type: "button", "data-id": r.id, "aria-label": "Reporte " + r.id + ", " + nombreCategoria(estado.config, r.categoria) });
      marcas.set(r.id, marca);
      capaMarcas.append(marca);
    }
    marca.className = "marcador m-" + (r.estado_calidad || "sin_calcular");
    marca.style.transform = "translate(" + px.toFixed(1) + "px," + py.toFixed(1) + "px)";
  }
  for (const [id, marca] of marcas) if (!usados.has(id)) { marca.remove(); marcas.delete(id); }

  lienzo.width = calor ? vista.w : 0; lienzo.height = calor ? vista.h : 0;
  if (calor) {
    const c = lienzo.getContext("2d");
    for (const [px, py] of puntos) {
      const g = c.createRadialGradient(px, py, 0, px, py, 46);
      g.addColorStop(0, "rgba(255, 94, 48, .42)"); g.addColorStop(1, "rgba(255, 94, 48, 0)");
      c.fillStyle = g; c.fillRect(px - 46, py - 46, 92, 92);
    }
  }
}

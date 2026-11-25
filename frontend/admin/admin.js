// Panel del equipo: entrada, navegacion y refresco automatico. Cada pestaña vive en su propio archivo.
import { botonTema } from "../js/interfaz.js";
import { pedir } from "../js/api.js";
import { pintarCalidad, pintarGente } from "./calidad.js";
import { alCambiar, api, cargarTodo, estado } from "./datos.js";
import { pintarDefensa } from "./defensa.js";
import { pintarInicio } from "./inicio.js";
import { iniciarMapa, mostrarMapa, centrarEn } from "./mapa.js";
import { dibujarLista, filtrarPorEstado, ganchos, iniciarReportes } from "./reportes.js";
import { pintarSistema } from "./sistema.js";
import { $, aviso, el, hace, icono } from "./ui.js";

const VISTAS = [
  { id: "inicio", nombre: "Inicio", icono: "inicio", principal: true },
  { id: "mapa", nombre: "Mapa", icono: "mapa", principal: true },
  { id: "reportes", nombre: "Reportes", icono: "reportes", principal: true },
  { id: "calidad", nombre: "Calidad", icono: "calidad", principal: true },
  { id: "gente", nombre: "Participantes", icono: "gente" },
  { id: "sistema", nombre: "Sistema", icono: "sistema" },
  { id: "defensa", nombre: "Defensa", icono: "defensa" },
];
const PINTAR = { inicio: () => pintarInicio(irA), calidad: () => pintarCalidad(irA), gente: pintarGente, sistema: pintarSistema, defensa: () => pintarDefensa(irA), reportes: dibujarLista, mapa: () => {} };
let actual = "inicio", cargando = false, iniciado = false;

function mostrarAcceso(mensaje) {
  $("app").hidden = true; $("acciones").hidden = true; $("acceso").hidden = false;
  $("clave").value = "";
  if (mensaje) { $("error-acceso").hidden = false; $("error-acceso").lastChild.textContent = mensaje; }
}

export function irA(vista, opciones = {}) {
  if (!VISTAS.some((v) => v.id === vista)) vista = "inicio";
  actual = vista;
  for (const v of VISTAS) $("vista-" + v.id).hidden = v.id !== vista;
  document.querySelectorAll("#nav button[data-vista]").forEach((b) => (b.dataset.vista === vista ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current")));
  mostrarMapa(vista === "mapa");
  if (opciones.estado) filtrarPorEstado(opciones.estado);
  PINTAR[vista]();
  if (location.hash !== "#" + vista) history.replaceState(null, "", "#" + vista);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function dibujarNavegacion() {
  const botones = VISTAS.map((v) => el("button", { type: "button", "data-vista": v.id, class: v.principal ? "" : "secundaria", onclick: () => irA(v.id) },
    icono(v.icono), el("span", { text: v.nombre }), v.id === "reportes" ? el("span", { class: "insignia", id: "insignia-reportes", hidden: true }) : null));
  botones.push(el("button", { type: "button", class: "mas-boton", onclick: abrirMas }, icono("mas-puntos"), el("span", { text: "Más" })));
  $("nav").replaceChildren(el("div", {}, ...botones));
}

function abrirMas() {
  $("mas").replaceChildren(el("div", { class: "hoja-caja" }, el("div", { class: "hoja-asa" }),
    el("div", { class: "hoja-cabecera" }, el("div", {}, el("h2", { text: "Más" })), el("button", { type: "button", class: "boton-icono", "aria-label": "Cerrar", onclick: () => $("mas").close() }, icono("cerrar"))),
    el("div", { class: "hoja-cuerpo" }, ...VISTAS.filter((v) => !v.principal).map((v) => el("button", { type: "button", class: "fila-reporte", onclick: () => { $("mas").close(); irA(v.id); } },
      el("span", { class: "ico-cat c-otro" }, icono(v.icono)), el("span", { class: "fila-texto" }, el("strong", { text: v.nombre })), icono("siguiente", "icono chevron"))))));
  $("mas").addEventListener("click", (e) => { if (e.target === $("mas")) $("mas").close(); }, { once: true });
  $("mas").showModal();
}

function dibujarBarra() {
  const vivo = el("span", { class: "vivo", id: "vivo", title: "Los datos se actualizan solos cada 30 segundos" }, el("i"), el("span", { id: "vivo-texto", text: "En vivo" }));
  const refrescar = el("button", { type: "button", class: "boton-icono", id: "boton-refrescar", "aria-label": "Actualizar ahora", onclick: () => actualizar(true) }, icono("refrescar"));
  const presentacion = el("button", { type: "button", class: "boton-icono", id: "boton-presentacion", "aria-pressed": "false", "aria-label": "Modo presentación: oculta códigos y ubicaciones",
    title: "Modo presentación: oculta códigos y ubicaciones", onclick: (e) => { const on = document.body.classList.toggle("presentacion"); e.currentTarget.setAttribute("aria-pressed", String(on)); aviso(on ? "Modo presentación activado" : "Modo presentación apagado"); } }, icono("ojo-cerrado"));
  const salir = el("button", { type: "button", class: "boton-icono", "aria-label": "Cerrar sesión", title: "Cerrar sesión", onclick: cerrarSesion }, icono("salir"));
  $("acciones").replaceChildren(vivo, presentacion, botonTema(), refrescar, salir);
  $("acciones").hidden = false;
}

async function actualizar(manual = false) {
  if (cargando || !estado.sesion) return;
  cargando = true;
  if (manual) $("boton-refrescar").classList.add("girando");
  try {
    await cargarTodo();
    if (manual) aviso("Datos al día");
  } catch (e) {
    if (e.estado === 401) mostrarSesionVencida();
    else if (manual) aviso(e.message, "error");
  } finally { cargando = false; $("boton-refrescar") && $("boton-refrescar").classList.remove("girando"); }
}

function mostrarSesionVencida() {
  estado.sesion = "";
  try { sessionStorage.removeItem("mcs.sesion"); } catch (e) { /* sin permiso */ }
  mostrarAcceso("Tu sesión venció. Entra de nuevo.");
}

async function cerrarSesion() {
  try { await api("/sesion", { method: "DELETE" }); } catch (e) { /* si ya venció, da igual */ }
  estado.sesion = "";
  try { sessionStorage.removeItem("mcs.sesion"); } catch (e) { /* sin permiso */ }
  document.body.classList.remove("presentacion");
  history.replaceState(null, "", location.pathname);
  mostrarAcceso();
}

async function arrancar() {
  dibujarBarra();
  dibujarNavegacion();
  if (!iniciado) {
    iniciado = true;
    iniciarMapa(); iniciarReportes();
    ganchos.irAlMapa = (lat, lon) => { centrarEn(lat, lon); irA("mapa"); };
    alCambiar(() => {
      const porRevisar = (estado.stats.por_estado || {}).revisar || 0;
      const insignia = $("insignia-reportes");
      if (insignia) { insignia.hidden = !porRevisar; insignia.textContent = String(porRevisar); }
      PINTAR[actual]();
      if (actual === "mapa") mostrarMapa(true);
    });
    setInterval(() => { if (!document.hidden && estado.sesion) actualizar(); }, 30000);
    setInterval(() => {
      if (!estado.actualizado) return;
      const s = Math.round((Date.now() - estado.actualizado) / 1000);
      const texto = $("vivo-texto");
      if (texto) { texto.textContent = s < 8 ? "En vivo" : "Actualizado hace " + (s < 60 ? s + " s" : Math.round(s / 60) + " min"); $("vivo").classList.toggle("viejo", s > 75); }
    }, 5000);
    window.addEventListener("hashchange", () => { if (estado.sesion) irA(location.hash.slice(1)); });
  }
  await cargarTodo();
  $("acceso").hidden = true;
  $("app").hidden = false;
  irA(location.hash.slice(1) || "inicio");
}

$("formulario-acceso").addEventListener("submit", async (e) => {
  e.preventDefault();
  const boton = $("boton-entrar");
  boton.disabled = true; boton.classList.add("cargando");
  $("error-acceso").hidden = true;
  try {
    const r = await pedir("/sesion", { method: "POST", headers: { "x-clave": $("clave").value.trim() } });
    estado.sesion = r.sesion;
    try { sessionStorage.setItem("mcs.sesion", r.sesion); } catch (err) { /* sin permiso: la sesion dura mientras no recargues */ }
    $("clave").value = "";
    await arrancar();
  } catch (error) {
    $("error-acceso").hidden = false;
    $("error-acceso").lastChild.textContent = error.estado === 401 ? "Clave incorrecta." : error.estado === 429 ? "Demasiados intentos. Espera un minuto." : error.message;
  } finally { boton.disabled = false; boton.classList.remove("cargando"); }
});

(async function inicio() {
  let guardada = "";
  try { guardada = sessionStorage.getItem("mcs.sesion") || ""; } catch (e) { /* sin permiso */ }
  if (!guardada) return;
  estado.sesion = guardada;
  try { await arrancar(); } catch (e) { mostrarSesionVencida(); }
})();

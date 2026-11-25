// Piezas de interfaz que comparten el formulario y el panel. Los textos entran siempre con textContent (nunca innerHTML):
// asi un dato raro no puede ejecutar codigo.
const SVG = "http://www.w3.org/2000/svg";
export const $ = (id) => document.getElementById(id);

// el("button", { class: "boton", onclick: fn }, "Texto", otroNodo)
export function el(etiqueta, atributos, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos || {})) {
    if (valor === false || valor == null) continue;
    if (clave === "class") nodo.className = valor;
    else if (clave === "text") nodo.textContent = valor;
    else if (clave.startsWith("on")) nodo.addEventListener(clave.slice(2), valor);
    else nodo.setAttribute(clave, valor === true ? "" : valor);
  }
  for (const hijo of hijos.flat()) if (hijo != null && hijo !== false) nodo.append(hijo);
  return nodo;
}

export function icono(nombre, clase = "icono") {
  const dibujo = document.createElementNS(SVG, "svg");
  dibujo.setAttribute("class", clase);
  dibujo.setAttribute("aria-hidden", "true");
  const uso = document.createElementNS(SVG, "use");
  uso.setAttribute("href", "/iconos.svg#i-" + nombre);
  dibujo.append(uso);
  return dibujo;
}

// aviso corto arriba de la pantalla (como las notificaciones del iPhone)
export function aviso(texto, tipo = "ok") {
  let caja = $("avisos");
  if (!caja) { caja = el("div", { class: "avisos", id: "avisos", "aria-live": "polite" }); document.body.append(caja); }
  const nota = el("div", { class: "aviso aviso-" + tipo, role: "status" }, icono(tipo === "error" ? "alerta" : "check"), el("span", { text: texto }));
  caja.append(nota);
  if (tipo === "ok" && navigator.vibrate) navigator.vibrate(10);
  setTimeout(() => nota.classList.add("saliendo"), 3800);
  setTimeout(() => nota.remove(), 4300);
}

// pregunta de confirmacion con el mismo estilo del sistema; devuelve true o false
export function confirmar({ titulo, texto, boton = "Confirmar", peligro = false }) {
  let dialogo = $("dialogo");
  if (!dialogo) { dialogo = el("dialog", { class: "dialogo", id: "dialogo" }); document.body.append(dialogo); }
  return new Promise((resolver) => {
    const cerrar = (valor) => { dialogo.close(); resolver(valor); };
    dialogo.replaceChildren(el("div", { class: "dialogo-caja" },
      el("h2", { text: titulo }), el("p", { class: "paso-ayuda", text: texto }),
      el("div", { class: "acciones" },
        el("button", { type: "button", class: "boton boton-secundario", text: "Cancelar", onclick: () => cerrar(false) }),
        el("button", { type: "button", class: "boton " + (peligro ? "boton-peligro" : "boton-primario"), text: boton, onclick: () => cerrar(true) }))));
    dialogo.addEventListener("cancel", () => resolver(false), { once: true });
    dialogo.showModal();
  });
}

// los numeros "suben" hasta su valor (da sensacion de panel vivo)
export function contar(nodo, valor, formato = (n) => Number(n).toLocaleString("es-EC")) {
  const final = Number(valor);
  if (!Number.isFinite(final) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { nodo.textContent = formato(final); return; }
  const inicio = performance.now();
  const paso = (ahora) => {
    const t = Math.min(1, (ahora - inicio) / 700);
    nodo.textContent = formato(Math.round(final * (1 - Math.pow(1 - t, 3))));
    if (t < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// boton que cambia entre Auto / Claro / Oscuro
export function botonTema() {
  const ICONOS = { auto: "auto", claro: "sol", oscuro: "luna" }, NOMBRES = { auto: "Automático", claro: "Claro", oscuro: "Oscuro" };
  const boton = el("button", { type: "button", class: "boton-icono" });
  const pintar = () => {
    const modo = window.MCS_TEMA ? window.MCS_TEMA.modo() : "auto";
    boton.replaceChildren(icono(ICONOS[modo]));
    boton.setAttribute("aria-label", "Apariencia: " + NOMBRES[modo] + ". Toca para cambiar");
    boton.title = "Apariencia: " + NOMBRES[modo];
  };
  boton.addEventListener("click", () => {
    const orden = ["auto", "claro", "oscuro"], ahora = window.MCS_TEMA.modo();
    window.MCS_TEMA.fijar(orden[(orden.indexOf(ahora) + 1) % 3]);
    pintar();
  });
  pintar();
  return boton;
}

// selector de tres opciones (para la pantalla de Ayuda)
export function selectorTema() {
  const opciones = [["auto", "Automático"], ["claro", "Claro"], ["oscuro", "Oscuro"]];
  const caja = el("div", { class: "segmentos", role: "group", "aria-label": "Apariencia" });
  const pintar = () => caja.replaceChildren(...opciones.map(([clave, texto]) =>
    el("button", { type: "button", "aria-pressed": String(window.MCS_TEMA.modo() === clave), text: texto, onclick: () => { window.MCS_TEMA.fijar(clave); pintar(); } })));
  pintar();
  return caja;
}

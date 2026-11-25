// Pestaña "Reportes": lista con filtros y la hoja de detalle donde el equipo decide qué hacer con cada reporte
import { api, cargarTodo, estado, olvidarFoto, urlDeFoto } from "./datos.js";
import { $, NOMBRE_DIMENSION, NOMBRE_ESTADO, aviso, colorDeNota, confirmar, el, fechaLarga, hace, icono, nombreCategoria, num, pildora } from "./ui.js";

export const ganchos = { irAlMapa: null };       // lo conecta admin.js para no mezclar las pestañas
const filtro = { estado: "todos", categoria: "", texto: "", limite: 40 };
const CHIPS = [["todos", "Todos"], ["aceptar", "Aceptados"], ["revisar", "Por revisar"], ["descartar", "Descartados"]];

export function filtrarPorEstado(nuevo) {
  Object.assign(filtro, { estado: nuevo, texto: "", categoria: "", limite: 40 });
  if ($("buscar-reportes")) { $("buscar-reportes").value = ""; $("filtro-categoria").value = ""; }
  dibujarChips();
  dibujarLista();
}

export function iniciarReportes() {
  const raiz = $("vista-reportes");
  const categorias = el("select", { id: "filtro-categoria", "aria-label": "Tipo de problema", onchange: (e) => { filtro.categoria = e.target.value; filtro.limite = 40; dibujarLista(); } },
    el("option", { value: "", text: "Todos los tipos" }));
  raiz.append(
    el("div", { class: "encabezado-vista" }, el("h2", { text: "Reportes" }), el("span", { class: "cuenta", id: "reportes-cuenta" })),
    el("div", { class: "barra-filtros" },
      el("label", { class: "buscador" }, icono("buscar"),
        el("input", { type: "search", id: "buscar-reportes", placeholder: "Buscar por número, código o texto", autocomplete: "off",
          oninput: (e) => { filtro.texto = e.target.value; filtro.limite = 40; dibujarLista(); } })),
      categorias),
    el("div", { class: "segmentos", id: "chips-reportes", role: "group", "aria-label": "Estado" }),
    el("div", { class: "lista", id: "lista-reportes" }),
    el("div", { class: "centrado" }, el("button", { type: "button", class: "boton boton-secundario", id: "ver-mas", text: "Ver más", onclick: () => { filtro.limite += 40; dibujarLista(); } })));
  $("hoja").addEventListener("click", (e) => { if (e.target === $("hoja")) $("hoja").close(); });
  dibujarChips();
}

function dibujarChips() {
  $("chips-reportes").replaceChildren(...CHIPS.map(([clave, texto]) =>
    el("button", { type: "button", "aria-pressed": String(filtro.estado === clave), text: texto,
      onclick: () => { filtro.estado = clave; filtro.limite = 40; dibujarChips(); dibujarLista(); } })));
}

export function dibujarLista() {
  if (!$("lista-reportes")) return;
  const selector = $("filtro-categoria");
  if (selector.options.length === 1 && estado.config) {
    for (const c of estado.config.categorias) selector.append(el("option", { value: c.id, text: c.nombre }));
  }
  const texto = filtro.texto.trim().toLowerCase().replace(/^#/, "");
  const filas = estado.reportes.filter((r) =>
    (filtro.estado === "todos" || (r.estado_calidad || "sin_calcular") === filtro.estado) &&
    (!filtro.categoria || r.categoria === filtro.categoria) &&
    (!texto || String(r.id) === texto || r.participante_id.toLowerCase().includes(texto) || r.descripcion.toLowerCase().includes(texto)))
    .sort((a, b) => b.id - a.id);
  $("reportes-cuenta").textContent = num(filas.length) + (filas.length === 1 ? " reporte" : " reportes");
  const lista = $("lista-reportes");
  if (!filas.length) {
    lista.replaceChildren(el("div", { class: "vacio-grande" }, icono("reportes"), el("strong", { text: estado.reportes.length ? "Nada con esos filtros" : "Todavía no hay reportes" }),
      el("span", { text: estado.reportes.length ? "Prueba con otro estado o borra la búsqueda." : "Cuando alguien envíe uno desde su celular, aparece aquí." })));
  } else {
    lista.replaceChildren(...filas.slice(0, filtro.limite).map((r) =>
      el("button", { type: "button", class: "fila-reporte", onclick: () => abrirHoja(r.id) },
        el("span", { class: "ico-cat c-" + r.categoria }, icono(r.categoria)),
        el("span", { class: "fila-texto" }, el("strong", { text: nombreCategoria(estado.config, r.categoria) + " · #" + r.id }),
          el("small", { text: hace(r.recibido_en) + " · " + (r.descripcion || "Sin descripción") })),
        pildora(r.estado_calidad, r.puntaje_calidad), icono("siguiente", "icono chevron"))));
  }
  $("ver-mas").hidden = filas.length <= filtro.limite;
}

// ---------- hoja de detalle ----------
function dato(titulo, valor) {
  return el("div", { class: "dato" }, el("dt", { text: titulo }), el("dd", {}, valor));
}

async function decidir(id, decision, mensaje) {
  try {
    await api("/reportes/" + id + "/decision", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision }) });
    aviso(mensaje);
    await cargarTodo();
    pintarHoja(id);
  } catch (e) { aviso(e.message, "error"); }
}

async function quitarFoto(r) {
  if (!await confirmar({ titulo: "¿Quitar la foto?", texto: "El reporte se queda, pero sin foto. Hazlo si se ven caras, placas u otros datos personales.", boton: "Quitar foto", peligro: true })) return;
  try {
    await api("/fotos/" + r.foto_id, { method: "DELETE" });
    olvidarFoto(r.foto_id);
    aviso("Foto quitada.");
    await cargarTodo();
    pintarHoja(r.id);
  } catch (e) { aviso(e.message, "error"); }
}

export function abrirHoja(id) {
  pintarHoja(id);
  if (!$("hoja").open) $("hoja").showModal();
}

function pintarHoja(id) {
  const r = estado.reportes.find((x) => x.id === id);
  if (!r) { $("hoja").close(); return; }
  const dims = r.dimensiones_calidad;
  const foto = r.foto_id ? el("div", { class: "hoja-foto cargando-foto" }) : null;
  if (foto) {
    const imagen = el("img", { alt: "Foto del reporte " + r.id });
    urlDeFoto(r.foto_id).then((u) => { imagen.src = u; foto.classList.remove("cargando-foto"); }).catch(() => { foto.textContent = "No se pudo abrir la foto"; });
    foto.append(imagen);
  }
  const porQue = dims ? el("div", { class: "por-que" }, ...Object.keys(NOMBRE_DIMENSION).map((d) => {
    const v = Math.round(100 * (dims[d] ?? 0));
    const barra = el("i"); barra.style.width = v + "%";
    return el("div", { class: "fila-barra mini n-" + colorDeNota(v) }, el("span", { text: NOMBRE_DIMENSION[d] }), el("div", { class: "pista" }, barra), el("span", { class: "valor", text: v + " %" }));
  })) : el("p", { class: "paso-ayuda", text: "Este reporte no tiene el detalle por dimensión. Toca «Recalcular» en la pestaña Calidad." });
  const demora = Math.max(0, Math.round((new Date(r.recibido_en) - new Date(r.fecha_dispositivo)) / 60000));
  const acciones = el("div", { class: "hoja-acciones" },
    el("button", { type: "button", class: "boton boton-primario", text: "Aceptar", disabled: r.estado_calidad === "aceptar" && r.revisado, onclick: () => decidir(r.id, "aceptar", "Reporte aceptado.") }),
    el("button", { type: "button", class: "boton boton-secundario", text: "Dejar por revisar", disabled: r.estado_calidad === "revisar" && r.revisado, onclick: () => decidir(r.id, "revisar", "Queda por revisar.") }),
    el("button", { type: "button", class: "boton boton-peligro", text: "Descartar", disabled: r.estado_calidad === "descartar" && r.revisado, onclick: () => decidir(r.id, "descartar", "Reporte descartado.") }),
    r.revisado ? el("button", { type: "button", class: "boton boton-texto", text: "Volver al cálculo automático", onclick: () => decidir(r.id, "auto", "Vuelve al cálculo automático.") }) : null,
    r.foto_id ? el("button", { type: "button", class: "boton boton-texto texto-peligro", text: "Quitar foto", onclick: () => quitarFoto(r) }) : null);
  $("hoja").replaceChildren(el("div", { class: "hoja-caja" },
    el("div", { class: "hoja-asa", "aria-hidden": "true" }),
    el("div", { class: "hoja-cabecera" },
      el("span", { class: "ico-cat grande c-" + r.categoria }, icono(r.categoria)),
      el("div", {}, el("h2", { text: nombreCategoria(estado.config, r.categoria) }), el("small", { text: "Reporte #" + r.id + " · " + hace(r.recibido_en) })),
      el("button", { type: "button", class: "boton-icono", "aria-label": "Cerrar", onclick: () => $("hoja").close() }, icono("cerrar"))),
    el("div", { class: "hoja-cuerpo" },
      foto,
      el("div", { class: "fila-pildoras" }, pildora(r.estado_calidad, r.puntaje_calidad), r.revisado ? el("span", { class: "etiqueta-chica", text: "Decidido por el equipo" }) : null),
      el("p", { class: "descripcion-reporte", text: r.descripcion || "Sin descripción." }),
      r.motivo_calidad ? el("div", { class: "alerta aviso" }, icono("alerta"), el("p", { text: "Ojo: " + r.motivo_calidad + "." })) : el("div", { class: "alerta ok" }, icono("check"), el("p", { text: "Todo en orden con este reporte." })),
      el("h3", { text: "Cómo sacó este puntaje" }), porQue,
      el("h3", { text: "Datos" }),
      el("dl", { class: "datos" },
        dato("Dónde", el("span", { class: "privado" }, r.lat.toFixed(5) + ", " + r.lon.toFixed(5) + (r.precision_m != null ? " (±" + Math.round(r.precision_m) + " m) " : " "),
          ganchos.irAlMapa ? el("button", { type: "button", class: "boton-enlace", text: "Ver en el mapa", onclick: () => { $("hoja").close(); ganchos.irAlMapa(r.lat, r.lon); } }) : null)),
        dato("Llegó", fechaLarga(r.recibido_en) + (demora > 1 ? " (tardó " + demora + " min)" : "")),
        dato("Celular", r.plataforma === "ios" ? "iPhone" : r.plataforma === "android" ? "Android" : "Otro"),
        dato("Participante", el("code", { class: "privado", text: r.participante_id })),
        dato("Consentimiento", "Aceptado · " + r.consentimiento_version))),
    acciones));
}

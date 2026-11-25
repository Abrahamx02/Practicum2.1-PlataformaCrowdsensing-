// Pestaña "Sistema": datos (descargar, importar, ejemplos), seguridad, servidor, documentación de la API y auditoría
import { api, bajar, cargarTodo, estado } from "./datos.js";
import { $, aviso, confirmar, el, fechaLarga, icono, num, tarjeta } from "./ui.js";

const SECCIONES = [["datos", "Datos"], ["seguridad", "Seguridad"], ["servidor", "Servidor"], ["api", "API"], ["auditoria", "Auditoría"]];
const ACCIONES = { inicio_sesion: "Entró al panel", importar: "Subió datos (CSV)", calidad: "Envió calidad externa", recalcular_calidad: "Recalculó la calidad", decidir_reporte: "Decidió un reporte",
  descartar_foto: "Quitó una foto", retirar_participante: "Retiró a un participante", retiro_voluntario: "Un participante se retiró solo", cargar_ejemplos: "Cargó datos de ejemplo",
  quitar_ejemplos: "Quitó datos de ejemplo", autoverificacion: "Probó todo (prueba en vivo)" };
let seccion = "datos";
export function irSeccionSistema(s) { seccion = s; }

export function pintarSistema() {
  const raiz = $("vista-sistema");
  const cuerpo = el("div", { class: "rejilla", id: "cuerpo-sistema" });
  raiz.replaceChildren(el("div", { class: "encabezado-vista" }, el("h2", { text: "Sistema" })),
    el("div", { class: "segmentos", role: "group", "aria-label": "Sección", style: "margin-bottom:14px" }, ...SECCIONES.map(([clave, texto]) =>
      el("button", { type: "button", "aria-pressed": String(seccion === clave), text: texto, onclick: () => { seccion = clave; pintarSistema(); } }))), cuerpo);
  ({ datos, seguridad, servidor, api: documentacion, auditoria })[seccion](cuerpo);
}

function esqueleto(caja) { caja.replaceChildren(el("div", { class: "esqueleto" }), el("div", { class: "esqueleto" })); }
async function descargar(boton, ruta, nombre) {
  boton.classList.add("cargando");
  try { await bajar(ruta, nombre); aviso("Descarga lista"); } catch (e) { aviso(e.message, "error"); } finally { boton.classList.remove("cargando"); }
}
const botonDescarga = (texto, ruta, nombre, tipo = "secundario") => { const b = el("button", { type: "button", class: "boton boton-" + tipo, onclick: () => descargar(b, ruta, nombre) }, icono("descargar"), texto); return b; };

// ---------- datos ----------
function datos(caja) {
  const archivo = el("input", { type: "file", accept: ".csv,text/csv", id: "archivo-csv" }), resultado = el("div");
  const subir = el("button", { type: "button", class: "boton boton-primario", onclick: async () => {
    if (!archivo.files[0]) { aviso("Primero elige un archivo CSV.", "error"); return; }
    subir.classList.add("cargando");
    try {
      const r = await api("/importar", { method: "POST", headers: { "Content-Type": "text/csv" }, body: await archivo.files[0].text() }, 120000);
      resultado.replaceChildren(el("div", { class: "alerta " + (r.rechazados ? "aviso" : "ok") }, icono(r.rechazados ? "alerta" : "check"),
        el("p", { text: "Se importaron " + r.importados + (r.rechazados ? " y " + r.rechazados + " no pasaron la validación." : ".") })),
        ...(r.errores || []).slice(0, 8).map((x) => el("p", { class: "paso-ayuda nota", text: "Fila " + x.fila + ": " + x.motivo })));
      await cargarTodo();
    } catch (e) { aviso(e.message, "error"); } finally { subir.classList.remove("cargando"); }
  } }, icono("subir"), "Importar");
  const cuantos = el("input", { type: "text", value: "120", inputmode: "numeric", "aria-label": "Cantidad de reportes de ejemplo", style: "max-width:110px" });
  const cargarEj = el("button", { type: "button", class: "boton boton-secundario", onclick: async () => {
    cargarEj.classList.add("cargando");
    try { const r = await api("/ejemplos", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cantidad: Number(cuantos.value) || 120 }) }, 120000); aviso("Listo: " + r.creados + " reportes de ejemplo."); await cargarTodo(); }
    catch (e) { aviso(e.message, "error"); } finally { cargarEj.classList.remove("cargando"); }
  } }, icono("mas"), "Cargar ejemplos");
  const quitarEj = el("button", { type: "button", class: "boton boton-peligro", onclick: async () => {
    if (!await confirmar({ titulo: "¿Quitar los datos de ejemplo?", texto: "Se borran solo los reportes de los participantes «demo-NN». Los reales no se tocan.", boton: "Quitar", peligro: true })) return;
    try { const r = await api("/ejemplos", { method: "DELETE" }); aviso("Se quitaron " + r.borrados + " reportes de ejemplo."); await cargarTodo(); } catch (e) { aviso(e.message, "error"); }
  } }, icono("basura"), "Quitar ejemplos");
  caja.replaceChildren(
    el("div", { class: "rejilla dos" },
      tarjeta("Descargar los datos", el("p", { class: "sub-titulo", text: "El paquete trae todo junto: datos crudos y depurados, mapa (GeoJSON), diccionario de datos y un manifiesto con la huella de cada archivo." }),
        el("div", { class: "rejilla" }, botonDescarga("Paquete completo (.zip)", "/exportar.zip", "observatorio_loja", "primario"), botonDescarga("Paquete para publicar (sin códigos)", "/exportar.zip?publico=true", "observatorio_loja_publicable"), botonDescarga("Paquete con fotos — respaldo", "/exportar.zip?fotos=true", "respaldo_con_fotos"),
          botonDescarga("Solo tabla (CSV)", "/exportar.csv", "reportes"), botonDescarga("Solo mapa (GeoJSON)", "/exportar.geojson", "reportes"))),
      tarjeta("Subir datos (CSV)", el("p", { class: "sub-titulo", text: "Sirve para cargar un CSV exportado antes o datos sintéticos. Cada fila se valida como si viniera del celular." }),
        el("div", { class: "archivo-fila" }, archivo, subir), resultado)),
    tarjeta("Datos de ejemplo para ensayar", el("p", { class: "sub-titulo", text: "Crea reportes realistas de 16 voluntarios «demo» en Loja, con errores a propósito (repetidos, fuera de zona, GPS malo, fechas raras) para ver trabajar al control de calidad. Se pueden quitar de un clic." }),
      el("div", { class: "archivo-fila" }, el("label", { class: "solo-lector", for: "x" }, "Cantidad"), cuantos, cargarEj, quitarEj)));
}

// ---------- seguridad ----------
async function seguridad(caja) {
  esqueleto(caja);
  try {
    const r = await api("/seguridad");
    caja.replaceChildren(tarjeta("Revisión de seguridad en vivo", el("p", { class: "sub-titulo", text: r.alertas ? r.alertas + " cosa(s) por arreglar" : r.avisos ? "Todo bien; hay " + r.avisos + " aviso(s) para tener en cuenta." : "Todo en orden." }),
      el("div", { class: "lista-chequeo" }, ...r.puntos.map((p, i) => {
        const nodo = el("div", { class: "chequeo " + p.nivel }, el("span", { class: "marca-chequeo" }, icono(p.nivel === "ok" ? "check" : "alerta")), el("div", {}, el("strong", { text: p.nombre }), el("small", { text: p.detalle })));
        nodo.style.animationDelay = i * 50 + "ms"; return nodo;
      }))),
      tarjeta("Qué está protegido", el("ul", { class: "consejos" }, el("li", { text: "Entras con la clave, pero el navegador solo guarda un permiso que vence y se anula al salir." }),
        el("li", { text: "Cada rol tiene su clave: el participante solo envía, el analista solo lee, el administrador decide." }), el("li", { text: "La documentación pública de la API está apagada; se ve aquí adentro." }),
        el("li", { text: "Ningún script ni imagen de otros sitios puede cargarse (salvo los mosaicos del mapa)." }), el("li", { text: "Usa «Modo presentación» (el ojo de arriba) para ocultar códigos y ubicaciones cuando compartas pantalla." }))));
  } catch (e) { caja.replaceChildren(el("div", { class: "alerta error" }, icono("alerta"), el("p", { text: e.message }))); }
}

// ---------- servidor ----------
async function servidor(caja) {
  esqueleto(caja);
  try {
    const s = await api("/servidor"), c = estado.capacidad;
    const fila = (n, v) => el("tr", {}, el("td", { text: n }), el("td", {}, v));
    const barra = el("i"); requestAnimationFrame(() => { barra.style.width = Math.max(1, c.porcentaje) + "%"; });
    caja.replaceChildren(el("div", { class: "rejilla dos" },
      tarjeta("Estado del servidor", el("table", { class: "tabla-simple" }, el("tbody", {}, fila("Versión", "v" + s.version), fila("Base de datos", "PostgreSQL con PostGIS " + s.postgis + " · " + s.base_de_datos),
        fila("Migraciones aplicadas", String(s.migraciones)), fila("Entorno", s.entorno + " · Python " + s.python), fila("Hora del servidor", fechaLarga(s.hora_servidor)),
        fila("Reportes / fotos / encuestas", s.reportes + " / " + s.fotos + " / " + s.encuestas), fila("Dirección", location.origin)))),
      tarjeta("Espacio de la base de datos", el("p", { class: "sub-titulo", text: (c.usado_bytes / 1e6).toFixed(1) + " MB de " + (c.limite_bytes / 1e6).toFixed(0) + " MB (" + c.porcentaje + " %)" }),
        el("div", { class: "barra-meta" }, barra), el("p", { class: "paso-ayuda nota", text: "Caben unos " + num(c.reportes_restantes_estimados) + " reportes más. " + c.nota }))));
  } catch (e) { caja.replaceChildren(el("div", { class: "alerta error" }, icono("alerta"), el("p", { text: e.message }))); }
}

// ---------- documentacion de la API y diccionario de datos ----------
async function documentacion(caja) {
  esqueleto(caja);
  try {
    const [spec, dic] = await Promise.all([api("/especificacion"), api("/diccionario")]);
    const rutas = [];
    for (const [ruta, metodos] of Object.entries(spec.paths)) for (const [metodo, d] of Object.entries(metodos)) rutas.push([metodo.toUpperCase(), ruta, d.summary || d.operationId || ""]);
    caja.replaceChildren(
      tarjeta("Diccionario de datos", el("p", { class: "sub-titulo", text: "Cada campo de un reporte: qué es y qué reglas tiene. Es el «contrato» entre la app, la API y el análisis." }),
        el("div", { class: "contenedor-tabla" }, el("table", { class: "tabla-simple" }, el("thead", {}, el("tr", {}, ...["Campo", "Tipo", "Obligatorio", "Regla", "Qué es"].map((t) => el("th", { text: t })))),
          el("tbody", {}, ...dic.map((c) => el("tr", {}, el("td", {}, el("code", { text: c.campo })), el("td", { text: c.tipo }), el("td", { text: c.obligatorio }), el("td", { text: c.restriccion }), el("td", { text: c.descripcion }))))))),
      tarjeta("Servicios de la API (v" + spec.info.version + ")", el("p", { class: "sub-titulo", text: rutas.length + " servicios. Cada uno pide la clave de su rol; los de administración solo funcionan con la sesión de este panel." }),
        ...rutas.map(([m, r, t]) => el("div", { class: "api-ruta" }, el("span", { class: "metodo m-" + m, text: m }), el("div", {}, el("code", { text: r }), el("small", { text: t }))))));
  } catch (e) { caja.replaceChildren(el("div", { class: "alerta error" }, icono("alerta"), el("p", { text: e.message }))); }
}

// ---------- auditoria ----------
async function auditoria(caja) {
  esqueleto(caja);
  try {
    const filas = await api("/auditoria");
    caja.replaceChildren(tarjeta("Quién hizo qué", el("p", { class: "sub-titulo", text: "Las últimas " + filas.length + " acciones del equipo. Los códigos de participantes se muestran en forma de huella." }),
      filas.length ? el("div", { class: "contenedor-tabla" }, el("table", { class: "tabla-simple" }, el("thead", {}, el("tr", {}, ...["Cuándo", "Quién", "Qué", "Detalle"].map((t) => el("th", { text: t })))),
        el("tbody", {}, ...filas.map((f) => el("tr", {}, el("td", { text: fechaLarga(f.cuando) }), el("td", { text: f.rol }), el("td", { text: ACCIONES[f.accion] || f.accion }), el("td", { text: f.detalle || "" })))))) : el("p", { class: "vacio", text: "Todavía no hay acciones." })));
  } catch (e) { caja.replaceChildren(el("div", { class: "alerta error" }, icono("alerta"), el("p", { text: e.message }))); }
}

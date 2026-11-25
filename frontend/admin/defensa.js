// Pestaña "Defensa": todo lo que hay que mostrar en la sustentacion, con evidencia en vivo
import { graficoBarras } from "./graficos.js";
import { api, estado } from "./datos.js";
import { irSeccionSistema } from "./sistema.js";
import { $, aviso, anillo, el, fechaLarga, icono, nombreCategoria, num, tarjeta } from "./ui.js";

const SECCIONES = [["entregables", "Entregables"], ["prueba", "Prueba en vivo"], ["informe", "Informe del piloto"], ["ficha", "Ficha del dataset"]];
let seccion = "entregables", ultimaPrueba = null;

// tipo: "app" = se demuestra aqui · "mixto" = la app lo respalda y hay un documento ya redactado (el equipo lo revisa y lo hace suyo)
//       "campo" = se hace en el piloto · "doc" = lo redacta el equipo al terminar
const GRUPOS = [
  ["Estudiante 1 · Captura de datos y aplicación", [
    ["Benchmarking de 3 apps de participación ciudadana", "mixto", "Documento listo en docs/entregables: compara FixMyStreet, SeeClickFix y «Cómo va mi barrio» (Loja). El equipo debe leerlo, comprobarlo y hacerlo suyo.", null],
    ["Prototipo navegable de pantallas", "app", "La app ya navega: Reportar (3 pasos), Mis reportes y Ayuda, en modo claro y oscuro.", ["Abrir la app", () => window.open("/", "_blank")]],
    ["App MVP (PWA)", "app", "Se instala como app, guarda reportes sin internet y los envía sola; el GPS se promedia y se confirma en un mapa.", ["Abrir la app", () => window.open("/", "_blank")]],
    ["Informe de pruebas funcionales y de usabilidad", "mixto", "Funcionales: documento con resultados reales y la «Prueba en vivo». Usabilidad: la encuesta de la app (resultados abajo); faltan las respuestas del piloto.", ["Prueba en vivo", () => ir("prueba")]],
    ["Resultados del cuestionario de experiencia de usuario", "app", "Encuesta corta dentro de la app (pestaña Ayuda). Los resultados salen abajo, en vivo.", ["Ver resultados", () => document.getElementById("caja-encuesta-admin") && document.getElementById("caja-encuesta-admin").scrollIntoView({ behavior: "smooth" })]],
    ["Manual técnico, manual de usuario y código final", "mixto", "Manual de usuario y manual técnico en docs/entregables, y la pestaña Ayuda de la app. El código está en GitHub.", null]]],
  ["Estudiante 2 · Backend y gestión de datos", [
    ["Entorno base reproducible y documentado", "app", "Un solo comando (docker compose up) levanta todo. El detalle del entorno está en Sistema → Servidor.", ["Ver servidor", () => irSistema("servidor")]],
    ["Modelo de datos y especificación de la API", "app", "Diccionario de datos y lista de servicios de la API, generados desde el código.", ["Ver API", () => irSistema("api")]],
    ["API MVP desplegada en entorno de pruebas", "app", "El servidor responde en esta dirección: " + location.origin, ["Ver servidor", () => irSistema("servidor")]],
    ["Suite de pruebas y guía de despliegue", "mixto", "20 comprobaciones que se ejecutan con un botón. La guía de despliegue (Docker, túnel, Render y Neon) está en el manual técnico.", ["Probar todo ahora", () => ir("prueba")]],
    ["Exportaciones versionadas del dataset con diccionario", "app", "Paquete ZIP con datos crudos y depurados, GeoJSON, diccionario y huellas SHA-256.", ["Descargar", () => irSistema("datos")]],
    ["Documentación de API, base de datos y respaldos", "app", "API y diccionario en Sistema; el respaldo completo (con fotos) se baja del mismo lugar.", ["Ver API", () => irSistema("api")]]]],
  ["Estudiante 3 · Calidad, análisis y visualización", [
    ["Ficha síntesis de dimensiones de calidad", "app", "Las seis dimensiones, qué mide cada una, su peso y su referencia, en Calidad.", ["Ver Calidad", () => irPanel("calidad")]],
    ["Catálogo de indicadores y boceto del dashboard", "app", "Indicadores con su definición (Calidad) y el dashboard con mapa (Inicio y Mapa).", ["Ver Calidad", () => irPanel("calidad")]],
    ["Dataset sintético y scripts de validación v1", "app", "Datos de ejemplo con errores a propósito (Sistema → Datos) y validación automática. Los scripts en pandas siguen en analisis/.", ["Ver Datos", () => irSistema("datos")]],
    ["Pipeline de calidad automatizado y calibrado", "app", "La calidad se calcula sola al llegar cada reporte; el calibrador muestra cómo cambian los resultados al mover umbrales.", ["Ver Calidad", () => irPanel("calidad")]],
    ["Dataset depurado y dashboard actualizado", "app", "El ZIP trae la versión depurada; el panel se actualiza solo cada 30 segundos.", ["Descargar", () => irSistema("datos")]],
    ["Informe de análisis del piloto y ficha del dataset", "mixto", "Se generan aquí con los datos reales (pestañas siguientes). Las conclusiones las escribe el equipo al terminar el piloto.", ["Ver informe", () => ir("informe")]]]],
  ["Equipo · Resultados de investigación", [
    ["Dataset documentado", "app", "Paquete ZIP con diccionario, ficha del dataset y huellas; hay una versión para publicar sin códigos.", ["Descargar", () => irSistema("datos")]],
    ["Prototipo funcionando de punta a punta", "app", "Captura → recepción → calidad → mapa e indicadores, sin intervención manual (la prueba en vivo lo comprueba).", ["Probar", () => ir("prueba")]],
    ["Piloto con 15 a 25 voluntarios y más de 300 reportes", "campo", "Se hace en campo del 14 al 27 de diciembre; el avance se ve aquí arriba, en vivo.", null],
    ["Informe técnico integrado", "doc", "Lo redacta el equipo al terminar el piloto; el informe del piloto de esta pestaña reúne los datos.", null]]],
];

let irPanel = () => {};
function ir(s) { seccion = s; pintarDefensa(); }
function irSistema(s) { irSeccionSistema(s); irPanel("sistema"); }

export function pintarDefensa(irA) {
  if (irA) irPanel = irA;
  const raiz = $("vista-defensa"), cuerpo = el("div", { class: "rejilla" });
  raiz.replaceChildren(el("div", { class: "encabezado-vista" }, el("h2", { text: "Defensa" })),
    el("div", { class: "segmentos no-imprimir", role: "group", "aria-label": "Sección", style: "margin-bottom:14px" }, ...SECCIONES.map(([clave, texto]) =>
      el("button", { type: "button", "aria-pressed": String(seccion === clave), text: texto, onclick: () => ir(clave) }))), cuerpo);
  ({ entregables, prueba, informe, ficha })[seccion](cuerpo);
}

// ---------- entregables ----------
async function entregables(caja) {
  const total = GRUPOS.reduce((a, g) => a + g[1].length, 0), enApp = GRUPOS.reduce((a, g) => a + g[1].filter((i) => i[1] === "app").length, 0);
  const mixtos = GRUPOS.reduce((a, g) => a + g[1].filter((i) => i[1] === "mixto").length, 0), s = estado.stats, p = s.piloto;
  const etiquetas = { app: "Se demuestra en la app", mixto: "App + documento", campo: "Se hace en campo", doc: "Lo redacta el equipo" };
  const encuesta = el("div", { id: "caja-encuesta-admin" });
  caja.replaceChildren(
    tarjeta(null, el("div", { class: "hero" }, anillo(100 * (enApp + mixtos / 2) / total, enApp + "/" + total, "en la app"),
      el("div", { class: "meta" }, el("h2", { text: "Qué se puede demostrar desde aquí" }),
        el("p", { class: "sub-titulo", text: enApp + " entregables se demuestran completos en la app y " + mixtos + " tienen además un documento ya redactado que el equipo debe revisar. El resto se hace en el piloto o se escribe al terminarlo." }),
        el("p", { class: "paso-ayuda nota", text: "Así no se promete de más: el piloto en campo y el informe técnico final no los puede hacer ninguna app." })))),
    tarjeta("El piloto, en vivo", el("div", { class: "meta" },
      metaFila("Reportes", s.reportes, p.meta_observaciones), metaFila("Voluntarios (mínimo)", s.participantes, p.participantes_min), metaFila("Prueba de humo (flujo completo)", Math.min(s.reportes, p.prueba_de_humo), p.prueba_de_humo)),
      el("p", { class: "paso-ayuda nota", text: "Flujo que se muestra sin tocar nada a mano: captura en el celular → recepción y validación → calidad automática → mapa e indicadores." })),
    ...GRUPOS.map(([titulo, items]) => tarjeta(titulo, ...items.map(([nombre, tipo, texto, accion]) =>
      el("div", { class: "entregable" }, el("strong", { text: nombre }), el("p", { text: texto }),
        el("div", { class: "acciones-fila" }, el("span", { class: "etiqueta-tipo t-" + tipo, text: etiquetas[tipo] }), accion ? el("button", { type: "button", class: "boton boton-secundario boton-chico", text: accion[0], onclick: accion[1] }) : null))))),
    tarjeta("Resultados de la encuesta de experiencia", encuesta));
  try {
    const r = await api("/encuestas");
    if (!r.respuestas) { encuesta.replaceChildren(el("p", { class: "vacio", text: "Todavía nadie respondió. La encuesta está en la pestaña Ayuda de la app y se ofrece al terminar un reporte." })); return; }
    const preguntas = ["Fue fácil enviar un reporte", "Tuve que pensar mucho (menos es mejor)", "La ubicación fue rápida y buena", "Volvería a usarla", "Me pareció confusa (menos es mejor)"];
    encuesta.replaceChildren(el("p", { class: "sub-titulo", text: r.respuestas + (r.respuestas === 1 ? " persona respondió" : " personas respondieron") + ". Índice de facilidad: " + Math.round(r.indice_medio) + " de 100 (versión corta inspirada en SUS)." }),
      ...r.medias.map((m, i) => { const barra = el("i"); barra.style.width = (m / 5 * 100) + "%"; return el("div", { class: "fila-barra" }, el("span", { class: "nombre", text: preguntas[i] }), el("div", { class: "pista" }, barra), el("span", { class: "valor", text: m.toFixed(1) + " / 5" })); }),
      ...r.comentarios.slice(0, 5).map((c) => el("p", { class: "paso-ayuda nota", text: "“" + c.comentario + "”" })));
  } catch (e) { encuesta.replaceChildren(el("p", { class: "vacio", text: e.message })); }
}

function metaFila(titulo, valor, total) {
  const barra = el("i"); requestAnimationFrame(() => requestAnimationFrame(() => { barra.style.width = Math.min(100, Math.round(100 * valor / total)) + "%"; }));
  return el("div", { class: "meta-fila" }, el("div", {}, el("span", { text: titulo }), el("strong", { text: num(valor) + " de " + num(total) })), el("div", { class: "barra-meta" }, barra));
}

// ---------- prueba en vivo ----------
function prueba(caja) {
  const lista = el("div", { class: "lista-chequeo" }), resumen = el("div");
  const boton = el("button", { type: "button", class: "boton boton-primario", onclick: correr }, icono("rayo"), "Probar todo ahora");
  async function correr() {
    boton.disabled = true; boton.classList.add("cargando"); lista.replaceChildren(el("div", { class: "esqueleto" }), el("div", { class: "esqueleto" })); resumen.replaceChildren();
    try {
      const r = await api("/autoverificacion", { method: "POST" }, 60000);
      ultimaPrueba = r;
      pintar(r, true);
    } catch (e) { lista.replaceChildren(el("div", { class: "alerta error" }, icono("alerta"), el("p", { text: e.message }))); }
    finally { boton.disabled = false; boton.classList.remove("cargando"); }
  }
  function pintar(r, animar) {
    resumen.replaceChildren(el("div", { class: "resultado-prueba" }, anillo(100 * r.correctas / r.total, r.correctas + "/" + r.total, "correctas", r.correctas === r.total ? "" : "n-malo"),
      el("div", {}, el("h2", { text: r.correctas === r.total ? "Todo funciona" : (r.total - r.correctas) + " comprobación(es) fallaron" }), el("p", { class: "sub-titulo", text: "Hecho el " + fechaLarga(r.hecho_en) + " · no dejó ningún dato en la base" }))));
    let grupo = "";
    lista.replaceChildren(...r.resultados.flatMap((x, i) => {
      const filas = [];
      if (x.grupo !== grupo) { grupo = x.grupo; filas.push(el("h3", { class: "grupo-titulo", text: grupo })); }
      const nodo = el("div", { class: "chequeo " + (x.ok ? "" : "mal") }, el("span", { class: "marca-chequeo" }, icono(x.ok ? "check" : "cerrar")), el("div", {}, el("strong", { text: x.nombre }), el("small", { text: x.detalle })), el("span", { class: "ms", text: x.ms + " ms" }));
      if (animar) nodo.style.animationDelay = i * 70 + "ms";
      filas.push(nodo); return filas;
    }));
  }
  caja.replaceChildren(tarjeta("Prueba en vivo del sistema", el("p", { class: "sub-titulo", text: "Con un botón se comprueba que la recepción, el control de calidad, la privacidad, la seguridad y las exportaciones funcionan. Todo ocurre en una transacción que se deshace: no queda ningún dato de prueba." }),
    el("div", { class: "acciones" }, boton), resumen, lista));
  if (ultimaPrueba) pintar(ultimaPrueba, false);
}

// ---------- informe del piloto ----------
const hora = (iso) => (new Date(iso).getUTCHours() + 19) % 24;      // hora de Ecuador (UTC-5)
function informe(caja) {
  const s = estado.stats, R = estado.reportes, p = s.piloto, dims = s.dimensiones || {};
  const dias = Object.keys(s.por_dia || {}).sort();
  const celdas = {};
  for (const r of R) { if (r.estado_calidad === "descartar") continue; const k = r.lat.toFixed(3) + "," + r.lon.toFixed(3); (celdas[k] = celdas[k] || { n: 0, cat: {}, lat: 0, lon: 0 }); const c = celdas[k]; c.n++; c.cat[r.categoria] = (c.cat[r.categoria] || 0) + 1; c.lat += r.lat; c.lon += r.lon; }
  const calientes = Object.values(celdas).sort((a, b) => b.n - a.n).slice(0, 5);
  const porHora = new Array(24).fill(0); R.forEach((r) => { porHora[hora(r.fecha_dispositivo)]++; });
  const pico = porHora.indexOf(Math.max(...porHora)), nombres = Object.fromEntries((estado.config.categorias || []).map((c) => [c.id, c.nombre]));
  const principal = Object.entries(s.por_categoria || {}).sort((a, b) => b[1] - a[1])[0];
  const aceptados = (s.por_estado || {}).aceptar || 0, hist = el("div"), cats = el("div"), mot = el("div");
  const filaHora = el("div", { class: "dias", "aria-label": "Reportes por hora del día" }, ...porHora.map((n, h) => { const c = el("div", { class: "dia" + (n ? "" : " cero"), title: h + ":00 — " + n }); const b = el("i"); if (n) b.style.height = Math.max(5, 100 * n / Math.max(...porHora)) + "%"; c.append(b); return c; }));
  caja.replaceChildren(
    el("div", { class: "no-imprimir acciones", style: "margin-top:0" }, el("button", { type: "button", class: "boton boton-primario", onclick: () => window.print() }, icono("imprimir"), "Imprimir o guardar como PDF")),
    el("article", { class: "tarjeta informe" },
      el("h1", { text: "Informe del piloto · Observatorio urbano Loja" }), el("p", { class: "sub-titulo", text: "Generado el " + fechaLarga(new Date().toISOString()) + " con los datos del sistema." }),
      el("h2", { text: "1. Resumen" }),
      el("p", { text: s.reportes ? "Se recibieron " + num(s.reportes) + " reportes de " + s.participantes + " participantes" + (dias.length ? " entre el " + dias[0] + " y el " + dias[dias.length - 1] : "") + ". " + Math.round(100 * aceptados / s.reportes) + " % quedó aceptado por el control de calidad (puntaje medio " + (s.puntaje_medio != null ? Math.round(s.puntaje_medio) : "—") + " de 100)." : "Todavía no hay reportes: carga datos de ejemplo o espera al piloto." }),
      el("ul", {}, el("li", { text: "Meta de reportes: " + num(s.reportes) + " de " + num(p.meta_observaciones) + " (" + Math.round(100 * s.reportes / p.meta_observaciones) + " %)." }), el("li", { text: "Voluntarios: " + s.participantes + " (mínimo " + p.participantes_min + ", máximo " + p.participantes_max + ")." }),
        el("li", { text: "Con foto: " + s.con_foto + ". Precisión media del GPS: " + (s.precision_media_m != null ? "±" + Math.round(s.precision_media_m) + " m" : "—") + "." })),
      el("h2", { text: "2. Qué problemas se ven" }), cats,
      principal ? el("p", { text: "El problema más reportado es «" + nombreCategoria(estado.config, principal[0]) + "» (" + principal[1] + " reportes, " + Math.round(100 * principal[1] / s.reportes) + " %)." }) : null,
      el("h2", { text: "3. Dónde se concentran (zonas de ~100 m, sin contar descartados)" }),
      calientes.length ? el("ul", {}, ...calientes.map((c, i) => el("li", { text: (i + 1) + ". " + c.n + " reportes cerca de " + (c.lat / c.n).toFixed(4) + ", " + (c.lon / c.n).toFixed(4) + " — sobre todo " + nombreCategoria(estado.config, Object.entries(c.cat).sort((a, b) => b[1] - a[1])[0][0]) + "." }))) : el("p", { class: "vacio", text: "Sin datos." }),
      el("h2", { text: "4. Cuándo se reporta (hora de Ecuador)" }), filaHora, el("div", { class: "dias-eje" }, el("span", { text: "0 h" }), el("span", { text: "12 h" }), el("span", { text: "23 h" })),
      s.reportes ? el("p", { text: "La hora con más reportes es las " + pico + ":00." }) : null,
      el("h2", { text: "5. Calidad de los datos" }),
      el("ul", {}, ...Object.entries(dims).map(([d, v]) => el("li", { text: d[0].toUpperCase() + d.slice(1) + ": " + (v == null ? "—" : Math.round(100 * v) + " %") + " (peso " + Math.round(100 * s.reglas.pesos[d]) + " %)" }))), mot,
      el("h2", { text: "6. Limitaciones" }),
      el("ul", {}, el("li", { text: "Los voluntarios no son una muestra al azar de la ciudad: los resultados describen al grupo del piloto." }), el("li", { text: "La clave del formulario es pública por diseño; el límite de envíos y el control de calidad reducen, pero no eliminan, los reportes falsos." }),
        el("li", { text: "La precisión del GPS depende del celular, el clima y los edificios." }), el("li", { text: "Los hallazgos son descriptivos: no prueban causas." })),
      el("h2", { text: "7. Conclusiones del equipo" }), el("p", { class: "vacio", text: "Escriban aquí (en el documento final) lo que concluyen. Este informe solo reúne los datos." })));
  graficoBarras(cats, s.por_categoria, nombres); graficoBarras(mot, s.motivos);
}

// ---------- ficha del dataset (Datasheets for Datasets) ----------
function ficha(caja) {
  const s = estado.stats, p = s.piloto, z = s.reglas.zona, cal = s.reglas;
  const sec = (t, ...c) => [el("h2", { text: t }), ...c];
  const ul = (...t) => el("ul", {}, ...t.map((x) => el("li", { text: x })));
  caja.replaceChildren(
    el("div", { class: "no-imprimir acciones", style: "margin-top:0" }, el("button", { type: "button", class: "boton boton-primario", onclick: () => window.print() }, icono("imprimir"), "Imprimir o guardar como PDF")),
    el("article", { class: "tarjeta informe" }, el("h1", { text: "Ficha del dataset · Observatorio urbano Loja" }), el("p", { class: "sub-titulo", text: "Basada en «Datasheets for Datasets» (Gebru et al., 2021) y los principios FAIR (Wilkinson et al., 2016). Los números se llenan solos." }),
      ...sec("Motivación", el("p", { text: "Reúne observaciones ciudadanas georreferenciadas de problemas urbanos en Loja para estudiar la calidad de los datos de crowdsensing y apoyar análisis urbano. Es parte de las prácticas pre-profesionales del Grupo de Investigación en IA Aplicada de la UTPL." })),
      ...sec("Composición", ul("Cada fila es un reporte ciudadano. Hay " + num(s.reportes) + " reportes de " + s.participantes + " participantes (seudónimos).", "Categorías: " + (estado.config.categorias || []).map((c) => c.nombre).join(", ") + ".", "Campos: ubicación, precisión, fechas, plataforma, foto opcional, consentimiento y el resultado del control de calidad (ver el diccionario en Sistema → API)." , "Zona: " + z.nombre + ".")),
      ...sec("Cómo se recolectó", ul("Desde el celular, con consentimiento informado y ubicación tomada solo al enviar.", "Meta del piloto: " + p.meta_observaciones + " reportes y " + p.participantes_min + " a " + p.participantes_max + " voluntarios en " + p.dias + " días.", "El GPS se promedia con varias lecturas y el participante puede corregir el punto en un mapa (queda marcado).")),
      ...sec("Limpieza y calidad", ul("Cada reporte recibe un puntaje de 0 a 100 con seis dimensiones: completitud, validez, exactitud posicional, consistencia temporal, unicidad y oportunidad.", "Aceptar desde " + cal.minimo_aceptar + " puntos; revisar desde " + cal.minimo_revisar + "; si no, descartar. Repetidos, fuera de zona, fecha rara o datos faltantes se descartan.", "El paquete de descarga incluye la versión cruda y la depurada (aceptados y por revisar).")),
      ...sec("Usos recomendados y no recomendados", ul("Recomendado: estudiar calidad de datos MCS, mapear problemas urbanos del piloto, probar métodos de validación.", "No recomendado: identificar personas, tomar decisiones de ciudad sin más datos, generalizar a toda Loja.")),
      ...sec("Ética y privacidad", ul("Participación voluntaria y consentimiento antes de pedir la ubicación (LOPDP, Ecuador 2021).", "Sin nombres, cédulas ni correos: solo un código al azar por celular.", "Las fotos pasan por un recorte que borra los datos EXIF y se revisan para quitar rostros y placas.", "Cada participante puede retirarse y borrar todo lo suyo desde la app.", "Acceso por roles y solo con fines académicos.")),
      ...sec("Distribución y mantenimiento", ul("Se entrega como paquete ZIP versionado con diccionario y huellas SHA-256 (Sistema → Datos).", "Licencia sugerida: uso académico y no comercial; la define el equipo con la tutora.", "Responsables: equipo de 5.º ciclo, con la tutora del grupo de investigación.")),
      ...sec("Principios FAIR", ul("Encontrable: archivos con nombre, versión y fecha; manifiesto con metadatos.", "Accesible: descarga con clave desde el panel; formatos abiertos (CSV, GeoJSON).", "Interoperable: coordenadas WGS84 y diccionario de datos.", "Reutilizable: reglas de calidad y licencia documentadas."))));
}

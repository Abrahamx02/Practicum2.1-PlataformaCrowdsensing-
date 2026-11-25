// Pestañas "Calidad" (las seis dimensiones, reglas, señales de confianza, indicadores y calibrador) y "Participantes"
import { graficoBarras } from "./graficos.js";
import { api, cargarTodo, estado } from "./datos.js";
import { $, NOMBRE_DIMENSION, anillo, aviso, colorDeNota, confirmar, el, hace, icono, num, tarjeta } from "./ui.js";

const DIMENSIONES = {
  completitud: ["¿Trae lo necesario?", "Categoría, ubicación, fecha y algo de texto o una foto.", "Wang y Strong (1996)"],
  validez: ["¿Los datos tienen sentido?", "Categoría permitida y coordenadas que existen.", "Batini et al. (2009)"],
  exactitud: ["¿La ubicación es buena?", "Dentro de la zona del piloto y con GPS preciso.", "ISO 19157-1"],
  consistencia: ["¿La fecha cuadra?", "La hora del celular coincide con la de llegada.", "ISO 19157-1"],
  unicidad: ["¿Es un reporte nuevo?", "No repite uno cercano, del mismo tipo y de hace pocos minutos.", "Batini et al. (2009)"],
  oportunidad: ["¿Llegó rápido?", "Mejor si llega en menos de 5 minutos.", "Wang y Strong (1996)"],
};
const SENALES = [
  ["ubicación puesta a mano", "El participante corrigió el pin en el mapa."], ["enviado en movimiento", "El celular iba rápido al capturar (en carro o bus)."],
  ["salto imposible entre reportes", "Dos reportes seguidos de la misma persona, muy lejos y casi al mismo tiempo."], ["ráfaga de reportes", "Muchos reportes de la misma persona en pocos minutos."],
  ["coordenadas redondeadas", "Latitud y longitud con 2 decimales: parecen escritas a mano."], ["precisión sospechosa", "El GPS dice ±0 m, algo que no existe."],
];
const SIMBOLO = { aceptar: "p-aceptar", revisar: "p-revisar", descartar: "p-descartar" };

const GRAVES = ["duplicado", "fuera de la zona", "fecha incoherente", "faltan datos"];

// Recalcula el estado de un reporte con otros pesos y umbrales (misma logica del servidor) para el calibrador
export function simular(r, pesos, aceptar, revisar) {
  if (r.revisado || !r.dimensiones_calidad) return r.estado_calidad || "sin_calcular";
  const suma = Object.values(pesos).reduce((a, b) => a + b, 0) || 1;
  const puntaje = 100 * Object.keys(pesos).reduce((a, d) => a + (pesos[d] / suma) * (r.dimensiones_calidad[d] || 0), 0);
  const motivo = r.motivo_calidad || "";
  if (GRAVES.some((g) => motivo.includes(g))) return "descartar";
  const aviso = SENALES.some(([s]) => motivo.includes(s));
  let e = puntaje >= revisar ? "revisar" : "descartar";
  if (puntaje >= aceptar && !motivo.includes("baja precisión") && !aviso) e = "aceptar";
  else if (puntaje >= aceptar && aviso) e = "revisar";
  return e;
}

function contarEstados(lista, pesos, aceptar, revisar) {
  const c = { aceptar: 0, revisar: 0, descartar: 0 };
  for (const r of lista) { const e = simular(r, pesos, aceptar, revisar); if (c[e] !== undefined) c[e]++; }
  return c;
}

function indicadores() {
  const R = estado.reportes, n = R.length || 1, pct = (k) => Math.round(100 * k / n) + " %";
  const cuantos = (f) => R.filter(f).length;
  const demoras = R.map((r) => (new Date(r.recibido_en) - new Date(r.fecha_dispositivo)) / 60000).filter((m) => m >= 0).sort((a, b) => a - b);
  const mediana = demoras.length ? demoras[Math.floor(demoras.length / 2)] : null;
  return [
    ["Reportes completos", "Con datos obligatorios y texto o foto", pct(cuantos((r) => r.dimensiones_calidad && r.dimensiones_calidad.completitud === 1))],
    ["Datos válidos", "Categoría permitida y coordenadas posibles", pct(cuantos((r) => r.dimensiones_calidad && r.dimensiones_calidad.validez === 1))],
    ["Buena precisión", "GPS de ±" + estado.stats.reglas.precision_maxima_m + " m o mejor", pct(cuantos((r) => r.precision_m != null && r.precision_m <= estado.stats.reglas.precision_maxima_m))],
    ["Dentro de la zona", "Punto dentro del área del piloto", pct(cuantos((r) => !r.motivo_calidad.includes("fuera de la zona")))],
    ["Repetidos", "Reportes marcados como duplicados", pct(cuantos((r) => r.motivo_calidad.includes("duplicado")))],
    ["Llegan rápido", "Llegan en menos de 5 minutos", pct(cuantos((r) => r.dimensiones_calidad && r.dimensiones_calidad.oportunidad === 1))],
    ["Tiempo típico de llegada", "Mediana entre captura y recepción", mediana == null ? "—" : mediana < 1 ? "menos de 1 min" : Math.round(mediana) + " min"],
    ["Aceptados", "Estado «aceptar»", pct(cuantos((r) => r.estado_calidad === "aceptar"))],
    ["Decididos por el equipo", "Revisados a mano", String(cuantos((r) => r.revisado))],
  ];
}

function calibrador() {
  const reglas = estado.stats.reglas, pesos = { ...reglas.pesos };
  let aceptar = reglas.minimo_aceptar, revisar = reglas.minimo_revisar;
  const antes = contarEstados(estado.reportes, reglas.pesos, reglas.minimo_aceptar, reglas.minimo_revisar);
  const resultado = el("div"), histograma = el("div", { class: "histograma" });
  const pintar = () => {
    const ahora = contarEstados(estado.reportes, pesos, aceptar, revisar);
    const d = (k) => { const x = ahora[k] - antes[k]; return x ? el("small", { class: x > 0 ? "delta-sube" : "delta-baja", text: (x > 0 ? "+" : "") + x + " vs. ahora" }) : el("small", { text: "igual que ahora" }); };
    resultado.replaceChildren(el("div", { class: "comparacion" },
      el("div", {}, el("strong", { text: String(ahora.aceptar) }), el("span", { class: "pildora p-aceptar", text: "Aceptados" }), d("aceptar")),
      el("div", {}, el("strong", { text: String(ahora.revisar) }), el("span", { class: "pildora p-revisar", text: "Por revisar" }), d("revisar")),
      el("div", {}, el("strong", { text: String(ahora.descartar) }), el("span", { class: "pildora p-descartar", text: "Descartados" }), d("descartar"))));
    const cubos = new Array(10).fill(0);
    for (const r of estado.reportes) if (r.dimensiones_calidad) {
      const suma = Object.values(pesos).reduce((a, b) => a + b, 0) || 1;
      const p = 100 * Object.keys(pesos).reduce((a, k) => a + (pesos[k] / suma) * (r.dimensiones_calidad[k] || 0), 0);
      cubos[Math.min(9, Math.floor(p / 10))]++;
    }
    const maximo = Math.max(1, ...cubos);
    histograma.replaceChildren(...cubos.map((n, i) => { const barra = el("i"); barra.style.height = Math.max(2, 100 * n / maximo) + "%"; return el("div", { class: "col n-" + colorDeNota(i * 10 + 5 >= aceptar ? 90 : i * 10 + 5 >= revisar ? 60 : 10) }, el("span", { text: n || "" }), barra, el("span", { text: i * 10 })); }));
  };
  const deslizador = (texto, valor, min, max, alCambiar, unidad = "") => {
    const salida = el("output", { text: valor + unidad });
    const campo = el("input", { type: "range", min, max, value: valor, "aria-label": texto, oninput: (e) => { salida.textContent = e.target.value + unidad; alCambiar(Number(e.target.value)); pintar(); } });
    return el("label", {}, el("span", { text: texto }), campo, salida);
  };
  const filas = [deslizador("Umbral aceptar", aceptar, 50, 100, (v) => { aceptar = v; }), deslizador("Umbral revisar", revisar, 0, 80, (v) => { revisar = v; })];
  for (const d of Object.keys(pesos)) filas.push(deslizador("Peso: " + NOMBRE_DIMENSION[d], Math.round(pesos[d] * 100), 0, 50, (v) => { pesos[d] = v / 100; }, " %"));
  pintar();
  return tarjeta("Calibrar las reglas", el("p", { class: "sub-titulo", text: "Mueve los umbrales y los pesos para ver cuántos reportes cambiarían de estado. Es una simulación: no toca ningún dato. Para dejarla fija, cambia «calidad» en configuracion.json." }),
    el("div", { class: "calibra" }, ...filas), el("h3", { class: "grupo-titulo", text: "Cómo quedarían" }), resultado, el("h3", { class: "grupo-titulo", text: "Puntajes de los reportes (de 0 a 100)" }), histograma,
    el("div", { class: "centrado" }, el("button", { type: "button", class: "boton boton-texto", text: "Volver a los valores actuales", onclick: pintarCalidad })));
}

export function pintarCalidad(irA) {
  const s = estado.stats, reglas = s.reglas, dims = s.dimensiones || {}, estados = s.por_estado || {}, raiz = $("vista-calidad");
  irA = irA || (() => {});
  const caja = (clave, texto) => { const b = el("button", { type: "button", class: "estado-caja " + SIMBOLO[clave], onclick: () => irA("reportes", { estado: clave }) }, el("strong", { text: String(estados[clave] || 0) }), el("span", { text: texto })); return b; };
  const recalcular = el("button", { type: "button", class: "boton boton-secundario", onclick: async (e) => {
    e.currentTarget.classList.add("cargando");
    try { const r = await api("/calidad/recalcular", { method: "POST" }); aviso("Listo: se recalcularon " + r.calculados + " reportes."); await cargarTodo(); }
    catch (err) { aviso(err.message, "error"); }
  } }, icono("refrescar"), "Recalcular todo");
  const medio = s.puntaje_medio != null ? Math.round(s.puntaje_medio) : null;
  const motivos = s.motivos || {};
  raiz.replaceChildren(
    el("div", { class: "encabezado-vista" }, el("h2", { text: "Calidad" }), el("span", { class: "cuenta", text: s.reportes + " reportes evaluados" })),
    el("div", { class: "rejilla" },
      tarjeta(null, el("div", { class: "hero" }, medio != null ? anillo(medio, String(medio), "puntaje medio", "n-" + colorDeNota(medio)) : el("p", { class: "vacio", text: "Sin datos todavía." }),
        el("div", { class: "meta" }, el("h2", { text: "Cada reporte se evalúa solo, al llegar" }),
          el("p", { class: "sub-titulo", text: "Seis preguntas dan un puntaje de 0 a 100. Con eso se decide: aceptar, revisar o descartar. " + (s.revisados_a_mano ? s.revisados_a_mano + " los decidió el equipo a mano." : "") }),
          el("div", { class: "puntos-calidad" }, caja("aceptar", "Aceptados"), caja("revisar", "Por revisar"), caja("descartar", "Descartados")),
          el("div", { class: "acciones" }, recalcular)))),
      el("div", { class: "rejilla dos" },
        tarjeta("Qué se mide (las seis dimensiones)", ...Object.keys(DIMENSIONES).map((d) => {
          const v = dims[d] == null ? null : Math.round(100 * dims[d]), barra = el("i");
          if (v != null) barra.style.width = v + "%";
          return el("div", { class: "dimension" }, el("div", { class: "cab" }, el("span", { text: DIMENSIONES[d][0] }), el("span", { class: "etiqueta-chica", text: "vale " + Math.round(100 * reglas.pesos[d]) + " %" })),
            el("small", { text: DIMENSIONES[d][1] + " · " + DIMENSIONES[d][2] }),
            el("div", { class: "fila-barra n-" + (v == null ? "ok" : colorDeNota(v)) }, el("div", { class: "pista" }, barra), el("span", { class: "valor", text: v == null ? "—" : v + " %" })));
        })),
        el("div", { class: "rejilla" },
          tarjeta("Cómo se decide", el("div", { class: "reglas" },
            el("div", { class: "regla" }, el("span", { class: "pildora p-aceptar", text: "Aceptar" }), el("span", { text: reglas.minimo_aceptar + " puntos o más, con GPS de ±" + reglas.precision_maxima_m + " m o mejor y sin señales de confianza." })),
            el("div", { class: "regla" }, el("span", { class: "pildora p-revisar", text: "Revisar" }), el("span", { text: "De " + reglas.minimo_revisar + " a " + (reglas.minimo_aceptar - 1) + " puntos, o si tiene alguna señal de confianza." })),
            el("div", { class: "regla" }, el("span", { class: "pildora p-descartar", text: "Descartar" }), el("span", { text: "Menos de " + reglas.minimo_revisar + " puntos, o si es repetido (a menos de " + reglas.distancia_duplicado_m + " m y " + reglas.minutos_duplicado + " min), está fuera de la zona, tiene fecha rara o le faltan datos." })))),
          tarjeta("Señales de confianza", el("p", { class: "sub-titulo", text: "No bajan el puntaje, pero impiden que el reporte se acepte solo: una persona lo mira." }),
            ...SENALES.map(([clave, texto]) => el("div", { class: "dimension" }, el("div", { class: "cab" }, el("span", { text: clave[0].toUpperCase() + clave.slice(1) }), el("span", { class: "etiqueta-chica", text: String(motivos[clave] || 0) })), el("small", { text: texto })))))),
      el("div", { class: "rejilla dos" },
        tarjeta("Problemas más frecuentes", el("div", { id: "motivos-grafico" })),
        tarjeta("Indicadores", el("div", { class: "contenedor-tabla" }, el("table", { class: "tabla-simple" }, el("tbody", {}, ...indicadores().map(([n, d, v]) => el("tr", {}, el("td", {}, el("strong", { text: n }), el("br"), el("small", { text: d })), el("td", { text: v })))))))),
      calibrador()));
  graficoBarras($("motivos-grafico"), motivos);
}

// ---------- Participantes ----------
let buscado = "";
export function pintarGente() {
  const p = estado.stats.piloto, raiz = $("vista-gente"), gente = estado.gente;
  const lista = el("div", { class: "lista", id: "lista-gente" });
  const dibujar = () => {
    const filas = gente.filter((g) => g.participante_id.toLowerCase().includes(buscado.toLowerCase()));
    lista.replaceChildren(...(filas.length ? filas.map((g) => {
      const pct = g.reportes ? Math.round(100 * g.aceptados / g.reportes) : 0;
      return el("div", { class: "fila-reporte", style: "cursor:default" }, el("span", { class: "ico-cat c-otro" }, icono("gente")),
        el("span", { class: "fila-texto" }, el("strong", {}, el("code", { class: "privado", text: g.participante_id })),
          el("small", { text: g.reportes + (g.reportes === 1 ? " reporte" : " reportes") + " · " + pct + " % aceptados" + (g.puntaje_medio != null ? " · puntaje " + Math.round(g.puntaje_medio) : "") + " · " + hace(g.ultimo_reporte) })),
        el("button", { type: "button", class: "boton boton-peligro boton-chico", text: "Retirar", onclick: () => retirar(g) }));
    }) : [el("div", { class: "vacio-grande" }, icono("gente"), el("strong", { text: gente.length ? "Nadie con ese código" : "Todavía no hay participantes" }))]));
  };
  raiz.replaceChildren(
    el("div", { class: "encabezado-vista" }, el("h2", { text: "Participantes" }), el("span", { class: "cuenta", text: gente.length + " de " + p.participantes_min + " (mínimo) · máximo " + p.participantes_max })),
    el("div", { class: "rejilla" }, tarjeta(null, el("div", { class: "hero" }, anillo(100 * gente.length / p.participantes_min, String(gente.length), "participantes"),
      el("div", { class: "meta" }, el("h2", { text: gente.length >= p.participantes_min ? "Ya hay suficientes voluntarios" : "Faltan " + (p.participantes_min - gente.length) + " voluntarios" }),
        el("p", { class: "sub-titulo", text: "Los códigos son seudónimos al azar: no hay nombres ni cédulas. Quien se retira desde su celular desaparece solo de esta lista." })))),
      el("label", { class: "buscador" }, icono("buscar"), el("input", { type: "search", placeholder: "Buscar un código", value: buscado, oninput: (e) => { buscado = e.target.value; dibujar(); } })), lista));
  dibujar();
}

async function retirar(g) {
  if (!await confirmar({ titulo: "¿Retirar a este participante?", texto: "Se borran sus " + g.reportes + " reportes y sus fotos. No se puede deshacer; queda anotado en Auditoría.", boton: "Retirar y borrar", peligro: true })) return;
  try { const r = await api("/participantes/" + encodeURIComponent(g.participante_id), { method: "DELETE" }); aviso("Retirado: se borraron " + (r.reportes_borrados ?? r.borrados ?? g.reportes) + " reportes."); await cargarTodo(); }
  catch (e) { aviso(e.message, "error"); }
}

// Pestaña "Inicio": como va el piloto de un vistazo
import { graficoAnillo, graficoBarras, graficoDias } from "./graficos.js";
import { estado } from "./datos.js";
import { $, anillo, contar, el, icono, nombreCategoria, num, tarjeta } from "./ui.js";

let primeraVez = true;

function meta(titulo, valor, total) {
  const barra = el("i");
  requestAnimationFrame(() => requestAnimationFrame(() => { barra.style.width = Math.min(100, Math.round(100 * valor / total)) + "%"; }));
  return el("div", { class: "meta-fila" }, el("div", {}, el("span", { text: titulo }), el("strong", { text: num(valor) + " de " + num(total) })), el("div", { class: "barra-meta" }, barra));
}

function kpi(titulo, valor, nota, indice, formato) {
  const numero = el("strong", { text: "—" });
  if (valor == null) numero.textContent = "—"; else if (primeraVez) contar(numero, valor, formato); else numero.textContent = (formato || num)(valor);
  const caja = el("div", { class: "kpi" }, el("span", { text: titulo }), numero, el("small", { text: nota }));
  caja.style.animationDelay = indice * 60 + "ms";
  return caja;
}

export function pintarInicio(irA) {
  const s = estado.stats, p = s.piloto, raiz = $("vista-inicio"), porEstado = s.por_estado || {};
  const diasConDatos = Object.keys(s.por_dia || {}).sort();
  const dia = diasConDatos.length ? Math.min(p.dias, Math.max(1, Math.round((Date.now() - new Date(diasConDatos[0] + "T00:00:00Z")) / 864e5) + 1)) : 0;
  const porRevisar = porEstado.revisar || 0, aceptados = porEstado.aceptar || 0;

  const atencion = [];
  if (!s.reportes) atencion.push(["aviso", "Todavía no hay reportes. Para ensayar, carga datos de ejemplo.", "Cargar ejemplos", () => irA("sistema")]);
  if (porRevisar) atencion.push(["aviso", porRevisar + (porRevisar === 1 ? " reporte espera" : " reportes esperan") + " tu decisión.", "Revisar", () => irA("reportes", { estado: "revisar" })]);
  if (s.reportes && s.reportes < p.prueba_de_humo) atencion.push(["aviso", "Faltan " + (p.prueba_de_humo - s.reportes) + " reportes para la prueba de humo (" + p.prueba_de_humo + ").", "Ver Defensa", () => irA("defensa")]);
  if (estado.capacidad && estado.capacidad.nivel !== "ok") atencion.push(["aviso", "La base de datos va en " + estado.capacidad.porcentaje + " % de su espacio.", "Ver Sistema", () => irA("sistema")]);
  if (!atencion.length) atencion.push(["ok", "Todo en orden: no hay nada pendiente.", null, null]);

  const dias = el("div"), categorias = el("div"), calidad = el("div"), plataformas = el("div");
  raiz.replaceChildren(
    el("div", { class: "encabezado-vista" }, el("h2", { text: "Inicio" }), el("span", { class: "cuenta", text: dia ? "Día " + dia + " de " + p.dias + " del piloto" : "Piloto sin empezar" })),
    el("div", { class: "rejilla" },
      tarjeta(null, el("div", { class: "hero" },
        anillo(100 * s.reportes / p.meta_observaciones, Math.round(100 * s.reportes / p.meta_observaciones) + " %", "de la meta"),
        el("div", { class: "meta" }, el("h2", { text: "Avance del piloto" }),
          meta("Reportes", s.reportes, p.meta_observaciones), meta("Participantes (mínimo)", s.participantes, p.participantes_min), meta("Prueba de humo", Math.min(s.reportes, p.prueba_de_humo), p.prueba_de_humo)))),
      tarjeta("Para hacer ahora", el("div", { class: "atencion" }, ...atencion.map(([tipo, texto, boton, accion]) =>
        el("div", { class: "atencion-fila " + tipo }, icono(tipo === "ok" ? "check" : "alerta"), el("span", { text: texto }),
          boton ? el("button", { type: "button", class: "boton boton-secundario boton-chico", text: boton, onclick: accion }) : null)))),
      el("div", { class: "kpis" },
        kpi("Reportes", s.reportes, "meta: " + num(p.meta_observaciones), 0), kpi("Participantes", s.participantes, "mínimo: " + p.participantes_min, 1),
        kpi("Aceptados", s.reportes ? Math.round(100 * aceptados / s.reportes) : null, "de cada 100 reportes", 2, (n) => n + " %"),
        kpi("Con foto", s.con_foto, "para revisar la privacidad", 3), kpi("Puntaje medio", s.puntaje_medio != null ? Math.round(s.puntaje_medio) : null, "de 100", 4),
        kpi("Precisión GPS", s.precision_media_m != null ? Math.round(s.precision_media_m) : null, "metros, en promedio", 5, (n) => "±" + n + " m")),
      el("div", { class: "rejilla dos" }, tarjeta("Reportes por día", dias), tarjeta("Calidad de los reportes", calidad)),
      el("div", { class: "rejilla dos" }, tarjeta("Qué problemas se reportan", categorias), tarjeta("Desde qué celular", plataformas))));
  graficoDias(dias, s.por_dia);
  graficoBarras(categorias, s.por_categoria, Object.fromEntries((estado.config.categorias || []).map((c) => [c.id, c.nombre])));
  graficoAnillo(calidad, s.por_estado, { aceptar: "Aceptados", revisar: "Por revisar", descartar: "Descartados", sin_calcular: "Sin calcular" });
  graficoBarras(plataformas, s.por_plataforma, { ios: "iPhone", android: "Android", otro: "Otro" });
  primeraVez = false;
}

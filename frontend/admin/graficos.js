// Graficos del panel: HTML, CSS y SVG sin librerias (la CSP no permite scripts ni estilos en linea).
const SVG = "http://www.w3.org/2000/svg";
const num = (n) => Number(n).toLocaleString("es-EC");

function el(etiqueta, clase, texto) {
  const e = document.createElement(etiqueta);
  if (clase) e.className = clase;
  if (texto !== undefined) e.textContent = texto;
  return e;
}
function svg(etiqueta, atributos) {
  const e = document.createElementNS(SVG, etiqueta);
  for (const [k, v] of Object.entries(atributos || {})) e.setAttribute(k, v);
  return e;
}
const corto = (iso) => new Date(iso + "T12:00:00Z").toLocaleDateString("es-EC", { timeZone: "UTC", day: "numeric", month: "short" }).replace(".", "");

// Reportes por dia (ultimos 30 dias con datos; los dias sin reportes cuentan 0)
export function graficoDias(contenedor, porDia) {
  const claves = Object.keys(porDia || {}).sort();
  if (!claves.length) { contenedor.replaceChildren(el("p", "vacio", "Aún no hay reportes para graficar.")); return; }
  const fin = new Date(claves[claves.length - 1] + "T12:00:00Z");
  const inicio = new Date(Math.max(new Date(claves[0] + "T12:00:00Z"), fin.getTime() - 29 * 864e5));
  const dias = [];
  for (let d = new Date(inicio); d <= fin; d = new Date(d.getTime() + 864e5)) dias.push(d.toISOString().slice(0, 10));
  const valores = dias.map((d) => porDia[d] || 0);
  const total = valores.reduce((a, b) => a + b, 0);
  const maximo = Math.max(1, ...valores);
  const resumen = "Total: " + num(total) + " · Máximo: " + num(maximo) + " en un día · Promedio: " + (total / dias.length).toFixed(1).replace(".", ",") + " por día";

  const grafico = el("div", "dias");
  grafico.setAttribute("role", "img");
  grafico.setAttribute("aria-label", "Reportes por día, del " + corto(dias[0]) + " al " + corto(dias[dias.length - 1]) + ". " + resumen);
  dias.forEach((dia, i) => {
    const columna = el("div", "dia" + (valores[i] ? "" : " cero"));
    const texto = corto(dia) + ": " + valores[i] + (valores[i] === 1 ? " reporte" : " reportes");
    columna.dataset.valor = texto;
    columna.title = texto;
    const barra = document.createElement("i");
    if (valores[i]) barra.style.height = Math.max(4, Math.round(100 * valores[i] / maximo)) + "%";
    columna.append(barra);
    grafico.append(columna);
  });
  const eje = el("div", "dias-eje");
  eje.append(el("span", "", corto(dias[0])), el("span", "", corto(dias[Math.floor(dias.length / 2)])), el("span", "", corto(dias[dias.length - 1])));
  contenedor.replaceChildren(el("p", "resumen-grafico", resumen), grafico, eje);
}

// Barras horizontales (categorias, plataformas)
export function graficoBarras(contenedor, datos, nombres = {}) {
  const filas = Object.entries(datos || {}).sort((a, b) => b[1] - a[1]);
  const total = filas.reduce((a, f) => a + f[1], 0);
  if (!total) { contenedor.replaceChildren(el("p", "vacio", "Sin datos todavía.")); return; }
  const maximo = filas[0][1];
  contenedor.replaceChildren(...filas.map(([clave, n]) => {
    const fila = el("div", "fila-barra");
    const pista = el("div", "pista");
    const barra = document.createElement("i");
    barra.style.width = Math.max(2, Math.round(100 * n / maximo)) + "%";
    pista.append(barra);
    fila.append(el("span", "nombre", nombres[clave] || clave), pista, el("span", "valor", num(n) + " · " + Math.round(100 * n / total) + " %"));
    return fila;
  }));
}

// Anillo (calidad de los reportes)
export function graficoAnillo(contenedor, datos, nombres = {}, etiquetaCentro = "reportes") {
  const orden = ["aceptar", "revisar", "descartar", "sin_calcular"];
  const filas = Object.entries(datos || {}).sort((a, b) => (orden.indexOf(a[0]) + 99) % 99 - (orden.indexOf(b[0]) + 99) % 99);
  const total = filas.reduce((a, f) => a + f[1], 0);
  if (!total) { contenedor.replaceChildren(el("p", "vacio", "Sin datos todavía.")); return; }
  const radio = 52, circunferencia = 2 * Math.PI * radio;
  const dibujo = svg("svg", { class: "anillo", viewBox: "0 0 140 140", role: "img", "aria-label": "Calidad de los reportes: " + filas.map(([k, n]) => (nombres[k] || k) + " " + n).join(", ") });
  dibujo.append(svg("circle", { class: "base", cx: 70, cy: 70, r: radio }));
  let acumulado = 0;
  for (const [clave, n] of filas) {
    const largo = circunferencia * n / total;
    dibujo.append(svg("circle", { class: "seg seg-" + clave, cx: 70, cy: 70, r: radio,
      "stroke-dasharray": Math.max(0, largo - (filas.length > 1 ? 1.5 : 0)).toFixed(2) + " " + circunferencia.toFixed(2), "stroke-dashoffset": (-acumulado).toFixed(2) }));
    acumulado += largo;
  }
  const grande = svg("text", { x: 70, y: 72 });
  grande.textContent = num(total);
  const chico = svg("text", { x: 70, y: 88, class: "sub" });
  chico.textContent = etiquetaCentro;
  dibujo.append(grande, chico);
  const leyenda = el("ul", "leyenda");
  for (const [clave, n] of filas) {
    const item = el("li");
    item.append(el("span", "sw sw-" + clave), el("span", "", nombres[clave] || clave), el("span", "valor", num(n) + " · " + Math.round(100 * n / total) + " %"));
    leyenda.append(item);
  }
  const caja = el("div", "anillo-caja");
  caja.append(dibujo, leyenda);
  contenedor.replaceChildren(caja);
}

// Pantallas "Mis reportes" y "Ayuda" de la app del participante: ver como le fue a cada reporte, tips de GPS, privacidad,
// encuesta de experiencia y el derecho a retirarse (borra sus reportes sin pedirselo al equipo).
import { pedir } from "./api.js";
import { $, aviso, confirmar, el, icono, selectorTema } from "./interfaz.js";

const NOMBRES_ESTADO = { recibido: "Recibido", aceptado: "Aceptado", en_revision: "En revisión", descartado: "Descartado" };
const PREGUNTAS = [
  "Me resultó fácil enviar un reporte.",
  "Tuve que pensar mucho para saber qué hacer.",
  "La ubicación se tomó rápido y bien.",
  "Volvería a usar esta app.",
  "Me pareció confusa o enredada.",
];

function hace(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 45) return "hace un momento";
  if (s < 3600) return "hace " + Math.round(s / 60) + " min";
  if (s < 86400) return "hace " + Math.round(s / 3600) + " h";
  return new Date(iso).toLocaleDateString("es-EC", { day: "numeric", month: "short" }).replace(".", "");
}

// ctx: { config(), codigo(), pendientes(), olvidarCodigo(), irA(vista) }
export function iniciarParticipante(ctx) {
  const cabecera = () => ({ headers: { "x-clave": ctx.config().clave_formulario } });

  // ---------- Mis reportes ----------
  async function cargarMisReportes() {
    const raiz = $("vista-mis");
    raiz.replaceChildren(el("div", { class: "encabezado-vista" }, el("h2", { text: "Mis reportes" }),
      el("button", { type: "button", class: "boton-icono", "aria-label": "Actualizar", onclick: cargarMisReportes }, icono("refrescar"))), el("div", { class: "lista", id: "mis-lista" }));
    const lista = $("mis-lista");
    const pendientes = ctx.pendientes();
    if (pendientes) lista.append(el("div", { class: "alerta aviso" }, icono("reloj"), el("p", { text: pendientes + (pendientes === 1 ? " reporte espera" : " reportes esperan") + " internet para enviarse. Se mandan solos." })));
    try {
      const filas = await pedir("/mis-reportes?participante_id=" + encodeURIComponent(ctx.codigo()), cabecera());
      if (!filas.length) {
        lista.append(el("div", { class: "vacio-grande" }, icono("lista"), el("strong", { text: "Aún no tienes reportes" }), el("span", { text: "Cuando envíes uno, aquí ves cómo le fue." }),
          el("button", { type: "button", class: "boton boton-primario", text: "Hacer mi primer reporte", onclick: () => ctx.irA("reportar") })));
        return;
      }
      for (const f of filas) {
        const c = ctx.config().categorias.find((x) => x.id === f.categoria);
        lista.append(el("div", { class: "fila-reporte", style: "cursor:default" },
          el("span", { class: "ico-cat c-" + f.categoria }, icono(f.categoria)),
          el("span", { class: "fila-texto" }, el("strong", { text: (c ? c.nombre : f.categoria) + " · #" + f.id }),
            el("small", { text: f.consejos.length ? f.consejos.join(" ") : hace(f.recibido_en) })),
          el("span", { class: "pildora p-" + f.estado }, el("i"), NOMBRES_ESTADO[f.estado])));
      }
    } catch (e) {
      lista.append(el("div", { class: "alerta error" }, icono("alerta"), el("p", { text: "No pudimos cargar tus reportes ahora. Revisa tu internet." })));
    }
  }

  // ---------- Ayuda ----------
  function pintarAyuda() {
    const respuestas = [0, 0, 0, 0, 0];
    const comentario = el("textarea", { rows: "3", maxlength: "280", placeholder: "¿Algo que mejorar? (opcional)" });
    const enviar = el("button", { type: "button", class: "boton boton-primario", text: "Enviar mis respuestas", disabled: true, onclick: async () => {
      enviar.disabled = true;
      try {
        await pedir("/encuesta", { method: "POST", headers: { "Content-Type": "application/json", "x-clave": ctx.config().clave_formulario },
          body: JSON.stringify({ participante_id: ctx.codigo(), respuestas, comentario: comentario.value.trim() }) });
        $("caja-encuesta").replaceChildren(el("div", { class: "alerta ok" }, icono("check"), el("p", { text: "¡Gracias! Tus respuestas ayudan a mejorar la app." })));
      } catch (e) { enviar.disabled = false; aviso(e.message || "No se pudo enviar", "error"); }
    } });
    const preguntas = PREGUNTAS.map((texto, i) => {
      const botones = [1, 2, 3, 4, 5].map((n) => el("button", { type: "button", "aria-pressed": "false", text: String(n), onclick: () => {
        respuestas[i] = n;
        botones.forEach((b, k) => b.setAttribute("aria-pressed", String(k + 1 === n)));
        enviar.disabled = respuestas.some((r) => !r);
      } }));
      return el("div", { class: "pregunta" }, el("strong", { text: texto }), el("div", { class: "opciones-escala" }, ...botones),
        el("div", { class: "extremos" }, el("span", { text: "Nada de acuerdo" }), el("span", { text: "Muy de acuerdo" })));
    });
    $("vista-ayuda").replaceChildren(
      el("div", { class: "encabezado-vista" }, el("h2", { text: "Ayuda" })),
      el("section", { class: "tarjeta" }, el("h2", { text: "Cómo se reporta" }),
        el("ol", { class: "pasos-ayuda" }, el("li", { text: "Elige qué problema ves y, si quieres, cuéntalo o agrega una foto." }),
          el("li", { text: "Toca «Ver dónde estoy». Espera a que el círculo se llene; si el pin no queda justo, mueve el mapa." }),
          el("li", { text: "Revisa, acepta y envía. Si no hay internet, se guarda y se manda solo después." }))),
      el("section", { class: "tarjeta" }, el("h2", { text: "Para que tu ubicación sea más exacta" }),
        el("ul", { class: "consejos" }, el("li", { text: "Sal a un lugar abierto: entre edificios y techos el GPS se confunde." }),
          el("li", { text: "Activa la ubicación «precisa» del celular y el GPS (no solo el Wi-Fi)." }),
          el("li", { text: "Espera unos 10 a 20 segundos sin moverte hasta que el círculo se ponga verde." }),
          el("li", { text: "Desactiva el ahorro de batería: reduce la precisión." }),
          el("li", { text: "Deja la hora del celular en automático." }))),
      el("section", { class: "tarjeta" }, el("h2", { text: "Apariencia" }), el("p", { class: "paso-ayuda", text: "Elige cómo se ve la app." }), selectorTema()),
      el("section", { class: "tarjeta" }, el("h2", { text: "Instalar en tu celular" }),
        el("p", { class: "paso-ayuda", text: "iPhone: toca Compartir y luego «Agregar a pantalla de inicio». Android: menú ⋮ y «Instalar app». Así abre como una app y también guarda tus reportes sin internet." })),
      el("section", { class: "tarjeta" }, el("h2", { text: "Tu privacidad" }),
        el("ul", { class: "consejos" },
          el("li", { text: "Para qué: este es un estudio académico de la UTPL sobre problemas urbanos en Loja." }),
          el("li", { text: "Qué se guarda: tipo de problema, descripción, ubicación y su precisión, fecha y hora, tipo de celular, cómo te movías (velocidad), si moviste el pin, tu foto (si la agregas) y un código al azar." }),
          el("li", { text: "Qué NO se guarda: tu nombre, correo, teléfono ni cédula. La ubicación solo se toma al enviar un reporte, nunca en segundo plano." }),
          el("li", { text: "Quién lo ve: solo el equipo del proyecto, con clave, para investigar. Participan personas de 18 años o más." }),
          el("li", { text: "Puedes retirarte cuando quieras y se borra todo lo tuyo." })),
        el("p", { class: "paso-ayuda nota" }, "Tu código: ", el("span", { class: "codigo", text: ctx.codigo() })),
        el("button", { type: "button", class: "boton boton-peligro boton-ancho", style: "margin-top:12px", text: "Borrar mis reportes y retirarme", onclick: retirarme })),
      el("section", { class: "tarjeta", id: "caja-encuesta" }, el("h2", { text: "¿Cómo te fue con la app?" }),
        el("p", { class: "paso-ayuda", text: "Son 5 preguntas rápidas (1 = nada de acuerdo, 5 = muy de acuerdo)." }),
        el("div", { class: "escala" }, ...preguntas, comentario, enviar)),
      el("p", { class: "paso-ayuda nota", style: "text-align:center", text: "Proyecto académico · Universidad Técnica Particular de Loja" }));
  }

  async function retirarme() {
    if (!await confirmar({ titulo: "¿Retirarte del estudio?", texto: "Se borran todos tus reportes, fotos y respuestas. No se puede deshacer.", boton: "Sí, borrar todo", peligro: true })) return;
    try {
      const r = await pedir("/mis-datos/" + encodeURIComponent(ctx.codigo()), { method: "DELETE", ...cabecera() });
      ctx.olvidarCodigo();
      aviso("Listo: se borraron " + r.reportes_borrados + (r.reportes_borrados === 1 ? " reporte" : " reportes") + ".");
      pintarAyuda();
    } catch (e) { aviso(e.message || "No se pudo borrar. Intenta de nuevo.", "error"); }
  }

  return { cargarMisReportes, pintarAyuda };
}

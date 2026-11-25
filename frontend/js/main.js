// Formulario del participante: coordina los tres pasos
import { ErrorApi, buscarSimilares, enviarReporte, obtenerConfiguracion } from "./api.js";
import { agregarPendiente, enviarPendientes, leerPendientes } from "./cola.js";
import { reducirFoto } from "./foto.js";
import { ErrorUbicacion, obtenerMejorUbicacion } from "./ubicacion.js";
import { crearMinimapa } from "./minimapa.js";
import { botonTema } from "./interfaz.js";
import { iniciarParticipante } from "./participante.js";
import { crearCodigoParticipante, crearUuid, dentroDeZona, detectarPlataforma, errorDeContenido, formatearBytes, guardarJson,
         leerJson, nivelDePrecision } from "./utilidades.js";

const CONFIG_POR_DEFECTO = {
  version_api: "",
  clave_formulario: "",
  categorias: [
    { id: "bache", nombre: "Bache", ayuda: "Hueco o daño en la calzada" },
    { id: "luminaria_danada", nombre: "Luminaria dañada", ayuda: "Poste o foco que no funciona" },
    { id: "basura", nombre: "Basura acumulada", ayuda: "Residuos en la vía pública" },
    { id: "otro", nombre: "Otro", ayuda: "Cualquier otro problema urbano" },
  ],
  zona: { lat_min: -4.010, lat_max: -3.975, lon_min: -79.220, lon_max: -79.185 },
  captura: { max_descripcion: 280, min_descripcion_otro: 8, precision_objetivo_m: 20, precision_aceptable_m: 50, espera_gps_s: 15, foto_max_lado_px: 800, foto_calidad: 0.7 },
  consentimiento: { version: "v2" },
};

const estado = { config: CONFIG_POR_DEFECTO, categoria: null, foto: null, ubicacion: null, buscando: false, enviando: false, pasoActual: 1 };
const $ = (id) => document.getElementById(id);

// ---------- configuracion (se guarda para poder abrir sin internet) ----------
async function cargarConfiguracion() {
  const guardada = leerJson("mcs.config", null);
  if (guardada) estado.config = guardada;
  try {
    estado.config = await obtenerConfiguracion();
    guardarJson("mcs.config", estado.config);
  } catch (e) {
    // sin internet: se usa la copia guardada o la de por defecto
  }
}

function codigoDeParticipante() {
  let codigo = leerJson("mcs.participante", null);
  if (!codigo) {
    codigo = crearCodigoParticipante();
    guardarJson("mcs.participante", codigo);
  }
  return codigo;
}

// ---------- interfaz general ----------
function mostrarPaso(numero) {
  estado.pasoActual = numero;
  for (const n of [1, 2, 3]) $("paso-" + n).hidden = n !== numero;
  $("pantalla-exito").hidden = true;
  $("zona-formulario").hidden = false;
  document.querySelectorAll("#progreso li").forEach((li, i) => {
    li.classList.toggle("actual", i + 1 === numero);
    li.classList.toggle("hecho", i + 1 < numero);
  });
  const titulo = $("titulo-" + numero);
  titulo.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function mostrarAlerta(id, texto) {
  const caja = $(id);
  if (!texto) { caja.hidden = true; return; }
  caja.querySelector("p").textContent = texto;
  caja.hidden = false;
}

function actualizarRed() {
  const boton = $("estado-red");
  const pendientes = leerPendientes().length;
  const enLinea = navigator.onLine;
  boton.classList.toggle("sin-red", !enLinea);
  boton.classList.toggle("pendientes", pendientes > 0);
  if (pendientes > 0) {
    $("estado-red-texto").textContent = pendientes + (pendientes === 1 ? " pendiente" : " pendientes");
    boton.title = enLinea ? "Toca para enviar ahora" : "Se enviarán cuando vuelva internet";
  } else {
    $("estado-red-texto").textContent = enLinea ? "En línea" : "Sin conexión";
    boton.title = "";
  }
}

// ---------- paso 1: categoria, descripcion y foto ----------
function dibujarCategorias() {
  const contenedor = $("categorias");
  contenedor.replaceChildren();
  for (const categoria of estado.config.categorias) {
    const etiqueta = document.createElement("label");
    etiqueta.className = "categoria";
    const entrada = document.createElement("input");
    entrada.type = "radio";
    entrada.name = "categoria";
    entrada.value = categoria.id;
    const contenido = document.createElement("span");
    contenido.className = "contenido";
    const icono = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icono.setAttribute("class", "icono");
    const uso = document.createElementNS("http://www.w3.org/2000/svg", "use");
    uso.setAttribute("href", "/iconos.svg#i-" + categoria.id);
    icono.append(uso);
    const nombre = document.createElement("strong");
    nombre.textContent = categoria.nombre;
    const ayuda = document.createElement("small");
    ayuda.textContent = categoria.ayuda;
    contenido.append(icono, nombre, ayuda);
    entrada.addEventListener("change", () => {
      estado.categoria = categoria.id;
      mostrarAlerta("error-paso-1", "");
      if (navigator.vibrate) navigator.vibrate(8);
      actualizarNotasDeContenido();
    });
    etiqueta.append(entrada, contenido);
    contenedor.append(etiqueta);
  }
  $("descripcion").maxLength = estado.config.captura.max_descripcion;
  $("contador-max").textContent = String(estado.config.captura.max_descripcion);
}

async function elegirFoto(evento) {
  const archivo = evento.target.files[0];
  if (!archivo) return;
  mostrarAlerta("error-paso-1", "");
  try {
    const foto = await reducirFoto(archivo, estado.config.captura.foto_max_lado_px, estado.config.captura.foto_calidad);
    quitarFoto();
    estado.foto = foto;
    $("foto-imagen").src = foto.urlVistaPrevia;
    $("foto-peso").textContent = formatearBytes(foto.bytes);
    $("foto-vista").hidden = false;
    $("boton-foto").lastChild.textContent = " Cambiar foto";
  } catch (e) {
    mostrarAlerta("error-paso-1", "No se pudo usar esa foto. Prueba con otra.");
  }
  evento.target.value = "";
}

function quitarFoto() {
  if (estado.foto) URL.revokeObjectURL(estado.foto.urlVistaPrevia);
  estado.foto = null;
  $("foto-vista").hidden = true;
  $("boton-foto").lastChild.textContent = " Añadir foto";
}

// En "Otro" la descripcion o la foto son obligatorias; en las demas categorias siguen siendo opcionales
function actualizarNotasDeContenido() {
  const minimo = estado.config.captura.min_descripcion_otro || 8;
  const pide = estado.categoria === "otro";
  $("descripcion-nota").textContent = pide ? "(obligatorio si no hay foto)" : "(opcional)";
  $("foto-nota").textContent = pide ? "(obligatoria si no escribes nada)" : "(opcional)";
  $("descripcion").placeholder = pide ? "Cuéntanos qué pasa (mínimo " + minimo + " letras)" : "Ej.: bache profundo frente a la entrada";
}

function continuarPaso1() {
  if (!estado.categoria) {
    mostrarAlerta("error-paso-1", "Elige el tipo de problema para continuar.");
    return;
  }
  const faltaContenido = errorDeContenido(estado.categoria, $("descripcion").value, Boolean(estado.foto), estado.config.captura.min_descripcion_otro || 8);
  $("descripcion").classList.toggle("campo-error", Boolean(faltaContenido));
  if (faltaContenido) {
    mostrarAlerta("error-paso-1", faltaContenido);
    $("descripcion").focus();
    return;
  }
  mostrarPaso(2);
  if (!estado.ubicacion) buscarUbicacion();
}

// ---------- paso 2: ubicacion ----------
function dibujarMedidor(punto, buscando) {
  const medidor = $("medidor");
  const valor = $("medidor-valor");
  medidor.classList.remove("excelente", "aceptable", "baja", "buscando");
  if (!punto) {
    medidor.classList.toggle("buscando", buscando);
    valor.style.strokeDashoffset = buscando ? "330" : "440";
    $("medidor-numero").textContent = buscando ? "…" : "—";
    $("medidor-texto").textContent = buscando ? "buscando señal" : "sin ubicación";
    return;
  }
  const nivel = nivelDePrecision(punto.precision, estado.config.captura);
  medidor.classList.add(nivel.nivel);
  if (buscando) medidor.classList.add("buscando");
  // mas precision (numero chico) = circulo mas lleno; se toma 100 m como "vacio"
  const llenado = Math.max(0.08, Math.min(1, 1 - punto.precision / 100));
  valor.style.strokeDashoffset = String(440 * (1 - llenado));
  $("medidor-numero").textContent = "±" + Math.round(punto.precision) + " m";
  $("medidor-texto").textContent = "precisión " + nivel.texto.toLowerCase();
}

function dibujarEtiquetasUbicacion() {
  const caja = $("etiquetas-ubicacion");
  caja.replaceChildren();
  const punto = estado.ubicacion;
  if (!punto) { $("coordenadas").textContent = ""; return; }
  const dentro = dentroDeZona(punto.lat, punto.lon, estado.config.zona);
  const zona = document.createElement("span");
  zona.className = "etiqueta-estado " + (dentro ? "ok" : "aviso");
  zona.textContent = dentro ? "Dentro de la zona del estudio" : "Fuera de la zona del estudio";
  caja.append(zona);
  $("coordenadas").textContent = punto.lat.toFixed(5) + ", " + punto.lon.toFixed(5);
}

function explicarErrorUbicacion(error) {
  if (error instanceof ErrorUbicacion) {
    if (error.codigo === "denegado") {
      const ios = detectarPlataforma(navigator.userAgent) === "ios";
      return ios
        ? "El permiso de ubicación está desactivado. En el iPhone: Ajustes > Privacidad y seguridad > Localización, activa Localización y permite a Safari “Al usar la app”."
        : "El permiso de ubicación está desactivado. Toca el candado junto a la dirección, entra a Permisos > Ubicación y elige Permitir.";
    }
    if (error.codigo === "sin_soporte") return "Este navegador no permite obtener la ubicación. Prueba con Safari o Chrome.";
    if (error.codigo === "no_disponible") return "No hay señal de ubicación. Activa el GPS del celular y sal a un lugar abierto.";
  }
  return "No se pudo obtener una ubicación a tiempo. Sal a un lugar abierto, activa el GPS e inténtalo de nuevo.";
}

async function buscarUbicacion() {
  if (estado.buscando) return;
  estado.buscando = true;
  estado.ubicacion = null;
  minimapa.ocultar();
  $("siguiente-2").disabled = true;
  const boton = $("boton-ubicacion");
  boton.disabled = true;
  boton.classList.add("cargando");
  mostrarAlerta("mensaje-ubicacion", "");
  dibujarMedidor(null, true);
  dibujarEtiquetasUbicacion();
  try {
    const punto = await obtenerMejorUbicacion({
      objetivoM: estado.config.captura.precision_objetivo_m,
      esperaMs: estado.config.captura.espera_gps_s * 1000,
      alProgreso: (mejor) => dibujarMedidor(mejor, true),
    });
    estado.ubicacion = { ...punto, gps: { lat: punto.lat, lon: punto.lon }, ajustada: false };
    minimapa.mostrar(estado.ubicacion);
    dibujarMedidor(punto, false);
    dibujarEtiquetasUbicacion();
    $("siguiente-2").disabled = false;
    if (nivelDePrecision(punto.precision, estado.config.captura).nivel === "baja") {
      $("mensaje-ubicacion").className = "alerta aviso";
      mostrarAlerta("mensaje-ubicacion", "La precisión es baja. Puedes mejorarla saliendo a un lugar abierto y tocando “Mejorar precisión”, o continuar así.");
    }
    boton.lastChild.textContent = " Mejorar precisión";
  } catch (error) {
    dibujarMedidor(null, false);
    $("mensaje-ubicacion").className = "alerta error";
    mostrarAlerta("mensaje-ubicacion", explicarErrorUbicacion(error));
    boton.lastChild.textContent = " Intentar de nuevo";
  } finally {
    estado.buscando = false;
    boton.disabled = false;
    boton.classList.remove("cargando");
  }
}

// ---------- paso 3: revisar y enviar ----------
function nombreDeCategoria(id) {
  const c = estado.config.categorias.find((x) => x.id === id);
  return c ? c.nombre : id;
}

function fila(titulo, valor) {
  const dt = document.createElement("dt");
  dt.textContent = titulo;
  const dd = document.createElement("dd");
  if (valor instanceof Node) dd.append(valor); else dd.textContent = valor;
  return [dt, dd];
}

async function continuarPaso2() {
  const descripcion = $("descripcion").value.trim();
  const resumen = $("resumen");
  resumen.replaceChildren();
  resumen.append(...fila("Categoría", nombreDeCategoria(estado.categoria)));
  resumen.append(...fila("Descripción", descripcion || "Sin descripción"));
  resumen.append(...fila("Ubicación", estado.ubicacion.lat.toFixed(5) + ", " + estado.ubicacion.lon.toFixed(5) +
                          " (±" + Math.round(estado.ubicacion.precision) + " m)" + (estado.ubicacion.ajustada ? " · corregida a mano" : "")));
  if (estado.foto) {
    const imagen = document.createElement("img");
    imagen.src = estado.foto.urlVistaPrevia;
    imagen.alt = "Foto del reporte";
    resumen.append(...fila("Foto", imagen));
  }
  mostrarAlerta("aviso-similar", "");
  mostrarAlerta("error-paso-3", "");
  mostrarPaso(3);
  if (navigator.onLine && estado.config.clave_formulario) {
    try {
      const r = await buscarSimilares(estado.ubicacion.lat, estado.ubicacion.lon, estado.categoria, estado.config.clave_formulario);
      if (r.similares > 0) {
        mostrarAlerta("aviso-similar", "Hace pocos minutos alguien reportó algo parecido a unos " + r.mas_cercano_m +
                      " m de aquí. Si es el mismo problema, no hace falta enviarlo otra vez.");
      }
    } catch (e) {
      // el aviso es opcional: si falla, se ignora
    }
  }
}

function armarReporte() {
  return {
    id_cliente: crearUuid(),
    participante_id: codigoDeParticipante(),
    categoria: estado.categoria,
    descripcion: $("descripcion").value.trim(),
    lat: estado.ubicacion.lat,
    lon: estado.ubicacion.lon,
    precision_m: estado.ubicacion.precision,
    fecha_dispositivo: new Date(estado.ubicacion.marca_de_tiempo || Date.now()).toISOString(),
    plataforma: detectarPlataforma(navigator.userAgent),
    navegador: navigator.userAgent.slice(0, 150),
    consentimiento: true,
    consentimiento_version: estado.config.consentimiento.version,
    foto_base64: estado.foto ? estado.foto.base64 : null,
    ubicacion_ajustada: Boolean(estado.ubicacion.ajustada),
    velocidad_ms: estado.ubicacion.velocidad ?? null,
  };
}

async function enviarConReintentoDeClave(datos) {
  try {
    return await enviarReporte(datos, estado.config.clave_formulario);
  } catch (error) {
    if (error instanceof ErrorApi && error.estado === 401 && navigator.onLine) {
      // la clave del formulario pudo cambiar: se pide la configuracion de nuevo y se reintenta una vez
      await cargarConfiguracion();
      return await enviarReporte(datos, estado.config.clave_formulario);
    }
    throw error;
  }
}

function mostrarExito(guardadoEnElCelular, id) {
  $("zona-formulario").hidden = true;
  const pantalla = $("pantalla-exito");
  pantalla.hidden = false;
  pantalla.classList.toggle("guardado", guardadoEnElCelular);
  $("titulo-exito").textContent = guardadoEnElCelular ? "Guardado en tu celular" : "¡Listo, enviado!";
  $("exito-texto").textContent = guardadoEnElCelular
    ? "No hay internet ahora. Tu reporte queda guardado y se envía solo cuando vuelva."
    : "Gracias por ayudar a Loja. Tu reporte es el número " + id + ".";
  $("exito-icono").firstElementChild.setAttribute("href", guardadoEnElCelular ? "/iconos.svg#i-reloj" : "/iconos.svg#i-check");
  $("exito-codigo").textContent = codigoDeParticipante();
  $("titulo-exito").focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function enviar() {
  if (estado.enviando) return;
  mostrarAlerta("error-paso-3", "");
  if (!$("consentimiento").checked) {
    mostrarAlerta("error-paso-3", "Debes aceptar el consentimiento para poder enviar el reporte.");
    return;
  }
  estado.enviando = true;
  const boton = $("boton-enviar");
  boton.disabled = true;
  boton.classList.add("cargando");
  const datos = armarReporte();
  try {
    if (!navigator.onLine) throw new ErrorApi("Sin conexión", 0, "sin_conexion");
    const respuesta = await enviarConReintentoDeClave(datos);
    reiniciarFormulario();
    mostrarExito(false, respuesta.id);
  } catch (error) {
    const sinRed = error instanceof ErrorApi && (error.estado === 0 || error.estado >= 500);
    if (sinRed) {
      if (agregarPendiente(datos)) {
        reiniciarFormulario();
        mostrarExito(true);
      } else {
        mostrarAlerta("error-paso-3", "No hay conexión y tu celular no pudo guardar el reporte. Inténtalo de nuevo cuando tengas internet.");
      }
    } else {
      mostrarAlerta("error-paso-3", error.message || "No se pudo enviar el reporte.");
    }
  } finally {
    estado.enviando = false;
    boton.disabled = false;
    boton.classList.remove("cargando");
    actualizarRed();
  }
}

function reiniciarFormulario() {
  estado.categoria = null;
  estado.ubicacion = null;
  quitarFoto();
  document.querySelectorAll('input[name="categoria"]').forEach((r) => { r.checked = false; });
  $("descripcion").value = "";
  $("descripcion").classList.remove("campo-error");
  $("contador").textContent = "0";
  actualizarNotasDeContenido();
  $("consentimiento").checked = false;
  minimapa.ocultar();
  dibujarMedidor(null, false);
  dibujarEtiquetasUbicacion();
  $("siguiente-2").disabled = true;
  $("boton-ubicacion").lastChild.textContent = " Ver dónde estoy";
  mostrarAlerta("mensaje-ubicacion", "");
}

// ---------- envio de pendientes ----------
async function vaciarPendientes() {
  if (!navigator.onLine || leerPendientes().length === 0) { actualizarRed(); return; }
  await cargarConfiguracion();
  await enviarPendientes((datos) => enviarReporte(datos, estado.config.clave_formulario));
  actualizarRed();
}

// ---------- arranque ----------
const minimapa = crearMinimapa($("minimapa"), (c) => {
  if (!estado.ubicacion) return;
  Object.assign(estado.ubicacion, { lat: c.lat, lon: c.lon, ajustada: c.ajustada });
  $("coordenadas").textContent = c.lat.toFixed(5) + ", " + c.lon.toFixed(5) + (c.ajustada ? " · corregida" : "");
  dibujarEtiquetasUbicacion();
  if (c.ajustada) $("coordenadas").textContent += " · corregida";
});

// ---------- pestañas: Reportar / Mis reportes / Ayuda ----------
let participante = null;
function irA(vista) {
  for (const nombre of ["reportar", "mis", "ayuda"]) $("vista-" + nombre).hidden = nombre !== vista;
  document.querySelectorAll(".pestanas button").forEach((b) => b.toggleAttribute("aria-current", b.dataset.vista === vista));
  document.querySelectorAll(".pestanas button").forEach((b) => { if (b.dataset.vista === vista) b.setAttribute("aria-current", "page"); });
  if (vista === "mis") participante.cargarMisReportes();
  if (vista === "ayuda") participante.pintarAyuda();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function iniciar() {
  const codigo = codigoDeParticipante();
  $("boton-tema").replaceWith(botonTema());
  participante = iniciarParticipante({
    config: () => estado.config, codigo: codigoDeParticipante, pendientes: () => leerPendientes().length, irA,
    olvidarCodigo: () => { try { localStorage.removeItem("mcs.participante"); localStorage.removeItem("mcs.pendientes.v3"); } catch (e) { /* sin permiso */ } },
  });
  document.querySelectorAll(".pestanas button").forEach((b) => b.addEventListener("click", () => irA(b.dataset.vista)));
  $("ver-mis").addEventListener("click", () => irA("mis"));
  $("ir-encuesta").addEventListener("click", () => { irA("ayuda"); setTimeout(() => $("caja-encuesta").scrollIntoView({ behavior: "smooth" }), 80); });
  dibujarCategorias();
  actualizarRed();

  $("descripcion").addEventListener("input", (e) => {
    $("contador").textContent = String(e.target.value.length);
    if (e.target.classList.contains("campo-error")) { e.target.classList.remove("campo-error"); mostrarAlerta("error-paso-1", ""); }
  });
  $("boton-foto").addEventListener("click", () => $("archivo-foto").click());
  $("archivo-foto").addEventListener("change", elegirFoto);
  $("quitar-foto").addEventListener("click", quitarFoto);
  $("siguiente-1").addEventListener("click", continuarPaso1);
  $("boton-ubicacion").addEventListener("click", buscarUbicacion);
  $("atras-2").addEventListener("click", () => mostrarPaso(1));
  $("siguiente-2").addEventListener("click", continuarPaso2);
  $("atras-3").addEventListener("click", () => mostrarPaso(2));
  $("boton-enviar").addEventListener("click", enviar);
  $("otro-reporte").addEventListener("click", () => mostrarPaso(1));
  $("estado-red").addEventListener("click", vaciarPendientes);
  window.addEventListener("online", vaciarPendientes);
  window.addEventListener("offline", actualizarRed);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => { /* la app funciona igual sin service worker */ });
  }

  await cargarConfiguracion();
  dibujarCategorias();
  await vaciarPendientes();
}

iniciar();

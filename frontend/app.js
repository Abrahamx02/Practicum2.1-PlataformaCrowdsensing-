// ===== parte 1: datos basicos =====
// Esta clave NO es secreta (queda visible en el navegador). Solo evita envios al azar.
// Debe ser igual a CLAVE_ESCRITURA del servidor.
const CLAVE_ESCRITURA = "lojamcs2026";
const URL_API = "/reportes";
const VERSION_CONSENTIMIENTO = "v1";   // cambiarla si cambia el texto del consentimiento

let ubicacion = null;
let fotoBase64 = null;

function obtenerParticipanteId() {
  let id = null;
  try {
    id = localStorage.getItem("participante_id");
    if (id === null) {
      id = "p-" + Math.random().toString(36).substring(2, 10);
      localStorage.setItem("participante_id", id);
    }
  } catch (e) {
    // en modo privado de Safari puede fallar el almacenamiento
    id = "p-" + Math.random().toString(36).substring(2, 10);
  }
  return id;
}

function detectarPlataforma() {
  const ua = navigator.userAgent;
  if (/iPhone|iPad|iPod/i.test(ua)) {
    return "ios";
  }
  if (/Android/i.test(ua)) {
    return "android";
  }
  return "otro";
}

function mostrarMensaje(texto, tipo) {
  const caja = document.getElementById("mensaje");
  caja.textContent = texto;
  caja.className = tipo;
}

// ===== parte 2: pedir la ubicacion =====
function pedirUbicacion() {
  const texto = document.getElementById("textoUbicacion");
  if (!navigator.geolocation) {
    texto.textContent = "Este navegador no permite obtener la ubicación.";
    return;
  }
  texto.textContent = "Obteniendo ubicación...";
  navigator.geolocation.getCurrentPosition(
    function (posicion) {
      ubicacion = {
        lat: posicion.coords.latitude,
        lon: posicion.coords.longitude,
        precision: posicion.coords.accuracy
      };
      texto.textContent = "Ubicación lista. Precisión aproximada: " + Math.round(ubicacion.precision) + " m";
    },
    function (error) {
      ubicacion = null;
      if (error.code === 1) {
        texto.textContent = "Negaste el permiso de ubicación. Actívalo en los ajustes del navegador y vuelve a intentar.";
      } else {
        texto.textContent = "No se pudo obtener la ubicación. Sal a un lugar abierto e intenta de nuevo.";
      }
    },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
  );
}

// ===== parte 3: foto opcional (se reduce el tamano antes de enviar) =====
function prepararFoto(evento) {
  const archivo = evento.target.files[0];
  const vista = document.getElementById("vistaPrevia");
  fotoBase64 = null;
  vista.style.display = "none";
  if (!archivo) {
    return;
  }
  if (!archivo.type.startsWith("image/")) {
    mostrarMensaje("El archivo debe ser una imagen.", "error");
    return;
  }
  const lector = new FileReader();
  lector.onload = function () {
    const imagen = new Image();
    imagen.onload = function () {
      const maximo = 800;
      let ancho = imagen.width;
      let alto = imagen.height;
      if (ancho >= alto && ancho > maximo) {
        alto = Math.round(alto * maximo / ancho);
        ancho = maximo;
      } else if (alto > ancho && alto > maximo) {
        ancho = Math.round(ancho * maximo / alto);
        alto = maximo;
      }
      const lienzo = document.createElement("canvas");
      lienzo.width = ancho;
      lienzo.height = alto;
      lienzo.getContext("2d").drawImage(imagen, 0, 0, ancho, alto);
      const url = lienzo.toDataURL("image/jpeg", 0.7);
      fotoBase64 = url.split(",")[1];
      vista.src = url;
      vista.style.display = "block";
    };
    imagen.src = lector.result;
  };
  lector.readAsDataURL(archivo);
}

// ===== parte 4: enviar el reporte =====
async function enviarReporte() {
  mostrarMensaje("", "");
  const categoria = document.getElementById("categoria").value;
  const descripcion = document.getElementById("descripcion").value.trim();
  const acepto = document.getElementById("consentimiento").checked;
  const boton = document.getElementById("botonEnviar");

  if (!acepto) {
    mostrarMensaje("Debes aceptar el consentimiento para poder enviar.", "error");
    return;
  }
  if (categoria === "") {
    mostrarMensaje("Elige una categoría.", "error");
    return;
  }
  if (ubicacion === null) {
    mostrarMensaje("Primero toca el botón para obtener tu ubicación.", "error");
    return;
  }

  const datos = {
    participante_id: obtenerParticipanteId(),
    categoria: categoria,
    descripcion: descripcion,
    lat: ubicacion.lat,
    lon: ubicacion.lon,
    precision_m: ubicacion.precision,
    fecha_dispositivo: new Date().toISOString(),
    plataforma: detectarPlataforma(),
    navegador: navigator.userAgent.substring(0, 150),
    consentimiento: true,
    consentimiento_version: VERSION_CONSENTIMIENTO,
    foto_base64: fotoBase64
  };

  boton.disabled = true;
  boton.textContent = "Enviando...";
  try {
    const respuesta = await fetch(URL_API, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-clave": CLAVE_ESCRITURA },
      body: JSON.stringify(datos)
    });
    if (respuesta.ok) {
      mostrarMensaje("Reporte enviado. ¡Gracias por participar!", "ok");
      limpiarFormulario();
      boton.textContent = "Enviar reporte";
    } else {
      mostrarMensaje("El servidor no aceptó el reporte (código " + respuesta.status + ").", "error");
      boton.textContent = "Reintentar envío";
    }
  } catch (e) {
    // sin internet: el reporte se guarda en el celular y se envia despues
    if (guardarPendiente(datos)) {
      mostrarMensaje("Sin conexión. El reporte quedó guardado en tu celular y se enviará solo cuando vuelva internet.", "ok");
      limpiarFormulario();
    } else {
      mostrarMensaje("No hay conexión y no se pudo guardar en el celular. Toca Reintentar cuando tengas internet.", "error");
    }
    boton.textContent = "Enviar reporte";
    mostrarPendientes();
  }
  boton.disabled = false;
}

function limpiarFormulario() {
  document.getElementById("categoria").value = "";
  document.getElementById("descripcion").value = "";
  document.getElementById("foto").value = "";
  document.getElementById("vistaPrevia").style.display = "none";
  document.getElementById("consentimiento").checked = false;
  document.getElementById("textoUbicacion").textContent = "Todavía no se ha obtenido la ubicación.";
  ubicacion = null;
  fotoBase64 = null;
}

// ===== parte 5: conectar los botones =====
document.getElementById("botonUbicacion").addEventListener("click", pedirUbicacion);
document.getElementById("foto").addEventListener("change", prepararFoto);
document.getElementById("botonEnviar").addEventListener("click", enviarReporte);

// ===== parte 6: reportes pendientes (cuando no hay internet) =====
function leerPendientes() {
  try {
    return JSON.parse(localStorage.getItem("pendientes") || "[]");
  } catch (e) {
    return [];
  }
}

function guardarListaPendientes(lista) {
  try {
    localStorage.setItem("pendientes", JSON.stringify(lista));
    return true;
  } catch (e) {
    return false;
  }
}

function guardarPendiente(datos) {
  const lista = leerPendientes();
  lista.push(datos);
  return guardarListaPendientes(lista);
}

function mostrarPendientes() {
  const n = leerPendientes().length;
  const caja = document.getElementById("avisoPendientes");
  if (n === 0) {
    caja.textContent = "";
  } else {
    caja.textContent = "Reportes guardados en este celular esperando internet: " + n;
  }
}

async function enviarPendientes() {
  const lista = leerPendientes();
  const faltan = [];
  for (const datos of lista) {
    try {
      const respuesta = await fetch(URL_API, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-clave": CLAVE_ESCRITURA },
        body: JSON.stringify(datos)
      });
      // si el servidor falla (500) se conserva; si rechaza los datos (4xx) no tiene sentido reintentar
      if (respuesta.status >= 500) {
        faltan.push(datos);
      }
    } catch (e) {
      faltan.push(datos);
    }
  }
  guardarListaPendientes(faltan);
  mostrarPendientes();
}

document.getElementById("codigoParticipante").textContent = obtenerParticipanteId();
window.addEventListener("online", enviarPendientes);
mostrarPendientes();
enviarPendientes();

// ===== parte 7: que la pagina abra aunque no haya internet (PWA) =====
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(function (e) {
    console.log("No se pudo registrar el service worker", e);
  });
}

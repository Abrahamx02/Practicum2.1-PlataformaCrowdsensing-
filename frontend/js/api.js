// Comunicacion con el servidor. Todos los pedidos tienen limite de tiempo.
const BASE = "/api/v1";

export class ErrorApi extends Error {
  constructor(mensaje, estado, codigo) {
    super(mensaje);
    this.estado = estado;     // codigo HTTP (0 = no hubo respuesta)
    this.codigo = codigo;     // codigo de error del servidor, por ejemplo "datos_invalidos"
  }
}

export async function pedir(ruta, opciones = {}, esperaMs = 20000) {
  const control = new AbortController();
  const reloj = setTimeout(() => control.abort(), esperaMs);
  let respuesta;
  try {
    respuesta = await fetch(BASE + ruta, { ...opciones, signal: control.signal });
  } catch (e) {
    const agotado = e && e.name === "AbortError";
    throw new ErrorApi(agotado ? "El servidor tardó demasiado en responder" : "No hay conexión con el servidor", 0, agotado ? "tiempo_agotado" : "sin_conexion");
  } finally {
    clearTimeout(reloj);
  }
  let cuerpo = null;
  try {
    cuerpo = await respuesta.json();
  } catch (e) {
    cuerpo = null;
  }
  if (!respuesta.ok) {
    const error = cuerpo && cuerpo.error ? cuerpo.error : {};
    throw new ErrorApi(error.mensaje || "Error del servidor (" + respuesta.status + ")", respuesta.status, error.codigo || "error");
  }
  return cuerpo;
}

export function obtenerConfiguracion() {
  return pedir("/configuracion", {}, 8000);
}

export function enviarReporte(datos, clave) {
  return pedir("/reportes", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-clave": clave },
    body: JSON.stringify(datos),
  }, 45000);     // 45 s: el servidor gratuito puede tardar en despertar
}

export function buscarSimilares(lat, lon, categoria, clave) {
  const parametros = new URLSearchParams({ lat: String(lat), lon: String(lon), categoria });
  return pedir("/reportes/similares?" + parametros.toString(), { headers: { "x-clave": clave } }, 6000);
}

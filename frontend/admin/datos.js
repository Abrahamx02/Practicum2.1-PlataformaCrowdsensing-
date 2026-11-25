// Datos del panel: una sola copia en memoria que comparten todas las vistas. Se refresca sola cada 30 segundos.
import { ErrorApi, pedir } from "../js/api.js";

export const estado = { sesion: "", config: null, reportes: [], stats: null, gente: [], capacidad: null, actualizado: 0 };
const oyentes = [];
export const alCambiar = (fn) => oyentes.push(fn);

export function api(ruta, opciones = {}, espera = 30000) {
  return pedir(ruta, { ...opciones, headers: { ...(opciones.headers || {}), "x-sesion": estado.sesion } }, espera);
}

async function traerReportes() {
  const todos = [];
  let despues = 0;
  for (let i = 0; i < 20; i++) {            // 20 paginas de 5000 = 100 000 reportes como maximo en pantalla
    const pagina = await api("/reportes?limite=5000&despues_de_id=" + despues);
    todos.push(...pagina.datos);
    if (pagina.siguiente === null) break;
    despues = pagina.siguiente;
  }
  return todos;
}

export async function cargarTodo() {
  const [stats, reportes, gente, capacidad, config] = await Promise.all([
    api("/estadisticas"), traerReportes(), api("/participantes"), api("/capacidad"), estado.config ? estado.config : pedir("/configuracion")]);
  Object.assign(estado, { stats, reportes, gente, capacidad, config, actualizado: Date.now() });
  oyentes.forEach((fn) => fn());
}

// las fotos piden la clave, por eso se bajan con fetch y se muestran como "blob" (un <img src> no puede enviar la clave)
const fotos = new Map();
export async function urlDeFoto(id) {
  if (!fotos.has(id)) {
    const r = await fetch("/api/v1/fotos/" + id, { headers: { "x-sesion": estado.sesion } });
    if (!r.ok) throw new ErrorApi("No se pudo abrir la foto", r.status, "foto");
    fotos.set(id, URL.createObjectURL(await r.blob()));
  }
  return fotos.get(id);
}
export function olvidarFoto(id) { URL.revokeObjectURL(fotos.get(id)); fotos.delete(id); }

export async function bajar(ruta, nombre) {
  const r = await fetch("/api/v1" + ruta, { headers: { "x-sesion": estado.sesion } });
  if (!r.ok) throw new Error("No se pudo descargar (" + r.status + ")");
  const enlace = document.createElement("a");
  enlace.href = URL.createObjectURL(await r.blob());
  const extension = ruta.includes(".zip") ? "" : ruta.includes(".csv") ? ".csv" : ".geojson";
  enlace.download = nombre + "_" + new Date().toISOString().slice(0, 10) + extension;
  enlace.click();
  URL.revokeObjectURL(enlace.href);
}

// Cola de reportes pendientes (cuando no hay internet). Se guardan en el celular y se envian despues.
import { leerJson, guardarJson } from "./utilidades.js";

const CLAVE = "mcs.pendientes.v3";

export function leerPendientes() {
  const lista = leerJson(CLAVE, []);
  return Array.isArray(lista) ? lista : [];
}

export function agregarPendiente(datos) {
  const lista = leerPendientes();
  lista.push(datos);
  return guardarJson(CLAVE, lista);
}

// Intenta enviar todos. "enviar" es una funcion que recibe un reporte y lanza ErrorApi si falla.
// Reglas: sin conexion o error del servidor (5xx) -> se conserva y se detiene;
//         clave vencida (401/429) -> se conserva y se detiene; rechazo de datos (otros 4xx) -> se descarta.
export async function enviarPendientes(enviar) {
  const lista = leerPendientes();
  const quedan = [];
  let enviados = 0;
  let descartados = 0;
  for (let i = 0; i < lista.length; i++) {
    try {
      await enviar(lista[i]);
      enviados++;
    } catch (error) {
      const estado = error && typeof error.estado === "number" ? error.estado : 0;
      if (estado === 0 || estado >= 500 || estado === 401 || estado === 429) {
        quedan.push(...lista.slice(i));
        break;
      }
      descartados++;
    }
  }
  guardarJson(CLAVE, quedan);
  return { enviados, descartados, quedan: quedan.length };
}

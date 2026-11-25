// Pruebas del JavaScript del formulario. Se ejecutan con:  node --test pruebas_frontend
import test from "node:test";
import assert from "node:assert/strict";

import { crearCodigoParticipante, crearUuid, dentroDeZona, detectarPlataforma, formatearBytes, guardarJson,
         leerJson, nivelDePrecision } from "../frontend/js/utilidades.js";
import { ErrorApi, buscarSimilares, enviarReporte, obtenerConfiguracion } from "../frontend/js/api.js";
import { agregarPendiente, enviarPendientes, leerPendientes } from "../frontend/js/cola.js";
import { ErrorUbicacion, obtenerMejorUbicacion } from "../frontend/js/ubicacion.js";

function almacenFalso() {
  const datos = {};
  globalThis.localStorage = { getItem: (k) => (k in datos ? datos[k] : null), setItem: (k, v) => { datos[k] = String(v); }, removeItem: (k) => { delete datos[k]; } };
  return datos;
}

test("el UUID tiene el formato correcto y no se repite", () => {
  const a = crearUuid();
  assert.match(a, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.notEqual(a, crearUuid());
});

test("el codigo de participante cumple lo que exige el servidor", () => {
  for (let i = 0; i < 200; i++) assert.match(crearCodigoParticipante(), /^[A-Za-z0-9_-]{3,40}$/);
});

test("deteccion de plataforma", () => {
  assert.equal(detectarPlataforma("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"), "ios");
  assert.equal(detectarPlataforma("Mozilla/5.0 (Linux; Android 14; Pixel 8)"), "android");
  assert.equal(detectarPlataforma("Mozilla/5.0 (Windows NT 10.0)"), "otro");
});

test("zona y niveles de precision", () => {
  const zona = { lat_min: -4.01, lat_max: -3.975, lon_min: -79.22, lon_max: -79.185 };
  assert.equal(dentroDeZona(-3.99, -79.2, zona), true);
  assert.equal(dentroDeZona(-3.5, -79.2, zona), false);
  const captura = { precision_objetivo_m: 20, precision_aceptable_m: 50 };
  assert.equal(nivelDePrecision(10, captura).nivel, "excelente");
  assert.equal(nivelDePrecision(35, captura).nivel, "aceptable");
  assert.equal(nivelDePrecision(80, captura).nivel, "baja");
  assert.equal(formatearBytes(500), "500 B");
  assert.equal(formatearBytes(2048), "2 KB");
});

test("leerJson y guardarJson no fallan aunque el almacenamiento falle", () => {
  almacenFalso();
  assert.equal(guardarJson("a", { x: 1 }), true);
  assert.deepEqual(leerJson("a", null), { x: 1 });
  globalThis.localStorage = { getItem() { throw new Error("modo privado"); }, setItem() { throw new Error("lleno"); } };
  assert.equal(guardarJson("a", 1), false);
  assert.equal(leerJson("a", "porDefecto"), "porDefecto");
});

test("la API devuelve el mensaje del servidor en los errores", async () => {
  globalThis.fetch = async () => ({ ok: false, status: 422, json: async () => ({ error: { codigo: "datos_invalidos", mensaje: "Hay datos incorrectos" } }) });
  await assert.rejects(() => enviarReporte({}, "k"), (e) => e instanceof ErrorApi && e.estado === 422 && e.codigo === "datos_invalidos" && e.message === "Hay datos incorrectos");
});

test("la API distingue 'sin conexion' de un error del servidor", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(() => obtenerConfiguracion(), (e) => e.estado === 0 && e.codigo === "sin_conexion");
  globalThis.fetch = async () => ({ ok: false, status: 502, json: async () => { throw new Error("no es json"); } });
  await assert.rejects(() => buscarSimilares(1, 2, "bache", "k"), (e) => e.estado === 502);
});

test("la API envia la clave y el cuerpo correctos", async () => {
  let visto = null;
  globalThis.fetch = async (url, op) => { visto = { url, op }; return { ok: true, status: 201, json: async () => ({ id: 7, estado: "creado" }) }; };
  const r = await enviarReporte({ categoria: "bache" }, "mi-clave");
  assert.equal(r.id, 7);
  assert.equal(visto.url, "/api/v1/reportes");
  assert.equal(visto.op.headers["x-clave"], "mi-clave");
  assert.deepEqual(JSON.parse(visto.op.body), { categoria: "bache" });
});

test("la cola envia en orden y descarta solo lo que el servidor rechaza", async () => {
  almacenFalso();
  for (const n of [1, 2, 3, 4]) agregarPendiente({ n });
  const respuestas = { 1: null, 2: new ErrorApi("datos malos", 422, "datos_invalidos"), 3: null, 4: null };
  const enviados = [];
  const r = await enviarPendientes(async (d) => { if (respuestas[d.n]) throw respuestas[d.n]; enviados.push(d.n); });
  assert.deepEqual(enviados, [1, 3, 4]);
  assert.deepEqual(r, { enviados: 3, descartados: 1, quedan: 0 });
  assert.equal(leerPendientes().length, 0);
});

test("la cola se detiene y conserva todo lo que sigue cuando no hay red", async () => {
  almacenFalso();
  for (const n of [1, 2, 3]) agregarPendiente({ n });
  const r = await enviarPendientes(async (d) => { if (d.n === 2) throw new ErrorApi("sin red", 0, "sin_conexion"); });
  assert.deepEqual(r, { enviados: 1, descartados: 0, quedan: 2 });
  assert.deepEqual(leerPendientes().map((x) => x.n), [2, 3]);
});

test("la cola conserva los reportes si la clave vencio (401) o hay demasiados pedidos (429)", async () => {
  almacenFalso();
  agregarPendiente({ n: 1 });
  let r = await enviarPendientes(async () => { throw new ErrorApi("clave", 401, "no_autorizado"); });
  assert.equal(r.quedan, 1);
  r = await enviarPendientes(async () => { throw new ErrorApi("lento", 429, "demasiadas_solicitudes"); });
  assert.equal(r.quedan, 1);
  r = await enviarPendientes(async () => { /* ahora si */ });
  assert.deepEqual(r, { enviados: 1, descartados: 0, quedan: 0 });
});

function geolocalizacionFalsa(eventos) {
  const llamadas = { limpiadas: 0 };
  return {
    llamadas,
    watchPosition(ok, error) { setTimeout(() => eventos.forEach((e) => (e.error ? error(e.error) : ok(e))), 0); return 1; },
    clearWatch() { llamadas.limpiadas++; },
  };
}
const punto = (precision, t = 1000) => ({ coords: { latitude: -3.99, longitude: -79.2, accuracy: precision }, timestamp: t });

test("la ubicacion se detiene apenas llega a la precision objetivo", async () => {
  const geo = geolocalizacionFalsa([punto(60), punto(30), punto(15), punto(5)]);
  const r = await obtenerMejorUbicacion({ objetivoM: 20, esperaMs: 2000, geolocation: geo });
  assert.equal(r.precision, 15);
  assert.equal(geo.llamadas.limpiadas, 1);
});

test("si no llega al objetivo, devuelve el mejor punto al terminar el tiempo", async () => {
  const geo = geolocalizacionFalsa([punto(90), punto(70), punto(80)]);
  const r = await obtenerMejorUbicacion({ objetivoM: 20, esperaMs: 60, geolocation: geo });
  assert.equal(r.precision, 70);
});

test("permiso denegado y falta de senal dan errores distintos", async () => {
  await assert.rejects(() => obtenerMejorUbicacion({ objetivoM: 20, esperaMs: 500, geolocation: geolocalizacionFalsa([{ error: { code: 1 } }]) }),
    (e) => e instanceof ErrorUbicacion && e.codigo === "denegado");
  await assert.rejects(() => obtenerMejorUbicacion({ objetivoM: 20, esperaMs: 40, geolocation: geolocalizacionFalsa([]) }),
    (e) => e.codigo === "sin_senal");
  await assert.rejects(() => obtenerMejorUbicacion({ objetivoM: 20, esperaMs: 40, geolocation: null }),
    (e) => e.codigo === "sin_soporte" || e.codigo === "sin_soporte");
});

import { errorDeContenido } from "../frontend/js/utilidades.js";
test("\"Otro\" sin texto ni foto da error; con una de las dos, no", () => {
  assert.notEqual(errorDeContenido("otro", "", false, 8), "");
  assert.notEqual(errorDeContenido("otro", "hola", false, 8), "");
  assert.equal(errorDeContenido("otro", "tapa de alcantarilla rota", false, 8), "");
  assert.equal(errorDeContenido("otro", "", true, 8), "");
  assert.equal(errorDeContenido("bache", "", false, 8), "");
});

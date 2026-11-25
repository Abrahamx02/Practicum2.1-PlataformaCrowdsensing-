// Service worker: guarda la pagina en el celular para que abra aunque no haya internet.
// Con internet siempre trae la version nueva; sin internet usa la guardada.
// IMPORTANTE: al cambiar archivos del formulario, subir el numero de NOMBRE_CACHE.
const NOMBRE_CACHE = "mcs-v5-0";
const ARCHIVOS = ["/", "/index.html", "/css/estilo.css", "/iconos.svg", "/logo-marca.svg", "/fuentes/inter-latin-opsz-normal.woff2", "/icono-maskable-512.png", "/js/main.js", "/js/api.js", "/js/cola.js", "/js/foto.js",
                  "/js/ubicacion.js", "/js/utilidades.js", "/js/tema.js", "/js/interfaz.js", "/js/geomapa.js", "/js/minimapa.js", "/js/participante.js", "/manifest.json", "/icono-192.png", "/icono-512.png"];

self.addEventListener("install", function (evento) {
  evento.waitUntil(caches.open(NOMBRE_CACHE).then(function (cache) { return cache.addAll(ARCHIVOS); }));
  self.skipWaiting();
});

self.addEventListener("activate", function (evento) {
  evento.waitUntil(caches.keys().then(function (nombres) {
    return Promise.all(nombres.filter(function (n) { return n !== NOMBRE_CACHE; }).map(function (n) { return caches.delete(n); }));
  }));
  self.clients.claim();
});

self.addEventListener("fetch", function (evento) {
  if (evento.request.method !== "GET") return;
  const url = new URL(evento.request.url);
  // solo los archivos del formulario; la API y el panel de administracion nunca se guardan
  if (url.origin !== location.origin || !ARCHIVOS.includes(url.pathname)) return;
  evento.respondWith(
    fetch(evento.request).then(function (respuesta) {
      const copia = respuesta.clone();
      caches.open(NOMBRE_CACHE).then(function (cache) { cache.put(evento.request, copia); });
      return respuesta;
    }).catch(function () { return caches.match(evento.request); })
  );
});

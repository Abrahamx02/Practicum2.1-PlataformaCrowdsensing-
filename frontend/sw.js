// Service worker: guarda la pagina en el celular para que abra aunque no haya internet.
// Con internet siempre trae la version nueva; sin internet usa la guardada.
const NOMBRE_CACHE = "mcs-v2";
const ARCHIVOS = ["/", "/index.html", "/estilo.css", "/app.js", "/manifest.json"];

self.addEventListener("install", function (evento) {
  evento.waitUntil(caches.open(NOMBRE_CACHE).then(function (cache) {
    return cache.addAll(ARCHIVOS);
  }));
  self.skipWaiting();
});

self.addEventListener("activate", function (evento) {
  evento.waitUntil(caches.keys().then(function (nombres) {
    return Promise.all(nombres.filter(function (n) { return n !== NOMBRE_CACHE; })
      .map(function (n) { return caches.delete(n); }));
  }));
  self.clients.claim();
});

self.addEventListener("fetch", function (evento) {
  if (evento.request.method !== "GET") {
    return;
  }
  const url = new URL(evento.request.url);
  if (url.origin !== location.origin || !ARCHIVOS.includes(url.pathname)) {
    return;
  }
  evento.respondWith(
    fetch(evento.request).then(function (respuesta) {
      const copia = respuesta.clone();
      caches.open(NOMBRE_CACHE).then(function (cache) { cache.put(evento.request, copia); });
      return respuesta;
    }).catch(function () {
      return caches.match(evento.request);
    })
  );
});

// Matematica y mosaicos del mapa (la usan el mapa del panel y el mini mapa del formulario). Sin librerias externas.
export const TILE = 256;

// longitud/latitud <-> pixeles del "mapa del mundo" a un nivel de zoom (proyeccion Web Mercator, la de todos los mapas web)
export function aMundo(lon, lat, z) {
  const s = TILE * 2 ** z, seno = Math.sin(lat * Math.PI / 180);
  return [(lon + 180) / 360 * s, (0.5 - Math.log((1 + seno) / (1 - seno)) / (4 * Math.PI)) * s];
}
export function aGeo(x, y, z) {
  const s = TILE * 2 ** z;
  return [x / s * 360 - 180, 180 / Math.PI * Math.atan(Math.sinh(Math.PI - 2 * Math.PI * y / s))];
}
// metros por pixel en una latitud y un zoom (para dibujar el circulo de precision)
export const metrosPorPixel = (lat, z) => 156543.03392 * Math.cos(lat * Math.PI / 180) / 2 ** z;

export const temaMapa = () => (document.documentElement.dataset.tema === "oscuro" ? "dark" : "light");

export function crearMosaico(tx, ty, z) {
  const n = 2 ** z, x = ((tx % n) + n) % n;
  const img = document.createElement("img");
  img.className = "mosaico";
  img.alt = "";
  img.width = img.height = TILE;
  img.draggable = false;
  img.decoding = "async";
  img.setAttribute("referrerpolicy", "origin");      // los mosaicos piden saber de que sitio vienen
  img.addEventListener("load", () => img.classList.add("listo"));
  img.src = "https://" + "abcd"[(tx + ty) & 3] + ".basemaps.cartocdn.com/" + temaMapa() + "_all/" + z + "/" + x + "/" + ty + (window.devicePixelRatio > 1 ? "@2x" : "") + ".png";
  return img;
}

// pone en `capa` los mosaicos que cubren una vista de w x h centrada en (lon, lat); reusa los que ya estan
export function dibujarMosaicos(capa, mosaicos, vista) {
  const [cx, cy] = aMundo(vista.lon, vista.lat, vista.z), ox = cx - vista.w / 2, oy = cy - vista.h / 2, n = 2 ** vista.z;
  const necesarios = new Set();
  for (let tx = Math.floor(ox / TILE); tx <= Math.floor((ox + vista.w) / TILE); tx++) {
    for (let ty = Math.floor(oy / TILE); ty <= Math.floor((oy + vista.h) / TILE); ty++) {
      if (ty < 0 || ty >= n) continue;
      const clave = vista.z + "/" + tx + "/" + ty;
      necesarios.add(clave);
      let img = mosaicos.get(clave);
      if (!img) { img = crearMosaico(tx, ty, vista.z); mosaicos.set(clave, img); capa.append(img); }
      img.style.transform = "translate(" + Math.round(tx * TILE - ox) + "px," + Math.round(ty * TILE - oy) + "px)";
    }
  }
  for (const [clave, img] of mosaicos) if (!necesarios.has(clave)) { img.remove(); mosaicos.delete(clave); }
  return [ox, oy];
}

export function limpiarMosaicos(mosaicos) {
  mosaicos.forEach((m) => m.remove());
  mosaicos.clear();
}

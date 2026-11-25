// Obtiene la mejor ubicacion posible: sigue el GPS unos segundos, se queda con la lectura mas precisa y, si hay varias buenas
// y cercanas entre si, promedia sus coordenadas (las lecturas mas precisas pesan mas). La precision que se informa NO se
// "mejora" por el promedio: se informa la de la mejor lectura, para no prometer mas de lo que hay.
export class ErrorUbicacion extends Error {
  constructor(mensaje, codigo) {
    super(mensaje);
    this.codigo = codigo;   // "denegado", "no_disponible", "sin_senal" o "sin_soporte"
  }
}

// opciones: { objetivoM, esperaMs, alProgreso(mejor), geolocation }
export function obtenerMejorUbicacion(opciones) {
  const geo = opciones.geolocation || (globalThis.navigator && globalThis.navigator.geolocation);
  return new Promise((resolver, rechazar) => {
    if (!geo) {
      rechazar(new ErrorUbicacion("Este navegador no permite obtener la ubicación", "sin_soporte"));
      return;
    }
    let mejor = null;
    const lecturas = [];
    let terminado = false;
    let idVigilancia = null;
    let reloj = null;

    function terminar(accion) {
      if (terminado) return;
      terminado = true;
      clearTimeout(reloj);
      if (idVigilancia !== null) geo.clearWatch(idVigilancia);
      if (mejor) Object.assign(mejor, promediar(lecturas, mejor));
      accion();
    }

    reloj = setTimeout(() => {
      if (mejor) {
        terminar(() => resolver(mejor));
      } else {
        terminar(() => rechazar(new ErrorUbicacion("No se pudo obtener la ubicación a tiempo", "sin_senal")));
      }
    }, opciones.esperaMs);

    idVigilancia = geo.watchPosition(
      (posicion) => {
        const punto = {
          lat: posicion.coords.latitude,
          lon: posicion.coords.longitude,
          precision: posicion.coords.accuracy,
          marca_de_tiempo: posicion.timestamp,
          velocidad: Number.isFinite(posicion.coords.speed) ? posicion.coords.speed : null,    // m/s, si el celular la da
          lecturas: 1,
        };
        lecturas.push(punto);
        if (mejor === null || punto.precision < mejor.precision) mejor = punto;
        if (opciones.alProgreso) opciones.alProgreso(mejor);
        if (mejor.precision <= opciones.objetivoM) terminar(() => resolver(mejor));
      },
      (error) => {
        if (error.code === 1) {
          terminar(() => rechazar(new ErrorUbicacion("Permiso de ubicación denegado", "denegado")));
        } else if (mejor === null && error.code === 2) {
          terminar(() => rechazar(new ErrorUbicacion("Ubicación no disponible", "no_disponible")));
        }
        // si ya hay un fix y llega un error pasajero, se sigue esperando
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: opciones.esperaMs }
    );
  });
}

function metros(a, b) {
  const k = 111320;
  return Math.hypot((a.lat - b.lat) * k, (a.lon - b.lon) * k * Math.cos(a.lat * Math.PI / 180));
}

// promedio ponderado (peso = 1 / precision^2) de las lecturas parecidas a la mejor; con menos de 3 no se promedia
export function promediar(lecturas, mejor) {
  const buenas = lecturas.filter((l) => l.precision <= mejor.precision * 2 && metros(l, mejor) <= Math.max(mejor.precision * 2, 10));
  if (buenas.length < 3) return { lecturas: buenas.length || 1 };
  let peso = 0, lat = 0, lon = 0;
  for (const l of buenas) { const w = 1 / (l.precision * l.precision); peso += w; lat += l.lat * w; lon += l.lon * w; }
  return { lat: lat / peso, lon: lon / peso, lecturas: buenas.length };
}

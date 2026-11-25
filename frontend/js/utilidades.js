// Funciones pequenas y sin dependencias (se pueden probar con node)

export function crearUuid() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  // respaldo para navegadores viejos: UUID version 4 con numeros aleatorios
  const bytes = new Uint8Array(16);
  if (globalThis.crypto && globalThis.crypto.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return hex.slice(0, 8) + "-" + hex.slice(8, 12) + "-" + hex.slice(12, 16) + "-" + hex.slice(16, 20) + "-" + hex.slice(20);
}

export function crearCodigoParticipante() {
  const letras = "abcdefghijkmnpqrstuvwxyz23456789";
  let codigo = "p-";
  const bytes = new Uint8Array(10);
  if (globalThis.crypto && globalThis.crypto.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 10; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  for (const b of bytes) codigo += letras[b % letras.length];
  return codigo;
}

export function detectarPlataforma(userAgent) {
  if (/iPhone|iPad|iPod/i.test(userAgent)) return "ios";
  if (/Android/i.test(userAgent)) return "android";
  return "otro";
}

export function dentroDeZona(lat, lon, zona) {
  return lat >= zona.lat_min && lat <= zona.lat_max && lon >= zona.lon_min && lon <= zona.lon_max;
}

// Devuelve el nivel de precision segun los umbrales de la configuracion
export function nivelDePrecision(metros, captura) {
  if (metros <= captura.precision_objetivo_m) return { nivel: "excelente", texto: "Excelente" };
  if (metros <= captura.precision_aceptable_m) return { nivel: "aceptable", texto: "Aceptable" };
  return { nivel: "baja", texto: "Baja" };
}

export function formatearBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// localStorage puede fallar (modo privado de Safari, almacenamiento lleno): siempre con try/catch
export function leerJson(clave, porDefecto) {
  try {
    const texto = globalThis.localStorage.getItem(clave);
    return texto === null ? porDefecto : JSON.parse(texto);
  } catch (e) {
    return porDefecto;
  }
}

export function guardarJson(clave, valor) {
  try {
    globalThis.localStorage.setItem(clave, JSON.stringify(valor));
    return true;
  } catch (e) {
    return false;
  }
}

// "Otro" no dice nada si no trae texto ni foto: devuelve el mensaje de error, o "" si esta bien
export function errorDeContenido(categoria, descripcion, hayFoto, minimo) {
  if (categoria !== "otro" || hayFoto || (descripcion || "").trim().length >= minimo) return "";
  return "En «Otro» cuéntanos qué pasa (mínimo " + minimo + " letras) o agrega una foto.";
}

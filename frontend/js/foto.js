// Reduce la foto antes de enviarla: menos peso, y de paso se borran los datos EXIF (como el GPS de la foto).
export async function reducirFoto(archivo, maximoLado, calidad) {
  if (!archivo.type.startsWith("image/")) throw new Error("El archivo debe ser una imagen");

  let imagen;
  if (typeof createImageBitmap === "function") {
    imagen = await createImageBitmap(archivo, { imageOrientation: "from-image" });
  } else {
    imagen = await new Promise((resolver, rechazar) => {
      const url = URL.createObjectURL(archivo);
      const elemento = new Image();
      elemento.onload = () => { URL.revokeObjectURL(url); resolver(elemento); };
      elemento.onerror = () => rechazar(new Error("No se pudo leer la imagen"));
      elemento.src = url;
    });
  }

  let ancho = imagen.width;
  let alto = imagen.height;
  const mayor = Math.max(ancho, alto);
  if (mayor > maximoLado) {
    ancho = Math.round(ancho * maximoLado / mayor);
    alto = Math.round(alto * maximoLado / mayor);
  }
  const lienzo = document.createElement("canvas");
  lienzo.width = ancho;
  lienzo.height = alto;
  lienzo.getContext("2d").drawImage(imagen, 0, 0, ancho, alto);
  if (imagen.close) imagen.close();

  const blob = await new Promise((resolver, rechazar) =>
    lienzo.toBlob((b) => (b ? resolver(b) : rechazar(new Error("No se pudo comprimir la imagen"))), "image/jpeg", calidad));
  const base64 = await new Promise((resolver, rechazar) => {
    const lector = new FileReader();
    lector.onload = () => resolver(String(lector.result).split(",")[1]);
    lector.onerror = () => rechazar(new Error("No se pudo leer la imagen"));
    lector.readAsDataURL(blob);
  });
  return { base64, bytes: blob.size, urlVistaPrevia: URL.createObjectURL(blob) };
}

# Descarga una version del dataset (CSV y GeoJSON) con la fecha en el nombre y un manifiesto con huellas.
# Uso:  python analisis/exportar_version.py
import os
import hashlib
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("API_URL", "http://127.0.0.1:8000")
clave = os.getenv("CLAVE_LECTURA") or os.getenv("CLAVE_ADMIN")
carpeta = "analisis/datos/exportaciones"
os.makedirs(carpeta, exist_ok=True)
hoy = str(date.today())

archivos = [("/exportar.csv", "reportes_" + hoy + ".csv"),
            ("/exportar.geojson", "reportes_" + hoy + ".geojson")]

lineas = []
for ruta, nombre in archivos:
    r = requests.get(url + ruta, headers={"x-clave": clave}, timeout=120)
    r.raise_for_status()
    with open(os.path.join(carpeta, nombre), "wb") as f:
        f.write(r.content)
    huella = hashlib.sha256(r.content).hexdigest()
    lineas.append(nombre + "," + str(len(r.content)) + "," + huella + "," + hoy)
    print("Guardado", nombre, len(r.content), "bytes")

manifiesto = os.path.join(carpeta, "manifiesto.csv")
nuevo = not os.path.exists(manifiesto)
with open(manifiesto, "a", encoding="utf-8") as f:
    if nuevo:
        f.write("archivo,bytes,sha256,fecha\n")
    for linea in lineas:
        f.write(linea + "\n")

# Descarga todas las fotos a una carpeta para revisarlas a mano (rostros, placas, datos personales).
# Las que no sirvan se borran con DELETE /fotos/ID (en /docs, con la clave de administrador).
# Uso:  python analisis/revisar_fotos.py
import os

import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("API_URL", "http://127.0.0.1:8000")
clave = os.getenv("CLAVE_ADMIN")
carpeta = "analisis/datos/fotos_para_revisar"
os.makedirs(carpeta, exist_ok=True)

lista = requests.get(url + "/fotos", headers={"x-clave": clave}, timeout=60).json()
print("Fotos en la base:", len(lista))
for foto in lista:
    r = requests.get(url + "/fotos/" + str(foto["id"]), headers={"x-clave": clave}, timeout=60)
    ruta = os.path.join(carpeta, "foto_" + str(foto["id"]) + ".jpg")
    with open(ruta, "wb") as f:
        f.write(r.content)
print("Revisa la carpeta", carpeta, "y borra de la base las que se vean personas o placas.")

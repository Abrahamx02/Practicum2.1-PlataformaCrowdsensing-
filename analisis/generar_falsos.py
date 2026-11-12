# Genera un CSV de 50 reportes falsos para practicar (con errores a proposito)
# Uso:  python analisis/generar_falsos.py
import random
from datetime import datetime, timedelta, timezone

import pandas as pd

random.seed(1)

categorias = ["bache", "luminaria_danada", "basura", "otro"]
plataformas = ["ios", "android"]
base = datetime(2026, 12, 14, 14, 0, tzinfo=timezone.utc)

filas = []
for i in range(1, 51):
    fecha = base + timedelta(minutes=random.randint(0, 60 * 24 * 3))
    fila = {
        "id": i,
        "recibido_en": fecha + timedelta(seconds=random.randint(1, 30)),
        "participante_id": "p-" + str(random.randint(1, 12)),
        "categoria": random.choice(categorias),
        "descripcion": "reporte de prueba numero " + str(i),
        "lat": round(random.uniform(-4.005, -3.980), 6),
        "lon": round(random.uniform(-79.215, -79.190), 6),
        "precision_m": round(random.uniform(3, 30), 1),
        "fecha_dispositivo": fecha,
        "plataforma": random.choice(plataformas),
        "navegador": "Prueba",
        "consentimiento": True,
        "foto_id": "",
    }
    filas.append(fila)

# errores puestos a proposito
for i in [3, 9, 17]:
    filas[i]["descripcion"] = ""                       # incompletos
for i in [5, 22, 31]:
    filas[i]["lat"] = -3.5                             # fuera de la zona
for i in [12, 40]:
    filas[i]["fecha_dispositivo"] = filas[i]["recibido_en"] + timedelta(days=3)   # fecha futura
for i in [7, 14, 27, 33]:
    filas[i]["precision_m"] = round(random.uniform(80, 300), 1)   # baja precision
for i in [20, 25, 36, 44, 48]:                         # duplicados de otro reporte
    original = filas[i - 1]
    filas[i]["categoria"] = original["categoria"]
    filas[i]["lat"] = original["lat"] + 0.00005
    filas[i]["lon"] = original["lon"]
    filas[i]["fecha_dispositivo"] = original["fecha_dispositivo"] + timedelta(minutes=3)
    filas[i]["recibido_en"] = filas[i]["fecha_dispositivo"] + timedelta(seconds=5)

tabla = pd.DataFrame(filas)
tabla.to_csv("analisis/datos/falsos.csv", index=False)
print("Listo: analisis/datos/falsos.csv con", len(tabla), "filas")

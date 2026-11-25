# Prueba de carga: envia muchos reportes a la vez y mide cuanto tarda el servidor.
# Sirve para descubrir los limites antes del piloto.
# Uso:  python analisis/prueba_carga.py --reportes 200 --hilos 10
# IMPORTANTE: el servidor limita los envios por IP (30 por minuto). Para esta prueba, encenderlo con
#   Windows PowerShell:  $env:LIMITE_REPORTES_POR_MINUTO = "100000"; uvicorn backend.main:app
# y usar siempre una base de DESARROLLO (esta prueba crea reportes con el participante "prueba-carga-N").
import argparse
import os
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--url", default=os.getenv("API_URL", "http://127.0.0.1:8000"))
parser.add_argument("--reportes", type=int, default=200)
parser.add_argument("--hilos", type=int, default=10)
parser.add_argument("--limpiar", action="store_true", help="borra al final los reportes de la prueba (usa CLAVE_ADMIN)")
args = parser.parse_args()

clave = os.getenv("CLAVE_ESCRITURA")
if not clave:
    raise SystemExit("Falta CLAVE_ESCRITURA en el .env")

configuracion = requests.get(args.url + "/api/v1/configuracion", timeout=30).json()
zona = configuracion["zona"]
categorias = [c["id"] for c in configuracion["categorias"]]


def un_envio(numero):
    ahora = datetime.now(timezone.utc) - timedelta(seconds=random.randint(0, 3600))
    datos = {
        "participante_id": "prueba-carga-" + str(numero % 20),
        "categoria": random.choice(categorias),
        "descripcion": "prueba de carga " + str(numero),
        "lat": random.uniform(zona["lat_min"], zona["lat_max"]),
        "lon": random.uniform(zona["lon_min"], zona["lon_max"]),
        "precision_m": random.uniform(4, 60),
        "fecha_dispositivo": ahora.isoformat(),
        "plataforma": random.choice(["ios", "android"]),
        "consentimiento": True,
    }
    inicio = time.perf_counter()
    try:
        r = requests.post(args.url + "/api/v1/reportes", json=datos, headers={"x-clave": clave}, timeout=60)
        estado = r.status_code
    except Exception:
        estado = 0
    return estado, (time.perf_counter() - inicio) * 1000


print("Enviando", args.reportes, "reportes con", args.hilos, "envios simultaneos a", args.url, "...")
inicio_total = time.perf_counter()
with ThreadPoolExecutor(max_workers=args.hilos) as grupo:
    resultados = list(grupo.map(un_envio, range(args.reportes)))
total = time.perf_counter() - inicio_total

tiempos = sorted(t for estado, t in resultados if estado == 201)
estados = {}
for estado, _ in resultados:
    estados[estado] = estados.get(estado, 0) + 1

print("\nTiempo total: %.1f s  (%.1f reportes por segundo)" % (total, args.reportes / total))
print("Respuestas por codigo:", estados)
if tiempos:
    def percentil(p):
        return tiempos[min(len(tiempos) - 1, int(len(tiempos) * p))]
    print("Tiempo por envio (ms): mediana %.0f | p95 %.0f | p99 %.0f | maximo %.0f" % (
        statistics.median(tiempos), percentil(0.95), percentil(0.99), tiempos[-1]))
if estados.get(429):
    print("\nAVISO: hubo respuestas 429 (limite de envios). Para esta prueba enciende el servidor con LIMITE_REPORTES_POR_MINUTO alto.")
if estados.get(0):
    print("AVISO: hubo envios sin respuesta (servidor caido o muy lento).")

for ruta in ("/api/v1/estadisticas",):
    clave_lectura = os.getenv("CLAVE_LECTURA")
    if clave_lectura:
        inicio = time.perf_counter()
        requests.get(args.url + ruta, headers={"x-clave": clave_lectura}, timeout=60)
        print("Estadisticas generales: %.0f ms" % ((time.perf_counter() - inicio) * 1000))
        inicio = time.perf_counter()
        r = requests.get(args.url + "/api/v1/exportar.csv", headers={"x-clave": clave_lectura}, timeout=120)
        print("Exportar todo a CSV: %.0f ms (%.0f KB)" % ((time.perf_counter() - inicio) * 1000, len(r.content) / 1024))

if args.limpiar:
    clave_admin = os.getenv("CLAVE_ADMIN")
    borrados = 0
    for n in range(20):
        r = requests.delete(args.url + "/api/v1/participantes/prueba-carga-" + str(n), headers={"x-clave": clave_admin}, timeout=60)
        if r.status_code == 200:
            borrados += r.json()["reportes_borrados"]
    print("Limpieza: se borraron", borrados, "reportes de prueba")

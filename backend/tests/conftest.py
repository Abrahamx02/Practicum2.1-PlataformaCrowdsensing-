# Preparacion de las pruebas. Necesitan el archivo .env (o variables de entorno) con
# DATABASE_URL, CLAVE_ESCRITURA, CLAVE_LECTURA y CLAVE_ADMIN. Usar SIEMPRE la base de desarrollo.
import os
from datetime import datetime, timezone

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from backend import seguridad
from backend.main import app

E = {"x-clave": os.getenv("CLAVE_ESCRITURA", "")}
L = {"x-clave": os.getenv("CLAVE_LECTURA", "")}
A = {"x-clave": os.getenv("CLAVE_ADMIN", "")}
PREFIJO = "prueba-"


def reporte(**cambios):
    datos = {
        "participante_id": PREFIJO + "auto",
        "categoria": "bache",
        "descripcion": "bache grande en la calle",
        "lat": -3.9931,
        "lon": -79.2042,
        "precision_m": 12.5,
        "fecha_dispositivo": datetime.now(timezone.utc).isoformat(),
        "plataforma": "android",
        "navegador": "Chrome",
        "consentimiento": True,
    }
    datos.update(cambios)
    return datos


def limpiar_base():
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        con.execute("DELETE FROM reportes WHERE participante_id LIKE %s", (PREFIJO + "%",))
        con.execute("DELETE FROM fotos WHERE id NOT IN (SELECT foto_id FROM reportes WHERE foto_id IS NOT NULL)")


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def ordenar():
    # cada prueba empieza sin limites acumulados y deja la base limpia
    seguridad.limite_reportes.registros = {}
    seguridad.limite_fallos.registros = {}
    limpiar_base()
    yield
    limpiar_base()

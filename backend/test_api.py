# Pruebas de la API. Se ejecutan con:  python -m pytest backend -v
# Necesitan el archivo .env con DATABASE_URL y las dos claves.
import os
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from backend.main import app

cliente = TestClient(app)
CLAVE_E = os.getenv("CLAVE_ESCRITURA")
CLAVE_A = os.getenv("CLAVE_ADMIN")
CLAVE_L = os.getenv("CLAVE_LECTURA")
ID_PRUEBA = "prueba-automatica"


def reporte_valido():
    return {
        "participante_id": ID_PRUEBA,
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


def borrar_pruebas():
    with psycopg.connect(os.getenv("DATABASE_URL")) as con:
        con.execute("DELETE FROM reportes WHERE participante_id = %s", (ID_PRUEBA,))


def test_salud():
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_envio_valido():
    r = cliente.post("/reportes", json=reporte_valido(), headers={"x-clave": CLAVE_E})
    assert r.status_code == 201
    assert "id" in r.json()
    borrar_pruebas()


def test_sin_clave():
    r = cliente.post("/reportes", json=reporte_valido())
    assert r.status_code == 401


def test_categoria_invalida():
    datos = reporte_valido()
    datos["categoria"] = "ruido"
    r = cliente.post("/reportes", json=datos, headers={"x-clave": CLAVE_E})
    assert r.status_code == 422


def test_latitud_fuera_de_rango():
    datos = reporte_valido()
    datos["lat"] = 120
    r = cliente.post("/reportes", json=datos, headers={"x-clave": CLAVE_E})
    assert r.status_code == 422


def test_sin_consentimiento():
    datos = reporte_valido()
    datos["consentimiento"] = False
    r = cliente.post("/reportes", json=datos, headers={"x-clave": CLAVE_E})
    assert r.status_code == 400


def test_listar_sin_clave_admin():
    r = cliente.get("/reportes", headers={"x-clave": CLAVE_E})
    assert r.status_code == 401


def test_listar_con_clave_admin():
    cliente.post("/reportes", json=reporte_valido(), headers={"x-clave": CLAVE_E})
    r = cliente.get("/reportes", headers={"x-clave": CLAVE_A})
    assert r.status_code == 200
    assert len(r.json()) >= 1
    borrar_pruebas()


def test_exportar_csv():
    r = cliente.get("/exportar.csv", headers={"x-clave": CLAVE_A})
    assert r.status_code == 200
    assert r.text.startswith("id,recibido_en")


def test_importar_csv():
    texto = "participante_id,categoria,descripcion,lat,lon,fecha_dispositivo,consentimiento\n"
    texto += ID_PRUEBA + ",basura,bolsas,-3.99,-79.20,2026-12-15T10:00:00+00:00,True\n"
    texto += ID_PRUEBA + ",ruido,mala categoria,-3.99,-79.20,2026-12-15T10:00:00+00:00,True\n"
    r = cliente.post("/importar", content=texto, headers={"x-clave": CLAVE_A})
    assert r.status_code == 200
    assert r.json()["importados"] == 1
    assert r.json()["rechazados"] == 1
    borrar_pruebas()


def test_foto_pequena():
    datos = reporte_valido()
    # una imagen diminuta en base64
    datos["foto_base64"] = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBD"
    r = cliente.post("/reportes", json=datos, headers={"x-clave": CLAVE_E})
    assert r.status_code == 201
    borrar_pruebas()


def test_exportar_geojson():
    cliente.post("/reportes", json=reporte_valido(), headers={"x-clave": CLAVE_E})
    r = cliente.get("/exportar.geojson", headers={"x-clave": CLAVE_A})
    assert r.status_code == 200
    assert r.json()["type"] == "FeatureCollection"
    punto = r.json()["features"][-1]["geometry"]["coordinates"]
    assert punto == [-79.2042, -3.9931]    # primero longitud, luego latitud
    borrar_pruebas()


def test_guardar_calidad():
    nuevo = cliente.post("/reportes", json=reporte_valido(), headers={"x-clave": CLAVE_E}).json()["id"]
    datos = [{"id": nuevo, "puntaje_calidad": 92.5, "estado_calidad": "aceptar"}]
    r = cliente.post("/calidad", json=datos, headers={"x-clave": CLAVE_A})
    assert r.status_code == 200
    assert r.json()["actualizados"] == 1
    borrar_pruebas()


def test_retirar_participante():
    cliente.post("/reportes", json=reporte_valido(), headers={"x-clave": CLAVE_E})
    r = cliente.delete("/participantes/" + ID_PRUEBA, headers={"x-clave": CLAVE_A})
    assert r.status_code == 200
    assert r.json()["reportes_borrados"] == 1
    r = cliente.delete("/participantes/" + ID_PRUEBA, headers={"x-clave": CLAVE_E})
    assert r.status_code == 401


def test_analista_puede_leer_pero_no_importar():
    r = cliente.get("/reportes", headers={"x-clave": CLAVE_L})
    assert r.status_code == 200
    r = cliente.post("/importar", content="a,b\n", headers={"x-clave": CLAVE_L})
    assert r.status_code == 401
    r = cliente.get("/fotos", headers={"x-clave": CLAVE_L})
    assert r.status_code == 401


def test_descartar_foto():
    datos = reporte_valido()
    datos["foto_base64"] = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBD"
    cliente.post("/reportes", json=datos, headers={"x-clave": CLAVE_E})
    lista = cliente.get("/fotos", headers={"x-clave": CLAVE_A}).json()
    assert len(lista) >= 1
    numero = lista[-1]["id"]
    r = cliente.delete("/fotos/" + str(numero), headers={"x-clave": CLAVE_A})
    assert r.status_code == 200
    r = cliente.get("/fotos/" + str(numero), headers={"x-clave": CLAVE_A})
    assert r.status_code == 404
    borrar_pruebas()

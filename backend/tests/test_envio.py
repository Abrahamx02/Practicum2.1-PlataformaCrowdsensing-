import base64
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import os

from backend.tests.conftest import A, E, L, PREFIJO, reporte

JPEG_MINIMO = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 40).decode()


def contar(sql, *valores):
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        return con.execute(sql, valores).fetchone()[0]


def test_envio_valido(cliente):
    r = cliente.post("/api/v1/reportes", json=reporte(), headers=E)
    assert r.status_code == 201
    assert r.json()["estado"] == "creado"


def test_sin_clave_o_con_clave_equivocada(cliente):
    assert cliente.post("/api/v1/reportes", json=reporte()).status_code == 401
    assert cliente.post("/api/v1/reportes", json=reporte(), headers={"x-clave": "otra"}).status_code == 401


def test_sin_consentimiento(cliente):
    r = cliente.post("/api/v1/reportes", json=reporte(consentimiento=False), headers=E)
    assert r.status_code == 400


def test_mismo_reporte_dos_veces_no_se_duplica(cliente):
    datos = reporte(id_cliente=str(uuid4()))
    primero = cliente.post("/api/v1/reportes", json=datos, headers=E)
    segundo = cliente.post("/api/v1/reportes", json=datos, headers=E)
    assert primero.status_code == 201
    assert segundo.status_code == 200
    assert segundo.json()["estado"] == "ya_recibido"
    assert segundo.json()["id"] == primero.json()["id"]
    assert contar("SELECT count(*) FROM reportes WHERE participante_id = %s", PREFIJO + "auto") == 1


def test_envios_simultaneos_con_el_mismo_id_guardan_uno_solo(cliente):
    datos = reporte(id_cliente=str(uuid4()))
    with ThreadPoolExecutor(max_workers=8) as grupo:
        respuestas = list(grupo.map(lambda _: cliente.post("/api/v1/reportes", json=datos, headers=E), range(8)))
    assert sorted(set(r.status_code for r in respuestas)) in ([200, 201], [201])
    assert contar("SELECT count(*) FROM reportes WHERE participante_id = %s", PREFIJO + "auto") == 1


def test_validaciones_con_mensaje_en_espanol(cliente):
    malos = {
        "categoria inexistente": reporte(categoria="ruido"),
        "latitud fuera de rango": reporte(lat=120),
        "longitud fuera de rango": reporte(lon=-300),
        "latitud NaN": reporte(lat="NaN"),
        "precision infinita": reporte(precision_m="Infinity"),
        "precision enorme": reporte(precision_m=1e30),
        "fecha sin zona horaria": reporte(fecha_dispositivo="2026-12-14T10:00:00"),
        "fecha del ano 1900": reporte(fecha_dispositivo="1900-01-01T00:00:00Z"),
        "fecha del ano 3000": reporte(fecha_dispositivo="3000-01-01T00:00:00Z"),
        "participante con simbolos": reporte(participante_id="<script>alert(1)</script>"),
        "participante muy corto": reporte(participante_id="ab"),
        "plataforma desconocida": reporte(plataforma="windows"),
        "navegador demasiado largo": reporte(navegador="a" * 5000),
        "descripcion de 281 letras": reporte(descripcion="a" * 281),
        "version de consentimiento rara": reporte(consentimiento_version="x1"),
        "id_cliente no es uuid": reporte(id_cliente="123"),
    }
    for nombre, datos in malos.items():
        r = cliente.post("/api/v1/reportes", json=datos, headers=E)
        assert r.status_code == 422, nombre
        assert r.json()["error"]["codigo"] == "datos_invalidos", nombre
        assert r.json()["error"]["mensaje"], nombre


def test_caracter_nulo_se_limpia_en_vez_de_romper(cliente):
    r = cliente.post("/api/v1/reportes", json=reporte(descripcion="hola\x00mundo"), headers=E)
    assert r.status_code == 201
    fila = cliente.get("/api/v1/reportes/" + str(r.json()["id"]), headers=L).json()
    assert fila["descripcion"] == "holamundo"


def test_fotos(cliente):
    assert cliente.post("/api/v1/reportes", json=reporte(foto_base64="%%no-es-base64%%"), headers=E).status_code == 400
    texto = base64.b64encode(b"esto no es una foto").decode()
    assert cliente.post("/api/v1/reportes", json=reporte(foto_base64=texto), headers=E).status_code == 400
    grande = base64.b64encode(b"\xff\xd8\xff" + b"0" * 600000).decode()
    assert cliente.post("/api/v1/reportes", json=reporte(foto_base64=grande), headers=E).status_code in (413, 422)
    ok = cliente.post("/api/v1/reportes", json=reporte(foto_base64=JPEG_MINIMO), headers=E)
    assert ok.status_code == 201
    fila = cliente.get("/api/v1/reportes/" + str(ok.json()["id"]), headers=L).json()
    assert fila["foto_id"]
    foto = cliente.get("/api/v1/fotos/" + str(fila["foto_id"]), headers=A)
    assert foto.status_code == 200
    assert foto.headers["content-type"] == "image/jpeg"


def test_limite_de_envios_por_minuto(cliente):
    codigos = [cliente.post("/api/v1/reportes", json=reporte(), headers=E).status_code for _ in range(32)]
    assert codigos.count(201) == 30
    assert codigos[-1] == 429


def test_aviso_de_reporte_similar_cercano(cliente):
    cliente.post("/api/v1/reportes", json=reporte(), headers=E)
    cerca = cliente.get("/api/v1/reportes/similares?lat=-3.99312&lon=-79.2042&categoria=bache", headers=E).json()
    assert cerca["similares"] == 1
    assert cerca["mas_cercano_m"] < 20
    lejos = cliente.get("/api/v1/reportes/similares?lat=-3.9800&lon=-79.2042&categoria=bache", headers=E).json()
    assert lejos["similares"] == 0
    otra_categoria = cliente.get("/api/v1/reportes/similares?lat=-3.9931&lon=-79.2042&categoria=basura", headers=E).json()
    assert otra_categoria["similares"] == 0
    assert cliente.get("/api/v1/reportes/similares?lat=-3.9931&lon=-79.2042", headers=L).status_code == 401

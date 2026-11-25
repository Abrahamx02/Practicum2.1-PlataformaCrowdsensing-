# Estas pruebas convierten las indicaciones del grupo de investigacion (Practicum_MCS_Indicaciones.pptx)
# en comprobaciones automaticas. Si una falla, el proyecto dejo de cumplir algo que piden.
import json
import os

import psycopg

from backend.config import CONFIG, RAIZ
from backend.tests.conftest import A, E, L, PREFIJO, reporte


def columnas_de_reportes():
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        filas = con.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'reportes'").fetchall()
    return {f[0] for f in filas}


def existe(*partes):
    return os.path.exists(os.path.join(RAIZ, *partes))


def test_contrato_de_datos_minimo():
    # identificador unico, participante seudonimizado, categoria, descripcion, fecha de captura y de recepcion,
    # ubicacion, precision, foto opcional, consentimiento y su version, plataforma, estado y puntaje de calidad
    esperadas = {"id", "participante_id", "categoria", "descripcion", "fecha_dispositivo", "recibido_en", "lat", "lon",
                 "ubicacion", "precision_m", "foto_id", "consentimiento", "consentimiento_version", "plataforma",
                 "estado_calidad", "puntaje_calidad"}
    assert esperadas <= columnas_de_reportes()


def test_no_se_guardan_datos_personales():
    prohibidas = {"nombre", "correo", "email", "telefono", "cedula", "direccion_ip", "ip"}
    assert not (prohibidas & columnas_de_reportes())


def test_seis_dimensiones_de_calidad_que_suman_uno():
    pesos = CONFIG["calidad"]["pesos"]
    assert set(pesos) == {"completitud", "validez", "exactitud", "consistencia", "unicidad", "oportunidad"}
    assert abs(sum(pesos.values()) - 1.0) < 1e-9


def test_estados_de_calidad_aceptar_revisar_descartar(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(), headers=E).json()["id"]
    for estado in ("aceptar", "revisar", "descartar"):
        r = cliente.post("/api/v1/calidad", json=[{"id": nuevo, "puntaje_calidad": 60, "estado_calidad": estado}], headers=A)
        assert r.status_code == 200
    assert cliente.post("/api/v1/calidad", json=[{"id": nuevo, "puntaje_calidad": 60, "estado_calidad": "otro"}], headers=A).status_code == 422


def test_exportacion_csv_y_geojson(cliente):
    assert cliente.get("/api/v1/exportar.csv", headers=L).status_code == 200
    assert cliente.get("/api/v1/exportar.geojson", headers=L).json()["type"] == "FeatureCollection"


def test_importacion_de_csv(cliente):
    assert cliente.post("/api/v1/importar", content="participante_id\n", headers=A).status_code == 200


def test_tres_roles_con_claves_distintas():
    claves = {os.environ["CLAVE_ESCRITURA"], os.environ["CLAVE_LECTURA"], os.environ["CLAVE_ADMIN"]}
    assert len(claves) == 3


def test_consentimiento_obligatorio_antes_de_guardar(cliente):
    assert cliente.post("/api/v1/reportes", json=reporte(consentimiento=False), headers=E).status_code == 400
    assert 'id="consentimiento"' in open(os.path.join(RAIZ, "frontend", "index.html"), encoding="utf-8").read()


def test_captura_sin_conexion_pwa():
    assert existe("frontend", "manifest.json") and existe("frontend", "sw.js") and existe("frontend", "js", "cola.js")
    assert "serviceWorker" in open(os.path.join(RAIZ, "frontend", "js", "main.js"), encoding="utf-8").read()


def test_derecho_a_retirarse(cliente):
    cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "retiro2"), headers=E)
    assert cliente.delete("/api/v1/participantes/" + PREFIJO + "retiro2", headers=A).json()["reportes_borrados"] == 1


def test_fotos_se_pueden_revisar_y_descartar(cliente):
    assert cliente.get("/api/v1/fotos", headers=A).status_code == 200
    assert existe("frontend", "admin", "index.html")


def test_metas_del_piloto():
    p = CONFIG["piloto"]
    assert p["meta_observaciones"] >= 300 and p["participantes_min"] == 15 and p["participantes_max"] == 25
    assert p["dias"] == 14 and p["prueba_de_humo"] == 50


def test_categorias_del_proyecto():
    ids = [c["id"] for c in CONFIG["categorias"]]
    assert ids[:3] == ["bache", "luminaria_danada", "basura"] and "otro" in ids


def test_entorno_reproducible_y_pruebas_automaticas():
    assert existe("Dockerfile") and existe("docker-compose.yml")
    assert existe(".github", "workflows", "ci.yml")
    assert existe("pytest.ini")


def test_documentos_entregables_en_el_repositorio():
    for nombre in ("diccionario_datos.md", "ARQUITECTURA.md", "SEGURIDAD.md", "CUMPLIMIENTO_INDICACIONES.md"):
        assert existe("docs", nombre), nombre
    assert existe("CHANGELOG.md") and existe("CONTRIBUTING.md")


def test_especificacion_de_la_api_para_otros_clientes(cliente):
    # la documentacion publica esta apagada; el administrador la ve (y la baja) desde el panel
    assert cliente.get("/openapi.json").status_code == 404 and cliente.get("/docs").status_code == 404
    r = cliente.get("/api/v1/especificacion", headers=A)
    assert r.status_code == 200
    assert "/api/v1/reportes" in r.json()["paths"]

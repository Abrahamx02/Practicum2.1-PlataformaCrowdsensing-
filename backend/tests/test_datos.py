import csv
import io

from backend.tests.conftest import A, E, L, PREFIJO, reporte


def crear(cliente, cuantos, **cambios):
    ids = []
    for i in range(cuantos):
        r = cliente.post("/api/v1/reportes", json=reporte(descripcion="n" + str(i), **cambios), headers=E)
        ids.append(r.json()["id"])
    return ids


def test_paginacion(cliente):
    ids = crear(cliente, 5)
    primera = cliente.get("/api/v1/reportes?limite=2", headers=L).json()
    mios = [d for d in primera["datos"] if d["participante_id"].startswith(PREFIJO)]
    assert primera["cantidad"] == 2
    assert primera["siguiente"] is not None or len(ids) <= 2
    todos = []
    ultimo = 0
    while True:
        pagina = cliente.get("/api/v1/reportes?limite=2&despues_de_id=" + str(ultimo), headers=L).json()
        todos.extend(pagina["datos"])
        if pagina["siguiente"] is None:
            break
        ultimo = pagina["siguiente"]
    mios = [d["id"] for d in todos if d["participante_id"].startswith(PREFIJO)]
    assert sorted(mios) == sorted(ids)


def test_filtros(cliente):
    crear(cliente, 2, categoria="basura", plataforma="ios")
    crear(cliente, 1, categoria="bache", plataforma="android")
    basura = cliente.get("/api/v1/reportes?categoria=basura&plataforma=ios", headers=L).json()["datos"]
    assert len([d for d in basura if d["participante_id"].startswith(PREFIJO)]) == 2
    assert all(d["categoria"] == "basura" for d in basura)
    assert cliente.get("/api/v1/reportes?categoria=ruido", headers=L).status_code == 422
    assert cliente.get("/api/v1/reportes?desde=basura", headers=L).status_code == 422
    assert cliente.get("/api/v1/reportes?limite=999999", headers=L).status_code == 422
    assert cliente.get("/api/v1/reportes?desde=2020-01-01T00:00:00Z&hasta=2100-01-01T00:00:00Z", headers=L).status_code == 200


def test_un_reporte(cliente):
    nuevo = crear(cliente, 1)[0]
    assert cliente.get("/api/v1/reportes/" + str(nuevo), headers=L).json()["id"] == nuevo
    assert cliente.get("/api/v1/reportes/99999999", headers=L).status_code == 404
    assert cliente.get("/api/v1/reportes/abc", headers=L).status_code == 422


def test_estadisticas(cliente):
    crear(cliente, 3, categoria="basura")
    s = cliente.get("/api/v1/estadisticas", headers=L).json()
    assert s["reportes"] >= 3
    assert s["por_categoria"]["basura"] >= 3
    assert s["participantes"] >= 1
    assert sum(s["por_dia"].values()) == s["reportes"]


def test_buscar_cercanos_ordenados_por_distancia(cliente):
    cliente.post("/api/v1/reportes", json=reporte(lat=-3.9931, lon=-79.2042), headers=E)
    cliente.post("/api/v1/reportes", json=reporte(lat=-3.9935, lon=-79.2042), headers=E)
    r = cliente.get("/api/v1/reportes/cercanos?lat=-3.9931&lon=-79.2042&radio_m=200", headers=L).json()
    distancias = [d["distancia_m"] for d in r["datos"] if True]
    assert distancias == sorted(distancias)
    assert r["cantidad"] >= 2
    assert cliente.get("/api/v1/reportes/cercanos?lat=-3.9931&lon=-79.2042&radio_m=0", headers=L).status_code == 422


def test_exportar_csv_protege_contra_formulas(cliente):
    cliente.post("/api/v1/reportes", json=reporte(descripcion="=HYPERLINK(\"http://malo\")"), headers=E)
    r = cliente.get("/api/v1/exportar.csv", headers=L)
    assert r.status_code == 200
    filas = list(csv.DictReader(io.StringIO(r.text)))
    mia = [f for f in filas if f["participante_id"].startswith(PREFIJO)][0]
    assert mia["descripcion"].startswith("'=")
    assert filas[0].keys() >= {"id", "lat", "lon", "puntaje_calidad", "estado_calidad", "consentimiento_version"}


def test_exportar_geojson_longitud_primero(cliente):
    cliente.post("/api/v1/reportes", json=reporte(), headers=E)
    r = cliente.get("/api/v1/exportar.geojson", headers=L).json()
    assert r["type"] == "FeatureCollection"
    mio = [f for f in r["features"] if f["properties"]["participante_id"].startswith(PREFIJO)][0]
    assert mio["geometry"]["coordinates"] == [-79.2042, -3.9931]

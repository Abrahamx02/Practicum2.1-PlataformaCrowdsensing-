# La calidad se calcula dentro del servidor, y el panel puede decidir, recalcular y listar participantes.
import base64
from datetime import datetime, timedelta, timezone

from backend import calidad
from backend.tests.conftest import A, E, L, PREFIJO, reporte

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 40).decode()


def ahora():
    return datetime.now(timezone.utc)


def leer(cliente, id_):
    return cliente.get("/api/v1/reportes/" + str(id_), headers=L).json()


def test_otro_sin_descripcion_ni_foto_se_rechaza(cliente):
    r = cliente.post("/api/v1/reportes", json=reporte(categoria="otro", descripcion=""), headers=E)
    assert r.status_code == 422 and "Otro" in r.json()["error"]["mensaje"]
    corto = cliente.post("/api/v1/reportes", json=reporte(categoria="otro", descripcion="hola"), headers=E)
    assert corto.status_code == 422


def test_otro_con_descripcion_o_con_foto_se_acepta(cliente):
    con_texto = cliente.post("/api/v1/reportes", json=reporte(categoria="otro", descripcion="tapa de alcantarilla rota"), headers=E)
    con_foto = cliente.post("/api/v1/reportes", json=reporte(categoria="otro", descripcion="", lat=-3.9932, foto_base64=JPEG), headers=E)
    assert con_texto.status_code == 201 and con_foto.status_code == 201


def test_las_otras_categorias_no_exigen_descripcion(cliente):
    assert cliente.post("/api/v1/reportes", json=reporte(descripcion=""), headers=E).status_code == 201


def test_la_calidad_se_calcula_al_llegar(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(), headers=E).json()["id"]
    fila = leer(cliente, nuevo)
    assert fila["estado_calidad"] == "aceptar" and fila["puntaje_calidad"] >= 80
    assert set(fila["dimensiones_calidad"]) == set(calidad.DIMENSIONES)
    assert fila["motivo_calidad"] == "" and fila["revisado"] is False


def test_fuera_de_la_zona_se_descarta_y_explica_por_que(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(lat=-2.5, lon=-78.0), headers=E).json()["id"]
    fila = leer(cliente, nuevo)
    assert fila["estado_calidad"] == "descartar" and "fuera de la zona" in fila["motivo_calidad"]


def test_baja_precision_queda_por_revisar(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(precision_m=80), headers=E).json()["id"]
    fila = leer(cliente, nuevo)
    assert fila["estado_calidad"] == "revisar" and "baja precisión" in fila["motivo_calidad"]


def test_duplicado_cercano_y_reciente_se_descarta(cliente):
    primero = cliente.post("/api/v1/reportes", json=reporte(), headers=E).json()["id"]
    segundo = cliente.post("/api/v1/reportes", json=reporte(lat=-3.99311, fecha_dispositivo=(ahora() + timedelta(minutes=1)).isoformat()),
                           headers=E).json()["id"]
    assert leer(cliente, primero)["estado_calidad"] == "aceptar"
    assert leer(cliente, segundo)["estado_calidad"] == "descartar" and "duplicado" in leer(cliente, segundo)["motivo_calidad"]


def test_fecha_muy_vieja_es_incoherente(cliente):
    viejo = (ahora() - timedelta(days=5)).isoformat()
    nuevo = cliente.post("/api/v1/reportes", json=reporte(fecha_dispositivo=viejo), headers=E).json()["id"]
    assert "fecha incoherente" in leer(cliente, nuevo)["motivo_calidad"]


def test_decision_manual_sobrevive_al_recalculo(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(lat=-2.5, lon=-78.0), headers=E).json()["id"]
    r = cliente.put("/api/v1/reportes/" + str(nuevo) + "/decision", json={"decision": "aceptar"}, headers=A)
    assert r.status_code == 200 and r.json()["estado_calidad"] == "aceptar" and r.json()["revisado"] is True
    cliente.post("/api/v1/calidad/recalcular", headers=A)
    assert leer(cliente, nuevo)["estado_calidad"] == "aceptar"
    volver = cliente.put("/api/v1/reportes/" + str(nuevo) + "/decision", json={"decision": "auto"}, headers=A).json()
    assert volver["revisado"] is False and volver["estado_calidad"] == "descartar"


def test_decision_y_recalculo_son_solo_del_administrador(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(), headers=E).json()["id"]
    for cabecera in (E, L, {}):
        assert cliente.put("/api/v1/reportes/" + str(nuevo) + "/decision", json={"decision": "aceptar"}, headers=cabecera).status_code == 401
        assert cliente.post("/api/v1/calidad/recalcular", headers=cabecera).status_code == 401
    assert cliente.put("/api/v1/reportes/" + str(nuevo) + "/decision", json={"decision": "borrar"}, headers=A).status_code == 422
    assert cliente.put("/api/v1/reportes/999999999/decision", json={"decision": "aceptar"}, headers=A).status_code == 404
    assert cliente.get("/api/v1/reportes/99999999999", headers=L).status_code == 422


def test_recalcular_ordena_los_duplicados_aunque_lleguen_al_reves(cliente):
    tarde = cliente.post("/api/v1/reportes", json=reporte(fecha_dispositivo=(ahora() - timedelta(minutes=1)).isoformat()), headers=E).json()["id"]
    pronto = cliente.post("/api/v1/reportes", json=reporte(lat=-3.99311, fecha_dispositivo=(ahora() - timedelta(minutes=4)).isoformat()),
                          headers=E).json()["id"]
    cliente.post("/api/v1/calidad/recalcular", headers=A)
    assert leer(cliente, pronto)["estado_calidad"] == "aceptar" and leer(cliente, tarde)["estado_calidad"] == "descartar"


def test_estadisticas_traen_dimensiones_motivos_y_reglas(cliente):
    cliente.post("/api/v1/reportes", json=reporte(lat=-2.5, lon=-78.0), headers=E)
    datos = cliente.get("/api/v1/estadisticas", headers=L).json()
    assert set(datos["dimensiones"]) == set(calidad.DIMENSIONES)
    assert datos["motivos"].get("fuera de la zona", 0) >= 1
    assert datos["reglas"]["minimo_aceptar"] == 80 and abs(sum(datos["reglas"]["pesos"].values()) - 1) < 1e-9


def test_lista_de_participantes(cliente):
    cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "ana"), headers=E)
    antes = (ahora() - timedelta(minutes=30)).isoformat()
    cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "ana", lat=-3.9900, fecha_dispositivo=antes), headers=E)
    filas = cliente.get("/api/v1/participantes", headers=L).json()
    ana = [f for f in filas if f["participante_id"] == PREFIJO + "ana"][0]
    assert ana["reportes"] == 2 and ana["aceptados"] == 2 and ana["puntaje_medio"] >= 80
    assert cliente.get("/api/v1/participantes", headers=E).status_code == 401


def test_csv_incluye_motivo_y_las_seis_dimensiones(cliente):
    cliente.post("/api/v1/reportes", json=reporte(), headers=E)
    cabecera = cliente.get("/api/v1/exportar.csv", headers=L).text.splitlines()[0].split(",")
    assert "motivo_calidad" in cabecera and all("p_" + d in cabecera for d in calidad.DIMENSIONES)


def test_importar_conserva_la_fecha_original(cliente):
    cab = "participante_id,categoria,descripcion,lat,lon,fecha_dispositivo,recibido_en,consentimiento,precision_m\n"
    fila = PREFIJO + "imp,bache,ok,-3.99123,-79.20456,2026-01-10T10:00:00Z,2026-01-10T10:01:00Z,True,5\n"
    assert cliente.post("/api/v1/importar", content=cab + fila, headers=A).json()["importados"] == 1
    datos = [d for d in cliente.get("/api/v1/reportes", headers=L).json()["datos"] if d["participante_id"] == PREFIJO + "imp"][0]
    assert datos["recibido_en"].startswith("2026-01-10") and datos["estado_calidad"] == "aceptar"


def test_evaluar_sin_base_de_datos():
    base = {"categoria": "bache", "lat": -3.99123, "lon": -79.20456, "precision_m": 10, "descripcion": "x", "tiene_foto": False,
            "fecha_dispositivo": ahora(), "recibido_en": ahora()}
    assert calidad.evaluar(base)["puntaje"] == 100.0
    assert calidad.evaluar({**base, "precision_m": None})["estado"] == "revisar"
    assert calidad.evaluar({**base, "descripcion": ""})["motivo"] == "sin descripción ni foto"


def test_salto_imposible_y_rafaga_piden_revision(cliente):
    cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "salto", lon=-79.2042), headers=E)
    lejos = cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "salto", lat=-3.9800, lon=-79.1900, categoria="basura"), headers=E).json()["id"]
    assert "salto imposible" in leer(cliente, lejos)["motivo_calidad"] and leer(cliente, lejos)["estado_calidad"] == "revisar"
    for i in range(6):
        ultimo = cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "rafaga", lat=-3.99 - i * 0.0005, categoria="basura"), headers=E).json()["id"]
    assert "ráfaga" in leer(cliente, ultimo)["motivo_calidad"]


def test_ubicacion_puesta_a_mano_y_en_movimiento_piden_revision(cliente):
    a_mano = cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "mano", ubicacion_ajustada=True), headers=E).json()["id"]
    rapido = cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "auto2", lat=-3.9990, velocidad_ms=15), headers=E).json()["id"]
    assert leer(cliente, a_mano)["estado_calidad"] == "revisar" and leer(cliente, a_mano)["ubicacion_ajustada"] is True
    assert "enviado en movimiento" in leer(cliente, rapido)["motivo_calidad"]


def test_coordenadas_redondeadas_son_sospechosas(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(participante_id=PREFIJO + "red", lat=-3.99, lon=-79.2), headers=E).json()["id"]
    assert "coordenadas redondeadas" in leer(cliente, nuevo)["motivo_calidad"]

# Pruebas de las reglas de calidad. Se ejecutan con:  python -m pytest analisis -v
import pandas as pd

from analisis.calidad import marcar_calidad, indicadores, distancia_m


def fila(**cambios):
    datos = {
        "id": 1,
        "recibido_en": "2026-12-14T15:00:10+00:00",
        "participante_id": "p-1",
        "categoria": "bache",
        "descripcion": "algo",
        "lat": -3.99,
        "lon": -79.20,
        "precision_m": 10.0,
        "fecha_dispositivo": "2026-12-14T15:00:00+00:00",
        "plataforma": "ios",
    }
    datos.update(cambios)
    return datos


def preparar(lista):
    df = pd.DataFrame(lista)
    df["fecha_dispositivo"] = pd.to_datetime(df["fecha_dispositivo"], utc=True)
    df["recibido_en"] = pd.to_datetime(df["recibido_en"], utc=True)
    return marcar_calidad(df)


def test_distancia_cero():
    assert distancia_m(-3.99, -79.2, -3.99, -79.2) == 0


def test_registro_bueno():
    df = preparar([fila()])
    assert df.loc[0, "valido"]


def test_incompleto():
    df = preparar([fila(descripcion="")])
    assert df.loc[0, "incompleto"]


def test_fuera_de_zona():
    df = preparar([fila(lat=-3.5)])
    assert df.loc[0, "fuera_rango"]


def test_fecha_futura():
    df = preparar([fila(fecha_dispositivo="2026-12-20T15:00:00+00:00")])
    assert df.loc[0, "fuera_rango"]


def test_baja_precision():
    df = preparar([fila(precision_m=120.0)])
    assert df.loc[0, "baja_precision"]


def test_duplicado():
    a = fila()
    b = fila(id=2, lat=-3.99003, fecha_dispositivo="2026-12-14T15:03:00+00:00",
             recibido_en="2026-12-14T15:03:10+00:00")
    df = preparar([a, b])
    assert df["duplicado"].sum() == 1


def test_no_duplicado_si_pasa_mucho_tiempo():
    a = fila()
    b = fila(id=2, fecha_dispositivo="2026-12-14T15:30:00+00:00",
             recibido_en="2026-12-14T15:30:10+00:00")
    df = preparar([a, b])
    assert df["duplicado"].sum() == 0


def test_indicadores():
    df = preparar([fila(), fila(id=2, descripcion="", categoria="basura")])
    ind = indicadores(df)
    assert ind["total"] == 2
    assert ind["completitud"] == 50.0


def test_puntaje_registro_perfecto():
    df = preparar([fila()])
    assert df.loc[0, "puntaje_calidad"] == 100.0
    assert df.loc[0, "estado_calidad"] == "aceptar"


def test_duplicado_se_descarta():
    a = fila()
    b = fila(id=2, fecha_dispositivo="2026-12-14T15:03:00+00:00", recibido_en="2026-12-14T15:03:10+00:00")
    df = preparar([a, b])
    assert df.loc[1, "estado_calidad"] == "descartar"


def test_baja_precision_se_revisa():
    df = preparar([fila(precision_m=80.0)])
    assert df.loc[0, "estado_calidad"] == "revisar"


def test_sin_descripcion_no_se_acepta():
    df = preparar([fila(descripcion="")])
    assert df.loc[0, "estado_calidad"] == "revisar"


def test_fuera_de_zona_se_descarta():
    df = preparar([fila(lat=-3.5)])
    assert df.loc[0, "estado_calidad"] == "descartar"

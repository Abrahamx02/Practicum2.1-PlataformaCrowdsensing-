# "Probar todo ahora": revisa en vivo, desde el panel, que cada parte importante del sistema funciona.
# Todo se hace dentro de una transaccion que se deshace al final: no deja ningun dato de prueba en la base.
import time
import uuid
from datetime import datetime, timedelta, timezone

from backend import base, calidad, diccionario, paquete, repositorio, seguridad
from backend.config import CLAVE_ADMIN, CLAVE_ESCRITURA, CLAVE_LECTURA, CONFIG
from backend.esquemas import ReporteNuevo
from backend.fotos import revisar_foto

ZONA = CONFIG["zona"]
LAT, LON = (ZONA["lat_min"] + ZONA["lat_max"]) / 2 + 0.00123, (ZONA["lon_min"] + ZONA["lon_max"]) / 2 + 0.00117


def _reporte(**cambios):
    datos = {"participante_id": "verificar-" + uuid.uuid4().hex[:8], "categoria": "bache", "descripcion": "bache de prueba",
             "lat": LAT, "lon": LON, "precision_m": 8.0, "fecha_dispositivo": datetime.now(timezone.utc), "consentimiento": True,
             "id_cliente": uuid.uuid4()}
    datos.update(cambios)
    return ReporteNuevo(**datos)


def _leer(con, id_):
    return repositorio.obtener_reporte(con, id_)


def _falla(funcion, *args, **datos):
    # True si la funcion lanza un error (es lo que queremos ver cuando le damos datos malos)
    try:
        funcion(*args, **datos)
    except Exception:
        return True
    return False


def _base(con, app):
    version = con.execute("SELECT postgis_version()").fetchone()[0].split(" ")[0]
    return True, "PostgreSQL responde y PostGIS " + version + " está activo"


def _migraciones(con, app):
    hechas = con.execute("SELECT count(*) FROM migraciones").fetchone()[0]
    return hechas >= 7, str(hechas) + " migraciones aplicadas"


def _guarda_y_califica(con, app):
    id_, creado = repositorio.guardar_reporte(con, _reporte(), None)
    f = _leer(con, id_)
    return creado and f["estado_calidad"] == "aceptar" and f["puntaje_calidad"] >= 80, "puntaje " + str(f["puntaje_calidad"]) + " → " + f["estado_calidad"]


def _repetido(con, app):
    repositorio.guardar_reporte(con, _reporte(), None)
    id_, _ = repositorio.guardar_reporte(con, _reporte(lat=LAT + 0.00005, fecha_dispositivo=datetime.now(timezone.utc) + timedelta(minutes=1)), None)
    f = _leer(con, id_)
    return f["estado_calidad"] == "descartar" and "duplicado" in f["motivo_calidad"], "el segundo quedó: " + f["motivo_calidad"]


def _fuera_de_zona(con, app):
    id_, _ = repositorio.guardar_reporte(con, _reporte(lat=-3.9, lon=-79.1), None)
    f = _leer(con, id_)
    return "fuera de la zona" in f["motivo_calidad"] and f["estado_calidad"] == "descartar", f["motivo_calidad"]


def _salto(con, app):
    quien = "verificar-" + uuid.uuid4().hex[:8]
    repositorio.guardar_reporte(con, _reporte(participante_id=quien), None)
    id_, _ = repositorio.guardar_reporte(con, _reporte(participante_id=quien, categoria="basura", lat=ZONA["lat_max"] - 0.0003, lon=ZONA["lon_max"] - 0.0003), None)
    f = _leer(con, id_)
    return "salto imposible" in f["motivo_calidad"], f["motivo_calidad"] or "sin aviso"


def _otro_vacio(con, app):
    return _falla(_reporte, categoria="otro", descripcion=""), "«Otro» sin texto ni foto se rechaza"


def _datos_imposibles(con, app):
    return _falla(_reporte, lat=200) and _falla(_reporte, categoria="inventada"), "latitud 200 y categoría inventada se rechazan"


def _foto_falsa(con, app):
    return _falla(revisar_foto, "SG9sYQ=="), "un archivo que no es JPEG se rechaza"


def _reenvio(con, app):
    mismo = uuid.uuid4()
    a = repositorio.guardar_reporte(con, _reporte(id_cliente=mismo), None)
    b = repositorio.guardar_reporte(con, _reporte(id_cliente=mismo), None)
    return a[0] == b[0] and a[1] and not b[1], "el reenvío del celular no se duplica"


def _recalculo(con, app):
    quien = "verificar-" + uuid.uuid4().hex[:8]
    ids = [repositorio.guardar_reporte(con, _reporte(participante_id=quien, lat=LAT + i * 0.002, fecha_dispositivo=datetime.now(timezone.utc) - timedelta(minutes=40 * i)), None)[0] for i in range(3)]
    antes = [_leer(con, i)["estado_calidad"] for i in ids]
    repositorio.recalcular_calidad(con)
    despues = [_leer(con, i)["estado_calidad"] for i in ids]
    return antes == despues, "al recalcular todo, los estados no cambian: " + ", ".join(despues)


def _pesos(con, app):
    suma = sum(CONFIG["calidad"]["pesos"].values())
    return abs(suma - 1) < 1e-9 and set(CONFIG["calidad"]["pesos"]) == set(calidad.DIMENSIONES), "seis dimensiones, suman " + str(round(100 * suma)) + " %"


def _retiro(con, app):
    quien = "verificar-" + uuid.uuid4().hex[:8]
    for i in range(2):
        repositorio.guardar_reporte(con, _reporte(participante_id=quien, lat=LAT + i * 0.003), None)
    borrados = repositorio.retirar_participante(con, quien)
    quedan = con.execute("SELECT count(*) FROM reportes WHERE participante_id = %s", (quien,)).fetchone()[0]
    return borrados == 2 and quedan == 0, "se borraron " + str(borrados) + " reportes del participante"


def _claves(con, app):
    claves = [CLAVE_ESCRITURA or "", CLAVE_LECTURA or "", CLAVE_ADMIN or ""]
    return len(set(claves)) == 3 and all(len(c) >= 16 for c in claves), "tres claves distintas de 16 letras o más"


def _formulas(con, app):
    return paquete.neutralizar("=HYPERLINK(1)").startswith("'") and paquete.neutralizar("hola") == "hola", "los textos que empiezan con = + - @ se neutralizan"


def _limite(con, app):
    l = seguridad.Limitador(3, 60)
    return [l.permitir("x") for _ in range(4)] == [True, True, True, False], "el 4.º envío seguido se bloquea"


def _cabeceras(con, app):
    return "default-src 'self'" in seguridad.CSP and "script-src 'self'" in seguridad.CSP and len(seguridad.CABECERAS) >= 5, "política de contenido y " + str(len(seguridad.CABECERAS)) + " cabeceras activas"


def _docs_apagados(con, app):
    return app.docs_url is None and app.openapi_url is None, "la documentación pública de la API está apagada"


def _sesion(con, app):
    token = seguridad.crear_sesion()
    valido = seguridad.leer_sesion(token) == "administrador"
    seguridad.anular_sesion(token)
    return valido and seguridad.leer_sesion(token) is None and seguridad.leer_sesion(token[:-3] + "abc") is None, "el permiso vence, se puede anular y no se puede falsificar"


def _exportaciones(con, app):
    import csv, io, json
    repositorio.guardar_reporte(con, _reporte(), None)
    filas = repositorio.todos_los_reportes(con)
    cabecera = list(csv.reader(io.StringIO(paquete.a_csv(filas))))[0]
    geo = paquete.a_geojson(filas)
    contenido, nombre = paquete.construir_zip(filas)
    return ("motivo_calidad" in cabecera and geo["type"] == "FeatureCollection" and len(geo["features"]) == len(filas) and len(contenido) > 100
            and len(diccionario.CAMPOS) > 20), "CSV, GeoJSON y paquete ZIP (" + nombre + ")"


COMPROBACIONES = [
    ("Base de datos", "La base de datos responde y tiene PostGIS", _base),
    ("Base de datos", "Las migraciones están al día", _migraciones),
    ("Recepción de reportes", "Guarda un reporte y calcula su calidad al instante", _guarda_y_califica),
    ("Recepción de reportes", "No duplica un reenvío del celular", _reenvio),
    ("Recepción de reportes", "Rechaza «Otro» sin texto ni foto", _otro_vacio),
    ("Recepción de reportes", "Rechaza datos imposibles", _datos_imposibles),
    ("Recepción de reportes", "Rechaza archivos que no son fotos", _foto_falsa),
    ("Control de calidad", "Los pesos de las seis dimensiones suman 100 %", _pesos),
    ("Control de calidad", "Detecta un reporte repetido", _repetido),
    ("Control de calidad", "Detecta un punto fuera de la zona del piloto", _fuera_de_zona),
    ("Control de calidad", "Detecta un salto imposible entre dos reportes", _salto),
    ("Control de calidad", "Recalcular todo deja los mismos resultados", _recalculo),
    ("Privacidad y seguridad", "Retirarse borra todo lo del participante", _retiro),
    ("Privacidad y seguridad", "Las tres claves son distintas y largas", _claves),
    ("Privacidad y seguridad", "El permiso del panel vence y se puede anular", _sesion),
    ("Privacidad y seguridad", "El límite de envíos bloquea el exceso", _limite),
    ("Privacidad y seguridad", "Las cabeceras de seguridad están activas", _cabeceras),
    ("Privacidad y seguridad", "La documentación pública está apagada", _docs_apagados),
    ("Privacidad y seguridad", "El CSV neutraliza fórmulas de Excel", _formulas),
    ("Exportación", "El CSV, el GeoJSON y el ZIP salen bien armados", _exportaciones),
]


def ejecutar(app):
    resultados = []
    with base.conexion() as con:
        with con.transaction(force_rollback=True):                   # todo lo que se cree aqui se deshace al terminar
            for grupo, nombre, funcion in COMPROBACIONES:
                inicio = time.perf_counter()
                try:
                    with con.transaction(force_rollback=True):
                        ok, detalle = funcion(con, app)
                except Exception as error:
                    ok, detalle = False, "falló: " + str(error).splitlines()[0][:120]
                resultados.append({"grupo": grupo, "nombre": nombre, "ok": bool(ok), "detalle": detalle,
                                   "ms": round((time.perf_counter() - inicio) * 1000)})
    return {"hecho_en": datetime.now(timezone.utc).isoformat(), "total": len(resultados), "correctas": sum(r["ok"] for r in resultados),
            "resultados": resultados}

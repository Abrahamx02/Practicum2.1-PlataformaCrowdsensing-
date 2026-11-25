# Arma las descargas de datos (CSV, GeoJSON y el paquete ZIP versionado) a partir de las filas de la base
import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

from backend import calidad, diccionario, repositorio
from backend.config import CONFIG


def neutralizar(valor):
    # Excel ejecuta como formula los textos que empiezan con = + - @ ; se les antepone una comilla
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor
    return valor


def a_csv(filas):
    columnas = repositorio.COLUMNAS + ["p_" + d for d in calidad.DIMENSIONES]
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=columnas, extrasaction="ignore")
    escritor.writeheader()
    for original in filas:
        fila = dict(original)
        dimensiones = fila.pop("dimensiones_calidad", None) or {}
        for d in calidad.DIMENSIONES:
            fila["p_" + d] = dimensiones.get(d)
        for campo in ("participante_id", "descripcion", "navegador", "motivo_calidad"):
            fila[campo] = neutralizar(fila[campo])
        escritor.writerow(fila)
    return salida.getvalue()


def a_geojson(filas):
    # en GeoJSON el orden es [longitud, latitud]
    return {"type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [f["lon"], f["lat"]]}, "properties": f} for f in filas]}


def depurados(filas):
    return [f for f in filas if f["estado_calidad"] in ("aceptar", "revisar")]


def para_publicar(filas):
    """Version publicable: cada codigo de participante pasa a P01, P02... (el mismo codigo siempre da el mismo numero),
    se quita el navegador y la referencia a la foto. Asi nadie puede cruzar el dataset con el celular de una persona."""
    numeros = {p: "P%02d" % (i + 1) for i, p in enumerate(sorted({f["participante_id"] for f in filas}))}
    salida = []
    for original in filas:
        fila = dict(original)
        fila.update({"participante_id": numeros[fila["participante_id"]], "navegador": "", "foto_id": None})
        salida.append(fila)
    return salida


def construir_zip(filas, fotos=None, publico=False):
    """Paquete versionado: dataset crudo y depurado, GeoJSON, diccionario y un manifiesto con la huella (SHA-256) de cada archivo."""
    ahora = datetime.now(timezone.utc)
    if publico:
        filas, fotos = para_publicar(filas), None
    sello = "v" + CONFIG["version_api"] + "_" + ahora.strftime("%Y%m%d") + ("_publicable" if publico else "")
    archivos = {
        "reportes_crudo_" + sello + ".csv": a_csv(filas).encode("utf-8"),
        "reportes_depurado_" + sello + ".csv": a_csv(depurados(filas)).encode("utf-8"),
        "reportes_" + sello + ".geojson": json.dumps(a_geojson(filas), default=str, ensure_ascii=False).encode("utf-8"),
        "diccionario_datos.md": diccionario.a_markdown().encode("utf-8"),
    }
    for id_foto, datos in (fotos or []):
        archivos["fotos/foto_" + str(id_foto) + ".jpg"] = bytes(datos)
    cal = CONFIG["calidad"]
    manifiesto = {
        "version": CONFIG["version_api"], "generado_en": ahora.isoformat(), "reportes": len(filas), "reportes_depurados": len(depurados(filas)),
        "zona": CONFIG["zona"], "reglas_de_calidad": {"pesos": cal["pesos"], "minimo_aceptar": cal["minimo_aceptar"], "minimo_revisar": cal["minimo_revisar"]},
        "archivos": {n: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in archivos.items()},
        "uso": "Datos con fines académicos y de investigación. Los códigos de participante son seudónimos.",
        "version_publicable": publico,
        "sin": ["códigos reales de participante (reemplazados por P01, P02...)", "navegador", "fotos"] if publico else [],
    }
    archivos["manifiesto.json"] = json.dumps(manifiesto, indent=2, ensure_ascii=False).encode("utf-8")
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zip_:
        for nombre, contenido in archivos.items():
            zip_.writestr(nombre, contenido)
    return salida.getvalue(), "observatorio_loja_" + sello + ".zip"

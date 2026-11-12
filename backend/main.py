# ===== parte 1: configuracion y modelo de datos =====
import os
import io
import csv
import base64
from datetime import datetime
from typing import Literal, Optional

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CLAVE_ESCRITURA = os.getenv("CLAVE_ESCRITURA")
CLAVE_LECTURA = os.getenv("CLAVE_LECTURA")   # rol analista: solo lee
CLAVE_ADMIN = os.getenv("CLAVE_ADMIN")       # rol administrador: todo

COLUMNAS = ["id", "recibido_en", "participante_id", "categoria", "descripcion", "lat", "lon",
            "precision_m", "fecha_dispositivo", "plataforma", "navegador", "consentimiento",
            "consentimiento_version", "foto_id", "puntaje_calidad", "estado_calidad"]

app = FastAPI(title="MCS Loja")


class ReporteNuevo(BaseModel):
    participante_id: str = Field(min_length=3, max_length=60)
    categoria: Literal["bache", "luminaria_danada", "basura", "otro"]
    descripcion: str = Field(default="", max_length=280)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    precision_m: Optional[float] = Field(default=None, ge=0)
    fecha_dispositivo: datetime
    plataforma: str = "otro"
    navegador: str = ""
    consentimiento: bool
    consentimiento_version: str = Field(default="v1", max_length=20)
    foto_base64: Optional[str] = Field(default=None, max_length=700000)


def revisar_clave(clave_enviada, clave_correcta):
    if not clave_correcta or clave_enviada != clave_correcta:
        raise HTTPException(status_code=401, detail="Clave incorrecta")


def revisar_lectura(clave_enviada):
    # pueden leer el analista y el administrador
    validas = []
    if CLAVE_LECTURA:
        validas.append(CLAVE_LECTURA)
    if CLAVE_ADMIN:
        validas.append(CLAVE_ADMIN)
    if clave_enviada not in validas:
        raise HTTPException(status_code=401, detail="Clave incorrecta")


# ===== parte 2: guardar un reporte =====
def guardar(con, datos):
    foto_id = None
    # si viene foto (se usa desde la seccion 10 de la guia)
    if datos.foto_base64:
        try:
            bytes_foto = base64.b64decode(datos.foto_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="La foto no es valida")
        fila = con.execute("INSERT INTO fotos (datos) VALUES (%s) RETURNING id", (bytes_foto,)).fetchone()
        foto_id = fila[0]

    sql = """
        INSERT INTO reportes (participante_id, categoria, descripcion, lat, lon, precision_m,
                              ubicacion, fecha_dispositivo, plataforma, navegador,
                              consentimiento, consentimiento_version, foto_id)
        VALUES (%s, %s, %s, %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    valores = (datos.participante_id, datos.categoria, datos.descripcion, datos.lat, datos.lon,
               datos.precision_m, datos.lon, datos.lat, datos.fecha_dispositivo,
               datos.plataforma, datos.navegador, datos.consentimiento,
               datos.consentimiento_version, foto_id)
    fila = con.execute(sql, valores).fetchone()
    return fila[0]


# ===== parte 3: endpoints publicos (los usa el formulario) =====
@app.get("/salud")
def salud():
    with psycopg.connect(DATABASE_URL) as con:
        con.execute("SELECT 1")
    return {"estado": "ok"}


@app.post("/reportes", status_code=201)
def crear_reporte(datos: ReporteNuevo, x_clave: Optional[str] = Header(default=None)):
    revisar_clave(x_clave, CLAVE_ESCRITURA)
    if datos.consentimiento is not True:
        raise HTTPException(status_code=400, detail="Se necesita el consentimiento")
    with psycopg.connect(DATABASE_URL) as con:
        nuevo_id = guardar(con, datos)
    return {"id": nuevo_id, "mensaje": "Reporte guardado"}


# ===== parte 4: endpoints de administrador (leer, exportar, importar) =====
def leer_reportes(categoria=None, desde=None):
    sql = "SELECT " + ", ".join(COLUMNAS) + " FROM reportes WHERE 1 = 1"
    valores = []
    if categoria:
        sql += " AND categoria = %s"
        valores.append(categoria)
    if desde:
        sql += " AND recibido_en >= %s"
        valores.append(desde)
    sql += " ORDER BY id"
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as con:
        filas = con.execute(sql, valores).fetchall()
    return filas


@app.get("/reportes")
def listar_reportes(categoria: Optional[str] = None, desde: Optional[str] = None,
                    x_clave: Optional[str] = Header(default=None)):
    revisar_lectura(x_clave)
    return leer_reportes(categoria, desde)


@app.get("/resumen")
def resumen(x_clave: Optional[str] = Header(default=None)):
    revisar_lectura(x_clave)
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as con:
        fila = con.execute(
            "SELECT COUNT(*) AS reportes, COUNT(DISTINCT participante_id) AS participantes FROM reportes"
        ).fetchone()
    return fila


@app.get("/exportar.csv")
def exportar(x_clave: Optional[str] = Header(default=None)):
    revisar_lectura(x_clave)
    filas = leer_reportes()
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=COLUMNAS)
    escritor.writeheader()
    for fila in filas:
        escritor.writerow(fila)
    return Response(content=salida.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=reportes.csv"})


@app.get("/exportar.geojson")
def exportar_geojson(x_clave: Optional[str] = Header(default=None)):
    revisar_lectura(x_clave)
    lista = []
    for fila in leer_reportes():
        propiedades = dict(fila)
        # en GeoJSON el orden es [longitud, latitud]
        punto = {"type": "Point", "coordinates": [fila["lon"], fila["lat"]]}
        lista.append({"type": "Feature", "geometry": punto, "properties": propiedades})
    return {"type": "FeatureCollection", "features": lista}


class ResultadoCalidad(BaseModel):
    id: int
    puntaje_calidad: float = Field(ge=0, le=100)
    estado_calidad: Literal["aceptar", "revisar", "descartar"]


@app.post("/calidad")
def guardar_calidad(resultados: list[ResultadoCalidad], x_clave: Optional[str] = Header(default=None)):
    revisar_clave(x_clave, CLAVE_ADMIN)
    with psycopg.connect(DATABASE_URL) as con:
        for r in resultados:
            con.execute("UPDATE reportes SET puntaje_calidad = %s, estado_calidad = %s WHERE id = %s",
                        (r.puntaje_calidad, r.estado_calidad, r.id))
    return {"actualizados": len(resultados)}


@app.delete("/participantes/{participante_id}")
def retirar_participante(participante_id: str, x_clave: Optional[str] = Header(default=None)):
    # derecho a retirarse: borra todos los reportes y fotos de ese codigo
    revisar_clave(x_clave, CLAVE_ADMIN)
    with psycopg.connect(DATABASE_URL) as con:
        filas = con.execute("DELETE FROM reportes WHERE participante_id = %s RETURNING foto_id",
                            (participante_id,)).fetchall()
        for fila in filas:
            if fila[0] is not None:
                con.execute("DELETE FROM fotos WHERE id = %s", (fila[0],))
    return {"reportes_borrados": len(filas)}


@app.post("/importar")
async def importar(request: Request, x_clave: Optional[str] = Header(default=None)):
    revisar_clave(x_clave, CLAVE_ADMIN)
    cuerpo = await request.body()
    lector = csv.DictReader(io.StringIO(cuerpo.decode("utf-8")))
    buenos = 0
    malos = 0
    with psycopg.connect(DATABASE_URL) as con:
        for fila in lector:
            fila = {clave: valor for clave, valor in fila.items() if valor != ""}
            try:
                datos = ReporteNuevo(**fila)
                guardar(con, datos)
                buenos += 1
            except Exception:
                malos += 1
    return {"importados": buenos, "rechazados": malos}


@app.get("/fotos")
def listar_fotos(x_clave: Optional[str] = Header(default=None)):
    revisar_clave(x_clave, CLAVE_ADMIN)
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as con:
        filas = con.execute("SELECT id, tipo, length(datos) AS bytes FROM fotos ORDER BY id").fetchall()
    return filas


@app.delete("/fotos/{foto_id}")
def descartar_foto(foto_id: int, x_clave: Optional[str] = Header(default=None)):
    # para fotos con rostros o placas: se borra la foto y el reporte se conserva sin foto
    revisar_clave(x_clave, CLAVE_ADMIN)
    with psycopg.connect(DATABASE_URL) as con:
        con.execute("UPDATE reportes SET foto_id = NULL WHERE foto_id = %s", (foto_id,))
        borradas = con.execute("DELETE FROM fotos WHERE id = %s RETURNING id", (foto_id,)).fetchall()
    if len(borradas) == 0:
        raise HTTPException(status_code=404, detail="No existe esa foto")
    return {"foto_borrada": foto_id}


@app.get("/fotos/{foto_id}")
def ver_foto(foto_id: int, x_clave: Optional[str] = Header(default=None)):
    revisar_clave(x_clave, CLAVE_ADMIN)
    with psycopg.connect(DATABASE_URL) as con:
        fila = con.execute("SELECT tipo, datos FROM fotos WHERE id = %s", (foto_id,)).fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe esa foto")
    return Response(content=bytes(fila[1]), media_type=fila[0])


# ===== parte 5: servir el formulario (SIEMPRE AL FINAL del archivo) =====
# Si agregan mas endpoints, pongan arriba de esta parte.
ruta_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=ruta_frontend, html=True), name="frontend")

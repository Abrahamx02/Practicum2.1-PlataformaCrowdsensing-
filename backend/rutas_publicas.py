# Rutas que usa el formulario del participante
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from backend import repositorio
from backend.base import conexion
from backend.config import CLAVE_ESCRITURA, CONFIG, IDS_CATEGORIAS
from backend.esquemas import Encuesta, ReporteNuevo
from backend.fotos import revisar_foto
from backend.seguridad import exigir_escritura, ip_del_cliente, limite_reportes, limite_similares

router = APIRouter()


@router.get("/salud", tags=["Estado"])
def salud(respuesta: Response):
    # a proposito dice poco: los detalles (version, PostGIS, hora) los ve solo el administrador en /servidor
    estado = {"estado": "ok"}
    try:
        with conexion() as con:
            con.execute("SELECT 1")
        estado["base_de_datos"] = "ok"
    except Exception:
        respuesta.status_code = 503
        estado["estado"] = "degradado"
        estado["base_de_datos"] = "sin conexión"
    return estado


@router.get("/configuracion", tags=["Estado"])
def configuracion():
    # el formulario lee de aqui las categorias, la zona y los limites (una sola fuente de verdad)
    # clave_formulario: es la clave del rol "participante". No es secreta (cualquiera que abre el formulario la recibe);
    # solo sirve para escribir reportes y esta protegida por el limite de envios. Las claves de lectura y admin NUNCA salen.
    # solo lo que el formulario necesita; metas del piloto y reglas de calidad no se publican
    return {"clave_formulario": CLAVE_ESCRITURA or "", "categorias": CONFIG["categorias"], "zona": CONFIG["zona"],
            "captura": CONFIG["captura"], "consentimiento": CONFIG["consentimiento"]}


@router.post("/reportes", status_code=201, tags=["Participante"])
def crear_reporte(datos: ReporteNuevo, request: Request, respuesta: Response, rol: str = Depends(exigir_escritura)):
    if not limite_reportes.permitir(ip_del_cliente(request)):
        raise HTTPException(status_code=429, detail="Enviaste muchos reportes en poco tiempo. Espera un minuto.")
    if datos.consentimiento is not True:
        raise HTTPException(status_code=400, detail="Se necesita el consentimiento para guardar el reporte")
    foto_bytes = revisar_foto(datos.foto_base64)
    with conexion() as con:
        nuevo_id, creado = repositorio.guardar_reporte(con, datos, foto_bytes)
    if not creado:
        respuesta.status_code = 200
    return {"id": nuevo_id, "estado": "creado" if creado else "ya_recibido"}


@router.get("/reportes/similares", tags=["Participante"])
def reportes_similares(request: Request, lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
                       categoria: Optional[str] = None, rol: str = Depends(exigir_escritura)):
    if not limite_similares.permitir(ip_del_cliente(request)):
        raise HTTPException(status_code=429, detail="Demasiadas consultas seguidas. Espera un minuto.")
    # antes de enviar: avisa si ya hay un reporte parecido muy cerca y muy reciente (evita duplicados)
    if categoria is not None and categoria not in IDS_CATEGORIAS:
        raise HTTPException(status_code=422, detail="Categoría no permitida")
    distancia = CONFIG["calidad"]["distancia_duplicado_m"]
    minutos = CONFIG["calidad"]["minutos_duplicado"]
    with conexion() as con:
        cercanos = repositorio.buscar_cercanos(con, lat, lon, distancia, categoria, minutos)
    mas_cercano = round(cercanos[0]["distancia_m"]) if cercanos else None
    return {"similares": len(cercanos), "mas_cercano_m": mas_cercano}


# ---------- lo que el participante puede hacer con lo suyo ----------
CONSEJOS = {
    "duplicado": "Ya había un reporte parecido muy cerca.",
    "fuera de la zona": "Quedó fuera de la zona del estudio.",
    "baja precisión": "El GPS no fue muy preciso. La próxima vez sal a un lugar abierto y espera unos segundos.",
    "fecha incoherente": "La hora de tu celular no coincidió con la del servidor. Activa la hora automática.",
    "sin descripción ni foto": "Una descripción o una foto ayuda a entender mejor el problema.",
    "ubicación puesta a mano": "Pusiste el punto tú mismo en el mapa; el equipo lo va a revisar.",
}
ESTADOS_SIMPLES = {"aceptar": "aceptado", "revisar": "en_revision", "descartar": "descartado"}


@router.get("/mis-reportes", tags=["Participante"])
def mis_reportes(request: Request, participante_id: str = Query(pattern=r"^[A-Za-z0-9_-]{3,40}$"), rol: str = Depends(exigir_escritura)):
    # el participante ve como le fue a cada reporte suyo. Los avisos antifraude no se explican: solo dicen "el equipo lo revisa".
    if not limite_similares.permitir(ip_del_cliente(request)):
        raise HTTPException(status_code=429, detail="Demasiadas consultas seguidas. Espera un minuto.")
    with conexion() as con:
        filas = repositorio.mis_reportes(con, participante_id)
    salida = []
    for f in filas:
        motivos = [m for m in f["motivo_calidad"].split(", ") if m]
        consejos = [CONSEJOS[m] for m in motivos if m in CONSEJOS]
        if any(m not in CONSEJOS for m in motivos):
            consejos.append("El equipo lo va a revisar.")
        salida.append({"id": f["id"], "categoria": f["categoria"], "recibido_en": f["recibido_en"],
                       "estado": ESTADOS_SIMPLES.get(f["estado_calidad"], "recibido"), "consejos": consejos})
    return salida


@router.delete("/mis-datos/{participante_id}", tags=["Participante"])
def retirarme(request: Request, participante_id: str = Path(pattern=r"^[A-Za-z0-9_-]{3,40}$"), rol: str = Depends(exigir_escritura)):
    # derecho a retirarse: quien tiene su codigo puede borrar sus reportes, fotos y encuestas sin pedirselo al equipo
    if not limite_similares.permitir(ip_del_cliente(request)):
        raise HTTPException(status_code=429, detail="Demasiadas consultas seguidas. Espera un minuto.")
    with conexion() as con:
        borrados = repositorio.retirar_participante(con, participante_id)
        repositorio.registrar_evento(con, "participante", "retiro_voluntario",
                                     "codigo " + repositorio.huella(participante_id) + ": " + str(borrados) + " reportes", ip_del_cliente(request))
    return {"reportes_borrados": borrados}


@router.post("/encuesta", status_code=201, tags=["Participante"])
def enviar_encuesta(datos: Encuesta, request: Request, rol: str = Depends(exigir_escritura)):
    if not limite_reportes.permitir(ip_del_cliente(request)):
        raise HTTPException(status_code=429, detail="Demasiados envíos seguidos. Espera un minuto.")
    with conexion() as con:
        return {"id": repositorio.guardar_encuesta(con, datos)}

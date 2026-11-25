# Errores con el mismo formato y en espanol:  {"error": {"codigo": ..., "mensaje": ..., "detalles": [...]}}
import logging

import psycopg
from psycopg_pool import PoolTimeout

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as ErrorHTTP

registro = logging.getLogger("mcs")

CODIGOS = {400: "solicitud_incorrecta", 401: "no_autorizado", 403: "prohibido", 404: "no_encontrado",
           405: "metodo_no_permitido", 413: "demasiado_grande", 422: "datos_invalidos",
           429: "demasiadas_solicitudes", 503: "servicio_no_disponible"}


def respuesta_error(estado, codigo, mensaje, detalles=None, id_solicitud=""):
    cuerpo = {"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or [], "id_solicitud": id_solicitud}}
    return JSONResponse(status_code=estado, content=cuerpo)


def traducir(error):
    # convierte el mensaje de pydantic (ingles) a algo entendible
    tipo = error.get("type", "")
    contexto = error.get("ctx", {}) or {}
    if tipo == "missing":
        return "Falta este dato"
    if tipo in ("string_too_long", "too_long"):
        return "Es demasiado largo (máximo " + str(contexto.get("max_length", "")) + ")"
    if tipo in ("string_too_short", "too_short"):
        return "Es demasiado corto"
    if tipo in ("less_than_equal", "greater_than_equal", "less_than", "greater_than"):
        return "Está fuera del rango permitido"
    if tipo == "string_pattern_mismatch":
        return "Tiene un formato no permitido"
    if tipo in ("finite_number", "float_parsing", "int_parsing", "datetime_parsing", "datetime_from_date_parsing",
                "bool_parsing", "uuid_parsing", "literal_error"):
        return "Valor no válido"
    if tipo == "value_error":
        return str(error.get("msg", "Valor no válido")).replace("Value error, ", "")
    return "Valor no válido"


def instalar_errores(app):
    @app.exception_handler(ErrorHTTP)
    async def error_http(request: Request, error: ErrorHTTP):
        codigo = CODIGOS.get(error.status_code, "error")
        mensaje = error.detail if isinstance(error.detail, str) else "Error"
        if error.status_code == 404 and mensaje == "Not Found":
            mensaje = "No se encontró lo que buscas"
        if error.status_code == 405:
            mensaje = "Método no permitido para esta ruta"
        return respuesta_error(error.status_code, codigo, mensaje, id_solicitud=getattr(request.state, "id_solicitud", ""))

    @app.exception_handler(RequestValidationError)
    async def error_validacion(request: Request, error: RequestValidationError):
        detalles = []
        for e in error.errors():
            campo = ".".join(str(p) for p in e.get("loc", []) if p not in ("body", "query", "path"))
            detalles.append({"campo": campo, "mensaje": traducir(e)})
        mensaje = "Hay datos incorrectos"
        if detalles:
            mensaje += ": " + "; ".join((d["campo"] + " - " if d["campo"] else "") + d["mensaje"] for d in detalles[:3])
        return respuesta_error(422, "datos_invalidos", mensaje, detalles, getattr(request.state, "id_solicitud", ""))

    @app.exception_handler(psycopg.OperationalError)
    @app.exception_handler(PoolTimeout)
    async def base_no_disponible(request: Request, error: Exception):
        # la base no responde (por ejemplo Neon despertando o sin internet): se avisa sin dar detalles tecnicos
        registro.error("Base de datos no disponible: %s", str(error).splitlines()[0][:150] if str(error) else type(error).__name__)
        return respuesta_error(503, "servicio_no_disponible",
                               "El servidor no pudo conectarse a la base de datos. Intenta de nuevo en un momento.",
                               id_solicitud=getattr(request.state, "id_solicitud", ""))

    @app.exception_handler(Exception)
    async def error_inesperado(request: Request, error: Exception):
        identificador = getattr(request.state, "id_solicitud", "")
        registro.exception("Error inesperado en %s (solicitud %s)", request.url.path, identificador)
        return respuesta_error(500, "error_interno",
                               "Ocurrió un error en el servidor. Intenta de nuevo; si sigue, informa el código " + identificador,
                               id_solicitud=identificador)

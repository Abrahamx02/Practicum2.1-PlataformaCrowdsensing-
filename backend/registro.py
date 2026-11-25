# Registro (logs) de cada pedido, con un identificador para seguirlo, y cabeceras de seguridad
import logging
import time
import uuid

from fastapi import Request

from backend.errores import respuesta_error
from backend.seguridad import CABECERAS, CSP, ip_del_cliente

MAXIMO_CUERPO = 1_000_000
MAXIMO_CUERPO_IMPORTAR = 5_500_000

registro = logging.getLogger("mcs")


def configurar_registro():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    registro.setLevel(logging.INFO)


def instalar_middleware(app):
    @app.middleware("http")
    async def registrar(request: Request, siguiente):
        identificador = request.headers.get("x-request-id", "")[:40] or uuid.uuid4().hex[:12]
        request.state.id_solicitud = identificador
        inicio = time.perf_counter()
        # cuerpo demasiado grande: se rechaza antes de leerlo (el importar de CSV permite mas)
        tamano = request.headers.get("content-length", "")
        maximo = MAXIMO_CUERPO_IMPORTAR if request.url.path == "/api/v1/importar" else MAXIMO_CUERPO
        if tamano.isdigit() and int(tamano) > maximo:
            respuesta = respuesta_error(413, "demasiado_grande", "El envío es demasiado grande", id_solicitud=identificador)
        else:
            respuesta = await siguiente(request)
        milisegundos = round((time.perf_counter() - inicio) * 1000)

        respuesta.headers["X-Request-ID"] = identificador
        for nombre, valor in CABECERAS.items():
            respuesta.headers[nombre] = valor
        # HSTS: el navegador recordara usar siempre HTTPS (solo si la conexion ya es segura)
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            respuesta.headers["Strict-Transport-Security"] = "max-age=31536000"
        ruta = request.url.path
        if not ruta.startswith(("/docs", "/openapi.json", "/redoc")):
            respuesta.headers["Content-Security-Policy"] = CSP
        if ruta.startswith("/api/"):
            respuesta.headers["Cache-Control"] = "no-store"
        elif not ruta.startswith(("/docs", "/openapi.json", "/redoc")):
            respuesta.headers["Cache-Control"] = "no-cache"      # el navegador pregunta si cambio (ETag) antes de reusar

        rol = getattr(request.state, "rol", "-")
        registro.info("%s %s -> %s %sms rol=%s ip=%s id=%s", request.method, ruta, respuesta.status_code,
                      milisegundos, rol, ip_del_cliente(request), identificador)
        return respuesta

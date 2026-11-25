# Punto de entrada: arma la aplicacion
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from backend import base, repositorio
from backend.config import CONFIG, HABILITAR_DOCS, MIGRAR_AL_INICIAR, RAIZ
from backend.errores import instalar_errores
from backend.registro import configurar_registro, instalar_middleware, registro
from backend.rutas_admin import router as rutas_admin
from backend.rutas_datos import router as rutas_datos
from backend.rutas_publicas import router as rutas_publicas

DESCRIPCION = """
API del prototipo de **Mobile Crowdsensing** para analítica urbana en Loja.

Roles (clave en el encabezado `x-clave`): **participante** (enviar reportes), **analista** (leer y exportar) y **administrador** (todo).
"""


@asynccontextmanager
async def ciclo_de_vida(app):
    configurar_registro()
    if MIGRAR_AL_INICIAR:
        try:
            aplicadas = base.aplicar_migraciones()
            if aplicadas:
                registro.info("Migraciones aplicadas: %s", ", ".join(aplicadas))
        except Exception as error:
            # si la base no esta lista, el servidor enciende igual y vuelve a intentar con  python tareas.py migrar
            registro.error("No se pudieron aplicar las migraciones: %s", str(error).splitlines()[0][:200])
    base.abrir_pool()
    try:
        with base.conexion() as con:
            hechos = repositorio.recalcular_calidad(con, solo_pendientes=True)["calculados"]
        if hechos:
            registro.info("Calidad calculada para %s reportes que no la tenian", hechos)
    except Exception as error:
        registro.warning("No se pudo calcular la calidad pendiente: %s", str(error).splitlines()[0][:150])
    registro.info("Servidor listo (version %s)", CONFIG["version_api"])
    yield
    base.cerrar_pool()


app = FastAPI(title="MCS Loja", version=CONFIG["version_api"], description=DESCRIPCION, lifespan=ciclo_de_vida,
              docs_url="/docs" if HABILITAR_DOCS else None, redoc_url=None, openapi_url="/openapi.json" if HABILITAR_DOCS else None)

instalar_middleware(app)
app.add_middleware(GZipMiddleware, minimum_size=1000)    # respuestas grandes (CSV, listas) viajan comprimidas
instalar_errores(app)

app.include_router(rutas_publicas, prefix="/api/v1")
app.include_router(rutas_datos, prefix="/api/v1")
app.include_router(rutas_admin, prefix="/api/v1")

# el formulario (carpeta frontend) se entrega en la direccion principal; va siempre al final
app.mount("/", StaticFiles(directory=os.path.join(RAIZ, "frontend"), html=True), name="frontend")

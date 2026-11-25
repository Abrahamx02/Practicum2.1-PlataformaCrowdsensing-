# Rutas de lectura para el analista y el administrador
from datetime import datetime
from typing import Literal, Optional

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response

from backend import repositorio
from backend.base import conexion
from backend import calidad, diccionario, paquete
from backend.config import CONFIG, IDS_CATEGORIAS
from backend.seguridad import exigir_lectura

router = APIRouter(tags=["Analista"])


@router.get("/reportes")
def listar_reportes(categoria: Optional[Literal["bache", "luminaria_danada", "basura", "otro"]] = None,
                    estado: Optional[Literal["aceptar", "revisar", "descartar", "sin_calcular"]] = None,
                    plataforma: Optional[Literal["ios", "android", "otro"]] = None,
                    desde: Optional[datetime] = None, hasta: Optional[datetime] = None,
                    despues_de_id: int = Query(default=0, ge=0), limite: int = Query(default=1000, ge=1, le=5000),
                    rol: str = Depends(exigir_lectura)):
    with conexion() as con:
        filas, siguiente = repositorio.listar_reportes(con, categoria, estado, plataforma, desde, hasta,
                                                       despues_de_id, limite)
    return {"cantidad": len(filas), "siguiente": siguiente, "datos": filas}


@router.get("/reportes/cercanos")
def reportes_cercanos(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
                      radio_m: float = Query(default=100, gt=0, le=5000), categoria: Optional[str] = None,
                      rol: str = Depends(exigir_lectura)):
    if categoria is not None and categoria not in IDS_CATEGORIAS:
        raise HTTPException(status_code=422, detail="Categoría no permitida")
    with conexion() as con:
        filas = repositorio.buscar_cercanos(con, lat, lon, radio_m, categoria)
    return {"cantidad": len(filas), "datos": filas}


@router.get("/reportes/{reporte_id}")
def un_reporte(reporte_id: Annotated[int, Path(ge=1, le=2147483647)], rol: str = Depends(exigir_lectura)):
    with conexion() as con:
        fila = repositorio.obtener_reporte(con, reporte_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe ese reporte")
    return fila


@router.get("/estadisticas")
def estadisticas(rol: str = Depends(exigir_lectura)):
    with conexion() as con:
        datos = repositorio.estadisticas(con)
    cal = CONFIG["calidad"]
    # las reglas se muestran en el panel ("como se calcula"); salen de configuracion.json
    datos["reglas"] = {"pesos": cal["pesos"], "minimo_aceptar": cal["minimo_aceptar"], "minimo_revisar": cal["minimo_revisar"],
                       "precision_maxima_m": cal["precision_maxima_m"], "distancia_duplicado_m": cal["distancia_duplicado_m"],
                       "minutos_duplicado": cal["minutos_duplicado"], "zona": CONFIG["zona"]}
    datos["piloto"] = CONFIG["piloto"]
    return datos


@router.get("/participantes")
def participantes(rol: str = Depends(exigir_lectura)):
    with conexion() as con:
        return repositorio.participantes(con)


@router.get("/diccionario")
def diccionario_de_datos(rol: str = Depends(exigir_lectura)):
    return [dict(zip(("campo", "tipo", "obligatorio", "restriccion", "descripcion"), c)) for c in diccionario.CAMPOS]


@router.get("/exportar.csv")
def exportar_csv(rol: str = Depends(exigir_lectura)):
    with conexion() as con:
        filas = repositorio.todos_los_reportes(con)
    return Response(content=paquete.a_csv(filas), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=reportes.csv"})


@router.get("/exportar.geojson")
def exportar_geojson(rol: str = Depends(exigir_lectura)):
    with conexion() as con:
        return paquete.a_geojson(repositorio.todos_los_reportes(con))


@router.get("/exportar.zip")
def exportar_zip(fotos: bool = False, publico: bool = False, rol: str = Depends(exigir_lectura)):
    # paquete versionado (crudo + depurado + GeoJSON + diccionario + manifiesto). Las fotos solo las puede incluir el administrador.
    if fotos and not publico and rol != "administrador":
        raise HTTPException(status_code=403, detail="Solo el administrador puede descargar las fotos")
    with conexion() as con:
        filas = repositorio.todos_los_reportes(con)
        contenido, nombre = paquete.construir_zip(filas, repositorio.todas_las_fotos(con) if (fotos and not publico) else None, publico)
    return Response(content=contenido, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=" + nombre})

# Rutas del administrador: importar, guardar calidad, fotos, retiro de participantes y auditoria
import csv
import io
import os
import platform
from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response
from pydantic import BaseModel, Field

from backend import repositorio
from backend.base import conexion
from backend.config import CONFIG
from backend.esquemas import ReporteNuevo, ResultadoCalidad
from backend.fotos import revisar_foto
from backend import autoverificacion, ejemplos, seguridad
from backend.seguridad import exigir_admin, exigir_clave_admin, ip_del_cliente

router = APIRouter(tags=["Administrador"])

MAXIMO_CSV_BYTES = 5_000_000


class Decision(BaseModel):
    decision: Literal["aceptar", "revisar", "descartar", "auto"]


def fecha_original(texto):
    # la importacion conserva "recibido_en" si el CSV lo trae (por ejemplo un CSV exportado antes); si no sirve, vale "ahora"
    try:
        fecha = datetime.fromisoformat(str(texto).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    fecha = fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)
    return min(fecha, datetime.now(timezone.utc))


@router.post("/importar")
async def importar(request: Request, rol: str = Depends(exigir_admin)):
    cuerpo = await request.body()
    if len(cuerpo) > MAXIMO_CSV_BYTES:
        raise HTTPException(status_code=413, detail="El archivo es demasiado grande (máximo 5 MB)")
    try:
        texto = cuerpo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV en UTF-8")
    lector = csv.DictReader(io.StringIO(texto))
    buenos = 0
    errores = []
    with conexion() as con:
        for numero, fila in enumerate(lector, start=2):      # la fila 1 es el encabezado
            fila = {clave: valor for clave, valor in fila.items() if clave and valor not in ("", None)}
            recibido = fecha_original(fila["recibido_en"]) if "recibido_en" in fila else None
            try:
                datos = ReporteNuevo(**fila)
                # cada fila en su propia "transaccion pequena": si una falla, las demas siguen
                with con.transaction():
                    repositorio.guardar_reporte(con, datos, revisar_foto(datos.foto_base64), recibido)
                buenos += 1
            except Exception as error:
                if len(errores) < 20:
                    errores.append({"fila": numero, "motivo": str(error).splitlines()[0][:120]})
        repositorio.registrar_evento(con, rol, "importar", str(buenos) + " importados", ip_del_cliente(request))
        if buenos:
            repositorio.recalcular_calidad(con)       # deja los duplicados en el orden correcto
    return {"importados": buenos, "rechazados": numero - 1 - buenos if buenos or errores else 0, "errores": errores}


@router.post("/calidad")
def guardar_calidad(resultados: Annotated[list[ResultadoCalidad], Field(max_length=10000)], request: Request,
                    rol: str = Depends(exigir_admin)):
    with conexion() as con:
        actualizados = repositorio.guardar_calidad(con, resultados)
        repositorio.registrar_evento(con, rol, "calidad", str(actualizados) + " actualizados", ip_del_cliente(request))
    return {"actualizados": actualizados}


@router.post("/calidad/recalcular")
def recalcular(request: Request, rol: str = Depends(exigir_admin)):
    with conexion() as con:
        resultado = repositorio.recalcular_calidad(con)
        repositorio.registrar_evento(con, rol, "recalcular_calidad", str(resultado["calculados"]) + " reportes", ip_del_cliente(request))
    return resultado


@router.put("/reportes/{reporte_id}/decision")
def decidir(reporte_id: Annotated[int, Path(ge=1, le=2147483647)], cuerpo: Decision, request: Request,
            rol: str = Depends(exigir_admin)):
    # el equipo acepta, descarta o deja "por revisar" un reporte; "auto" devuelve el calculo automatico
    with conexion() as con:
        fila = repositorio.decidir_reporte(con, reporte_id, cuerpo.decision)
        if fila is not None:
            repositorio.registrar_evento(con, rol, "decidir_reporte", "reporte " + str(reporte_id) + ": " + cuerpo.decision,
                                         ip_del_cliente(request))
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe ese reporte")
    return fila


@router.get("/fotos")
def listar_fotos(rol: str = Depends(exigir_admin)):
    with conexion() as con:
        return repositorio.listar_fotos(con)


@router.get("/fotos/{foto_id}")
def ver_foto(foto_id: Annotated[int, Path(ge=1, le=2147483647)], rol: str = Depends(exigir_admin)):
    with conexion() as con:
        fila = repositorio.obtener_foto(con, foto_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="No existe esa foto")
    return Response(content=bytes(fila[1]), media_type=fila[0], headers={"Cache-Control": "no-store"})


@router.delete("/fotos/{foto_id}")
def descartar_foto(foto_id: Annotated[int, Path(ge=1, le=2147483647)], request: Request, rol: str = Depends(exigir_admin)):
    with conexion() as con:
        borrada = repositorio.borrar_foto(con, foto_id)
        if borrada:
            repositorio.registrar_evento(con, rol, "descartar_foto", "foto " + str(foto_id), ip_del_cliente(request))
    if not borrada:
        raise HTTPException(status_code=404, detail="No existe esa foto")
    return {"foto_borrada": foto_id}


@router.delete("/participantes/{participante_id}")
def retirar_participante(participante_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{3,40}$")], request: Request,
                         rol: str = Depends(exigir_admin)):
    # derecho a retirarse: borra todos los reportes y fotos de ese codigo
    with conexion() as con:
        borrados = repositorio.retirar_participante(con, participante_id)
        repositorio.registrar_evento(con, rol, "retirar_participante",
                                     "codigo " + repositorio.huella(participante_id) + ": " + str(borrados) + " reportes",
                                     ip_del_cliente(request))
    return {"reportes_borrados": borrados}


@router.get("/auditoria")
def auditoria(rol: str = Depends(exigir_admin)):
    with conexion() as con:
        return repositorio.listar_eventos(con)


@router.get("/capacidad")
def capacidad(rol: str = Depends(exigir_admin)):
    # cuanto espacio se usa de la base de datos gratuita y cuantos reportes mas caben (estimado)
    with conexion() as con:
        fila = repositorio.capacidad(con)
    limite = CONFIG["capacidad"]["limite_bytes"]
    porcentaje = round(100 * fila["usado_bytes"] / limite, 2)
    # Estimacion: ~500 bytes por reporte (medido) + la parte de reportes que llevan foto por el peso promedio de una foto.
    # Si todavia hay pocos datos se usan supuestos prudentes (30 % con foto, 100 KB por foto).
    fraccion_con_foto = fila["fotos"] / fila["reportes"] if fila["reportes"] >= 20 else 0.3
    foto_promedio = float(fila["foto_promedio_bytes"]) if fila["fotos"] > 0 else 100000
    por_reporte = 500 + fraccion_con_foto * foto_promedio
    restantes = int(max(0, limite - fila["usado_bytes"]) / por_reporte)
    nivel = "ok"
    if porcentaje >= CONFIG["capacidad"]["alerta_porcentaje"]:
        nivel = "alerta"
    elif porcentaje >= CONFIG["capacidad"]["aviso_porcentaje"]:
        nivel = "aviso"
    return {"usado_bytes": fila["usado_bytes"], "limite_bytes": limite, "porcentaje": porcentaje, "nivel": nivel,
            "reportes": fila["reportes"], "fotos": fila["fotos"],
            "bytes_por_reporte_promedio": int(por_reporte), "reportes_restantes_estimados": restantes,
            "nota": CONFIG["capacidad"]["nota"]}


# ---------- sesion del panel ----------
@router.post("/sesion")
def abrir_sesion(request: Request, rol: str = Depends(exigir_clave_admin)):
    # el panel cambia la clave por un permiso que vence; asi la clave no queda guardada en el navegador
    with conexion() as con:
        repositorio.registrar_evento(con, rol, "inicio_sesion", "", ip_del_cliente(request))
    return {"sesion": seguridad.crear_sesion(rol), "vence_en_horas": seguridad.SESION_HORAS}


@router.delete("/sesion")
def cerrar_sesion(x_sesion: Optional[str] = Header(default=None), rol: str = Depends(exigir_admin)):
    seguridad.anular_sesion(x_sesion)
    return {"cerrada": True}


# ---------- servidor, seguridad y documentacion (solo administrador) ----------
@router.get("/servidor")
def servidor(rol: str = Depends(exigir_admin)):
    with conexion() as con:
        postgis = con.execute("SELECT postgis_version()").fetchone()[0].split(" ")[0]
        migraciones = con.execute("SELECT count(*) FROM migraciones").fetchone()[0]
        tablas = con.execute("SELECT (SELECT count(*) FROM reportes), (SELECT count(*) FROM fotos), (SELECT count(*) FROM encuestas)").fetchone()
    return {"version": CONFIG["version_api"], "hora_servidor": datetime.now(timezone.utc).isoformat(), "base_de_datos": "ok", "postgis": postgis,
            "migraciones": migraciones, "python": platform.python_version(),
            "entorno": "Docker" if os.path.exists("/.dockerenv") else "Servidor o equipo local",
            "reportes": tablas[0], "fotos": tablas[1], "encuestas": tablas[2]}


@router.get("/seguridad")
def revision_de_seguridad(request: Request, rol: str = Depends(exigir_admin)):
    # chequeo en vivo: cada punto dice "ok", "aviso" o "alerta" y explica en palabras simples
    from backend.config import CLAVE_ADMIN, CLAVE_ESCRITURA, CLAVE_LECTURA, HABILITAR_DOCS
    puntos = []

    def punto(nombre, nivel, detalle):
        puntos.append({"nombre": nombre, "nivel": nivel, "detalle": detalle})
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    punto("Conexión cifrada (HTTPS)", "ok" if https else "aviso",
          "Los datos viajan cifrados." if https else "Esta conexión no está cifrada. En tu computador es normal; con el túnel o en Render sí lo está.")
    claves = [CLAVE_ESCRITURA or "", CLAVE_LECTURA or "", CLAVE_ADMIN or ""]
    fuertes = len(set(claves)) == 3 and all(len(c) >= 16 for c in claves)
    punto("Claves de los tres roles", "ok" if fuertes else "alerta", "Son distintas y largas." if fuertes else "Deben ser distintas y de 16 letras o más.")
    punto("Documentación pública de la API", "aviso" if HABILITAR_DOCS else "ok",
          "Está encendida (solo para desarrollo)." if HABILITAR_DOCS else "Apagada: nadie ve el mapa de la API desde afuera.")
    punto("Límite de envíos", "ok", str(seguridad.limite_reportes.maximo) + " reportes por minuto por conexión; las claves malas se bloquean tras " + str(seguridad.limite_fallos.maximo) + " intentos.")
    detras = bool(request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip"))
    punto("Identificar a cada visitante", "aviso" if detras and not seguridad.CONFIAR_EN_PROXY else "ok",
          "Estás detrás de un túnel o proxy pero no se confía en él: todos comparten el mismo límite. Activa CONFIAR_EN_PROXY=1 en el .env."
          if detras and not seguridad.CONFIAR_EN_PROXY else "Cada visitante se cuenta por separado.")
    fallos = seguridad.fallos_ultima_hora()
    punto("Intentos con clave incorrecta (última hora)", "ok" if fallos == 0 else "aviso" if fallos < 10 else "alerta",
          "Ninguno." if fallos == 0 else str(fallos) + " intentos. Si no fuiste tú, cambia las claves.")
    with conexion() as con:
        sin_consentimiento = con.execute("SELECT count(*) FROM reportes WHERE NOT consentimiento").fetchone()[0]
        fotos = con.execute("SELECT count(*) FROM fotos").fetchone()[0]
        capacidad = repositorio.capacidad(con)
    punto("Consentimiento", "ok" if sin_consentimiento == 0 else "alerta",
          "Todos los reportes tienen consentimiento." if sin_consentimiento == 0 else str(sin_consentimiento) + " reportes sin consentimiento.")
    punto("Fotos con datos personales", "ok" if fotos == 0 else "aviso", "No hay fotos." if fotos == 0 else str(fotos) + " fotos: míralas en Reportes y quita las que muestren caras o placas.")
    uso = round(100 * capacidad["usado_bytes"] / CONFIG["capacidad"]["limite_bytes"], 1)
    punto("Espacio de la base de datos", "ok" if uso < CONFIG["capacidad"]["aviso_porcentaje"] else "aviso", str(uso) + " % del plan gratuito.")
    punto("Permiso del panel", "ok", "Dura " + str(seguridad.SESION_HORAS) + " horas y se anula al cerrar sesión. La clave no se guarda en el navegador.")
    return {"puntos": puntos, "alertas": sum(p["nivel"] == "alerta" for p in puntos), "avisos": sum(p["nivel"] == "aviso" for p in puntos)}


@router.get("/especificacion")
def especificacion(request: Request, rol: str = Depends(exigir_admin)):
    return request.app.openapi()


@router.post("/autoverificacion")
def autoverificar(request: Request, rol: str = Depends(exigir_admin)):
    resultado = autoverificacion.ejecutar(request.app)
    with conexion() as con:
        repositorio.registrar_evento(con, rol, "autoverificacion", str(resultado["correctas"]) + " de " + str(resultado["total"]), ip_del_cliente(request))
    return resultado


class PedidoEjemplos(BaseModel):
    cantidad: int = Field(default=120, ge=10, le=400)


@router.post("/ejemplos", status_code=201)
def cargar_ejemplos(cuerpo: PedidoEjemplos, request: Request, rol: str = Depends(exigir_admin)):
    with conexion() as con:
        creados = ejemplos.crear(con, cuerpo.cantidad)
        repositorio.registrar_evento(con, rol, "cargar_ejemplos", str(creados) + " reportes", ip_del_cliente(request))
    return {"creados": creados}


@router.delete("/ejemplos")
def quitar_ejemplos(request: Request, rol: str = Depends(exigir_admin)):
    with conexion() as con:
        borrados = ejemplos.borrar(con)
        repositorio.registrar_evento(con, rol, "quitar_ejemplos", str(borrados) + " reportes", ip_del_cliente(request))
    return {"borrados": borrados}


@router.get("/encuestas")
def encuestas(rol: str = Depends(exigir_admin)):
    with conexion() as con:
        return repositorio.resumen_encuestas(con)

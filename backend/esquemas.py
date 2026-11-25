# Forma de los datos que entran a la API (validaciones con pydantic)
import re
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.config import CONFIG, IDS_CATEGORIAS, LIMITES


def limpiar_texto(texto):
    # quita caracteres de control (incluido el nulo, que la base de datos rechaza); deja salto de linea y tabulacion
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto).strip()


class ReporteNuevo(BaseModel):
    id_cliente: Optional[UUID] = None
    participante_id: str = Field(pattern=r"^[A-Za-z0-9_-]{3,40}$")
    categoria: str
    descripcion: str = Field(default="", max_length=280)
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)
    precision_m: Optional[float] = Field(default=None, ge=0, le=100000, allow_inf_nan=False)
    fecha_dispositivo: datetime
    plataforma: Literal["ios", "android", "otro"] = "otro"
    navegador: str = Field(default="", max_length=200)
    consentimiento: bool
    consentimiento_version: str = Field(default="v2", pattern=r"^v[0-9]{1,3}$")
    foto_base64: Optional[str] = Field(default=None, max_length=700000)
    ubicacion_ajustada: bool = False      # el participante movio el pin en el mapa
    velocidad_ms: Optional[float] = Field(default=None, ge=0, le=400, allow_inf_nan=False)

    @field_validator("categoria")
    @classmethod
    def categoria_permitida(cls, valor):
        if valor not in IDS_CATEGORIAS:
            raise ValueError("categoría no permitida")
        return valor

    @field_validator("descripcion", "navegador")
    @classmethod
    def sin_caracteres_raros(cls, valor):
        return limpiar_texto(valor)

    @field_validator("fecha_dispositivo")
    @classmethod
    def fecha_razonable(cls, valor):
        if valor.tzinfo is None:
            raise ValueError("la fecha debe incluir la zona horaria (por ejemplo 2026-12-14T10:00:00Z)")
        minima = datetime.fromisoformat(LIMITES["fecha_minima"]).replace(tzinfo=timezone.utc)
        maxima = datetime.now(timezone.utc) + timedelta(days=LIMITES["dias_maximos_futuro"])
        if valor < minima or valor > maxima:
            raise ValueError("la fecha está fuera del rango posible")
        return valor


    @model_validator(mode="after")
    def otro_necesita_contenido(self):
        # un reporte de tipo "otro" sin texto ni foto no dice nada: se pide una de las dos cosas
        minimo = CONFIG["captura"]["min_descripcion_otro"]
        if self.categoria == "otro" and len(self.descripcion) < minimo and not self.foto_base64:
            raise ValueError("En «Otro» cuenta qué pasa (mínimo " + str(minimo) + " letras) o agrega una foto")
        return self


class Encuesta(BaseModel):
    participante_id: str = Field(pattern=r"^[A-Za-z0-9_-]{3,40}$")
    respuestas: list[int] = Field(min_length=5, max_length=5)
    comentario: str = Field(default="", max_length=280)

    @field_validator("respuestas")
    @classmethod
    def entre_uno_y_cinco(cls, valor):
        if any(v < 1 or v > 5 for v in valor):
            raise ValueError("cada respuesta va de 1 a 5")
        return valor

    @field_validator("comentario")
    @classmethod
    def comentario_limpio(cls, valor):
        return limpiar_texto(valor)


class ResultadoCalidad(BaseModel):
    id: int
    puntaje_calidad: float = Field(ge=0, le=100, allow_inf_nan=False)
    estado_calidad: Literal["aceptar", "revisar", "descartar"]

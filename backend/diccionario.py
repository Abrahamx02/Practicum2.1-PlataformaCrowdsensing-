# Diccionario de datos: una sola lista que usan el panel, la exportacion y la documentacion
CAMPOS = [
    ("id", "entero", "automático", "único", "Identificador único del reporte"),
    ("recibido_en", "fecha-hora UTC", "automático", "", "Cuándo llegó al servidor"),
    ("participante_id", "texto", "sí", "3 a 40 letras, números, - o _", "Código aleatorio del celular (seudónimo; no es el nombre)"),
    ("categoria", "texto", "sí", "bache, luminaria_danada, basura, otro", "Tipo de problema urbano"),
    ("descripcion", "texto", "en «Otro» (o foto)", "máximo 280 caracteres", "Detalle escrito por el participante"),
    ("lat", "decimal", "sí", "-90 a 90", "Latitud WGS84"),
    ("lon", "decimal", "sí", "-180 a 180", "Longitud WGS84"),
    ("precision_m", "decimal", "no", "0 a 100 000", "Precisión del GPS en metros"),
    ("fecha_dispositivo", "fecha-hora UTC", "sí", "con zona horaria", "Momento en que el celular obtuvo la ubicación"),
    ("plataforma", "texto", "no", "ios, android, otro", "Sistema del celular"),
    ("navegador", "texto", "no", "máximo 200", "Datos técnicos del navegador"),
    ("consentimiento", "verdadero/falso", "sí", "debe ser verdadero", "Aceptó participar"),
    ("consentimiento_version", "texto", "sí", "v + número", "Versión del texto de consentimiento aceptado"),
    ("foto_id", "entero", "no", "solo JPEG, hasta 500 KB", "Foto asociada (sin datos EXIF)"),
    ("ubicacion_ajustada", "verdadero/falso", "no", "", "El participante movió el pin en el mapa"),
    ("velocidad_ms", "decimal", "no", "0 a 400", "Velocidad del celular al capturar (m/s)"),
    ("puntaje_calidad", "decimal", "calculado", "0 a 100", "Puntaje global de calidad"),
    ("estado_calidad", "texto", "calculado", "aceptar, revisar, descartar", "Decisión del control de calidad (o del equipo)"),
    ("motivo_calidad", "texto", "calculado", "", "Por qué no quedó en «aceptar» (vacío si todo está bien)"),
    ("revisado", "verdadero/falso", "calculado", "", "Una persona del equipo decidió el estado a mano"),
    ("p_completitud", "decimal", "calculado", "0 a 1", "¿Trae los datos obligatorios y algo de texto o foto?"),
    ("p_validez", "decimal", "calculado", "0 a 1", "¿Categoría permitida y coordenadas posibles?"),
    ("p_exactitud", "decimal", "calculado", "0 a 1", "¿Dentro de la zona y con GPS preciso?"),
    ("p_consistencia", "decimal", "calculado", "0 a 1", "¿La fecha del celular cuadra con la de llegada?"),
    ("p_unicidad", "decimal", "calculado", "0 a 1", "¿No es un reporte repetido?"),
    ("p_oportunidad", "decimal", "calculado", "0 a 1", "¿Llegó rápido a la plataforma?"),
]


def a_markdown():
    filas = ["# Diccionario de datos", "", "| Campo | Tipo | Obligatorio | Restricción | Descripción |", "|---|---|---|---|---|"]
    filas += ["| " + " | ".join(c) + " |" for c in CAMPOS]
    return "\n".join(filas) + "\n"

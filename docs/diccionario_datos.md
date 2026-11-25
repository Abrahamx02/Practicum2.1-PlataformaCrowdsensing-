# Diccionario de datos (versión 4)

| Campo | Tipo | Obligatorio | Valores / restricción | Descripción |
|-------|------|-------------|-----------------------|-------------|
| id | entero | automático | único | Identificador único del reporte |
| id_cliente | UUID | no | único | Lo crea el celular; evita duplicar un reenvío (no se exporta) |
| recibido_en | fecha-hora UTC | automático | | Cuándo llegó al servidor |
| participante_id | texto | sí | `^[A-Za-z0-9_-]{3,40}$` | Código aleatorio del celular (seudónimo) |
| categoria | texto | sí | las de `configuracion.json` | Tipo de observación (bache, luminaria_danada, basura, otro) |
| descripcion | texto | no | máximo 280, sin caracteres de control | Detalle escrito por el participante |
| lat | decimal | sí | -90 a 90, finito | Latitud WGS84 |
| lon | decimal | sí | -180 a 180, finito | Longitud WGS84 |
| precision_m | decimal | no | 0 a 100 000, finito | Precisión del GPS en metros |
| ubicacion | geography(Point,4326) | automático | | Punto PostGIS, longitud primero (no se exporta; se deriva de lon y lat) |
| fecha_dispositivo | fecha-hora UTC | sí | con zona horaria; entre 2020-01-01 y un año a futuro | Momento en que se obtuvo la ubicación en el celular |
| plataforma | texto | no | ios, android, otro | Sistema del celular |
| navegador | texto | no | máximo 200 | Datos del navegador |
| consentimiento | verdadero/falso | sí | debe ser verdadero | Aceptó el consentimiento |
| consentimiento_version | texto | sí | `v` + número (por defecto v1) | Versión del texto aceptado |
| foto_id | entero | no | | Foto asociada (tabla `fotos`, solo JPEG hasta 500 KB) |
| ubicacion_ajustada | verdadero/falso | no | por defecto falso | El participante movió el pin en el mapa (máximo 150 m del GPS); impide aceptar solo |
| velocidad_ms | decimal | no | 0 a 400 | Velocidad del celular al capturar, en m/s |
| puntaje_calidad | decimal | calculado | 0 a 100 | Puntaje global de calidad (lo calcula el servidor al llegar el reporte) |
| estado_calidad | texto | calculado | aceptar, revisar, descartar | Decisión del control de calidad, o del equipo si `revisado` es verdadero |
| motivo_calidad | texto | calculado | | Por qué no quedó en «aceptar» (vacío si todo está bien) |
| revisado | verdadero/falso | calculado | | Una persona del equipo decidió el estado a mano; el recálculo no lo cambia |
| p_completitud, p_validez, p_exactitud, p_consistencia, p_unicidad, p_oportunidad | decimal | calculado | 0 a 1 | Puntaje de cada una de las seis dimensiones (solo en las exportaciones) |

Columnas que agrega el análisis (no están en la base): `incompleto`, `fuera_rango`, `baja_precision`, `duplicado`, `valido`,
`p_completitud`, `p_validez`, `p_exactitud`, `p_consistencia`, `p_unicidad`, `p_oportunidad`, `demora_min`, `motivo_calidad`.

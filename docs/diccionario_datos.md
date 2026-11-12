# Diccionario de datos (version 2)

| Campo | Tipo | Obligatorio | Valores / restriccion | Descripcion |
|-------|------|-------------|-----------------------|-------------|
| id | entero | automatico | unico | Identificador unico del reporte |
| recibido_en | fecha-hora UTC | automatico | | Cuando llego al servidor |
| participante_id | texto | si | 3 a 60 caracteres | Codigo anonimo creado en el celular (seudonimo) |
| categoria | texto | si | bache, luminaria_danada, basura, otro | Tipo de observacion |
| descripcion | texto | no | maximo 280 | Detalle escrito por el participante |
| lat | decimal | si | -90 a 90 | Latitud WGS84 |
| lon | decimal | si | -180 a 180 | Longitud WGS84 |
| precision_m | decimal | no | mayor o igual a 0 | Precision del GPS en metros |
| ubicacion | geography(Point,4326) | automatico | | Punto PostGIS (lon, lat) |
| fecha_dispositivo | fecha-hora UTC | si | | Hora del celular al capturar |
| plataforma | texto | no | ios, android, otro | Sistema del celular |
| navegador | texto | no | maximo 150 | Datos del navegador |
| consentimiento | verdadero/falso | si | debe ser verdadero | Acepto el consentimiento |
| consentimiento_version | texto | si | por defecto v1 | Version del texto aceptado |
| foto_id | entero | no | | Foto asociada (tabla fotos) |
| puntaje_calidad | decimal | calculado | 0 a 100 | Puntaje global del modulo de calidad |
| estado_calidad | texto | calculado | aceptar, revisar, descartar | Decision del modulo de calidad |

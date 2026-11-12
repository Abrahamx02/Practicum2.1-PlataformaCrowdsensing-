# Contrato de datos (version 2)

El contrato completo esta en `docs/diccionario_datos.md` y en el Documento de diseno.
No cambiar despues de iniciar el piloto. Todo cambio lo aprueba el equipo y se registra con version.

Campos que envia el formulario (JSON): participante_id, categoria, descripcion, lat, lon, precision_m,
fecha_dispositivo, plataforma, navegador, consentimiento, consentimiento_version, foto_base64 (opcional).

Campos que pone el servidor: id, recibido_en, ubicacion (punto PostGIS), foto_id.
Campos que calcula el modulo de calidad: puntaje_calidad (0 a 100) y estado_calidad (aceptar, revisar, descartar).

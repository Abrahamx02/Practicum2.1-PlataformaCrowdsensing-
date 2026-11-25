# Contrato de datos (versión 3)

El contrato completo está en `docs/diccionario_datos.md` y en el Documento de diseño (`docs/entregables/`).
No cambiar después de iniciar el piloto. Todo cambio lo aprueba el equipo completo y se registra con versión en el `CHANGELOG.md`.

**Campos que envía la app (JSON):** `id_cliente`, `participante_id`, `categoria`, `descripcion`, `lat`, `lon`, `precision_m`,
`fecha_dispositivo`, `plataforma`, `navegador`, `consentimiento`, `consentimiento_version` (`v2`), `ubicacion_ajustada`,
`velocidad_ms` y `foto_base64` (opcional).

**Campos que pone el servidor:** `id`, `recibido_en`, `ubicacion` (punto PostGIS) y `foto_id`.

**Campos que calcula el control de calidad:** `puntaje_calidad` (0 a 100), `estado_calidad` (aceptar, revisar, descartar),
`motivo_calidad`, `dimensiones_calidad` (seis valores de 0 a 1) y `revisado` (decisión manual del equipo).

**Regla de «Otro»:** si la categoría es `otro`, la descripción debe tener al menos 8 letras o debe haber una foto.

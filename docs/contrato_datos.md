# Contrato de datos (no cambiar despues de iniciar el piloto)

| Campo | Tipo | Obligatorio | Descripcion |
|-------|------|-------------|-------------|
| participante_id | texto | si | codigo anonimo generado en el celular |
| categoria | texto | si | bache, luminaria_danada, basura, otro |
| descripcion | texto (max 280) | no | detalle escrito por el participante |
| lat, lon | decimal | si | coordenadas GPS del celular |
| precision_m | decimal | no | precision del GPS en metros |
| fecha_dispositivo | fecha-hora | si | hora del celular al enviar (UTC) |
| plataforma | texto | no | ios, android u otro |
| navegador | texto | no | datos del navegador |
| consentimiento | verdadero/falso | si | debe ser verdadero |
| foto_base64 | texto | no | foto reducida (solo se envia, se guarda en tabla fotos) |
| recibido_en | fecha-hora | automatico | la pone el servidor |

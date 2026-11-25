# Guion de la demostración (todo desde el panel)

Antes de empezar: `docker compose up`, abrir `http://127.0.0.1:8000/admin/` (o la dirección del túnel) y entrar con la clave de administrador.
Con el túnel, abrir la app del participante en un celular real. Si van a compartir pantalla, activar el **ojo** (modo presentación).

| Min | Qué mostrar | Dónde | Qué decir |
|---|---|---|---|
| 0–1 | El problema y el flujo | Defensa → Entregables | Captura → recepción → calidad → visualización; la pestaña dice qué entregables se demuestran en la app, cuáles tienen documento y cuáles se hacen en el piloto |
| 1–3 | **Captura en vivo** con un celular | App → Reportar | GPS con varias lecturas, círculo de precisión, mini mapa; «Otro» exige texto o foto; funciona sin internet |
| 3–4 | El reporte aparece solo | Panel → Inicio y Reportes | Llegó, se calificó solo (sin script aparte); abrir el reporte y mostrar «Cómo sacó este puntaje» |
| 4–6 | Datos con problemas a propósito | Sistema → Datos → Cargar ejemplos; luego Mapa | Repetidos, fuera de zona, GPS malo, fechas raras; mapa de calor |
| 6–8 | **Control de calidad** | Calidad | Seis dimensiones, reglas, señales de confianza, indicadores; decidir un reporte a mano; **calibrador** moviendo umbrales |
| 8–9 | Participación y privacidad | Participantes; app → Ayuda | Códigos seudónimos, retiro voluntario (borra todo), modo presentación |
| 9–11 | **Prueba en vivo** | Defensa → Prueba en vivo | «Probar todo ahora»: 20 comprobaciones; no deja datos |
| 11–12 | Seguridad | Sistema → Seguridad | Revisión en vivo; sesión con vencimiento; documentación pública apagada |
| 12–13 | Datos listos para investigar | Sistema → Datos (ZIP) y Defensa → Informe / Ficha | Crudo y depurado, diccionario, huellas SHA-256; informe y ficha generados con los datos |
| 13–14 | Cierre | Defensa → Entregables | Qué está cubierto, qué falta redactar, límites honestos |

Al terminar: Sistema → Datos → **Quitar ejemplos** para dejar solo los reportes reales.

## Si algo falla en vivo
- El mapa sin fondo: no hay internet para los mosaicos; los puntos y la zona se ven igual.
- El celular no da GPS: abrir por HTTPS (túnel), aceptar el permiso y salir a un lugar abierto.
- «Sesión venció»: entrar de nuevo con la clave.

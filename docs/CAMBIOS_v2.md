# Cambios de la versión 2 (según las indicaciones del grupo de investigación)

## Qué cambió y por qué
| Cambio | Archivos | Motivo (indicaciones) |
|---|---|---|
| Campo `consentimiento_version` (el formulario envía "v1") | schema.sql, main.py, app.js | El contrato pide "consentimiento y su versión" |
| Campos `puntaje_calidad` y `estado_calidad` en cada reporte | schema.sql, main.py, calidad.py | El contrato pide "estado y puntaje de calidad" |
| Puntaje 0-100 con 6 dimensiones y estado aceptar / revisar / descartar | calidad.py, test_calidad.py | "Módulo de calidad que asigne un puntaje a cada observación" |
| Exportación GeoJSON (`/exportar.geojson`) | main.py | "importación/exportación (CSV, GeoJSON)" |
| `POST /calidad` para guardar el puntaje en la base | main.py, calidad.py | Para que el puntaje viaje con cada observación |
| `DELETE /participantes/{codigo}` (derecho a retirarse) | main.py | Aviso de privacidad: derecho a retirarse |
| El participante ve su código en el formulario | index.html, app.js | Necesita el código para pedir su retiro |
| Reportes pendientes guardados en el celular cuando no hay internet | app.js | "Registrar observaciones en campo, incluso sin conexión" |
| Dashboard con puntaje medio y conteo de aceptar / revisar / descartar | dashboard.py | Indicadores de calidad en el dashboard |

## Cómo aplicarlo (con ramas)
1. `git checkout main`, `git pull`, `git checkout -b actualizacion-v2`
2. Copiar estos archivos encima de los del repositorio (mismas rutas).
3. En Neon, SQL Editor, ejecutar `backend/migracion_v2.sql` (solo si la base ya tenía las tablas).
4. `python -m pytest -v` (deben pasar 14 pruebas de backend y 14 de análisis).
5. `git add .`, `git commit -m "Version 2: puntaje de calidad, GeoJSON, retiro y envio sin conexion"`, `git push -u origin actualizacion-v2`, Pull Request y revisión.

## Pesos del puntaje (propuesta, a calibrar con el piloto)
Completitud 0,20 - Validez de dominio 0,15 - Exactitud posicional 0,25 - Consistencia temporal 0,15 - Unicidad 0,15 - Oportunidad 0,10.
Aceptar: puntaje >= 80, sin faltantes y con precisión <= 50 m. Revisar: >= 50. Descartar: menos de 50, o duplicado, fuera de rango o sin ubicación/categoría.
Estos umbrales son una propuesta del equipo: la tutora espera que los justifiquen y los calibren.

## Agregado después (versión completa)
- Rol analista (`CLAVE_LECTURA`): solo lee y exporta. Agregarla al `.env` y a Render.
- Fotos: `GET /fotos`, `DELETE /fotos/{id}` y `analisis/revisar_fotos.py` para descartar rostros y placas.
- PWA: `manifest.json`, `sw.js` e iconos para abrir y reportar sin conexión.
- `analisis/exportar_version.py`: CSV y GeoJSON con fecha y huella sha256.
- Docker: `Dockerfile` y `docker-compose.yml` (no probados en el entorno donde se preparó; si fallan, avisar).
- `docs/diccionario_datos.md`.

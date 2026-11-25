# Auditoría de la versión 4 (flujos, lógica y seguridad)

Revisión hecha sobre el proyecto completo. Cada hallazgo dice qué se encontró, qué se hizo y cómo se comprobó.

## Hallazgos de lógica y de flujo

| # | Qué se encontró | Qué se hizo | Comprobación |
|---|---|---|---|
| 1 | **La calidad solo se calculaba con un script de Python aparte**; el panel mostraba «sin calcular» | Se calcula en el servidor al llegar cada reporte, con recálculo y decisión manual | `test_calidad_integrada.py`; Calidad en el panel |
| 2 | Un reporte «Otro» sin texto ni foto se aceptaba (no decía nada) | Se exige texto (mínimo 8 letras) o foto en la app y en el servidor | Pruebas de Python y de JavaScript; flujo real en navegador simulado |
| 3 | El puntaje «0» se mostraba como «sin calcular» (valor 0 tratado como vacío) | Se compara con `null` | Inicio y Calidad |
| 4 | Con túnel o Render todos los visitantes compartían la misma IP: el límite de envíos y el bloqueo de claves valían para todos juntos | `CONFIAR_EN_PROXY=1` por defecto en Docker (el puerto solo escucha en 127.0.0.1) y aviso en la revisión de seguridad | Sistema → Seguridad |
| 5 | La importación de CSV perdía `recibido_en`: todo lo antiguo salía «fecha incoherente» | Se conserva la fecha original y se recalcula en orden | `test_importar_conserva_la_fecha_original` |
| 6 | Los duplicados dependían del orden de llegada (celular sin internet) | «Recalcular» deja todo en el orden de captura | `test_recalcular_ordena_los_duplicados...` |
| 7 | El participante no sabía cómo le fue a sus reportes y para retirarse debía pedírselo al equipo | Pestañas Mis reportes y Ayuda (retiro voluntario) | `test_el_participante_ve_sus_reportes_y_puede_retirarse` |
| 8 | El GPS tomaba solo la mejor lectura y no había forma de corregir un punto malo | Promedio ponderado de lecturas buenas, velocidad, mini mapa y corrección (máx. 150 m, queda marcada) | Pruebas de JavaScript; navegador simulado |
| 9 | Los reportes sospechosos (saltos, ráfagas, coordenadas escritas a mano) se aceptaban solos | Señales de confianza: impiden aceptar solo | `test_salto_imposible...`, `test_coordenadas_redondeadas...` |
| 10 | El «piloto» y el panel dependían de pantallas distintas (Streamlit) | Todo dentro de `/admin/`; se eliminaron los archivos de Streamlit | Navegador simulado recorriendo las 7 pestañas |

## Hallazgos de seguridad

| # | Qué se encontró | Qué se hizo |
|---|---|---|
| 11 | `/docs` y `/openapi.json` públicos | Apagados; el administrador ve la API en el panel |
| 12 | `/salud` y `/configuracion` publicaban versión, PostGIS, metas y reglas | Reducidos a lo mínimo |
| 13 | La clave de administrador quedaba en el navegador | Sesión firmada que vence y se anula |
| 14 | `/reportes/{id}` aceptaba números enormes (error 500) | Rango validado (422) |
| 15 | La consulta «reportes parecidos» no tenía límite | Límite por IP |
| 16 | El contenedor corría como administrador | Usuario sin privilegios |
| 17 | Archivos del sitio podían quedar en caché con una versión vieja | `Cache-Control: no-cache` (el navegador pregunta por ETag) |
| 18 | La clave del `.env` apareció en capturas y en el zip enviado | **Cambiar las tres claves** (`python tareas.py crear-env` en un `.env` nuevo) y no subir `.env` a Git |

## Qué NO se pudo comprobar aquí
- **Mosaicos del mapa** (CARTO/OpenStreetMap): el entorno de revisión no tiene internet; se verificó el mapa con puntos, zona y calor, no el fondo.
- **GPS de un celular real**, cámara y modo sin internet en un teléfono: se probó con ubicación simulada y un navegador de escritorio.
- **Docker, Render y Neon**: los archivos están actualizados pero no se ejecutaron aquí (se probó con PostgreSQL 16 + PostGIS 3.4 locales).
- Si el primer *Pull Request* sale rojo en GitHub, copien el mensaje de error.

## Límites que se mantienen
- La clave del formulario es pública por diseño; el límite por IP y la calidad reducen, no eliminan, los reportes falsos.
- «Aceptar» no prueba que el problema exista: solo que el dato es consistente.
- Las reglas son de un prototipo: calibrarlas con datos del piloto (Calidad → Calibrar).

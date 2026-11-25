# Cumplimiento de las indicaciones del grupo de investigación

Referencia: `Practicum_MCS_Indicaciones.pptx` y el PDF del Prácticum. Lo técnico se comprueba automáticamente con
`backend/tests/test_cumplimiento.py` (corre en `python tareas.py probar` y en cada Pull Request). **Este cuadro se revisa en cada versión nueva.**

Estados: **Cubierto** (hay código y prueba) · **Parcial** (hay avance; falta algo que depende del equipo o del piloto) · **Pendiente** (lo hace el equipo).

## Producto

| Indicación | Estado | Evidencia |
|---|---|---|
| App web responsive para registrar observaciones, con consentimiento previo | Cubierto | `frontend/`, `test_consentimiento_obligatorio...` |
| Captura de GPS con precisión, fecha, categoría, descripción y foto opcional | Cubierto | `frontend/js/ubicacion.js`, `esquemas.py` |
| Registro incluso sin conexión | Cubierto | `js/cola.js`, `sw.js`, `manifest.json`; probado de punta a punta en navegador |
| Contrato de datos mínimo (id, participante seudonimizado, categoría, descripción, fechas de captura y recepción, ubicación, precisión, foto, consentimiento y versión, plataforma, estado y puntaje de calidad) | Cubierto | `migraciones/`, `docs/diccionario_datos.md`, `test_contrato_de_datos_minimo` |
| No se recolectan datos personales | Cubierto | `test_no_se_guardan_datos_personales` |
| API REST y base geoespacial (PostgreSQL + PostGIS) con validaciones | Cubierto | `backend/`, `esquemas.py`, tests de validación |
| Roles de acceso (y sesión con vencimiento para el panel) | Cubierto (3 roles) | `seguridad.py`, `test_roles_separados`, `test_panel.py` |
| Importar y exportar (CSV y GeoJSON), exportaciones versionadas | Cubierto | `rutas_datos.py`, `analisis/exportar_version.py` |
| Módulo de calidad: seis dimensiones, puntaje 0-100, estado aceptar / revisar / descartar, calculado al llegar cada reporte | Cubierto | `backend/calidad.py`, panel → Calidad, `test_calidad_integrada.py` |
| Dashboard geoespacial con mapas, filtros e indicadores | Cubierto | Panel → Inicio, Mapa, Reportes, Calidad (`frontend/admin/`) |
| Derecho a retirarse | Cubierto | El participante se retira solo desde Ayuda (`DELETE /mis-datos/{codigo}`); el administrador también (Participantes) |
| Fotos identificables se descartan o anonimizan | Cubierto (proceso) | Panel de administración > Fotos; la foto se recomprime sin EXIF |
| Entorno reproducible (Docker) y pruebas automáticas (pytest) | Cubierto | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml` |
| Repositorio como fuente de verdad: issues, tablero, pull requests | Cubierto (proceso) | `CONTRIBUTING.md`, plantillas de `.github/` |

## Proceso y entregables académicos

| Indicación | Estado | Dónde |
|---|---|---|
| H0: plan, repositorio, tablero, plan individual, fichas de lectura | Parcial | Repositorio y entorno con Docker: `README.md`, `docs/entregables/Manual_tecnico…`. El plan individual, las fichas de lectura y la bitácora (`docs/bitacora.md`) las escribe cada integrante |
| H1: documento de diseño (historias de usuario, contrato, arquitectura, consentimiento) | Cubierto | `docs/entregables/Documento_de_diseno_MCS_v2.docx`, `docs/ARQUITECTURA.md`, `docs/contrato_datos.md` |
| Modelo de consentimiento informado y aviso de privacidad | Cubierto | `docs/entregables/Consentimiento_y_aviso_de_privacidad_MCS_v2.docx` (texto `v2`, el mismo que muestra la app) |
| Benchmarking de 3 apps | Cubierto (revisar) | `docs/entregables/Benchmarking_apps_participacion_ciudadana_MCS.docx`: FixMyStreet, SeeClickFix y «Cómo va mi barrio»; el equipo debe leerlo y hacerlo suyo |
| Prototipo navegable de pantallas | Cubierto | La propia app: pestañas Reportar, Mis reportes y Ayuda |
| Informe de pruebas funcionales y de usabilidad (cuestionario SUS) | Parcial | `docs/entregables/Informe_de_pruebas_MCS.docx` (resultados reales de las pruebas automáticas); los casos en celulares y la encuesta se ejecutan antes y durante el piloto |
| Prueba de humo: 50 observaciones en el campus (H3) | Pendiente (campo) | Meta en `configuracion.json` (`piloto.prueba_de_humo`); plan en `docs/entregables/Plan_del_piloto…` |
| Piloto: 15 a 25 voluntarios, más de 300 observaciones en 2 semanas | Pendiente (se hace en campo) | Seguimiento en vivo: panel → Inicio y Defensa |
| Dataset depurado con diccionario y ficha (Datasheets for Datasets, FAIR) | Cubierto | `docs/entregables/Ficha_del_dataset_MCS_v2.docx`; panel → Sistema → Datos (ZIP crudo, depurado y publicable) y Defensa → Ficha del dataset (con los números reales) |
| Guía de despliegue y documentación de la API | Cubierto | `render.yaml`, `docs/openapi.json`, panel → Sistema → API |
| Informe del piloto con datos reales | Cubierto (borrador automático) | Panel → Defensa → Informe del piloto |
| Informe técnico, presentación y demostración en vivo | Pendiente | Guion en `docs/GUION_DEFENSA.md`; el informe técnico lo escribe el equipo al cerrar el piloto |

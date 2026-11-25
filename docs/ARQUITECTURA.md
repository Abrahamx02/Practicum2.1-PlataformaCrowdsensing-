# Arquitectura

## Visión general

```
 Celular (PWA)                 Servidor (FastAPI)                         Base de datos
 ┌────────────────┐  HTTPS   ┌───────────────────────────────┐   TLS   ┌──────────────────────┐
 │ Reportar       │ ───────► │ /api/v1  rutas, seguridad,    │ ──────► │ PostgreSQL + PostGIS │
 │ Mis reportes   │          │   validación, errores         │  pool   │ reportes, fotos,     │
 │ Ayuda          │          │   calidad.py: 6 dimensiones   │         │ encuestas, eventos   │
 ├────────────────┤          │   + señales de confianza      │         └──────────────────────┘
 │ Panel del      │ ───────► │ /        app del participante │
 │ equipo (/admin)│  sesión  │ /admin/  panel (estático)     │
 └────────────────┘          └───────────────────────────────┘
```

La calidad se calcula **dentro del servidor** apenas llega cada reporte (`backend/calidad.py`); el panel solo la muestra y permite decidir,
recalcular y calibrar. `analisis/calidad.py` (pandas) es la versión 1 de los scripts de validación para analizar un CSV fuera del servidor. Las seis dimensiones, los pesos y los umbrales son los mismos que en el servidor (`backend/calidad.py`); difiere en dos cosas: aquí una descripción vacía cuenta como dato faltante y no se calculan las señales de confianza.

Una sola fuente de verdad para lo que se comparte: **`configuracion.json`** (categorías, zona, umbrales, pesos de calidad,
metas del piloto, límites). Lo leen el servidor, el módulo de calidad y —por `/api/v1/configuracion`, solo lo necesario— el formulario.

## Backend (carpeta `backend/`)

Capas pequeñas, cada una con una sola responsabilidad. Las rutas no tienen SQL; el SQL no conoce HTTP.

| Archivo | Responsabilidad |
|---|---|
| `config.py` | Lee `.env` y `configuracion.json` |
| `base.py` | *Pool* de conexiones y migraciones |
| `esquemas.py` | Forma y validación de los datos que entran |
| `seguridad.py` | Roles, comparación de claves, límite de pedidos, cabeceras |
| `errores.py` | Errores en español con un solo formato |
| `registro.py` | Registro de cada pedido con identificador, cabeceras de seguridad |
| `fotos.py` | Revisión de fotos (JPEG, tamaño) |
| `repositorio.py` | **Todo el SQL** del proyecto |
| `rutas_publicas.py` | Salud, configuración, enviar reporte, aviso de similares |
| `rutas_datos.py` | Lectura, filtros, estadísticas, exportación (analista) |
| `rutas_admin.py` | Importar, calidad, fotos, retiro, auditoría, capacidad (administrador) |
| `main.py` | Arma la aplicación |
| `migraciones/` | Cambios de la base, en orden (`001_...sql`, `002_...sql`) |
| `tests/` | Pruebas (incluye `test_cumplimiento.py`) |

### Qué pasa cuando llega un reporte

1. `registro` asigna un identificador a la solicitud y mide el tiempo.
2. `seguridad.exigir_escritura` revisa la clave (en tiempo constante) y cuenta intentos fallidos.
3. `esquemas.ReporteNuevo` valida cada campo (si falla: error 422 en español).
4. `rutas_publicas` aplica el límite de envíos, exige el consentimiento y revisa la foto.
5. `repositorio.guardar_reporte` inserta con `ON CONFLICT (id_cliente) DO NOTHING`: un reenvío no duplica.
6. La respuesta es `201 creado` o `200 ya_recibido`.

### Decisiones y por qué

| Decisión | Por qué |
|---|---|
| Migraciones versionadas en vez de `schema.sql` | Cambiar la base sin perder datos y adoptar bases que ya existen |
| *Pool* de conexiones (`max_idle` 240 s) | Abrir una conexión a Neon en cada pedido es lento; el tiempo muerto menor a 5 min evita conexiones muertas cuando Neon se suspende |
| `id_cliente` (UUID) por reporte | El envío sin conexión puede reintentar; así el servidor no duplica |
| Paginación (`limite` ≤ 5000, `despues_de_id`) | Respuestas de tamaño predecible aunque crezcan los datos |
| `/estadisticas` calculado en SQL | El panel no descarga todo para mostrar cifras |
| Categorías solo en `configuracion.json` | Agregar una no exige tocar la base ni varios archivos |
| Auditoría de acciones del administrador | Trazabilidad del derecho a retirarse y de los borrados |
| Un solo servidor (sin estado propio) | Se puede mover a cualquier plataforma o poner detrás de varios servidores |

## Frontend (carpeta `frontend/`)

JavaScript nativo en módulos, sin frameworks ni librerías externas (menos mantenimiento, funciona sin conexión).

| Archivo | Responsabilidad |
|---|---|
| `index.html`, `css/estilo.css` | Formulario de 3 pasos, diseño con modo oscuro y accesible |
| `js/main.js` | Coordina los pasos |
| `js/api.js` | Pedidos al servidor con límite de tiempo y errores claros |
| `js/ubicacion.js` | Sigue el GPS unos segundos y se queda con la mejor lectura |
| `js/foto.js` | Reduce la foto (y borra su EXIF) antes de enviarla |
| `js/cola.js` | Reportes pendientes cuando no hay internet |
| `js/utilidades.js` | Funciones pequeñas y probadas |
| `sw.js`, `manifest.json` | PWA: instalable y abre sin conexión |
| `admin/` | Panel del administrador |

Pruebas del JavaScript: `npm test` (14 pruebas con el ejecutor incluido en Node, sin instalar nada más).

## Calidad

`backend/calidad.py` calcula seis dimensiones (completitud, validez, exactitud posicional, consistencia temporal, unicidad, oportunidad),
un puntaje 0 a 100 y un estado (aceptar, revisar, descartar) con su **motivo**. Además detecta **señales de confianza** (ubicación puesta
a mano, enviado en movimiento, salto imposible entre reportes, ráfaga, coordenadas redondeadas, precisión sospechosa): no bajan el puntaje,
pero impiden aceptar solo. Los pesos y umbrales están en `configuracion.json`. El administrador puede decidir un reporte a mano (el recálculo
no lo toca) y simular otros umbrales en el calibrador de la pestaña Calidad.

## Panel del equipo (carpeta `frontend/admin/`)

| Archivo | Pestaña |
|---|---|
| `admin.js` | Entrada con sesión, navegación y refresco cada 30 s |
| `inicio.js` | Inicio: avance del piloto y qué hacer |
| `mapa.js` (+ `js/geomapa.js`) | Mapa propio con mosaicos y calor, sin librerías |
| `reportes.js` | Lista, filtros y hoja de detalle con decisiones |
| `calidad.js` | Calidad, calibrador y Participantes |
| `sistema.js` | Datos (ZIP, CSV, ejemplos), seguridad, servidor, API, auditoría |
| `defensa.js` | Entregables, prueba en vivo, informe del piloto, ficha del dataset |

## Cómo agregar cosas

| Quiero... | Haz esto |
|---|---|
| Una categoría nueva | Agrega un bloque en `configuracion.json` y un icono `i-ID` en `frontend/iconos.svg` |
| Cambiar la zona o un umbral | Edita `configuracion.json` (nada más) |
| Una columna nueva | Archivo nuevo en `backend/migraciones/` (`006_...sql`), campo en `esquemas.py`, columna en `repositorio.py` y `diccionario_datos.md` |
| Una ruta nueva | Función en `repositorio.py` y ruta en el archivo `rutas_*.py` de su rol, con su prueba |

## Resistencia a fallos (probado)
- Si la base de datos se apaga o tarda en despertar, el servidor **sigue encendido**: responde `503` en español, `/api/v1/salud` dice `degradado`, y se recupera solo cuando la base vuelve (probado apagando y encendiendo PostgreSQL con el servidor corriendo).
- Si la base no está lista al encender, el servidor arranca igual; las migraciones se reintentan con `python tareas.py migrar`.
- Los reportes enviados desde celulares sin conexión se guardan en el celular y se reenvían sin duplicarse (`id_cliente`).

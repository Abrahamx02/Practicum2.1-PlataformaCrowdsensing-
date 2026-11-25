# Portabilidad y escalabilidad

## Portabilidad (versión móvil u otros clientes)

El servidor no sabe nada del formulario: solo expone una **API versionada y documentada** (`/api/v1`, especificación en `docs/openapi.json`,
generada con `python tareas.py openapi`). Cualquier cliente puede usarla.

| Camino | Esfuerzo | Cómo |
|---|---|---|
| Instalar el formulario como app (PWA) | Ya está | Safari: Compartir > Añadir a pantalla de inicio. Chrome: Instalar app |
| Publicar en tiendas con la misma página | Bajo | Envolver el `frontend/` con **Capacitor** (Android/iOS) y apuntar a la URL del servidor; el GPS y la cámara se piden igual |
| App nativa o Flutter / React Native | Medio | Generar el cliente desde `docs/openapi.json`; la lógica de cola y de precisión (`js/cola.js`, `js/ubicacion.js`) está escrita para trasladarse |
| Otra ciudad | Bajo | Cambiar `zona` y `categorias` en `configuracion.json` |
| Otro servidor | Bajo | `Dockerfile` y `render.yaml` incluidos; el servidor no guarda estado propio |

## Escalabilidad sin salir del plan gratuito

Medido: un reporte sin foto ocupa **unos 490 bytes** (con índices). Una base de PostGIS vacía ocupa ~16 MB. Una foto reducida (800 px) suele
pesar 60 a 200 KB.

| Escenario (Neon gratuito: 1 GB por proyecto) | Capacidad aproximada |
|---|---|
| Solo reportes sin foto | más de 1 800 000 |
| Con una foto de 100 KB cada 5 reportes | unos 40 000 |
| Todos con foto de 100 KB | unos 9 500 |
| Meta del piloto (300 observaciones, fotos en la mitad) | menos del 3 % |

Medir lo real: `python tareas.py capacidad` o el panel de administración (muestra uso, nivel de aviso y reportes restantes estimados). El estimado es prudente: mientras hay pocos datos supone que el 30 % de los reportes lleva una foto de 100 KB, y se afina solo con los datos reales.
Los límites de los planes gratuitos cambian: revísalos al crear cuentas y cada vez que el panel avise.

### Si algún día se acerca el límite (escalera, de menos a más trabajo)

| Nivel | Cuándo | Qué hacer | Mantenimiento |
|---|---|---|---|
| 0. Hoy | < 70 % | Nada. Revisar el panel una vez por semana | Ninguno |
| 1. Respaldar y limpiar | 70 % | `exportar`; borrar fotos descartadas; bajar `foto_max_lado_px` o `foto_calidad` en `configuracion.json` (las fotos pesan menos) | Mínimo |
| 2. Fotos fuera de la base | 90 % | Mover solo las fotos a un almacén de archivos (Cloudflare R2, Backblaze B2 u Object Storage de Neon, verificar planes). La base guarda solo la dirección. Cambio acotado: `fotos.py`, `repositorio.py` y dos rutas | Medio, una vez |
| 3. Otra base | Si todo lo anterior no alcanza | Mismo PostgreSQL en otro proveedor (`pg_dump` / `pg_restore`), o plan de pago de Neon (cobra por uso) | Bajo |
| 4. Servidor propio | Operación permanente | Docker en un VPS pequeño o servidor institucional | Alto (respaldos y actualizaciones los hace el equipo) |

Neon **no condiciona el desarrollo**: es PostgreSQL estándar. Todo lo que usa PostGIS (`ST_DWithin`, índices GiST) funciona igual en cualquier
PostgreSQL con PostGIS, y la capa `repositorio.py` es el único lugar con SQL.

### Rendimiento (qué ya está resuelto)
- *Pool* de conexiones, respuestas comprimidas (gzip), paginación, índices por fecha/categoría/estado/ubicación.
- Cifras del servidor: prueba de carga en una máquina de desarrollo con base local: ~275 reportes por segundo con 12 envíos simultáneos (mediana 39 ms, p95 89 ms). Con Neon en la nube se suma la latencia de red (decenas de ms por consulta) y el servicio gratuito de Render tarda ~1 min en despertar tras 15 min sin uso. Medir en tu entorno: `python analisis/prueba_carga.py`.
- Calidad: 20 000 reportes en ~1,5 s.

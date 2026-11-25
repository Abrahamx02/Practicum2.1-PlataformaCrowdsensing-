# Seguridad y protección de datos

## Principios
1. **Minimizar**: solo se guarda lo necesario. No hay nombres, correos, teléfonos, cédulas ni direcciones IP en la base (hay una prueba que lo exige).
2. **Seudonimizar**: cada celular crea un código aleatorio (`p-xxxxxxxxxx`). Es el único identificador del participante.
3. **Consentimiento primero**: no se toma ni se guarda la ubicación sin aceptar el consentimiento (versionado en cada reporte).
4. **Derecho a retirarse**: el participante se retira solo desde la pestaña Ayuda (borra reportes, fotos y encuestas); el administrador también puede, y todo queda en la auditoría.
5. **Mínimo privilegio**: tres roles con claves distintas.

## Qué protege cada capa

| Amenaza | Medida | Dónde / prueba |
|---|---|---|
| Espiar datos en tránsito | HTTPS en Render, `sslmode=require` hacia la base, HSTS (el navegador recuerda usar HTTPS) | `registro.py`, `verificar.py`, `test_basico` |
| Datos en reposo | Neon cifra en reposo y fuerza TLS (según su documentación de seguridad); fotos pequeñas y sin EXIF | proveedor + `foto.js` |
| Adivinar claves | Comparación en tiempo constante; bloqueo de 1 min tras 10 fallos por IP (429) | `seguridad.py`, `test_bloqueo...` |
| Inundar con reportes falsos | Límite de 30 envíos por minuto por IP (detrás de Render se usa la IP que agrega el proxy, variable `CONFIAR_EN_PROXY=1`; si no, nadie puede esquivarlo escribiendo `X-Forwarded-For`); cuerpos de más de 1 MB se rechazan sin leerlos; `id_cliente` evita duplicados | `seguridad.py`, `test_limite...` |
| Datos mal formados o maliciosos | Validación estricta: rangos, NaN/infinito, fechas, longitudes, patrones, caracteres de control | `esquemas.py`, `test_validaciones...` |
| Inyección de SQL | Todas las consultas usan parámetros (`%s`); nunca se arma SQL con texto del usuario | `repositorio.py` |
| Fórmulas maliciosas en Excel (CSV) | Los textos que empiezan con `= + - @` se neutralizan al exportar | `rutas_datos.py`, `test_exportar_csv...` |
| Archivos disfrazados de foto | Solo JPEG (firma de bytes), tamaño máximo; el navegador la recomprime | `fotos.py`, `test_fotos` |
| Scripts inyectados en la página (XSS) | CSP estricta (solo recursos propios), el formulario usa `textContent` y no `innerHTML` con datos de usuario | `registro.py`, `test_cabeceras...` |
| Clickjacking y sniffing | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` | `registro.py` |
| Acciones sin rastro | Auditoría de importar, calidad, borrar fotos y retirar participantes (el código del participante se guarda como huella, no completo) | `eventos`, `test_retirar...` |
| Errores que filtran detalles | Los errores 500 devuelven un mensaje general y un identificador; el detalle queda solo en el registro del servidor | `errores.py` |

## Claves y secretos
- Viven solo en `.env` (tu computador) y en las variables de entorno de Render. **Nunca en Git** (`.gitignore` y `git status`).
- `python tareas.py crear-env` genera claves aleatorias largas. `python tareas.py verificar` avisa si son cortas o repetidas.
- La clave del rol **participante** no es secreta: cualquiera que abre el formulario la recibe (`/configuracion`). Solo sirve para enviar reportes y está limitada por tasa. Las de **analista** y **administrador** nunca salen del servidor.
- **Rotar una clave**: cambia la variable en Render (y en tu `.env`), reinicia. El formulario vuelve a pedirla solo; los reportes pendientes en celulares se reenvían con la nueva.
- **Si se filtra algo** (clave en Git, captura con la cadena de Neon): 1) cambia la contraseña en Neon y las tres claves, 2) actualiza Render y `.env`, 3) `git rm --cached` del archivo y nuevo commit (el historial conserva el valor viejo: por eso se cambia), 4) revisa la auditoría.

## Retención y respaldo
- Los datos se conservan solo durante el Prácticum y su evaluación (confirmar plazo con la tutora; está en el consentimiento).
- Respaldos: `python tareas.py exportar` (CSV y GeoJSON con huella sha256). Guardarlos fuera de Git, en dos lugares.
- Las fotos con rostros o placas se descartan desde el panel de administración antes de entregar el dataset.

## Limitaciones conocidas (honestas)
- No hay cuentas de usuario: la protección del participante es la clave del formulario + límite de tasa. Alcanza para un piloto de 15 a 25 voluntarios; para un lanzamiento abierto habría que agregar cuentas o verificación (ver `PORTABILIDAD_Y_ESCALABILIDAD.md`).
- El límite de tasa vive en memoria de un servidor: con varios servidores habría que moverlo a la base o a un servicio externo.
- La clave del administrador es una sola y compartida. Para equipos más grandes conviene una clave por persona.
- El panel de administración guarda la clave en `sessionStorage` solo mientras la pestaña está abierta.
- La ubicación es dato personal sensible: aunque se seudonimiza, muchos puntos de una misma persona podrían revelar rutinas. Por eso el dataset que se publique debe quitar el código de participante o agruparlo (ficha del dataset).

## Novedades de la versión 4: menos cosas a la vista

| Medida | Qué evita |
|---|---|
| `/docs` y `/openapi.json` apagados (`HABILITAR_DOCS=0`); el administrador ve la API dentro del panel | Que cualquiera conozca todas las rutas de la API |
| `/salud` solo dice `ok`; versión, PostGIS y hora salen en `/servidor` (administrador) | Revelar versiones a quien busca fallos conocidos |
| `/configuracion` pública solo trae lo que el formulario necesita (sin metas del piloto ni reglas de calidad) | Que se conozca cómo se puntúa para engañar al control |
| El panel guarda un **permiso que vence** (8 h, firmado, anulable) y no la clave de administrador | Robo de la clave desde el navegador |
| Sin cabecera `Server`; `X-Robots-Tag: noindex`; `Cross-Origin-*` en `same-origin` | Fingerprinting e indexación en buscadores |
| El participante no ve por qué se marcó una señal antifraude, solo «el equipo lo revisa» | Aprender a esquivar las reglas |
| Contenedor sin permisos de administrador (usuario `mcs`) | Daño mayor si alguien lograra entrar al contenedor |
| Límite también en las consultas «parecidos», «mis reportes» y «retirarme» | Consultas en masa para adivinar códigos |
| Revisión de seguridad en vivo (panel → Sistema → Seguridad) y 6 señales de confianza en la calidad | Descubrir tarde un problema de configuración o datos falsos |
| **Modo presentación** (ojo en la barra del panel): desenfoca códigos y ubicaciones | Mostrar datos sin querer al compartir pantalla |

Límite honesto: la clave del formulario sigue siendo pública por diseño (cualquiera con la dirección puede enviar). Alcanza para un piloto de
15 a 25 voluntarios; no para un lanzamiento abierto.

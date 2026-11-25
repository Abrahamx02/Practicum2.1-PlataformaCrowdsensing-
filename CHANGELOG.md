# Historial de cambios

Formato: `MAYOR.MENOR.PARCHE`. Cada versión dice **qué cambia**, **qué debe hacer el equipo** y **qué se rompe**.

## 4.0.0 · 2026-11-22

### Qué cambia
- **Todo en un solo panel** (`/admin/`): Inicio, Mapa, Reportes, Calidad, Participantes, Sistema y Defensa. Se eliminó el dashboard de Streamlit.
- **La calidad se calcula en el servidor** al llegar cada reporte (antes dependía de un script aparte, por eso el puntaje salía «sin calcular»). Se puede recalcular, decidir a mano y calibrar los umbrales.
- **Señales de confianza** (ubicación a mano, en movimiento, salto imposible, ráfaga, coordenadas redondeadas, precisión sospechosa).
- **«Otro» necesita descripción o foto** (en la app y en el servidor; mínimo configurable en `configuracion.json`).
- **Ubicación mejor**: varias lecturas del GPS con promedio ponderado, velocidad, mini mapa con círculo de precisión y corrección del punto (máximo 150 m).
- **App del participante con pestañas**: Mis reportes (cómo le fue a cada uno), Ayuda (tips, privacidad, retirarse, encuesta) y modo claro/oscuro/automático.
- **Defensa en el panel**: entregables con evidencia, «Prueba en vivo» (20 comprobaciones que no dejan datos), informe del piloto, ficha del dataset y encuesta de experiencia.
- **Datos**: paquete ZIP versionado (crudo, depurado, GeoJSON, diccionario, huellas), importación con fecha original y datos de ejemplo que se pueden quitar.
- **Seguridad**: documentación pública apagada, `/salud` mínimo, sesión con vencimiento, revisión de seguridad en vivo, contenedor sin root. Ver `docs/SEGURIDAD.md`.
- **Diseño nuevo** con animaciones suaves, botones uniformes y hojas inferiores; un solo `estilo.css` y `iconos.svg`.
- Migraciones 006 y 007 (se aplican solas). 99 pruebas de Python y 15 de JavaScript.

### Qué debe hacer el equipo
- Reconstruir el contenedor: `docker compose up --build`. Los datos existentes se conservan y la calidad pendiente se calcula al encender.
- Poner `CONFIAR_EN_PROXY=1` en `.env` si usan túnel o Render. Cambiar las claves si estuvieron expuestas.

### Qué se rompe
- `/docs` y `/openapi.json` ya no existen públicamente (usar el panel o `HABILITAR_DOCS=1` solo en desarrollo).
- `/salud` ya no devuelve versión ni PostGIS (usar `/servidor` con la clave de administrador). `/configuracion` ya no trae `piloto`, `duplicado` ni `version_api`.
- El panel usa sesión (`x-sesion`) en lugar de enviar la clave en cada petición (la clave en `x-clave` sigue sirviendo para otros clientes).

## 3.0.0 · 2026-11-18

### Qué cambia
- **Backend en capas**: configuración, base de datos con *pool* de conexiones, migraciones versionadas, seguridad por roles, errores en español con formato común, registro con identificador de solicitud y repositorio de consultas SQL.
- **API versionada** en `/api/v1`. Nuevas rutas: `/configuracion`, `/estadisticas`, `/capacidad`, `/reportes/{id}`, `/reportes/cercanos`, `/reportes/similares`, `/auditoria`.
- **Idempotencia**: cada reporte lleva un `id_cliente`; si el celular lo reenvía, no se duplica.
- **Seguridad**: comparación de claves en tiempo constante, bloqueo por intentos fallidos, límite de envíos por IP, cabeceras de seguridad (CSP, HSTS, etc.), validación estricta (fechas, texto, números, fotos JPEG), protección contra fórmulas en el CSV y auditoría de acciones del administrador.
- **Formulario nuevo** en tres pasos, con diseño sobrio, modo oscuro, medidor de precisión del GPS, aviso de reporte similar cercano, envío sin conexión y módulos de JavaScript con pruebas.
- **Panel de administración** (`/admin/`): resumen del piloto, almacenamiento, revisión de fotos, retiro de participantes, auditoría y exportación.
- **Calidad**: configuración compartida con el servidor (`configuracion.json`), más rápida (20 000 reportes en ~1,5 s), con motivo de cada decisión y resumen por participante.
- **Dashboard rediseñado** con pestañas, mapa, calidad, participación y descargas.
- Resistencia a fallos de la base de datos (503 en español y recuperación automática), cuerpo máximo de 1 MB, IP detrás de proxy solo con `CONFIAR_EN_PROXY=1`.
- 69 pruebas de Python (API, calidad y cumplimiento de las indicaciones) y 14 de JavaScript.
- Comandos unificados (`tareas.py`), autodiagnóstico (`verificar.py`), prueba de carga, Docker, `render.yaml` y pruebas de CI.

### Qué debe hacer el equipo
1. Seguir `docs/PROTOCOLO_DE_ACTUALIZACION.md`.
2. Las claves del formulario ya no se escriben en `app.js`: el servidor las entrega en `/api/v1/configuracion`.
3. `backend/schema.sql` desaparece: las tablas se crean con las migraciones (se adoptan las bases que ya existían).

### Qué se rompe
- Las rutas antiguas sin prefijo (`/reportes`, `/exportar.csv`...) ahora son `/api/v1/...`.
- `GET /api/v1/reportes` devuelve `{cantidad, siguiente, datos}` (paginado) en vez de una lista.

## 2.x
Versiones anteriores (puntaje de calidad, GeoJSON, roles, envío sin conexión, retiro de participantes).

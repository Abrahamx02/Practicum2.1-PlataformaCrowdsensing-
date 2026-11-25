# Observatorio urbano · Loja (MCS Loja)

Prototipo de plataforma de **Mobile Crowdsensing** para analítica urbana (Prácticum 2.1, UTPL).
Las personas reportan problemas de la ciudad desde el celular (con ubicación y foto opcional); el sistema guarda los reportes,
**evalúa su calidad con un puntaje de 0 a 100** y todo se ve y se administra desde **un solo panel web**.

Equipo: Emilio Cueva, Abraham Ayala y Carlos Correa.

## Qué incluye

| Pieza | Para quién | Dónde |
|---|---|---|
| App del participante (PWA, funciona sin internet): Reportar, Mis reportes y Ayuda; modo claro y oscuro | Participante | `http://127.0.0.1:8000/` |
| **Panel del equipo**: Inicio, Mapa, Reportes, Calidad, Participantes, Sistema y Defensa | Administrador | `http://127.0.0.1:8000/admin/` |
| API REST versionada (`/api/v1`); su documentación se ve dentro del panel (Sistema → API) | Programadores y otras apps | — |
| Comandos del proyecto | Equipo | `python tareas.py` |

No hay pantallas aparte en Python: el dashboard, el control de calidad, la prueba del sistema, el informe del piloto y la ficha del
dataset viven dentro del panel. La carpeta `analisis/` conserva los scripts de validación v1 en pandas (para analizar un CSV fuera del servidor). Las seis dimensiones, los pesos y los umbrales son los mismos que en el servidor (`backend/calidad.py`); difiere en dos cosas: aquí una descripción vacía cuenta como dato faltante y no se calculan las señales de confianza.

## Empezar con Docker (lo más fácil)

```
python tareas.py crear-env            (crea .env con tres claves nuevas al azar)
docker compose up --build
```

Abre `http://127.0.0.1:8000/admin/` y entra con `CLAVE_ADMIN`. Las tablas se crean solas (migraciones automáticas).
Para probar desde un celular, usa un túnel HTTPS (el GPS y la cámara lo exigen):  `cloudflared tunnel --url http://localhost:8000`.

## Empezar sin Docker (con Neon)

```
python -m venv venv
venv\Scripts\activate                      (Mac/Linux: source venv/bin/activate)
pip install -r requirements-local.txt
python tareas.py crear-env "CADENA_DE_CONEXION_DE_NEON"
python tareas.py iniciar
```

## Cada día

| Comando | Qué hace |
|---|---|
| `python tareas.py iniciar` | Enciende el servidor |
| `python tareas.py dashboard` | Abre el panel del equipo en el navegador |
| `python tareas.py probar` | Pruebas automáticas (para desarrollar; en la defensa se usa «Prueba en vivo» del panel) |
| `python tareas.py capacidad` | Cuánto espacio gratuito de la base queda |
| `python tareas.py exportar` | Descarga CSV y GeoJSON con fecha y huella |

## Los tres roles

| Rol | Clave (en `.env`) | Puede |
|---|---|---|
| Participante | `CLAVE_ESCRITURA` | Enviar reportes y ver/borrar los suyos (la usa la app) |
| Analista | `CLAVE_LECTURA` | Leer, filtrar y exportar |
| Administrador | `CLAVE_ADMIN` | Todo: decidir reportes, importar, datos de ejemplo, fotos, retirar participantes, seguridad |

## Documentación

- [Guion de la demostración](docs/GUION_DEFENSA.md) · [Auditoría de la versión 4](docs/AUDITORIA_V4.md)
- [Arquitectura](docs/ARQUITECTURA.md) · [Seguridad y protección de datos](docs/SEGURIDAD.md)
- [Cumplimiento de las indicaciones del grupo de investigación](docs/CUMPLIMIENTO_INDICACIONES.md)
- [Portabilidad y escalabilidad](docs/PORTABILIDAD_Y_ESCALABILIDAD.md) · [Cómo actualizar](docs/PROTOCOLO_DE_ACTUALIZACION.md) · [Cómo trabajar con ramas](CONTRIBUTING.md)
- [Diccionario de datos](docs/diccionario_datos.md) · [Contrato de datos](docs/contrato_datos.md) · [Cambios entre versiones](CHANGELOG.md)

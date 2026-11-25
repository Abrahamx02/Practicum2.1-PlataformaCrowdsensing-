# Seguridad

Este es un proyecto académico (prácticas pre-profesionales, UTPL, Loja). No hay una versión «de producción», pero se cuidan los datos de las
personas que participan en el piloto.

## Cómo avisar de un problema de seguridad

Si encuentras una falla (por ejemplo una forma de ver datos sin clave), **no la publiques en un *issue* abierto**. Escribe por mensaje privado a
quienes mantienen el repositorio (los tres integrantes del equipo aparecen en el README) o abre un *Security advisory* privado desde la pestaña
*Security* del repositorio. Responderemos lo antes posible y anotaremos la corrección en el `CHANGELOG.md`.

## Qué nunca debe subirse

El archivo `.env`, claves, cadenas de conexión a la base de datos, respaldos de la base (`.dump`), paquetes de datos descargados (`.zip`),
fotos de participantes ni listas con nombres. El `.gitignore` bloquea los más comunes; revisa `git status` antes de cada commit.

## Si una clave se expuso

Cámbiala de inmediato (en el `.env` local, en Render y en Neon) y reinicia el servicio. Borrar el archivo del repositorio no basta: queda en el historial.

## Qué medidas tiene el sistema

Están descritas en [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) y se revisan en vivo desde el panel (Sistema → Seguridad).

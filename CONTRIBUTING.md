# Cómo trabajar en el repositorio

**Regla de oro: `main` siempre funciona.** Render publica desde `main`; si algo roto entra, se rompe para todos.
Por eso **nadie hace commit directo a `main`**: todo entra por una rama y un Pull Request revisado.

## Ciclo de cada tarea

```
git checkout main
git pull
git checkout -b feat/nombre-corto
   ... trabajar ...
python tareas.py probar
git add -A
git commit -m "feat: explica en una línea qué hiciste"
git push -u origin feat/nombre-corto
gh pr create --fill --base main
```

1. En GitHub, **otra persona** (no quien lo escribió) revisa la pestaña *Files changed*, comenta y aprueba.
2. Esperar la marca verde de las pruebas automáticas (Actions).
3. Unir con **Squash and merge** y borrar la rama. Excepción: una entrega grande (por ejemplo una versión nueva) con varios commits bien explicados se une con **Create a merge commit**, para conservar el historial.
4. Todos: `git checkout main` y `git pull`.

## Nombres de ramas

| Prefijo | Para qué | Ejemplo |
|---|---|---|
| `feat/` | Una función nueva | `feat/filtro-por-fecha` |
| `fix/` | Corregir un error | `fix/precision-en-iphone` |
| `docs/` | Solo documentación | `docs/manual-de-usuario` |
| `test/` | Solo pruebas | `test/casos-de-fotos` |
| `chore/` | Mantenimiento, configuración | `chore/actualizar-librerias` |

Una rama = una tarea = un Pull Request. Las ramas viven 1 o 2 días. Si `main` avanzó, trae sus cambios con
`git pull origin main` estando en tu rama.

## Mensajes de commit

`tipo: qué se hizo` en una línea, en presente. Ejemplos: `feat: agrega aviso de reporte similar`, `fix: corrige el orden lon/lat`, `docs: explica el retiro de participantes`.

## Tareas y tablero

Toda tarea es un *issue* (plantillas en `.github/ISSUE_TEMPLATE`). En el Pull Request se escribe `Closes #número`
para que el issue se cierre solo. Etiquetas: `tarea`, `bug`, y la prioridad.

## Versiones

Cada entrega importante se marca con una etiqueta: `git tag -a v4.0.0 -m "Versión 4.0.0"` y `git push origin v4.0.0`. Ver `docs/PUBLICAR_UNA_VERSION.md`. Los cambios se anotan en `CHANGELOG.md`.

## Qué nunca se sube

El archivo `.env`, claves, datos reales de participantes (`crudo*.csv`), fotos, y la carpeta `venv`. Antes de cada commit, `git status` lo muestra.
Si por error subes una clave, cámbiala de inmediato (ver `docs/SEGURIDAD.md`).

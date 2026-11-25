# Qué hacer cuando llega una versión nueva del proyecto

Cada versión nueva viene en un `.zip` con su entrada en `CHANGELOG.md` (qué cambia, qué debes hacer, qué se rompe).
**Nunca copies el zip encima de tu carpeta a mano**: usa `tareas.py actualizar`, que no toca tus claves, tu bitácora ni tus datos.

## Pasos (en la carpeta del proyecto, con el entorno virtual activo)

```
git checkout main
git pull
git checkout -b chore/actualizacion-X.Y.Z

python tareas.py actualizar "C:\ruta\al\proyecto.zip"            <- solo MIRA qué cambiaría
python tareas.py actualizar "C:\ruta\al\proyecto.zip" --aplicar  <- aplica los cambios

pip install -r requirements-local.txt
python tareas.py migrar
python tareas.py probar
python tareas.py verificar

git status
git diff --stat
git add -A
git commit -m "chore: actualiza a la version X.Y.Z"
git push -u origin chore/actualizacion-X.Y.Z
gh pr create --fill --base main
```

Luego otra persona revisa el Pull Request, se espera la marca verde y se une con *Squash and merge*. Después:

```
git checkout main
git pull
git tag vX.Y.Z
git push --tags
```

## Qué nunca se sobrescribe
`.env`, `venv/`, `.git/`, `README.md`, `docs/bitacora.md`, `docs/pruebas_celulares.md`, y los datos
(`analisis/datos/crudo*`, `exportaciones/`, `fotos_para_revisar/`).

## Si algo falla
| Situación | Qué hacer |
|---|---|
| `probar` o `verificar` fallan | No hagas commit. Lee el mensaje; si no lo entiendes, pásalo con el nombre de la versión. |
| Quieres volver atrás antes de commit | `git checkout .` descarta todos los cambios sin commit (los archivos nuevos se borran con `git clean -fd`). |
| Ya hiciste commit y quieres deshacerlo | `git reset --soft HEAD~1` (conserva los cambios) o simplemente cierra el Pull Request sin unir. |
| Cambió la base de datos | `tareas.py migrar` aplica solo lo que falta; las migraciones nunca borran datos (se revisan antes de entregarse). |
| El servidor ya publicado | Se actualiza solo cuando unes el Pull Request a `main` (Render vuelve a publicar). Revisa `/api/v1/salud`. |

## Reglas de este protocolo
1. Una versión nueva **siempre** entra por rama y Pull Request, nunca directo a `main`.
2. Antes de unir: `probar` y `verificar` sin fallas, y el CI en verde.
3. El piloto en marcha **no se actualiza** salvo errores graves (el contrato de datos no cambia desde el 10 de diciembre).
4. Si dos personas actualizan a la vez, solo una crea la rama; la otra espera a que se una y hace `git pull`.

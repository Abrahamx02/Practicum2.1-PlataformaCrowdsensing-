# Cómo publicar una versión nueva

Una versión nueva entra por una rama y un Pull Request, como cualquier cambio (ver `CONTRIBUTING.md`). Lo que cambia es el cierre: se
une conservando los commits y se marca con una etiqueta.

1. **Rama desde `main` actualizado:** `git switch main`, `git pull`, `git switch -c release/vX.Y.Z`.
2. **Cambios en commits pequeños y explicados:** un commit por tema (base de datos, API, calidad, app, panel, documentación…), con título
   corto en presente y un párrafo que cuente el porqué. Formato: `tipo(ámbito): qué se hizo` (`feat`, `fix`, `docs`, `test`, `chore`).
3. **Antes de subir:** `python tareas.py probar` y `git status`. No debe aparecer `.env` ni ningún `.zip`.
4. **Pull Request:** `git push -u origin release/vX.Y.Z` y abrirlo en GitHub. Otra persona revisa *Files changed*; esperar la marca verde de Actions.
5. **Unir con «Create a merge commit»** (no *squash*) y borrar la rama.
6. **Etiquetar:** `git switch main`, `git pull`, `git tag -a vX.Y.Z -m "Versión X.Y.Z"`, `git push origin vX.Y.Z`.
7. **Release en GitHub:** *Releases → Draft a new release*, elegir la etiqueta y pegar la sección de ese número del `CHANGELOG.md`.
8. **Desplegar:** si hay Render conectado, el *push* a `main` redespliega solo. Después, abrir el panel y correr Defensa → Prueba en vivo.

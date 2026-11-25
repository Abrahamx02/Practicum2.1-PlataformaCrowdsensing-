# Comandos del proyecto en un solo lugar. Uso:  python tareas.py COMANDO
#
#   iniciar        enciende el servidor (formulario, panel de administracion y API) en http://127.0.0.1:8000
#   probar         ejecuta todas las pruebas (Python y JavaScript)
#   verificar      revisa la configuracion y que todo funcione
#   migrar         aplica los cambios pendientes de la base de datos
#   dashboard      abre el panel del equipo (mapa, calidad, defensa) en el navegador
#   capacidad      muestra cuanto espacio de la base de datos se usa
#   crear-env CADENA   crea el archivo .env con claves aleatorias (CADENA es la de conexion de Neon)
#   exportar       descarga CSV y GeoJSON con fecha y huella (el servidor debe estar encendido)
#   openapi        guarda la especificacion de la API en docs/openapi.json
#   limpiar-pruebas  borra los reportes de prueba (participantes "prueba-" y "verificar-")
#   actualizar ZIP [--aplicar]   mira (o aplica) los cambios de una version nueva del proyecto
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
os.chdir(RAIZ)


def ejecutar(comando, **opciones):
    print("> " + " ".join(comando))
    return subprocess.call(comando, **opciones)


def iniciar():
    sys.exit(ejecutar([sys.executable, "-m", "uvicorn", "backend.main:app", "--reload"]))


def probar():
    codigo = ejecutar([sys.executable, "-m", "pytest", "-q"])
    if shutil.which("npm"):
        codigo = ejecutar(["npm", "test", "--silent"], shell=(os.name == "nt")) or codigo
    else:
        print("(npm no esta instalado: se omiten las pruebas de JavaScript)")
    sys.exit(codigo)


def verificar():
    sys.exit(ejecutar([sys.executable, "verificar.py"]))


def migrar():
    from backend.base import aplicar_migraciones
    aplicadas = aplicar_migraciones()
    print("Migraciones aplicadas:", ", ".join(aplicadas) if aplicadas else "ninguna (todo al dia)")


def dashboard():
    # el dashboard ya no es una pantalla aparte: es el panel del equipo, dentro del mismo servidor
    import webbrowser
    webbrowser.open("http://127.0.0.1:8000/admin/")
    print("Abierto http://127.0.0.1:8000/admin/  (el servidor debe estar encendido: docker compose up)")


def capacidad():
    import psycopg
    from dotenv import load_dotenv
    load_dotenv()
    with open("configuracion.json", encoding="utf-8") as f:
        limite = json.load(f)["capacidad"]["limite_bytes"]
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        usado, fotos, reportes = con.execute("SELECT pg_database_size(current_database()), (SELECT count(*) FROM fotos), (SELECT count(*) FROM reportes)").fetchone()
    print("Usado: %.1f MB de %.0f MB (%.2f %%)" % (usado / 1e6, limite / 1e6, 100 * usado / limite))
    print("Reportes:", reportes, "| fotos:", fotos)
    if usado / limite > 0.9:
        print("ALERTA: casi sin espacio. Descarga un respaldo (exportar) y revisa 'Escalabilidad' en docs/ARQUITECTURA.md")


def crear_env(cadena):
    if os.path.exists(".env"):
        sys.exit("Ya existe un .env. Borralo a mano si quieres crear uno nuevo (se perderian tus claves).")
    if not cadena.startswith("postgres"):
        sys.exit("La cadena de conexion debe empezar con postgresql://")
    texto = ("DATABASE_URL=" + cadena + "\nCLAVE_ESCRITURA=" + secrets.token_urlsafe(18) + "\nCLAVE_LECTURA=" + secrets.token_urlsafe(18)
             + "\nCLAVE_ADMIN=" + secrets.token_urlsafe(18) + "\nAPI_URL=http://127.0.0.1:8000\nCONFIAR_EN_PROXY=0\n")
    with open(".env", "w", encoding="utf-8", newline="\n") as archivo:
        archivo.write(texto)
    print("Listo: se creo .env con tres claves aleatorias. No lo subas a Git. Para ver las claves, abre el archivo .env")


def exportar():
    sys.exit(ejecutar([sys.executable, "analisis/exportar_version.py"]))


def openapi():
    from backend.main import app
    with open("docs/openapi.json", "w", encoding="utf-8") as archivo:
        json.dump(app.openapi(), archivo, ensure_ascii=False, indent=2)
    print("Guardado docs/openapi.json (sirve para generar un cliente movil: iOS, Android, Flutter...)")


def limpiar_pruebas():
    import psycopg
    from dotenv import load_dotenv
    load_dotenv()
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        n = con.execute("WITH b AS (DELETE FROM reportes WHERE participante_id LIKE 'prueba-%' OR participante_id LIKE 'verificar-%' RETURNING 1) SELECT count(*) FROM b").fetchone()[0]
        con.execute("DELETE FROM fotos WHERE id NOT IN (SELECT foto_id FROM reportes WHERE foto_id IS NOT NULL)")
    print("Reportes de prueba borrados:", n)


# ---------- actualizar con una version nueva del proyecto ----------
# Estos archivos y carpetas son del equipo o contienen datos: nunca se tocan.
PROTEGIDOS_EXACTOS = {".env", "docs/bitacora.md", "docs/pruebas_celulares.md", "README.md"}
PROTEGIDOS_PREFIJOS = ("venv/", ".venv/", ".git/", "node_modules/", "analisis/datos/exportaciones/", "analisis/datos/fotos_para_revisar/",
                       "analisis/datos/crudo")


def protegido(ruta):
    return ruta in PROTEGIDOS_EXACTOS or ruta.startswith(PROTEGIDOS_PREFIJOS) or "__pycache__" in ruta or ruta.endswith(".pyc")


def actualizar(ruta_zip, aplicar):
    if not os.path.exists(ruta_zip):
        sys.exit("No encuentro el archivo: " + ruta_zip)
    with tempfile.TemporaryDirectory() as temporal:
        with zipfile.ZipFile(ruta_zip) as z:
            z.extractall(temporal)
        origen = temporal
        # el zip puede traer una carpeta raiz (mcs-piloto/...): se busca donde esta configuracion.json
        for carpeta, _, archivos in os.walk(temporal):
            if "configuracion.json" in archivos:
                origen = carpeta
                break
        nuevos, cambiados, iguales, omitidos, en_zip = [], [], 0, [], set()
        for carpeta, _, archivos in os.walk(origen):
            for nombre in archivos:
                completa = os.path.join(carpeta, nombre)
                relativa = os.path.relpath(completa, origen).replace("\\", "/")
                en_zip.add(relativa)
                if protegido(relativa):
                    omitidos.append(relativa)
                    continue
                destino = os.path.join(RAIZ, relativa)
                if not os.path.exists(destino):
                    nuevos.append(relativa)
                elif open(completa, "rb").read() != open(destino, "rb").read():
                    cambiados.append(relativa)
                else:
                    iguales += 1
                    continue
                if aplicar:
                    os.makedirs(os.path.dirname(destino), exist_ok=True)
                    shutil.copy2(completa, destino)
        sobran = []
        for carpeta_raiz in ("backend", "frontend", "analisis", "pruebas_frontend"):
            for carpeta, _, archivos in os.walk(os.path.join(RAIZ, carpeta_raiz)):
                for nombre in archivos:
                    relativa = os.path.relpath(os.path.join(carpeta, nombre), RAIZ).replace("\\", "/")
                    if relativa not in en_zip and not protegido(relativa) and "analisis/datos/" not in relativa:
                        sobran.append(relativa)
    titulo = "SE APLICARON" if aplicar else "SIMULACION (no se cambio nada)"
    print("\n=== " + titulo + " ===")
    print("Nuevos (%d):" % len(nuevos)); [print("   + " + r) for r in nuevos]
    print("Modificados (%d):" % len(cambiados)); [print("   ~ " + r) for r in cambiados]
    print("Sin cambios:", iguales, "| Protegidos (no se tocan):", len(omitidos))
    if sobran:
        print("\nArchivos que la version nueva ya no trae (puedes borrarlos con git rm si ya no sirven):")
        [print("   - " + r) for r in sobran]
    if not aplicar:
        print("\nSi todo se ve bien, aplica con:  python tareas.py actualizar \"" + ruta_zip + "\" --aplicar")
    else:
        print("\nSiguientes pasos:\n  1. git status  y  git diff  (revisa los cambios)\n  2. python tareas.py migrar\n  3. python tareas.py probar\n  4. python tareas.py verificar\n"
              "  5. git add -A, git commit, git push y abre el Pull Request")


def main():
    if len(sys.argv) < 2:
        print(__doc__ if __doc__ else open(__file__, encoding="utf-8").read().split("import json")[0])
        return
    comando = sys.argv[1]
    if comando == "actualizar":
        if len(sys.argv) < 3:
            sys.exit("Uso: python tareas.py actualizar RUTA_DEL_ZIP [--aplicar]")
        return actualizar(sys.argv[2], "--aplicar" in sys.argv)
    if comando == "crear-env":
        # sin cadena: sirve para Docker (la base viene en docker-compose); con cadena: para Neon u otra base
        return crear_env(sys.argv[2] if len(sys.argv) > 2 else "postgresql://mcs:mcs@127.0.0.1:5433/mcs")
    comandos = {"iniciar": iniciar, "probar": probar, "verificar": verificar, "migrar": migrar, "dashboard": dashboard,
                "capacidad": capacidad, "exportar": exportar, "openapi": openapi, "limpiar-pruebas": limpiar_pruebas}
    if comando not in comandos:
        sys.exit("Comando desconocido: " + comando + ". Escribe  python tareas.py  para ver la lista.")
    comandos[comando]()


main()

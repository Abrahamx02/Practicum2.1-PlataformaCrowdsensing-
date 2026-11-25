# Revisa que todo este bien configurado y funcionando. Uso:  python verificar.py
# Prueba el servidor "por dentro" (sin encender uvicorn) con la base de datos del archivo .env.
import os
import re
import sys

OK, FALLA, AVISO = "OK   ", "FALLA", "AVISO"
resultados = []


def anotar(estado, nombre, detalle=""):
    resultados.append((estado, nombre, detalle))
    print("[" + estado + "] " + nombre + ((" - " + detalle) if detalle else ""))


def revisar_entorno():
    anotar(OK if sys.version_info >= (3, 11) else FALLA, "Version de Python", sys.version.split()[0] + " (se necesita 3.11 o mayor)")
    if not os.path.exists(".env") and not os.getenv("DATABASE_URL"):
        anotar(FALLA, "Archivo .env", "no existe. Crealo con:  python tareas.py crear-env \"CADENA_DE_NEON\"")
        return False
    from dotenv import load_dotenv
    load_dotenv()
    claves = {}
    for nombre in ("CLAVE_ESCRITURA", "CLAVE_LECTURA", "CLAVE_ADMIN"):
        valor = os.getenv(nombre, "")
        claves[nombre] = valor
        if not valor:
            anotar(FALLA, nombre, "falta en el .env")
        elif len(valor) < 12:
            anotar(AVISO, nombre, "es muy corta (usa 12 caracteres o mas)")
        else:
            anotar(OK, nombre, "definida")
    if len(set(v for v in claves.values() if v)) < len([v for v in claves.values() if v]):
        anotar(FALLA, "Claves distintas", "las tres claves deben ser diferentes")
    url = os.getenv("DATABASE_URL", "")
    if not url:
        anotar(FALLA, "DATABASE_URL", "falta en el .env")
        return False
    local = bool(re.search(r"@(localhost|127\.0\.0\.1|db)[:/]", url))
    if local or "sslmode=require" in url:
        anotar(OK, "Conexion cifrada (TLS)", "local" if local else "sslmode=require")
    else:
        anotar(FALLA, "Conexion cifrada (TLS)", "la cadena de la base debe terminar en ?sslmode=require")
    return all(claves.values())


def revisar_base():
    import psycopg
    from backend.base import aplicar_migraciones
    try:
        aplicadas = aplicar_migraciones()
        anotar(OK, "Base de datos", "conectada; migraciones nuevas aplicadas: " + (", ".join(aplicadas) or "ninguna"))
    except Exception as error:
        anotar(FALLA, "Base de datos", str(error).splitlines()[0][:150])
        return False
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        version = con.execute("SELECT postgis_version()").fetchone()[0].split(" ")[0]
        anotar(OK, "PostGIS", version)
        tablas = [f[0] for f in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'").fetchall()]
        faltan = [t for t in ("reportes", "fotos", "eventos", "migraciones") if t not in tablas]
        anotar(OK if not faltan else FALLA, "Tablas", "completas" if not faltan else "faltan: " + ", ".join(faltan))
    return True


def revisar_api():
    from datetime import datetime, timezone
    from fastapi.testclient import TestClient
    from backend import seguridad
    from backend.main import app
    E = {"x-clave": os.environ["CLAVE_ESCRITURA"]}
    L = {"x-clave": os.environ["CLAVE_LECTURA"]}
    A = {"x-clave": os.environ["CLAVE_ADMIN"]}
    seguridad.limite_fallos.registros = {}
    with TestClient(app) as c:
        r = c.get("/api/v1/salud")
        anotar(OK if r.status_code == 200 else FALLA, "API: /salud", r.text[:80])
        anotar(OK if c.get("/").status_code == 200 else FALLA, "Formulario web", "se entrega en /")
        anotar(OK if c.get("/admin/").status_code == 200 else FALLA, "Panel de administracion", "se entrega en /admin/")
        malo = c.get("/api/v1/reportes", headers=E).status_code == 401 and c.get("/api/v1/auditoria", headers=L).status_code == 401
        bueno = c.get("/api/v1/reportes", headers=L).status_code == 200 and c.get("/api/v1/auditoria", headers=A).status_code == 200
        anotar(OK if malo and bueno else FALLA, "Roles", "participante no lee, analista no administra, administrador puede todo")
        seguridad.limite_fallos.registros = {}
        dato = {"participante_id": "verificar-auto", "categoria": "otro", "descripcion": "prueba de verificacion",
                "lat": -3.9931, "lon": -79.2042, "precision_m": 10, "fecha_dispositivo": datetime.now(timezone.utc).isoformat(),
                "plataforma": "otro", "consentimiento": True}
        r = c.post("/api/v1/reportes", json=dato, headers=E)
        anotar(OK if r.status_code == 201 else FALLA, "Guardar un reporte", str(r.status_code) + " " + r.text[:80])
        if r.status_code == 201:
            leido = c.get("/api/v1/reportes/" + str(r.json()["id"]), headers=L)
            anotar(OK if leido.status_code == 200 and leido.json()["lat"] == -3.9931 else FALLA, "Leer el reporte guardado", "lat y lon correctas")
        borrado = c.delete("/api/v1/participantes/verificar-auto", headers=A)
        anotar(OK if borrado.status_code == 200 else FALLA, "Borrar el reporte de prueba", borrado.text[:60])
        cap = c.get("/api/v1/capacidad", headers=A)
        if cap.status_code == 200:
            d = cap.json()
            estado = OK if d["nivel"] == "ok" else AVISO
            anotar(estado, "Almacenamiento", str(d["porcentaje"]) + " % usado (" + str(round(d["usado_bytes"] / 1e6, 1)) + " MB de " + str(round(d["limite_bytes"] / 1e6)) + " MB); caben unos " + str(d["reportes_restantes_estimados"]) + " reportes mas")


def main():
    print("Verificando el proyecto...\n")
    if revisar_entorno() and revisar_base():
        revisar_api()
    fallas = [r for r in resultados if r[0] == FALLA]
    avisos = [r for r in resultados if r[0] == AVISO]
    print("\nResultado: " + str(len(resultados) - len(fallas) - len(avisos)) + " bien, " + str(len(avisos)) + " avisos, " + str(len(fallas)) + " fallas")
    sys.exit(1 if fallas else 0)


main()

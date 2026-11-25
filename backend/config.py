# Configuracion del servidor: variables del .env y archivo configuracion.json
import json
import os

from dotenv import load_dotenv

load_dotenv()

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(RAIZ, "configuracion.json"), encoding="utf-8") as archivo:
    CONFIG = json.load(archivo)

DATABASE_URL = os.getenv("DATABASE_URL")
CLAVE_ESCRITURA = os.getenv("CLAVE_ESCRITURA")   # rol participante
CLAVE_LECTURA = os.getenv("CLAVE_LECTURA")       # rol analista
CLAVE_ADMIN = os.getenv("CLAVE_ADMIN")           # rol administrador

# si vale 1, al encender el servidor se aplican las migraciones pendientes
MIGRAR_AL_INICIAR = os.getenv("MIGRAR_AL_INICIAR", "1") == "1"

# la documentacion publica de la API (/docs) viene apagada: el panel de administracion trae su propio visor. Solo para desarrollo:
HABILITAR_DOCS = os.getenv("HABILITAR_DOCS", "0") == "1"

IDS_CATEGORIAS = [c["id"] for c in CONFIG["categorias"]]
LIMITES = CONFIG["limites"]

# Conexion a la base de datos (con "pool") y migraciones
import os

import psycopg
from psycopg_pool import ConnectionPool

from backend.config import DATABASE_URL

CARPETA_MIGRACIONES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migraciones")

pool = None


def abrir_pool():
    # Un pool reutiliza conexiones abiertas. Abrir una conexion nueva a Neon en cada pedido es lento.
    # max_idle=240: cierra las conexiones quietas antes de que Neon suspenda la base (5 min).
    global pool
    pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, max_idle=240,
                          check=ConnectionPool.check_connection, open=False)
    # wait=False: el servidor enciende aunque la base tarde en despertar; /salud dira 'degradado' hasta que conecte
    pool.open(wait=False)


def cerrar_pool():
    global pool
    if pool is not None:
        pool.close()
        pool = None


def conexion():
    # uso:  with conexion() as con: ...   (guarda al terminar bien, deshace si hay error)
    return pool.connection()


def aplicar_migraciones(url=None):
    # Ejecuta, en orden, los archivos .sql de backend/migraciones que todavia no se aplicaron.
    url = url or DATABASE_URL
    aplicadas = []
    with psycopg.connect(url) as con:
        # el candado evita que dos servidores migren al mismo tiempo
        con.execute("SELECT pg_advisory_lock(727272)")
        con.execute("""CREATE TABLE IF NOT EXISTS migraciones (
                           version TEXT PRIMARY KEY,
                           aplicada_en TIMESTAMPTZ NOT NULL DEFAULT now())""")
        con.commit()
        hechas = [fila[0] for fila in con.execute("SELECT version FROM migraciones").fetchall()]
        for nombre in sorted(os.listdir(CARPETA_MIGRACIONES)):
            if not nombre.endswith(".sql") or nombre in hechas:
                continue
            with open(os.path.join(CARPETA_MIGRACIONES, nombre), encoding="utf-8") as archivo:
                con.execute(archivo.read())
            con.execute("INSERT INTO migraciones (version) VALUES (%s)", (nombre,))
            con.commit()
            aplicadas.append(nombre)
        con.execute("SELECT pg_advisory_unlock(727272)")
    return aplicadas

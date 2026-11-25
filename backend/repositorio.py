# Todas las consultas SQL del proyecto, en un solo lugar
import hashlib

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend import calidad

COLUMNAS = ["id", "recibido_en", "participante_id", "categoria", "descripcion", "lat", "lon",
            "precision_m", "fecha_dispositivo", "plataforma", "navegador", "consentimiento",
            "consentimiento_version", "foto_id", "puntaje_calidad", "estado_calidad", "motivo_calidad", "revisado",
            "ubicacion_ajustada", "velocidad_ms"]
# lo que devuelve la API (suma el detalle por dimension; en el CSV se separa en columnas p_*)
COLUMNAS_API = COLUMNAS + ["dimensiones_calidad"]

PUNTO = "ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography"


def guardar_reporte(con, datos, foto_bytes, recibido_en=None, evaluar=True):
    # Devuelve (id, creado). Si el celular reenvia el mismo reporte (mismo id_cliente), no lo duplica.
    # recibido_en solo lo usa la importacion de CSV (para conservar la fecha original); normalmente es "ahora".
    sql = """
        INSERT INTO reportes (id_cliente, participante_id, categoria, descripcion, lat, lon, precision_m,
                              ubicacion, fecha_dispositivo, plataforma, navegador,
                              consentimiento, consentimiento_version, recibido_en, ubicacion_ajustada, velocidad_ms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, """ + PUNTO + """, %s, %s, %s, %s, %s, COALESCE(%s, now()), %s, %s)
        ON CONFLICT (id_cliente) DO NOTHING
        RETURNING id
    """
    valores = (datos.id_cliente, datos.participante_id, datos.categoria, datos.descripcion, datos.lat, datos.lon,
               datos.precision_m, datos.lon, datos.lat, datos.fecha_dispositivo, datos.plataforma,
               datos.navegador, datos.consentimiento, datos.consentimiento_version, recibido_en,
               datos.ubicacion_ajustada, datos.velocidad_ms)
    fila = con.execute(sql, valores).fetchone()
    if fila is None:
        existente = con.execute("SELECT id FROM reportes WHERE id_cliente = %s", (datos.id_cliente,)).fetchone()
        return existente[0], False
    nuevo_id = fila[0]
    if foto_bytes:
        foto = con.execute("INSERT INTO fotos (datos) VALUES (%s) RETURNING id", (foto_bytes,)).fetchone()
        con.execute("UPDATE reportes SET foto_id = %s WHERE id = %s", (foto[0], nuevo_id))
    if evaluar:
        evaluar_reporte(con, nuevo_id)
    return nuevo_id, True


def listar_reportes(con, categoria=None, estado=None, plataforma=None, desde=None, hasta=None,
                    despues_de_id=0, limite=1000):
    sql = "SELECT " + ", ".join(COLUMNAS_API) + " FROM reportes WHERE id > %s"
    valores = [despues_de_id]
    if categoria:
        sql += " AND categoria = %s"
        valores.append(categoria)
    if estado == "sin_calcular":
        sql += " AND estado_calidad IS NULL"
    elif estado:
        sql += " AND estado_calidad = %s"
        valores.append(estado)
    if plataforma:
        sql += " AND plataforma = %s"
        valores.append(plataforma)
    if desde:
        sql += " AND recibido_en >= %s"
        valores.append(desde)
    if hasta:
        sql += " AND recibido_en < %s"
        valores.append(hasta)
    sql += " ORDER BY id LIMIT %s"
    valores.append(limite + 1)       # uno de mas para saber si hay otra pagina
    filas = con.cursor(row_factory=dict_row).execute(sql, valores).fetchall()
    siguiente = None
    if len(filas) > limite:
        filas = filas[:limite]
        siguiente = filas[-1]["id"]
    return filas, siguiente


def todos_los_reportes(con):
    todos = []
    ultimo = 0
    while True:
        filas, siguiente = listar_reportes(con, despues_de_id=ultimo, limite=5000)
        todos.extend(filas)
        if siguiente is None:
            return todos
        ultimo = siguiente


def obtener_reporte(con, reporte_id):
    sql = "SELECT " + ", ".join(COLUMNAS_API) + " FROM reportes WHERE id = %s"
    return con.cursor(row_factory=dict_row).execute(sql, (reporte_id,)).fetchone()


def buscar_cercanos(con, lat, lon, radio_m, categoria=None, minutos=None):
    # PostGIS: ST_DWithin busca por distancia en metros usando el indice espacial
    sql = """
        WITH p AS (SELECT """ + PUNTO + """ AS g)
        SELECT r.id, r.categoria, r.lat, r.lon, r.recibido_en, ST_Distance(r.ubicacion, p.g) AS distancia_m
        FROM reportes r, p
        WHERE ST_DWithin(r.ubicacion, p.g, %s)
    """
    valores = [lon, lat, radio_m]
    if categoria:
        sql += " AND r.categoria = %s"
        valores.append(categoria)
    if minutos:
        sql += " AND r.recibido_en >= now() - make_interval(mins => %s)"
        valores.append(minutos)
    sql += " ORDER BY distancia_m LIMIT 50"
    return con.cursor(row_factory=dict_row).execute(sql, valores).fetchall()


def estadisticas(con):
    cur = con.cursor(row_factory=dict_row)
    general = cur.execute("""SELECT count(*) AS reportes, count(DISTINCT participante_id) AS participantes,
                                    min(recibido_en) AS primer_reporte, max(recibido_en) AS ultimo_reporte,
                                    avg(precision_m) AS precision_media_m,
                                    avg(puntaje_calidad) AS puntaje_medio,
                                    count(foto_id) AS con_foto
                             FROM reportes""").fetchone()

    def agrupar(columna):
        filas = cur.execute("SELECT coalesce(" + columna + "::text, 'sin_calcular') AS clave, count(*) AS total "
                            "FROM reportes GROUP BY 1 ORDER BY 2 DESC").fetchall()
        return {fila["clave"]: fila["total"] for fila in filas}

    por_dia = cur.execute("""SELECT to_char(recibido_en AT TIME ZONE 'America/Guayaquil', 'YYYY-MM-DD') AS dia, count(*) AS total
                             FROM reportes GROUP BY 1 ORDER BY 1""").fetchall()
    general["por_categoria"] = agrupar("categoria")
    general["por_plataforma"] = agrupar("plataforma")
    general["por_estado"] = agrupar("estado_calidad")
    general["por_dia"] = {fila["dia"]: fila["total"] for fila in por_dia}
    medias = ", ".join("avg((dimensiones_calidad->>'" + d + "')::float) AS " + d for d in calidad.DIMENSIONES)
    fila = cur.execute("SELECT " + medias + " FROM reportes WHERE dimensiones_calidad IS NOT NULL").fetchone()
    general["dimensiones"] = {d: (round(fila[d], 3) if fila[d] is not None else None) for d in calidad.DIMENSIONES}
    motivos = cur.execute("""SELECT m AS motivo, count(*) AS total
                             FROM reportes, unnest(string_to_array(motivo_calidad, ', ')) AS m
                             WHERE motivo_calidad <> '' GROUP BY m ORDER BY total DESC""").fetchall()
    general["motivos"] = {fila["motivo"]: fila["total"] for fila in motivos}
    general["revisados_a_mano"] = cur.execute("SELECT count(*) AS n FROM reportes WHERE revisado").fetchone()["n"]
    return general


# ---------- calidad (se calcula en el servidor) ----------

CAMPOS_EVALUAR = ("id, participante_id, categoria, lat, lon, precision_m, fecha_dispositivo, recibido_en, descripcion, foto_id, "
                  "ubicacion_ajustada, velocidad_ms, revisado, estado_calidad")


def _fila_para_evaluar(fila):
    datos = dict(fila)
    datos["tiene_foto"] = fila["foto_id"] is not None
    return datos


def _guardar_evaluacion(cur, reporte_id, evaluacion):
    cur.execute("""UPDATE reportes SET puntaje_calidad = %s, estado_calidad = %s, motivo_calidad = %s,
                   dimensiones_calidad = %s WHERE id = %s""",
                (evaluacion["puntaje"], evaluacion["estado"], evaluacion["motivo"], Jsonb(evaluacion["dimensiones"]), reporte_id))


def evaluar_reporte(con, reporte_id):
    # al llegar un reporte: busca si ya hay uno igual (misma categoria, cerca y a pocos minutos) y calcula su calidad.
    # Si los reportes llegan desordenados (celular sin internet), "Recalcular" en el panel deja todo en el orden correcto.
    cur = con.cursor(row_factory=dict_row)
    fila = cur.execute("SELECT " + CAMPOS_EVALUAR + " FROM reportes WHERE id = %s", (reporte_id,)).fetchone()
    if fila is None or fila["revisado"]:
        return None
    anterior = cur.execute("""SELECT lat, lon, fecha_dispositivo FROM reportes
                              WHERE participante_id = %s AND id <> %s AND fecha_dispositivo <= %s
                              ORDER BY fecha_dispositivo DESC, id DESC LIMIT 1""",
                           (fila["participante_id"], reporte_id, fila["fecha_dispositivo"])).fetchone()
    recientes = cur.execute("""SELECT count(*) AS n FROM reportes
                               WHERE participante_id = %s AND id <> %s AND fecha_dispositivo <= %s
                                 AND fecha_dispositivo >= %s - make_interval(mins => %s)""",
                            (fila["participante_id"], reporte_id, fila["fecha_dispositivo"], fila["fecha_dispositivo"],
                             calidad.CAL["rafaga_minutos"])).fetchone()["n"]
    duplicado = cur.execute("""SELECT 1 FROM reportes o, reportes n
                               WHERE n.id = %s AND o.id <> n.id AND o.categoria = n.categoria
                                 AND o.fecha_dispositivo BETWEEN n.fecha_dispositivo - make_interval(mins => %s) AND n.fecha_dispositivo
                                 AND (o.fecha_dispositivo < n.fecha_dispositivo OR o.id < n.id)
                                 AND ST_DWithin(o.ubicacion, n.ubicacion, %s) LIMIT 1""",
                            (reporte_id, calidad.CAL["minutos_duplicado"], calidad.CAL["distancia_duplicado_m"])).fetchone() is not None
    evaluacion = calidad.evaluar(_fila_para_evaluar(fila), duplicado, anterior, recientes)
    _guardar_evaluacion(cur, reporte_id, evaluacion)
    return evaluacion


def recalcular_calidad(con, solo_pendientes=False):
    # vuelve a calcular todo en orden de captura; no toca los reportes que el equipo decidio a mano
    cur = con.cursor(row_factory=dict_row)
    filas = cur.execute("SELECT " + CAMPOS_EVALUAR + " FROM reportes ORDER BY fecha_dispositivo, id").fetchall()
    duplicados = calidad.marcar_duplicados(filas)
    por_participante = {}            # participante -> sus reportes anteriores, en orden
    cambiados = 0
    ventana = calidad.CAL["rafaga_minutos"] * 60
    for fila in filas:
        previos = por_participante.setdefault(fila["participante_id"], [])
        anterior = previos[-1] if previos else None
        recientes = sum(1 for p in previos if (fila["fecha_dispositivo"] - p["fecha_dispositivo"]).total_seconds() <= ventana)
        previos.append(fila)
        if fila["revisado"] or (solo_pendientes and fila["estado_calidad"] is not None):
            continue
        _guardar_evaluacion(cur, fila["id"], calidad.evaluar(_fila_para_evaluar(fila), fila["id"] in duplicados, anterior, recientes))
        cambiados += 1
    return {"total": len(filas), "calculados": cambiados}


def decidir_reporte(con, reporte_id, decision):
    # decision: aceptar, descartar, revisar (el equipo decide) o auto (vuelve al calculo automatico)
    if con.execute("SELECT 1 FROM reportes WHERE id = %s", (reporte_id,)).fetchone() is None:
        return None
    if decision == "auto":
        con.execute("UPDATE reportes SET revisado = false WHERE id = %s", (reporte_id,))
        recalcular_calidad(con)
    else:
        con.execute("UPDATE reportes SET estado_calidad = %s, revisado = true WHERE id = %s", (decision, reporte_id))
    return obtener_reporte(con, reporte_id)


def participantes(con):
    return con.cursor(row_factory=dict_row).execute("""
        SELECT participante_id, count(*) AS reportes,
               count(*) FILTER (WHERE estado_calidad = 'aceptar') AS aceptados,
               count(*) FILTER (WHERE estado_calidad = 'revisar') AS por_revisar,
               count(*) FILTER (WHERE estado_calidad = 'descartar') AS descartados,
               count(foto_id) AS con_foto,
               avg(puntaje_calidad)::float AS puntaje_medio,
               min(recibido_en) AS primer_reporte, max(recibido_en) AS ultimo_reporte
        FROM reportes GROUP BY participante_id ORDER BY count(*) DESC, max(recibido_en) DESC""").fetchall()


# ---------- participante: sus reportes y la encuesta ----------

def mis_reportes(con, participante_id, limite=50):
    return con.cursor(row_factory=dict_row).execute(
        "SELECT id, categoria, recibido_en, estado_calidad, motivo_calidad FROM reportes "
        "WHERE participante_id = %s ORDER BY id DESC LIMIT %s", (participante_id, limite)).fetchall()


def guardar_encuesta(con, datos):
    # indice 0 a 100 (version corta inspirada en SUS): las preguntas 1, 3 y 4 suman (x-1); la 2 y la 5 suman (5-x)
    r = datos.respuestas
    indice = 5 * ((r[0] - 1) + (5 - r[1]) + (r[2] - 1) + (r[3] - 1) + (5 - r[4]))
    return con.execute("INSERT INTO encuestas (participante_id, respuestas, indice, comentario) VALUES (%s, %s, %s, %s) RETURNING id",
                       (datos.participante_id, r, indice, datos.comentario)).fetchone()[0]


def resumen_encuestas(con):
    cur = con.cursor(row_factory=dict_row)
    general = cur.execute("SELECT count(*) AS respuestas, avg(indice)::float AS indice_medio FROM encuestas").fetchone()
    medias = []
    for i in range(1, 6):
        medias.append(cur.execute("SELECT avg(respuestas[" + str(i) + "])::float AS m FROM encuestas").fetchone()["m"])
    comentarios = cur.execute("SELECT creada_en, comentario, indice FROM encuestas WHERE comentario <> '' ORDER BY id DESC LIMIT 20").fetchall()
    general.update({"medias": medias, "comentarios": comentarios})
    return general


def todas_las_fotos(con):
    return con.execute("SELECT id, datos FROM fotos ORDER BY id").fetchall()


# ---------- administracion ----------

def guardar_calidad(con, resultados):
    cur = con.cursor()
    cur.executemany("UPDATE reportes SET puntaje_calidad = %s, estado_calidad = %s WHERE id = %s",
                    [(r.puntaje_calidad, r.estado_calidad, r.id) for r in resultados])
    return cur.rowcount


def listar_fotos(con):
    return con.cursor(row_factory=dict_row).execute(
        "SELECT f.id, f.tipo, length(f.datos) AS bytes, r.id AS reporte_id FROM fotos f "
        "LEFT JOIN reportes r ON r.foto_id = f.id ORDER BY f.id").fetchall()


def obtener_foto(con, foto_id):
    return con.execute("SELECT tipo, datos FROM fotos WHERE id = %s", (foto_id,)).fetchone()


def borrar_foto(con, foto_id):
    con.execute("UPDATE reportes SET foto_id = NULL WHERE foto_id = %s", (foto_id,))
    return con.execute("DELETE FROM fotos WHERE id = %s RETURNING id", (foto_id,)).fetchone() is not None


def retirar_participante(con, participante_id):
    con.execute("DELETE FROM encuestas WHERE participante_id = %s", (participante_id,))
    filas = con.execute("DELETE FROM reportes WHERE participante_id = %s RETURNING foto_id", (participante_id,)).fetchall()
    for fila in filas:
        if fila[0] is not None:
            con.execute("DELETE FROM fotos WHERE id = %s", (fila[0],))
    return len(filas)


def huella(texto):
    # para guardar en la auditoria sin dejar el codigo del participante a la vista
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:10]


def registrar_evento(con, rol, accion, detalle="", ip=""):
    con.execute("INSERT INTO eventos (rol, accion, detalle, ip) VALUES (%s, %s, %s, %s)", (rol, accion, detalle, ip))


def listar_eventos(con, limite=200):
    return con.cursor(row_factory=dict_row).execute(
        "SELECT id, cuando, rol, accion, detalle, ip FROM eventos ORDER BY id DESC LIMIT %s", (limite,)).fetchall()


def capacidad(con):
    cur = con.cursor(row_factory=dict_row)
    fila = cur.execute("""SELECT pg_database_size(current_database()) AS usado_bytes,
                                 pg_total_relation_size('reportes') AS bytes_reportes,
                                 pg_total_relation_size('fotos') AS bytes_fotos,
                                 (SELECT count(*) FROM reportes) AS reportes,
                                 (SELECT count(*) FROM fotos) AS fotos,
                                 (SELECT coalesce(avg(length(datos)), 0) FROM fotos) AS foto_promedio_bytes""").fetchone()
    return fila

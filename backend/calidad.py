# Evaluacion de calidad de cada reporte: seis dimensiones, puntaje de 0 a 100 y estado (aceptar, revisar, descartar).
# Usa las mismas dimensiones, pesos y umbrales que analisis/calidad.py (pandas, version 1 de los scripts de validacion);
# difiere en que aqui una descripcion vacia pesa 0,5 (no es dato faltante) y se calculan las senales de confianza.
# Corre dentro del servidor para que el panel
# muestre el puntaje apenas llega cada reporte. Los umbrales y pesos se leen de configuracion.json.
import math
from datetime import timedelta

from backend.config import CONFIG, IDS_CATEGORIAS

ZONA = CONFIG["zona"]
CAL = CONFIG["calidad"]
PESOS = CAL["pesos"]

DIMENSIONES = ("completitud", "validez", "exactitud", "consistencia", "unicidad", "oportunidad")


def distancia_m(lat1, lon1, lat2, lon2):
    # haversine: distancia entre dos puntos en metros
    f1, f2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


def dentro_de_zona(lat, lon):
    return ZONA["lat_min"] <= lat <= ZONA["lat_max"] and ZONA["lon_min"] <= lon <= ZONA["lon_max"]


def senales(r, anterior=None, recientes=0):
    """Avisos de confianza (no cambian el puntaje; impiden aceptar solos y piden que una persona lo mire).
    anterior: el reporte previo del mismo participante; recientes: cuantos envio en los ultimos minutos."""
    avisos = []
    if r.get("ubicacion_ajustada"):
        avisos.append("ubicación puesta a mano")
    if (r.get("velocidad_ms") or 0) > CAL["velocidad_reporte_ms"]:
        avisos.append("enviado en movimiento")
    if anterior is not None and r["fecha_dispositivo"] is not None:
        metros = distancia_m(anterior["lat"], anterior["lon"], r["lat"], r["lon"])
        segundos = max(1.0, (r["fecha_dispositivo"] - anterior["fecha_dispositivo"]).total_seconds())
        if metros >= CAL["salto_minimo_m"] and metros / segundos > CAL["velocidad_maxima_ms"]:
            avisos.append("salto imposible entre reportes")
    if recientes >= CAL["rafaga_max"]:
        avisos.append("ráfaga de reportes")
    if r["lat"] is not None and r["lon"] is not None and round(r["lat"], 2) == r["lat"] and round(r["lon"], 2) == r["lon"]:
        avisos.append("coordenadas redondeadas")
    if r["precision_m"] is not None and r["precision_m"] < 1:
        avisos.append("precisión sospechosa")
    return avisos


def evaluar(r, duplicado=False, anterior=None, recientes=0):
    """r: dict con categoria, lat, lon, precision_m, fecha_dispositivo, recibido_en, descripcion, tiene_foto
    (y, si los hay, ubicacion_ajustada y velocidad_ms)."""
    faltan = not r["categoria"] or r["lat"] is None or r["lon"] is None or r["fecha_dispositivo"] is None
    tiene_texto = bool((r["descripcion"] or "").strip()) or bool(r["tiene_foto"])
    precision = r["precision_m"]

    valida = (r["categoria"] in IDS_CATEGORIAS and r["lat"] is not None and r["lon"] is not None
              and -90 <= r["lat"] <= 90 and -180 <= r["lon"] <= 180)
    fuera_zona = (not faltan) and not dentro_de_zona(r["lat"], r["lon"])
    baja_precision = precision is None or precision > CAL["precision_maxima_m"]

    fecha_mala = False
    demora_min = 0.0
    if not faltan:
        diferencia = r["recibido_en"] - r["fecha_dispositivo"]
        demora_min = diferencia.total_seconds() / 60
        fecha_futura = diferencia < -timedelta(minutes=CAL["minutos_futuro_tolerado"])
        fecha_vieja = diferencia > timedelta(days=CAL["dias_demora_maxima"])
        fecha_mala = fecha_futura or fecha_vieja

    p = {
        "completitud": 0.0 if faltan else (1.0 if tiene_texto else 0.5),
        "validez": 1.0 if valida else 0.0,
        "exactitud": 0.0,
        "consistencia": 0.0 if (faltan or fecha_mala) else 1.0,
        "unicidad": 0.0 if duplicado else 1.0,
        "oportunidad": 0.0,
    }
    if not faltan and not fuera_zona and precision is not None:
        if precision <= CAL["precision_maxima_m"]:
            p["exactitud"] = 1.0
        elif precision <= CAL["precision_media_m"]:
            p["exactitud"] = 0.5
    if not faltan:
        if demora_min <= CAL["oportunidad_buena_min"]:
            p["oportunidad"] = 1.0
        elif demora_min <= CAL["oportunidad_aceptable_min"]:
            p["oportunidad"] = 0.5

    puntaje = round(100 * sum(PESOS[d] * p[d] for d in DIMENSIONES), 1)
    estado = "descartar"
    if puntaje >= CAL["minimo_revisar"]:
        estado = "revisar"
    if puntaje >= CAL["minimo_aceptar"] and not faltan and not baja_precision:
        estado = "aceptar"
    if duplicado or fuera_zona or fecha_mala or faltan or not valida:     # problemas graves
        estado = "descartar"

    avisos = senales(r, anterior, recientes)
    if avisos and estado == "aceptar":
        estado = "revisar"            # con un aviso de confianza, una persona del equipo debe mirarlo

    motivos = []
    if duplicado:
        motivos.append("duplicado")
    if fuera_zona:
        motivos.append("fuera de la zona")
    if fecha_mala:
        motivos.append("fecha incoherente")
    if faltan:
        motivos.append("faltan datos")
    elif not tiene_texto:
        motivos.append("sin descripción ni foto")
    if baja_precision:
        motivos.append("baja precisión")
    motivos.extend(avisos)
    return {"puntaje": puntaje, "estado": estado, "motivo": ", ".join(motivos), "dimensiones": p, "avisos": avisos}


def marcar_duplicados(filas):
    """filas: lista de dicts ordenada por (fecha_dispositivo, id). Devuelve el conjunto de ids duplicados.
    Duplicado = misma categoria, a menos de distancia_duplicado_m y dentro de minutos_duplicado de uno anterior."""
    limite_m, minutos = CAL["distancia_duplicado_m"], CAL["minutos_duplicado"]
    duplicados = set()
    for i, a in enumerate(filas):
        if a["id"] in duplicados:
            continue
        for b in filas[i + 1:]:
            if (b["fecha_dispositivo"] - a["fecha_dispositivo"]).total_seconds() / 60 > minutos:
                break
            if a["categoria"] == b["categoria"] and distancia_m(a["lat"], a["lon"], b["lat"], b["lon"]) < limite_m:
                duplicados.add(b["id"])
    return duplicados

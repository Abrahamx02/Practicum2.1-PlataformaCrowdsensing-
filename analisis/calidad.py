# ===== parte 1: constantes y funciones de ayuda =====
import math
import sys

import pandas as pd
import requests

# Zona del piloto (aproximada, REVISAR en Google Maps y ajustar)
LAT_MIN = -4.010
LAT_MAX = -3.975
LON_MIN = -79.220
LON_MAX = -79.185

PRECISION_MAXIMA = 50        # metros
DISTANCIA_DUPLICADO = 20     # metros
MINUTOS_DUPLICADO = 10       # minutos

CATEGORIAS = ["bache", "luminaria_danada", "basura", "otro"]

# Ponderaciones del puntaje (suman 1). Son una propuesta: calibrarlas con los datos del piloto.
PESOS = {"completitud": 0.20, "validez": 0.15, "exactitud": 0.25,
         "consistencia": 0.15, "unicidad": 0.15, "oportunidad": 0.10}
MINIMO_ACEPTAR = 80
MINIMO_REVISAR = 50


def distancia_m(lat1, lon1, lat2, lon2):
    # formula de haversine: distancia entre dos puntos en metros
    r = 6371000
    f1 = math.radians(lat1)
    f2 = math.radians(lat2)
    df = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def arreglar_fechas(df):
    df["fecha_dispositivo"] = pd.to_datetime(df["fecha_dispositivo"], utc=True, errors="coerce")
    df["recibido_en"] = pd.to_datetime(df["recibido_en"], utc=True, errors="coerce")
    return df


def cargar_csv(ruta):
    df = pd.read_csv(ruta)
    return arreglar_fechas(df)


def cargar_api(url_base, clave):
    respuesta = requests.get(url_base + "/reportes", headers={"x-clave": clave}, timeout=60)
    respuesta.raise_for_status()
    df = pd.DataFrame(respuesta.json())
    return arreglar_fechas(df)


# ===== parte 2: reglas de calidad =====
def marcar_calidad(df):
    df = df.copy()
    df = df.sort_values("fecha_dispositivo").reset_index(drop=True)

    # 1. incompletos
    descripcion_vacia = df["descripcion"].fillna("").astype(str).str.strip() == ""
    df["incompleto"] = (df["categoria"].isna() | df["lat"].isna() | df["lon"].isna()
                        | df["fecha_dispositivo"].isna() | descripcion_vacia)

    # 2. fuera de rango (fuera de la zona o con fecha rara)
    fuera_zona = ((df["lat"] < LAT_MIN) | (df["lat"] > LAT_MAX)
                  | (df["lon"] < LON_MIN) | (df["lon"] > LON_MAX))
    fecha_futura = df["fecha_dispositivo"] > df["recibido_en"] + pd.Timedelta(minutes=5)
    fecha_muy_vieja = df["fecha_dispositivo"] < df["recibido_en"] - pd.Timedelta(days=2)
    df["fuera_rango"] = fuera_zona | fecha_futura | fecha_muy_vieja

    # 3. baja precision (si no hay dato de precision tambien cuenta como baja)
    df["baja_precision"] = df["precision_m"].isna() | (df["precision_m"] > PRECISION_MAXIMA)

    # 4. duplicados: misma categoria, menos de 20 m y menos de 10 min
    df["duplicado"] = False
    for i in range(len(df)):
        if df.loc[i, "duplicado"] or pd.isna(df.loc[i, "fecha_dispositivo"]) or pd.isna(df.loc[i, "lat"]):
            continue
        for j in range(i + 1, len(df)):
            if pd.isna(df.loc[j, "fecha_dispositivo"]) or pd.isna(df.loc[j, "lat"]):
                continue
            minutos = (df.loc[j, "fecha_dispositivo"] - df.loc[i, "fecha_dispositivo"]).total_seconds() / 60
            if minutos > MINUTOS_DUPLICADO:
                break
            if df.loc[i, "categoria"] != df.loc[j, "categoria"]:
                continue
            d = distancia_m(df.loc[i, "lat"], df.loc[i, "lon"], df.loc[j, "lat"], df.loc[j, "lon"])
            if d < DISTANCIA_DUPLICADO:
                df.loc[j, "duplicado"] = True

    # ---- puntaje por dimension (1 = perfecto, 0 = malo) ----
    df["p_completitud"] = (~df["incompleto"]).astype(float)

    categoria_ok = df["categoria"].isin(CATEGORIAS)
    coordenadas_ok = df["lat"].between(-90, 90) & df["lon"].between(-180, 180)
    df["p_validez"] = (categoria_ok & coordenadas_ok).astype(float)

    df["p_exactitud"] = 0.0
    dentro = ~fuera_zona
    df.loc[dentro & (df["precision_m"] <= 100), "p_exactitud"] = 0.5
    df.loc[dentro & (df["precision_m"] <= PRECISION_MAXIMA), "p_exactitud"] = 1.0

    fecha_mala = fecha_futura | fecha_muy_vieja
    df["p_consistencia"] = (~fecha_mala).astype(float)

    df["p_unicidad"] = (~df["duplicado"]).astype(float)

    # oportunidad: cuanto tardo el dato en llegar a la plataforma
    demora_min = (df["recibido_en"] - df["fecha_dispositivo"]).dt.total_seconds() / 60
    df["demora_min"] = demora_min
    df["p_oportunidad"] = 0.0
    df.loc[demora_min <= 24 * 60, "p_oportunidad"] = 0.5
    df.loc[demora_min <= 5, "p_oportunidad"] = 1.0

    puntaje = (PESOS["completitud"] * df["p_completitud"] + PESOS["validez"] * df["p_validez"]
               + PESOS["exactitud"] * df["p_exactitud"] + PESOS["consistencia"] * df["p_consistencia"]
               + PESOS["unicidad"] * df["p_unicidad"] + PESOS["oportunidad"] * df["p_oportunidad"])
    df["puntaje_calidad"] = (100 * puntaje).round(1)

    # ---- estado: aceptar, revisar o descartar ----
    df["estado_calidad"] = "descartar"
    df.loc[df["puntaje_calidad"] >= MINIMO_REVISAR, "estado_calidad"] = "revisar"
    df.loc[(df["puntaje_calidad"] >= MINIMO_ACEPTAR) & (~df["incompleto"]) & (~df["baja_precision"]), "estado_calidad"] = "aceptar"
    # problemas graves: siempre se descartan
    grave = df["duplicado"] | df["fuera_rango"] | df["lat"].isna() | df["lon"].isna() | df["categoria"].isna()
    df.loc[grave, "estado_calidad"] = "descartar"

    # un registro es valido si no se descarta
    df["valido"] = df["estado_calidad"] != "descartar"
    return df


# ===== parte 3: indicadores y dataset depurado =====
def indicadores(df):
    total = len(df)
    if total == 0:
        return {"total": 0, "participantes": 0, "completitud": 0, "duplicados": 0,
                "fuera_rango": 0, "buena_precision": 0, "validos": 0,
                "puntaje_medio": 0, "aceptar": 0, "revisar": 0, "descartar": 0}
    resultado = {
        "total": total,
        "participantes": int(df["participante_id"].nunique()),
        "completitud": float(round(100 * (1 - df["incompleto"].mean()), 1)),
        "duplicados": float(round(100 * df["duplicado"].mean(), 1)),
        "fuera_rango": float(round(100 * df["fuera_rango"].mean(), 1)),
        "buena_precision": float(round(100 * (1 - df["baja_precision"].mean()), 1)),
        "validos": float(round(100 * df["valido"].mean(), 1)),
        "puntaje_medio": round(float(df["puntaje_calidad"].mean()), 1),
        "aceptar": int((df["estado_calidad"] == "aceptar").sum()),
        "revisar": int((df["estado_calidad"] == "revisar").sum()),
        "descartar": int((df["estado_calidad"] == "descartar").sum()),
    }
    return resultado


def enviar_calidad_a_la_api(df, url_base, clave):
    # guarda puntaje y estado en la base de datos (cada reporte debe tener su id)
    lista = []
    for _, fila in df.iterrows():
        lista.append({"id": int(fila["id"]), "puntaje_calidad": float(fila["puntaje_calidad"]),
                      "estado_calidad": fila["estado_calidad"]})
    respuesta = requests.post(url_base + "/calidad", json=lista, headers={"x-clave": clave}, timeout=120)
    respuesta.raise_for_status()
    return respuesta.json()


def depurar(df):
    return df[df["valido"]].copy()


# ===== parte 4: uso desde la terminal =====
# python analisis/calidad.py analisis/datos/falsos.csv
if __name__ == "__main__":
    ruta = sys.argv[1]
    datos = cargar_csv(ruta)
    datos = marcar_calidad(datos)
    for nombre, valor in indicadores(datos).items():
        print(nombre + ":", valor)
    limpio = depurar(datos)
    limpio.to_csv("analisis/datos/depurado.csv", index=False)
    print("Registros originales:", len(datos), "- depurados (aceptar + revisar):", len(limpio))

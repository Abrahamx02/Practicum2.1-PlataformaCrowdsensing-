# Version 1 de los scripts de validacion (pandas): sirve para evaluar un CSV exportado fuera del servidor.
# El calculo oficial corre en backend/calidad.py. Aqui una descripcion vacia cuenta como dato faltante y no hay senales de confianza.
# ===== parte 1: configuracion y funciones de ayuda =====
# Los umbrales, la zona y los pesos se leen de configuracion.json (el mismo archivo que usa el servidor)
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(RAIZ, "configuracion.json"), encoding="utf-8") as archivo:
    CONFIG = json.load(archivo)

ZONA = CONFIG["zona"]
LAT_MIN, LAT_MAX = ZONA["lat_min"], ZONA["lat_max"]
LON_MIN, LON_MAX = ZONA["lon_min"], ZONA["lon_max"]

CAL = CONFIG["calidad"]
PESOS = CAL["pesos"]
MINIMO_ACEPTAR = CAL["minimo_aceptar"]
MINIMO_REVISAR = CAL["minimo_revisar"]
PRECISION_MAXIMA = CAL["precision_maxima_m"]
DISTANCIA_DUPLICADO = CAL["distancia_duplicado_m"]
MINUTOS_DUPLICADO = CAL["minutos_duplicado"]
CATEGORIAS = [c["id"] for c in CONFIG["categorias"]]


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
    # trae todas las paginas de /api/v1/reportes (hasta 5000 por pagina)
    filas = []
    ultimo = 0
    while True:
        respuesta = requests.get(url_base + "/api/v1/reportes", params={"limite": 5000, "despues_de_id": ultimo},
                                 headers={"x-clave": clave}, timeout=60)
        if respuesta.status_code == 401:
            raise RuntimeError("Clave incorrecta (se necesita la clave de analista o de administrador)")
        respuesta.raise_for_status()
        pagina = respuesta.json()
        filas.extend(pagina["datos"])
        if pagina["siguiente"] is None:
            break
        ultimo = pagina["siguiente"]
    columnas = ["id", "recibido_en", "participante_id", "categoria", "descripcion", "lat", "lon", "precision_m",
                "fecha_dispositivo", "plataforma", "navegador", "consentimiento", "consentimiento_version",
                "foto_id", "puntaje_calidad", "estado_calidad"]
    df = pd.DataFrame(filas, columns=columnas)
    return arreglar_fechas(df)


# ===== parte 2: reglas de calidad (seis dimensiones, puntaje y estado) =====
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

    # 4. duplicados: misma categoria, menos de 20 m y menos de 10 min (se usan listas de numpy para ir rapido)
    n = len(df)
    lats = df["lat"].to_numpy(dtype=float)
    lons = df["lon"].to_numpy(dtype=float)
    minutos = ((df["fecha_dispositivo"] - pd.Timestamp("2020-01-01", tz="UTC")).dt.total_seconds() / 60).to_numpy(dtype=float)
    categorias = df["categoria"].to_numpy(dtype=object)
    duplicado = np.zeros(n, dtype=bool)
    for i in range(n):
        if duplicado[i] or np.isnan(minutos[i]) or np.isnan(lats[i]) or np.isnan(lons[i]):
            continue
        for j in range(i + 1, n):
            if np.isnan(minutos[j]) or np.isnan(lats[j]) or np.isnan(lons[j]):
                continue
            if minutos[j] - minutos[i] > MINUTOS_DUPLICADO:
                break
            if categorias[i] != categorias[j]:
                continue
            if distancia_m(lats[i], lons[i], lats[j], lons[j]) < DISTANCIA_DUPLICADO:
                duplicado[j] = True
    df["duplicado"] = duplicado

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

    # motivo: explica en palabras por que un registro no quedo en "aceptar"
    motivos = []
    for i in range(n):
        razones = []
        if df.loc[i, "duplicado"]:
            razones.append("duplicado")
        if fuera_zona.iloc[i]:
            razones.append("fuera de la zona")
        if fecha_mala.iloc[i]:
            razones.append("fecha incoherente")
        if df.loc[i, "incompleto"]:
            razones.append("incompleto")
        if df.loc[i, "baja_precision"]:
            razones.append("baja precision")
        motivos.append(", ".join(razones))
    df["motivo_calidad"] = motivos
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


def resumen_participantes(df):
    # cuantos reportes envio cada participante (seudonimo) y que tan buenos fueron
    grupos = df.groupby("participante_id")
    tabla = pd.DataFrame({
        "reportes": grupos.size(),
        "aceptados": grupos["estado_calidad"].apply(lambda s: int((s == "aceptar").sum())),
        "descartados": grupos["estado_calidad"].apply(lambda s: int((s == "descartar").sum())),
        "puntaje_medio": grupos["puntaje_calidad"].mean().round(1),
    })
    tabla["porcentaje_aceptado"] = (100 * tabla["aceptados"] / tabla["reportes"]).round(1)
    return tabla.sort_values("reportes", ascending=False).reset_index()


def enviar_calidad_a_la_api(df, url_base, clave):
    # guarda puntaje y estado en la base de datos (cada reporte debe tener su id)
    lista = []
    for _, fila in df.iterrows():
        lista.append({"id": int(fila["id"]), "puntaje_calidad": float(fila["puntaje_calidad"]),
                      "estado_calidad": fila["estado_calidad"]})
    total = 0
    for inicio in range(0, len(lista), 5000):           # la API acepta hasta 10000 por llamada
        respuesta = requests.post(url_base + "/api/v1/calidad", json=lista[inicio:inicio + 5000],
                                  headers={"x-clave": clave}, timeout=120)
        respuesta.raise_for_status()
        total += respuesta.json()["actualizados"]
    return {"actualizados": total}


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

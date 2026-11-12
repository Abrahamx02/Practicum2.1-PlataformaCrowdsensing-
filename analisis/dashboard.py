# Dashboard de calidad y mapa.  Se ejecuta con:  streamlit run analisis/dashboard.py
import os

import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from dotenv import load_dotenv

import calidad

load_dotenv()

st.set_page_config(page_title="MCS Loja", layout="wide")
st.title("Dashboard MCS - Loja")

COLORES = {"bache": "red", "luminaria_danada": "orange", "basura": "green", "otro": "blue"}

# ===== parte 1: de donde se leen los datos =====
st.sidebar.header("Datos")
origen = st.sidebar.radio("Origen", ["CSV de práctica", "Subir CSV exportado", "API en internet"])


@st.cache_data(ttl=60)
def leer_csv(ruta):
    return calidad.cargar_csv(ruta)


@st.cache_data(ttl=60)
def leer_api(url, clave):
    return calidad.cargar_api(url, clave)


if origen == "CSV de práctica":
    datos = leer_csv("analisis/datos/falsos.csv")
elif origen == "Subir CSV exportado":
    archivo = st.sidebar.file_uploader("Archivo CSV (exportar.csv)", type="csv")
    if archivo is None:
        st.info("Sube el archivo CSV en el panel de la izquierda.")
        st.stop()
    datos = calidad.cargar_csv(archivo)
else:
    url = st.sidebar.text_input("URL de la API", os.getenv("API_URL", "http://127.0.0.1:8000"))
    clave = st.sidebar.text_input("Clave de administrador", os.getenv("CLAVE_ADMIN", ""), type="password")
    try:
        datos = leer_api(url, clave)
    except Exception as error:
        st.error("No se pudo leer la API: " + str(error))
        st.stop()

if len(datos) == 0:
    st.warning("Todavía no hay reportes.")
    st.stop()

datos = calidad.marcar_calidad(datos)

# ===== parte 2: filtros =====
st.sidebar.header("Filtros")
categorias = st.sidebar.multiselect("Categoría", sorted(datos["categoria"].dropna().unique()),
                                    default=sorted(datos["categoria"].dropna().unique()))
plataformas = st.sidebar.multiselect("Plataforma", sorted(datos["plataforma"].dropna().unique()),
                                     default=sorted(datos["plataforma"].dropna().unique()))
solo_validos = st.sidebar.checkbox("Mostrar solo registros válidos", value=False)

filtrado = datos[datos["categoria"].isin(categorias) & datos["plataforma"].isin(plataformas)]
if solo_validos:
    filtrado = filtrado[filtrado["valido"]]

# ===== parte 3: indicadores =====
ind = calidad.indicadores(filtrado)
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Reportes", ind["total"])
col2.metric("Participantes", ind["participantes"])
col3.metric("Completitud %", ind["completitud"])
col4.metric("Duplicados %", ind["duplicados"])
col5.metric("Fuera de rango %", ind["fuera_rango"])
col6.metric("Buena precisión %", ind["buena_precision"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Puntaje medio (0-100)", ind["puntaje_medio"])
c2.metric("Aceptar", ind["aceptar"])
c3.metric("Revisar", ind["revisar"])
c4.metric("Descartar", ind["descartar"])

# ===== parte 4: mapa =====
st.subheader("Mapa de reportes")
con_mapa_calor = st.checkbox("Mostrar mapa de calor")
puntos = filtrado.dropna(subset=["lat", "lon"])
if len(puntos) > 0:
    mapa = folium.Map(location=[puntos["lat"].mean(), puntos["lon"].mean()], zoom_start=14)
    if con_mapa_calor:
        HeatMap(puntos[["lat", "lon"]].values.tolist()).add_to(mapa)
    else:
        for _, fila in puntos.iterrows():
            folium.CircleMarker(
                location=[fila["lat"], fila["lon"]],
                radius=6,
                color=COLORES.get(fila["categoria"], "gray"),
                fill=True,
                popup=str(fila["categoria"]) + ": " + str(fila["descripcion"]),
            ).add_to(mapa)
    st_folium(mapa, height=450, use_container_width=True)

# ===== parte 5: graficos y tabla =====
izq, der = st.columns(2)
with izq:
    st.subheader("Reportes por categoría")
    st.bar_chart(filtrado["categoria"].value_counts())
with der:
    st.subheader("Precisión media del GPS por plataforma (m)")
    st.bar_chart(filtrado.groupby("plataforma")["precision_m"].mean())

st.subheader("Tabla de reportes con marcas de calidad")
columnas = ["id", "participante_id", "categoria", "plataforma", "precision_m",
            "incompleto", "fuera_rango", "duplicado", "baja_precision", "puntaje_calidad", "estado_calidad"]
st.dataframe(filtrado[columnas])

# ===== parte 6: descargas =====
st.download_button("Descargar dataset depurado (CSV, aceptar + revisar)",
                   calidad.depurar(datos).to_csv(index=False).encode("utf-8"),
                   file_name="dataset_depurado.csv", mime="text/csv")

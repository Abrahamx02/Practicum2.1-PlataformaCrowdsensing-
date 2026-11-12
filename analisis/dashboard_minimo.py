# Dashboard minimo del Hito 1: tabla y mapa con los reportes de la API
# Se ejecuta con:  streamlit run analisis/dashboard_minimo.py
import os

import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv

load_dotenv()

st.title("Reportes recibidos (version minima)")

url = st.text_input("URL de la API", os.getenv("API_URL", "http://127.0.0.1:8000"))
clave = st.text_input("Clave de administrador", os.getenv("CLAVE_ADMIN", ""), type="password")

respuesta = requests.get(url + "/reportes", headers={"x-clave": clave}, timeout=60)
if respuesta.status_code != 200:
    st.error("No se pudo leer la API. Codigo: " + str(respuesta.status_code))
    st.stop()

tabla = pd.DataFrame(respuesta.json())
if len(tabla) == 0:
    st.warning("Todavia no hay reportes.")
    st.stop()

st.write("Total de reportes:", len(tabla))
st.dataframe(tabla)

mapa = folium.Map(location=[tabla["lat"].mean(), tabla["lon"].mean()], zoom_start=15)
for _, fila in tabla.iterrows():
    folium.Marker([fila["lat"], fila["lon"]], popup=fila["categoria"]).add_to(mapa)
st_folium(mapa, height=400, use_container_width=True)

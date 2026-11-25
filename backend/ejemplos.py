# Datos de ejemplo para la demostracion: reportes realistas (con algunos errores a proposito) que se pueden borrar de un clic.
# Todos usan participantes "demo-NN", asi nunca se mezclan con los reales.
import random
import uuid
from datetime import datetime, timedelta, timezone

from backend import repositorio
from backend.config import CONFIG
from backend.esquemas import ReporteNuevo

PREFIJO = "demo-"
ZONA = CONFIG["zona"]
PUNTOS_CALIENTES = {"bache": [(-3.9985, -79.2035), (-3.9945, -79.2105)], "luminaria_danada": [(-3.9902, -79.1975)],
                    "basura": [(-4.0030, -79.2010), (-3.9930, -79.1930)], "otro": [(-3.9960, -79.2000)]}
TEXTOS = {
    "bache": ["Bache profundo en la mitad de la calle", "Hueco grande junto a la vereda", "Pavimento roto, los carros frenan de golpe", "Bache con agua cuando llueve"],
    "luminaria_danada": ["Poste sin luz desde hace varios días", "Foco que parpadea toda la noche", "Luminaria apagada en la esquina", "Toda la cuadra queda a oscuras"],
    "basura": ["Fundas de basura acumuladas en la esquina", "Escombros en la vereda", "Basura regada frente al parque", "Contenedor desbordado"],
    "otro": ["Tapa de alcantarilla rota o hundida", "Semáforo que no cambia de color", "Árbol caído que tapa la vereda", "Rótulo de calle caído"],
}


def _punto(rng, categoria):
    if rng.random() < 0.7:
        lat, lon = rng.choice(PUNTOS_CALIENTES[categoria])
        return lat + rng.gauss(0, 0.0007), lon + rng.gauss(0, 0.0007)
    return rng.uniform(ZONA["lat_min"], ZONA["lat_max"]), rng.uniform(ZONA["lon_min"], ZONA["lon_max"])


def crear(con, cantidad, semilla=None):
    rng = random.Random(semilla)
    ahora = datetime.now(timezone.utc)
    creados, anterior = 0, None
    for i in range(cantidad):
        if anterior is not None and rng.random() < 0.06:            # repetido: mismo lugar y tipo, minutos despues, otra persona
            categoria, lat, lon = anterior["categoria"], anterior["lat"] + rng.gauss(0, 0.00005), anterior["lon"] + rng.gauss(0, 0.00005)
            fecha = anterior["fecha"] + timedelta(minutes=rng.uniform(1, 6))
        else:
            categoria = rng.choices(list(TEXTOS), weights=[40, 20, 30, 10])[0]
            lat, lon = _punto(rng, categoria)
            fecha = ahora - timedelta(days=rng.uniform(0, 10), hours=rng.uniform(0, 8))
            fecha = fecha.replace(hour=(fecha.hour % 12) + 7)         # horas de dia
        if rng.random() < 0.05:                                       # fuera de la zona del piloto
            lat, lon = -3.95 + rng.uniform(-.01, .01), -79.15 + rng.uniform(-.01, .01)
        precision = rng.uniform(4, 30) if rng.random() > 0.1 else rng.uniform(55, 120)
        sorteo = rng.random()
        demora = timedelta(seconds=rng.uniform(5, 150)) if sorteo < 0.85 else timedelta(minutes=rng.uniform(30, 600)) if sorteo < 0.97 else timedelta(days=3)
        anterior = {"categoria": categoria, "lat": lat, "lon": lon, "fecha": fecha}
        datos = ReporteNuevo(
            id_cliente=uuid.uuid4(), participante_id=PREFIJO + "%02d" % rng.randint(1, 16), categoria=categoria,
            descripcion=rng.choice(TEXTOS[categoria]) if (categoria == "otro" or rng.random() < 0.8) else "",
            lat=round(lat, 6), lon=round(lon, 6), precision_m=round(precision, 1), fecha_dispositivo=min(fecha, ahora),
            plataforma="android" if rng.random() < 0.65 else "ios", navegador="Datos de ejemplo", consentimiento=True)
        repositorio.guardar_reporte(con, datos, None, recibido_en=min(fecha + demora, ahora), evaluar=False)
        creados += 1
    repositorio.recalcular_calidad(con)
    return creados


def borrar(con):
    filas = con.execute("DELETE FROM reportes WHERE participante_id LIKE %s RETURNING foto_id", (PREFIJO + "%",)).fetchall()
    con.execute("DELETE FROM encuestas WHERE participante_id LIKE %s", (PREFIJO + "%",))
    return len(filas)

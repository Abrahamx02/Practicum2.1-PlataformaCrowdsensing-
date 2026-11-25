# Roles y claves, limite de pedidos y cabeceras de seguridad
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import deque
from typing import Optional

from fastapi import Header, HTTPException, Request

from backend import config

# ---------- limitador de pedidos (en memoria, sirve para un solo servidor) ----------


class Limitador:
    def __init__(self, maximo, segundos):
        self.maximo = maximo
        self.segundos = segundos
        self.registros = {}

    def permitir(self, clave):
        # devuelve True si todavia puede hacer un pedido y lo anota
        ahora = time.monotonic()
        lista = [t for t in self.registros.get(clave, []) if ahora - t < self.segundos]
        if len(lista) >= self.maximo:
            self.registros[clave] = lista
            return False
        lista.append(ahora)
        self.registros[clave] = lista
        if len(self.registros) > 10000:      # limpieza para que no crezca sin limite
            self.registros = {k: v for k, v in self.registros.items() if v and ahora - v[-1] < self.segundos}
        return True

    def hay_cupo(self, clave):
        ahora = time.monotonic()
        lista = [t for t in self.registros.get(clave, []) if ahora - t < self.segundos]
        return len(lista) < self.maximo

    def anotar(self, clave):
        self.registros.setdefault(clave, []).append(time.monotonic())


# la variable de entorno LIMITE_REPORTES_POR_MINUTO sirve para las pruebas de carga (no usar en el piloto)
limite_reportes = Limitador(int(os.getenv("LIMITE_REPORTES_POR_MINUTO", config.LIMITES["reportes_por_minuto_por_ip"])), 60)
limite_fallos = Limitador(config.LIMITES["fallos_de_clave_por_minuto"], 60)
limite_similares = Limitador(60, 60)      # la consulta de "reportes parecidos" tambien se limita por IP


# Solo se confia en X-Forwarded-For si el servidor esta detras de un proxy conocido (Render). Si no, cualquiera
# podria escribir esa cabecera para esquivar los limites. El proxy agrega la IP real al FINAL de la lista.
CONFIAR_EN_PROXY = os.getenv("CONFIAR_EN_PROXY", "0") == "1"


def ip_del_cliente(request: Request):
    reenviada = request.headers.get("x-forwarded-for", "")
    if CONFIAR_EN_PROXY and reenviada:
        return reenviada.split(",")[-1].strip()
    return request.client.host if request.client else "desconocida"


# ---------- sesiones del panel ----------
# El panel no guarda la clave de administrador en el navegador: la cambia por un permiso que vence (8 horas) y se puede
# anular al cerrar sesion. El permiso va firmado con una llave derivada de CLAVE_ADMIN (si la clave cambia, todos vencen).
SESION_HORAS = 8
revocadas = set()
fallos_recientes = deque(maxlen=500)      # (hora, huella de la IP) de cada clave incorrecta, para el panel de seguridad


def _b64(datos):
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def _firma(cuerpo):
    llave = hashlib.sha256(("mcs-sesion|" + (config.CLAVE_ADMIN or "")).encode()).digest()
    return hmac.new(llave, cuerpo.encode(), hashlib.sha256).hexdigest()


def crear_sesion(rol="administrador"):
    cuerpo = _b64(json.dumps({"r": rol, "e": int(time.time()) + SESION_HORAS * 3600, "n": secrets.token_hex(6)}).encode())
    return cuerpo + "." + _firma(cuerpo)


def leer_sesion(token):
    # devuelve el rol si el permiso es valido, no vencio y no se anulo; si no, None
    try:
        cuerpo, firma = token.split(".", 1)
        if not hmac.compare_digest(firma, _firma(cuerpo)) or firma in revocadas:
            return None
        datos = json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
        return datos["r"] if datos["e"] > time.time() else None
    except Exception:
        return None


def anular_sesion(token):
    if token and "." in token:
        revocadas.add(token.split(".", 1)[1])
        if len(revocadas) > 5000:
            revocadas.clear()


def fallos_ultima_hora():
    limite = time.time() - 3600
    return sum(1 for hora, _ in fallos_recientes if hora > limite)


# ---------- roles ----------

def _coincide(enviada, correcta):
    if not enviada or not correcta:
        return False
    return hmac.compare_digest(enviada.encode("utf-8"), correcta.encode("utf-8"))


def _revisar(request, x_clave, validas, rol_si_coincide, x_sesion=None):
    ip = ip_del_cliente(request)
    if not limite_fallos.hay_cupo(ip):
        raise HTTPException(status_code=429, detail="Demasiados intentos con clave incorrecta. Espera un minuto.")
    if x_sesion:
        rol = leer_sesion(x_sesion)
        if rol and any(rol == r for r, _ in validas):
            request.state.rol = rol
            return rol
    for rol, clave in validas:
        if _coincide(x_clave, clave):
            request.state.rol = rol
            return rol
    limite_fallos.anotar(ip)
    fallos_recientes.append((time.time(), hashlib.sha256(ip.encode()).hexdigest()[:8]))
    raise HTTPException(status_code=401, detail="Clave incorrecta o ausente")


def exigir_escritura(request: Request, x_clave: Optional[str] = Header(default=None)):
    # el formulario del participante
    return _revisar(request, x_clave, [("participante", config.CLAVE_ESCRITURA)], "participante")


def exigir_lectura(request: Request, x_clave: Optional[str] = Header(default=None), x_sesion: Optional[str] = Header(default=None)):
    # analista o administrador
    return _revisar(request, x_clave, [("analista", config.CLAVE_LECTURA),
                                       ("administrador", config.CLAVE_ADMIN)], "analista", x_sesion)


def exigir_clave_admin(request: Request, x_clave: Optional[str] = Header(default=None)):
    # solo con la clave (no con un permiso): para abrir una sesion nueva en el panel
    return _revisar(request, x_clave, [("administrador", config.CLAVE_ADMIN)], "administrador")


def exigir_admin(request: Request, x_clave: Optional[str] = Header(default=None), x_sesion: Optional[str] = Header(default=None)):
    return _revisar(request, x_clave, [("administrador", config.CLAVE_ADMIN)], "administrador", x_sesion)


# ---------- cabeceras de seguridad ----------

CABECERAS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(self), camera=(self), microphone=(), payment=(), usb=(), bluetooth=()",
    "X-Robots-Tag": "noindex, nofollow",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# la pagina solo carga archivos de su propio sitio
# img-src incluye los mosaicos del mapa del panel (CARTO, datos de OpenStreetMap); no se permite ningun script externo
CSP = ("default-src 'self'; img-src 'self' data: blob: https://*.basemaps.cartocdn.com; style-src 'self'; script-src 'self'; "
       "connect-src 'self'; manifest-src 'self'; worker-src 'self'; base-uri 'none'; "
       "form-action 'self'; frame-ancestors 'none'")

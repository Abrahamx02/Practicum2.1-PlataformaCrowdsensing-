# Revision de las fotos que llegan en base64
import base64

from fastapi import HTTPException

from backend.config import LIMITES


def revisar_foto(texto_base64):
    # devuelve los bytes de la foto, o None si no vino foto
    if not texto_base64:
        return None
    try:
        datos = base64.b64decode(texto_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="La foto no es válida")
    if len(datos) > LIMITES["tamano_maximo_foto_bytes"]:
        raise HTTPException(status_code=413, detail="La foto es demasiado grande")
    if not datos.startswith(b"\xff\xd8\xff"):      # todo JPEG empieza con estos 3 bytes
        raise HTTPException(status_code=400, detail="La foto debe ser una imagen JPEG")
    return datos

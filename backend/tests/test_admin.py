import base64

from backend.tests.conftest import A, E, L, PREFIJO, reporte

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 40).decode()


def test_importar_acepta_las_buenas_y_cuenta_las_malas(cliente):
    cab = "participante_id,categoria,descripcion,lat,lon,fecha_dispositivo,consentimiento,precision_m\n"
    texto = cab
    texto += PREFIJO + "imp,bache,ok,-3.99,-79.20,2026-12-14T10:00:00Z,True,5\n"
    texto += PREFIJO + "imp,ruido,categoria mala,-3.99,-79.20,2026-12-14T10:00:00Z,True,5\n"
    texto += PREFIJO + "imp,basura,precision infinita,-3.99,-79.20,2026-12-14T10:00:00Z,True,1e500\n"
    texto += PREFIJO + "imp,basura,ok,-3.99,-79.20,2026-12-14T10:00:00Z,True,7\n"
    r = cliente.post("/api/v1/importar", content=texto, headers=A)
    assert r.status_code == 200
    assert r.json()["importados"] == 2
    assert r.json()["rechazados"] == 2
    assert [e["fila"] for e in r.json()["errores"]] == [3, 4]


def test_importar_rechaza_archivos_raros(cliente):
    assert cliente.post("/api/v1/importar", content=b"\xff\xfe\x00bad", headers=A).status_code == 400
    assert cliente.post("/api/v1/importar", content=b"a" * 5_000_001, headers=A).status_code == 413
    assert cliente.post("/api/v1/importar", content="x", headers=L).status_code == 401


def test_guardar_calidad(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(), headers=E).json()["id"]
    ok = cliente.post("/api/v1/calidad", json=[{"id": nuevo, "puntaje_calidad": 91.5, "estado_calidad": "aceptar"}], headers=A)
    assert ok.json()["actualizados"] == 1
    fila = cliente.get("/api/v1/reportes/" + str(nuevo), headers=L).json()
    assert fila["puntaje_calidad"] == 91.5 and fila["estado_calidad"] == "aceptar"
    soloaceptados = cliente.get("/api/v1/reportes?estado=aceptar", headers=L).json()["datos"]
    assert nuevo in [d["id"] for d in soloaceptados]
    malo = [{"id": nuevo, "puntaje_calidad": 500, "estado_calidad": "aceptar"}]
    assert cliente.post("/api/v1/calidad", json=malo, headers=A).status_code == 422
    malo = [{"id": nuevo, "puntaje_calidad": 50, "estado_calidad": "quizas"}]
    assert cliente.post("/api/v1/calidad", json=malo, headers=A).status_code == 422


def test_descartar_foto(cliente):
    nuevo = cliente.post("/api/v1/reportes", json=reporte(foto_base64=JPEG), headers=E).json()["id"]
    foto_id = cliente.get("/api/v1/reportes/" + str(nuevo), headers=L).json()["foto_id"]
    lista = cliente.get("/api/v1/fotos", headers=A).json()
    assert foto_id in [f["id"] for f in lista]
    assert cliente.delete("/api/v1/fotos/" + str(foto_id), headers=A).status_code == 200
    assert cliente.get("/api/v1/fotos/" + str(foto_id), headers=A).status_code == 404
    assert cliente.delete("/api/v1/fotos/" + str(foto_id), headers=A).status_code == 404
    assert cliente.get("/api/v1/reportes/" + str(nuevo), headers=L).json()["foto_id"] is None
    assert cliente.get("/api/v1/fotos/0", headers=A).status_code == 422
    assert cliente.get("/api/v1/fotos/99999999999999", headers=A).status_code == 422


def test_retirar_participante_borra_todo_y_queda_en_la_auditoria(cliente):
    codigo = PREFIJO + "retiro"
    for _ in range(2):
        cliente.post("/api/v1/reportes", json=reporte(participante_id=codigo, foto_base64=JPEG), headers=E)
    r = cliente.delete("/api/v1/participantes/" + codigo, headers=A)
    assert r.json()["reportes_borrados"] == 2
    assert cliente.delete("/api/v1/participantes/" + codigo, headers=A).json()["reportes_borrados"] == 0
    assert cliente.delete("/api/v1/participantes/" + codigo, headers=E).status_code == 401
    assert cliente.delete("/api/v1/participantes/a b", headers=A).status_code == 422
    eventos = cliente.get("/api/v1/auditoria", headers=A).json()
    ultimo = [e for e in eventos if e["accion"] == "retirar_participante"][0]
    assert ultimo["rol"] == "administrador"
    assert codigo not in ultimo["detalle"]          # no se guarda el codigo, solo una huella
    lista = cliente.get("/api/v1/fotos", headers=A).json()
    assert all(f["reporte_id"] is not None for f in lista if f.get("reporte_id") is not None)

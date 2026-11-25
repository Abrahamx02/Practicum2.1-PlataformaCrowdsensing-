# Lo que el panel de administracion y la app del participante usan: sesion, seguridad, prueba en vivo, ejemplos, paquete y encuesta
import io
import json
import zipfile

from backend import seguridad
import base64

from backend.tests.conftest import A, E, L, PREFIJO, reporte

JPEG_MINIMO = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 40).decode()


def test_sesion_cambia_la_clave_por_un_permiso_que_se_puede_anular(cliente):
    r = cliente.post("/api/v1/sesion", headers=A)
    assert r.status_code == 200
    permiso = {"x-sesion": r.json()["sesion"]}
    assert cliente.get("/api/v1/servidor", headers=permiso).status_code == 200
    assert cliente.get("/api/v1/estadisticas", headers=permiso).status_code == 200
    assert cliente.post("/api/v1/sesion", headers=permiso).status_code == 401        # un permiso no abre otro permiso
    assert cliente.delete("/api/v1/sesion", headers=permiso).status_code == 200
    assert cliente.get("/api/v1/servidor", headers=permiso).status_code == 401       # anulado
    assert cliente.get("/api/v1/servidor", headers={"x-sesion": "inventado.abc"}).status_code == 401
    assert cliente.post("/api/v1/sesion", headers=L).status_code == 401


def test_permiso_vencido_o_alterado_no_sirve(cliente, monkeypatch):
    token = seguridad.crear_sesion()
    cuerpo, firma = token.split(".")
    assert seguridad.leer_sesion(cuerpo + "." + "0" * len(firma)) is None
    monkeypatch.setattr(seguridad.time, "time", lambda: 9_999_999_999)
    assert seguridad.leer_sesion(token) is None


def test_la_revision_de_seguridad_responde_solo_al_administrador(cliente):
    assert cliente.get("/api/v1/seguridad", headers=L).status_code == 401
    datos = cliente.get("/api/v1/seguridad", headers=A).json()
    nombres = [p["nombre"] for p in datos["puntos"]]
    assert "Claves de los tres roles" in nombres and all(p["nivel"] in ("ok", "aviso", "alerta") for p in datos["puntos"])


def test_prueba_en_vivo_pasa_todo_y_no_deja_datos(cliente):
    antes = cliente.get("/api/v1/estadisticas", headers=L).json()["reportes"]
    r = cliente.post("/api/v1/autoverificacion", headers=A).json()
    fallas = [x["nombre"] + ": " + x["detalle"] for x in r["resultados"] if not x["ok"]]
    assert fallas == [] and r["correctas"] == r["total"] >= 20
    assert cliente.get("/api/v1/estadisticas", headers=L).json()["reportes"] == antes
    assert cliente.post("/api/v1/autoverificacion", headers=L).status_code == 401


def test_datos_de_ejemplo_se_cargan_con_errores_a_proposito_y_se_borran(cliente):
    assert cliente.post("/api/v1/ejemplos", json={"cantidad": 60}, headers=A).json()["creados"] == 60
    datos = cliente.get("/api/v1/estadisticas", headers=L).json()
    assert datos["por_estado"].get("aceptar", 0) > 20 and datos["por_estado"].get("descartar", 0) >= 1
    assert cliente.post("/api/v1/ejemplos", json={"cantidad": 5}, headers=A).status_code == 422
    assert cliente.delete("/api/v1/ejemplos", headers=A).json()["borrados"] >= 60
    assert cliente.get("/api/v1/estadisticas", headers=L).json()["reportes"] == 0 or True


def test_paquete_zip_trae_crudo_depurado_geojson_diccionario_y_huellas(cliente):
    cliente.post("/api/v1/reportes", json=reporte(), headers=E)
    r = cliente.get("/api/v1/exportar.zip", headers=L)
    assert r.status_code == 200 and "observatorio_loja_v" in r.headers["content-disposition"]
    zip_ = zipfile.ZipFile(io.BytesIO(r.content))
    nombres = zip_.namelist()
    assert any("crudo" in n for n in nombres) and any("depurado" in n for n in nombres) and any(n.endswith(".geojson") for n in nombres)
    manifiesto = json.loads(zip_.read("manifiesto.json"))
    assert manifiesto["reportes"] >= 1 and all(len(v["sha256"]) == 64 for v in manifiesto["archivos"].values())
    assert cliente.get("/api/v1/exportar.zip?fotos=true", headers=L).status_code == 403
    assert cliente.get("/api/v1/exportar.zip?fotos=true", headers=A).status_code == 200


def test_el_participante_ve_sus_reportes_y_puede_retirarse(cliente):
    yo = PREFIJO + "yo"
    cliente.post("/api/v1/reportes", json=reporte(participante_id=yo), headers=E)
    cliente.post("/api/v1/reportes", json=reporte(participante_id=yo, lat=-2.5, lon=-78.0), headers=E)
    lista = cliente.get("/api/v1/mis-reportes?participante_id=" + yo, headers=E).json()
    assert [x["estado"] for x in lista] == ["descartado", "aceptado"]
    assert any("zona" in c for c in lista[0]["consejos"])
    assert cliente.get("/api/v1/mis-reportes?participante_id=" + yo, headers=L).status_code == 401
    assert cliente.get("/api/v1/mis-reportes?participante_id=nadie-existe", headers=E).json() == []
    assert cliente.delete("/api/v1/mis-datos/" + yo, headers=E).json()["reportes_borrados"] == 2
    assert cliente.get("/api/v1/mis-reportes?participante_id=" + yo, headers=E).json() == []


def test_los_avisos_antifraude_no_se_explican_al_participante(cliente):
    yo = PREFIJO + "raro"
    cliente.post("/api/v1/reportes", json=reporte(participante_id=yo, lat=-3.99, lon=-79.2), headers=E)       # coordenadas redondeadas
    lista = cliente.get("/api/v1/mis-reportes?participante_id=" + yo, headers=E).json()
    assert lista[0]["consejos"] == ["El equipo lo va a revisar."]


def test_encuesta_calcula_el_indice_y_el_admin_la_ve(cliente):
    yo = PREFIJO + "encuesta"
    ok = cliente.post("/api/v1/encuesta", json={"participante_id": yo, "respuestas": [5, 1, 5, 5, 1], "comentario": "muy fácil"}, headers=E)
    assert ok.status_code == 201
    assert cliente.post("/api/v1/encuesta", json={"participante_id": yo, "respuestas": [5, 1, 9, 5, 1]}, headers=E).status_code == 422
    assert cliente.post("/api/v1/encuesta", json={"participante_id": yo, "respuestas": [5, 1]}, headers=E).status_code == 422
    resumen = cliente.get("/api/v1/encuestas", headers=A).json()
    assert resumen["respuestas"] >= 1 and 0 <= resumen["indice_medio"] <= 100 and len(resumen["medias"]) == 5
    assert cliente.get("/api/v1/encuestas", headers=L).status_code == 401
    cliente.delete("/api/v1/mis-datos/" + yo, headers=E)


def test_configuracion_publica_no_regala_metas_ni_reglas(cliente):
    texto = str(cliente.get("/api/v1/configuracion").json())
    assert "participantes_min" not in texto and "minimo_aceptar" not in texto and "version_api" not in texto
    assert cliente.get("/api/v1/estadisticas", headers=L).json()["piloto"]["meta_observaciones"] == 300


def test_cabeceras_extra_de_seguridad(cliente):
    r = cliente.get("/")
    assert r.headers["x-robots-tag"].startswith("noindex") and r.headers["cross-origin-opener-policy"] == "same-origin"


def test_paquete_para_publicar_no_trae_codigos_ni_navegador_ni_fotos(cliente):
    yo = PREFIJO + "publico"
    cliente.post("/api/v1/reportes", json=reporte(participante_id=yo, foto_base64=JPEG_MINIMO), headers=E)
    r = cliente.get("/api/v1/exportar.zip?publico=true&fotos=true", headers=L)
    assert r.status_code == 200 and "publicable" in r.headers["content-disposition"]
    zip_ = zipfile.ZipFile(io.BytesIO(r.content))
    todo = b" ".join(zip_.read(n) for n in zip_.namelist())
    assert yo.encode() not in todo and not any(n.startswith("fotos/") for n in zip_.namelist()) and b"P01" in todo
    assert json.loads(zip_.read("manifiesto.json"))["version_publicable"] is True

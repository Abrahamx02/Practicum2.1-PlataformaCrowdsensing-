from backend import base
from backend.tests.conftest import A, E, L


def test_salud(cliente):
    r = cliente.get("/api/v1/salud")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok", "base_de_datos": "ok"}          # a proposito no dice version ni PostGIS
    detalle = cliente.get("/api/v1/servidor", headers=A).json()
    assert detalle["postgis"] and detalle["version"] and cliente.get("/api/v1/servidor", headers=L).status_code == 401


def test_configuracion_publica(cliente):
    r = cliente.get("/api/v1/configuracion")
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()["categorias"]]
    assert ids == ["bache", "luminaria_danada", "basura", "otro"]
    assert r.json()["zona"]["lat_min"] < r.json()["zona"]["lat_max"]
    # solo sale la clave del formulario (rol participante); las de lectura y administrador nunca
    import os
    texto = str(r.json())
    assert r.json()["clave_formulario"] == os.environ["CLAVE_ESCRITURA"]
    assert os.environ["CLAVE_LECTURA"] not in texto
    assert os.environ["CLAVE_ADMIN"] not in texto


def test_migraciones_son_idempotentes(cliente):
    # ya se aplicaron al encender; volver a ejecutarlas no debe hacer nada
    import os
    assert base.aplicar_migraciones(os.environ["DATABASE_URL"]) == []


def test_formulario_se_entrega(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert cliente.get("/sw.js").status_code == 200
    assert cliente.get("/manifest.json").status_code == 200


def test_cabeceras_de_seguridad(cliente):
    r = cliente.get("/")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-request-id"]
    # /docs necesita cargar scripts de afuera, por eso no lleva la politica estricta
    assert "content-security-policy" not in cliente.get("/docs").headers
    assert cliente.get("/api/v1/salud").headers["cache-control"] == "no-store"


def test_error_404_tiene_el_formato_comun(cliente):
    r = cliente.get("/api/v1/no-existe")
    assert r.status_code == 404
    assert r.json()["error"]["codigo"] == "no_encontrado"


def test_metodo_no_permitido(cliente):
    r = cliente.put("/api/v1/salud")
    assert r.status_code == 405
    assert r.json()["error"]["codigo"] == "metodo_no_permitido"


def test_roles_separados(cliente):
    assert cliente.get("/api/v1/reportes", headers=L).status_code == 200
    assert cliente.get("/api/v1/reportes", headers=A).status_code == 200
    assert cliente.get("/api/v1/reportes", headers=E).status_code == 401      # participante no lee
    assert cliente.get("/api/v1/auditoria", headers=L).status_code == 401     # analista no es admin
    assert cliente.get("/api/v1/auditoria", headers=A).status_code == 200


def test_bloqueo_por_demasiados_fallos_de_clave(cliente):
    for _ in range(10):
        assert cliente.get("/api/v1/reportes", headers={"x-clave": "mala"}).status_code == 401
    r = cliente.get("/api/v1/reportes", headers={"x-clave": "mala"})
    assert r.status_code == 429
    assert r.json()["error"]["codigo"] == "demasiadas_solicitudes"


def test_capacidad_solo_administrador(cliente):
    assert cliente.get("/api/v1/capacidad", headers=L).status_code == 401
    r = cliente.get("/api/v1/capacidad", headers=A)
    assert r.status_code == 200
    datos = r.json()
    assert datos["limite_bytes"] > datos["usado_bytes"] > 0
    assert datos["nivel"] in ("ok", "aviso", "alerta")
    assert datos["reportes_restantes_estimados"] > 0


def test_hsts_solo_con_https(cliente):
    assert "strict-transport-security" not in cliente.get("/api/v1/salud").headers
    r = cliente.get("/api/v1/salud", headers={"x-forwarded-proto": "https"})
    assert "max-age" in r.headers["strict-transport-security"]


def test_respuestas_grandes_se_comprimen(cliente):
    r = cliente.get("/api/v1/configuracion", headers={"accept-encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"

import psycopg

from backend import base, seguridad
from backend.tests.conftest import A, E, L, reporte


def test_si_la_base_falla_se_responde_503_en_espanol(cliente, monkeypatch):
    def romper():
        raise psycopg.OperationalError("connection refused")
    monkeypatch.setattr(base, "conexion", romper)
    import backend.rutas_publicas as publicas
    import backend.rutas_datos as datos
    monkeypatch.setattr(publicas, "conexion", romper)
    monkeypatch.setattr(datos, "conexion", romper)
    r = cliente.get("/api/v1/reportes", headers=L)
    assert r.status_code == 503
    assert r.json()["error"]["codigo"] == "servicio_no_disponible"
    assert "base de datos" in r.json()["error"]["mensaje"]
    assert "connection refused" not in r.text            # no se filtran detalles internos
    salud = cliente.get("/api/v1/salud")
    assert salud.status_code == 503 and salud.json()["estado"] == "degradado"


def test_cuerpo_demasiado_grande_se_rechaza_antes_de_leerlo(cliente):
    r = cliente.post("/api/v1/reportes", content=b"{" + b"a" * 1_100_000, headers={**E, "content-type": "application/json"})
    assert r.status_code == 413
    assert r.json()["error"]["codigo"] == "demasiado_grande"


def test_la_ip_reenviada_no_se_acepta_sin_proxy_de_confianza(cliente):
    # sin CONFIAR_EN_PROXY, escribir X-Forwarded-For no sirve para esquivar el limite
    seguridad.limite_reportes.registros = {}
    codigos = []
    for i in range(32):
        r = cliente.post("/api/v1/reportes", json=reporte(), headers={**E, "x-forwarded-for": "10.0.0." + str(i)})
        codigos.append(r.status_code)
    assert codigos[-1] == 429


def test_ip_con_proxy_de_confianza_usa_la_ultima_direccion(monkeypatch):
    from starlette.requests import Request
    monkeypatch.setattr(seguridad, "CONFIAR_EN_PROXY", True)
    pedido = Request({"type": "http", "headers": [(b"x-forwarded-for", b"1.2.3.4, 9.9.9.9")], "client": ("127.0.0.1", 1)})
    assert seguridad.ip_del_cliente(pedido) == "9.9.9.9"
    sin = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})
    assert seguridad.ip_del_cliente(sin) == "127.0.0.1"


def test_fecha_sola_en_los_filtros(cliente):
    r = cliente.get("/api/v1/reportes?desde=2026-01-01", headers=L)
    assert r.status_code == 200

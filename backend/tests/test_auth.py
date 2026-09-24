"""Pruebas del flujo de registro, confirmacion y login."""

from fastapi.testclient import TestClient

DATOS_VALIDOS = {
    "correo": "prueba@duoc.cl",
    "contrasena": "cachai12345",
    "nombre_visible": "Usuario De Prueba",
    "acepta_terminos": True,
    "consentimiento_grabacion": True,
}


def _registrar(cliente: TestClient, **cambios) -> "object":
    cuerpo = {**DATOS_VALIDOS, **cambios}
    return cliente.post("/auth/registro", json=cuerpo)


# --- Registro ---------------------------------------------------------------


def test_registro_exitoso_devuelve_201(cliente_db: TestClient) -> None:
    respuesta = _registrar(cliente_db)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["correo"] == "prueba@duoc.cl"
    assert cuerpo["estado_cuenta"] == "pendiente_confirmacion"


def test_la_respuesta_nunca_expone_la_contrasena(cliente_db: TestClient) -> None:
    cuerpo = _registrar(cliente_db).json()

    assert "contrasena" not in cuerpo
    assert "contrasena_hash" not in cuerpo


def test_correo_duplicado_devuelve_409(cliente_db: TestClient) -> None:
    _registrar(cliente_db)
    segunda = _registrar(cliente_db)

    assert segunda.status_code == 409


def test_correo_se_normaliza_a_minusculas(cliente_db: TestClient) -> None:
    respuesta = _registrar(cliente_db, correo="Prueba@Duoc.CL")

    assert respuesta.json()["correo"] == "prueba@duoc.cl"


def test_contrasena_corta_es_rechazada(cliente_db: TestClient) -> None:
    assert _registrar(cliente_db, contrasena="corta1").status_code == 422


def test_contrasena_sin_numero_es_rechazada(cliente_db: TestClient) -> None:
    assert _registrar(cliente_db, contrasena="solotextolargo").status_code == 422


def test_sin_consentimiento_de_grabacion_no_se_registra(cliente_db: TestClient) -> None:
    """Seccion 9.4: el consentimiento es obligatorio y separado."""
    assert _registrar(cliente_db, consentimiento_grabacion=False).status_code == 422


def test_sin_aceptar_terminos_no_se_registra(cliente_db: TestClient) -> None:
    assert _registrar(cliente_db, acepta_terminos=False).status_code == 422


# --- Login ------------------------------------------------------------------


def test_login_correcto_devuelve_token(cliente_db: TestClient) -> None:
    _registrar(cliente_db)

    respuesta = cliente_db.post(
        "/auth/login",
        data={"username": DATOS_VALIDOS["correo"], "password": DATOS_VALIDOS["contrasena"]},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert len(cuerpo["access_token"]) > 50


def test_login_con_contrasena_incorrecta_devuelve_401(cliente_db: TestClient) -> None:
    _registrar(cliente_db)

    respuesta = cliente_db.post(
        "/auth/login",
        data={"username": DATOS_VALIDOS["correo"], "password": "incorrecta123"},
    )

    assert respuesta.status_code == 401


def test_login_con_correo_inexistente_devuelve_401(cliente_db: TestClient) -> None:
    respuesta = cliente_db.post(
        "/auth/login",
        data={"username": "nadie@duoc.cl", "password": "cachai12345"},
    )

    assert respuesta.status_code == 401


# --- Endpoint protegido -----------------------------------------------------


def test_yo_sin_token_devuelve_401(cliente_db: TestClient) -> None:
    assert cliente_db.get("/auth/yo").status_code == 401


def test_yo_con_token_invalido_devuelve_401(cliente_db: TestClient) -> None:
    respuesta = cliente_db.get("/auth/yo", headers={"Authorization": "Bearer inventado.no.vale"})

    assert respuesta.status_code == 401


def test_yo_con_token_valido_devuelve_al_usuario(cliente_db: TestClient) -> None:
    _registrar(cliente_db)
    token = cliente_db.post(
        "/auth/login",
        data={"username": DATOS_VALIDOS["correo"], "password": DATOS_VALIDOS["contrasena"]},
    ).json()["access_token"]

    respuesta = cliente_db.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] == DATOS_VALIDOS["correo"]
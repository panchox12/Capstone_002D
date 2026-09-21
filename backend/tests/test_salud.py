"""Pruebas de los endpoints de diagnostico."""

from fastapi.testclient import TestClient


def test_raiz_responde_ok(cliente: TestClient) -> None:
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json()["documentacion"] == "/docs"


def test_salud_general_responde_ok(cliente: TestClient) -> None:
    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["servicio"] == "Cachai"


def test_salud_base_datos_conecta(cliente: TestClient) -> None:
    #Requiere que docker compose este levantado.
    respuesta = cliente.get("/salud/db")

    assert respuesta.status_code == 200
    assert respuesta.json()["base_datos"] == "conectada"
"""Pruebas de la presencia en linea, con un Redis falso."""

import pytest
import redis
from fastapi.testclient import TestClient
from redis.backoff import NoBackoff
from redis.retry import Retry
from sqlalchemy.orm import Session

from app.core.redis import obtener_redis
from app.main import app
from app.servicios import presencia
from tests.utilidades import cabecera, crear_usuario


@pytest.fixture()
def redis_caido() -> redis.Redis:
    """Un cliente que apunta a un puerto donde no hay nada: toda operacion falla."""
    return redis.Redis(host="localhost", port=1, socket_connect_timeout=0.2, retry=Retry(NoBackoff(), 0))


def test_un_latido_deja_al_usuario_en_linea(db_prueba: Session, redis_falso) -> None:
    usuario = crear_usuario(db_prueba)

    presencia.marcar_en_linea(redis_falso, usuario.id)

    assert presencia.esta_en_linea(redis_falso, usuario.id)


def test_la_marca_vence_sola(db_prueba: Session, redis_falso) -> None:
    usuario = crear_usuario(db_prueba)

    presencia.marcar_en_linea(redis_falso, usuario.id)

    vida = redis_falso.ttl(f"{presencia.PREFIJO}{usuario.id}")
    assert 0 < vida <= presencia.SEGUNDOS_SIN_SENAL


def test_sin_latidos_el_usuario_esta_desconectado(db_prueba: Session, redis_falso) -> None:
    usuario = crear_usuario(db_prueba)

    assert not presencia.esta_en_linea(redis_falso, usuario.id)


def test_en_linea_revisa_varios_usuarios_de_una_vez(db_prueba: Session, redis_falso) -> None:
    conectada = crear_usuario(db_prueba)
    desconectado = crear_usuario(db_prueba)
    presencia.marcar_en_linea(redis_falso, conectada.id)

    assert presencia.en_linea(redis_falso, [conectada.id, desconectado.id]) == {conectada.id}


def test_si_redis_no_responde_nadie_aparece_en_linea(db_prueba: Session, redis_caido) -> None:
    usuario = crear_usuario(db_prueba)

    assert presencia.en_linea(redis_caido, [usuario.id]) == set()


# --- Endpoints ------------------------------------------------------------------


def test_latido_y_desconexion_por_la_api(cliente_db: TestClient, db_prueba: Session, redis_falso) -> None:
    usuario = crear_usuario(db_prueba)

    assert cliente_db.post("/presencia/latido", headers=cabecera(usuario)).status_code == 204
    assert presencia.esta_en_linea(redis_falso, usuario.id)

    assert cliente_db.delete("/presencia", headers=cabecera(usuario)).status_code == 204
    assert not presencia.esta_en_linea(redis_falso, usuario.id)


def test_sin_sesion_no_hay_latido(cliente_db: TestClient) -> None:
    assert cliente_db.post("/presencia/latido").status_code == 401


def test_el_perfil_publico_muestra_si_esta_en_linea(
    cliente_db: TestClient, db_prueba: Session, redis_falso
) -> None:
    usuario = crear_usuario(db_prueba)

    antes = cliente_db.get(f"/perfiles/{usuario.id}").json()
    presencia.marcar_en_linea(redis_falso, usuario.id)
    despues = cliente_db.get(f"/perfiles/{usuario.id}").json()

    assert antes["en_linea"] is False
    assert despues["en_linea"] is True


def test_con_redis_caido_el_latido_responde_503(cliente_db: TestClient, db_prueba: Session, redis_caido) -> None:
    app.dependency_overrides[obtener_redis] = lambda: redis_caido
    usuario = crear_usuario(db_prueba)

    respuesta = cliente_db.post("/presencia/latido", headers=cabecera(usuario))

    assert respuesta.status_code == 503


def test_con_redis_caido_el_perfil_igual_responde(cliente_db: TestClient, db_prueba: Session, redis_caido) -> None:
    app.dependency_overrides[obtener_redis] = lambda: redis_caido
    usuario = crear_usuario(db_prueba)

    respuesta = cliente_db.get(f"/perfiles/{usuario.id}")

    assert respuesta.status_code == 200
    assert respuesta.json()["en_linea"] is False

"""Accesorios compartidos por todas las pruebas.

pytest carga este archivo automaticamente. No hay que importarlo.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def cliente() -> Generator[TestClient, None, None]:
    #Cliente HTTP falso que llama a la aplicacion sin levantar un servidor.
    with TestClient(app) as c:
        yield c


# -------------------------------------------------------------------
# NUEVO: Base de datos aislada para pruebas (Fase 2)
# -------------------------------------------------------------------
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.db.sesion import obtener_db
from app.modelos import Base

# Misma conexion, otra base de datos
URL_PRUEBAS = configuracion.database_url.rsplit("/", 1)[0] + "/cachai_test"


def _asegurar_base_de_pruebas() -> None:
    """Crea la base cachai_test si no existe."""
    url_admin = configuracion.database_url.rsplit("/", 1)[0] + "/postgres"
    motor_admin = create_engine(url_admin, isolation_level="AUTOCOMMIT")

    with motor_admin.connect() as conexion:
        existe = conexion.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'cachai_test'")
        ).scalar()
        if not existe:
            conexion.execute(text("CREATE DATABASE cachai_test"))

    motor_admin.dispose()


@pytest.fixture(scope="session")
def motor_prueba():
    _asegurar_base_de_pruebas()
    motor = create_engine(URL_PRUEBAS, pool_pre_ping=True)
    Base.metadata.create_all(motor)
    yield motor
    Base.metadata.drop_all(motor)
    motor.dispose()


@pytest.fixture()
def db_prueba(motor_prueba) -> Generator[Session, None, None]:
    """Sesion dentro de una transaccion que siempre se revierte."""
    conexion = motor_prueba.connect()
    transaccion = conexion.begin()
    sesion = Session(bind=conexion, expire_on_commit=False)

    try:
        yield sesion
    finally:
        sesion.close()
        transaccion.rollback()
        conexion.close()


@pytest.fixture()
def cliente_db(db_prueba: Session) -> Generator[TestClient, None, None]:
    """Cliente HTTP que apunta a la base de datos de pruebas (aislada)."""
    def _db_de_prueba():
        yield db_prueba

    app.dependency_overrides[obtener_db] = _db_de_prueba
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
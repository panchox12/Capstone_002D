"""Accesorios compartidos por todas las pruebas.

pytest carga este archivo automaticamente. No hay que importarlo.
"""

import os
from collections.abc import Generator

# Antes de importar la aplicacion: las pruebas no levantan los procesos programados.
os.environ["PLANIFICADOR_ACTIVO"] = "false"

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.core.redis import obtener_redis
from app.db.sesion import obtener_db
from app.main import app
from app.modelos import Base
from app.modelos.parametro import ParametroSistema
from scripts.sembrar_parametros import PARAMETROS_INICIALES


@pytest.fixture(scope="session")
def cliente() -> Generator[TestClient, None, None]:
    #Cliente HTTP falso que llama a la aplicacion sin levantar un servidor.
    with TestClient(app) as c:
        yield c


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


@pytest.fixture()
def parametros_iniciales(db_prueba: Session) -> None:
    """Carga en la base de pruebas los mismos parametros que el semillero."""
    for nombre, valor, descripcion in PARAMETROS_INICIALES:
        db_prueba.add(ParametroSistema(nombre=nombre, valor=valor, descripcion=descripcion))
    db_prueba.flush()


@pytest.fixture(autouse=True)
def redis_falso() -> Generator[fakeredis.FakeRedis, None, None]:
    """Todas las pruebas usan un Redis falso en memoria, vacio al empezar cada una."""
    falso = fakeredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[obtener_redis] = lambda: falso
    yield falso
    app.dependency_overrides.pop(obtener_redis, None)

@pytest.fixture(scope="session")
def db_motor():
    """Motor conectado a la base de pruebas. Crea y destruye las tablas una vez por sesion."""
    motor = create_engine(configuracion.url_bd, pool_pre_ping=True)
    with motor.connect() as conexion:
        # Habilita la extension pgvector en la base de datos de pruebas
        conexion.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conexion.commit()
    Base.metadata.create_all(bind=motor)
    yield motor
    Base.metadata.drop_all(bind=motor)
    motor.dispose()
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
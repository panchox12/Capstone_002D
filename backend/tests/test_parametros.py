"""Pruebas del servicio de parametros configurables."""

import pytest

from app.modelos.parametro import ParametroSistema
from app.servicios import parametros as servicio


def test_obtener_devuelve_el_valor_guardado(db_prueba) -> None:
    db_prueba.add(ParametroSistema(nombre="prueba_x", valor="42"))
    db_prueba.commit()

    assert servicio.obtener(db_prueba, "prueba_x") == "42"


def test_obtener_entero_convierte_a_numero(db_prueba) -> None:
    db_prueba.add(ParametroSistema(nombre="prueba_y", valor="7"))
    db_prueba.commit()

    assert servicio.obtener_entero(db_prueba, "prueba_y") == 7


def test_obtener_lanza_error_si_no_existe(db_prueba) -> None:
    with pytest.raises(ValueError):
        servicio.obtener(db_prueba, "no_existe")
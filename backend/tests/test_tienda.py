"""Pruebas de la tienda: paquetes, compras e historial."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modelos.compra import EstadoCompra
from app.modelos.lote_tokens import LoteDeTokens, OrigenLote, TipoSaldo
from app.servicios import tienda, tokens
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


def test_una_compra_crea_un_lote_pagado_que_vence_en_30_dias(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)

    compra = tienda.comprar(db_prueba, usuario.id, "popular")
    lote = db_prueba.get(LoteDeTokens, compra.lote_id)

    assert compra.estado == EstadoCompra.PAGADA
    assert (compra.cantidad_tokens, compra.monto_pesos) == (13, 990)
    assert lote.tipo_saldo == TipoSaldo.PAGADO
    assert lote.origen == OrigenLote.COMPRA
    assert (lote.fecha_vencimiento - lote.fecha_recepcion) == timedelta(days=30)
    assert tokens.calcular_saldo(db_prueba, usuario.id, TipoSaldo.PAGADO) == 13


def test_cada_compra_es_un_lote_distinto(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)

    primera = tienda.comprar(db_prueba, usuario.id, "basico")
    segunda = tienda.comprar(db_prueba, usuario.id, "basico")

    assert primera.lote_id != segunda.lote_id
    assert tokens.calcular_saldo(db_prueba, usuario.id) == 10


def test_un_paquete_inexistente_no_se_vende(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)

    with pytest.raises(tienda.PaqueteInexistente):
        tienda.comprar(db_prueba, usuario.id, "gratis-para-siempre")


def test_los_paquetes_grandes_tienen_mejor_precio_por_token() -> None:
    precios = [paquete.pesos_por_token for paquete in tienda.PAQUETES.values()]

    assert precios == sorted(precios, reverse=True)


def test_comprar_por_la_api_y_ver_el_historial(cliente_db: TestClient, db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)

    respuesta = cliente_db.post("/tienda/compras", json={"paquete": "basico"}, headers=cabecera(usuario))
    assert respuesta.status_code == 201
    cliente_db.post("/tienda/compras", json={"paquete": "volumen"}, headers=cabecera(usuario))

    historial = cliente_db.get("/tienda/compras", headers=cabecera(usuario)).json()

    assert [c["paquete"] for c in historial] == ["volumen", "basico"]
    assert historial[1]["tokens_restantes"] == 5


def test_el_historial_muestra_cuanto_queda_de_cada_compra(cliente_db: TestClient, db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    tienda.comprar(db_prueba, usuario.id, "basico")
    tokens.retener(db_prueba, usuario.id, 3)

    historial = cliente_db.get("/tienda/compras", headers=cabecera(usuario)).json()

    assert historial[0]["tokens_restantes"] == 2
    assert historial[0]["vencida"] is False


def test_sin_sesion_no_se_compra(cliente_db: TestClient) -> None:
    assert cliente_db.post("/tienda/compras", json={"paquete": "basico"}).status_code == 401


def test_los_paquetes_son_publicos(cliente_db: TestClient) -> None:
    respuesta = cliente_db.get("/tienda/paquetes")

    assert respuesta.status_code == 200
    assert [p["codigo"] for p in respuesta.json()] == ["basico", "popular", "volumen"]
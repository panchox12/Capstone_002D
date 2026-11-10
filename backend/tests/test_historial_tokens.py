"""Pruebas del historial de tokens: entradas, consumos, devoluciones y pagos."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.retencion import Retencion
from app.servicios import habilidades, presencia, solicitudes, temas, tokens
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


def test_una_entrada_aparece_con_su_origen(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    tokens.otorgar(db_prueba, usuario.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)

    (movimiento,) = tokens.historial(db_prueba, usuario.id)

    assert movimiento["tipo"] == "entrega"
    assert movimiento["origen"] == "entrega_semanal"
    assert movimiento["cantidad"] == 10
    assert movimiento["saldo_resultante"] == 10


def test_un_consumo_de_varios_lotes_es_un_solo_movimiento(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    tokens.otorgar(db_prueba, usuario.id, 2, TipoSaldo.GRATIS, OrigenLote.VIDEO, 3)
    tokens.otorgar(db_prueba, usuario.id, 5, TipoSaldo.PAGADO, OrigenLote.COMPRA, 30)

    tokens.retener(db_prueba, usuario.id, 4)
    movimientos = tokens.historial(db_prueba, usuario.id)

    assert [m["tipo"] for m in movimientos] == ["consumo", "compra", "entrega"]
    assert movimientos[0]["cantidad"] == -4
    assert movimientos[0]["saldo_resultante"] == 3


def test_la_devolucion_vuelve_a_sumar(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    tokens.otorgar(db_prueba, usuario.id, 6, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    retencion = tokens.retener(db_prueba, usuario.id, 3)

    tokens.reembolsar(db_prueba, retencion.id, "rechazada")
    ultimo = tokens.historial(db_prueba, usuario.id)[0]

    assert ultimo["tipo"] == "reembolso"
    assert ultimo["cantidad"] == 3
    assert ultimo["saldo_resultante"] == 6


def test_cada_uno_ve_el_tema_y_a_la_otra_persona(db_prueba: Session, redis_falso) -> None:
    tutor = crear_usuario(db_prueba, nombre="Rodrigo Salas", verificado=True)
    aprendiz = crear_usuario(db_prueba, nombre="Valentina Rojas", verificado=True)
    presencia.marcar_en_linea(redis_falso, tutor.id)
    tokens.otorgar(db_prueba, aprendiz.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    raiz = temas.crear(db_prueba, "Ciencias exactas")
    grupo = temas.crear(db_prueba, "Matematicas", raiz.id)
    algebra = temas.crear(db_prueba, "Algebra", grupo.id)
    habilidad = habilidades.publicar(db_prueba, tutor.id, algebra.id, 3)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")
    retencion = db_prueba.execute(select(Retencion).where(Retencion.solicitud_id == solicitud.id)).scalar_one()

    tokens.liberar(db_prueba, retencion.id, tutor.id)
    del_aprendiz = tokens.historial(db_prueba, aprendiz.id)[0]
    del_tutor = tokens.historial(db_prueba, tutor.id)[0]

    assert (del_aprendiz["tipo"], del_aprendiz["cantidad"]) == ("consumo", -3)
    assert (del_aprendiz["tema"], del_aprendiz["contraparte"]) == ("Algebra", "Rodrigo Salas")
    assert (del_tutor["origen"], del_tutor["cantidad"]) == ("pago_por_ensenar", 3)
    assert (del_tutor["tema"], del_tutor["contraparte"]) == ("Algebra", "Valentina Rojas")


def test_la_ruta_entrega_solo_lo_propio_y_respeta_el_limite(cliente_db: TestClient, db_prueba: Session) -> None:
    ana = crear_usuario(db_prueba)
    otro = crear_usuario(db_prueba)
    for _ in range(3):
        tokens.otorgar(db_prueba, ana.id, 1, TipoSaldo.GRATIS, OrigenLote.VIDEO, 7)
    tokens.otorgar(db_prueba, otro.id, 5, TipoSaldo.PAGADO, OrigenLote.COMPRA, 30)

    respuesta = cliente_db.get("/tokens/movimientos", params={"limite": 2}, headers=cabecera(ana))

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 2
    assert [m["saldo_resultante"] for m in datos] == [3, 2]
    assert all(m["origen"] == "video" for m in datos)


def test_sin_sesion_no_hay_historial(cliente_db: TestClient) -> None:
    assert cliente_db.get("/tokens/movimientos").status_code == 401
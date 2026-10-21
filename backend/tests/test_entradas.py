"""Pruebas de las entradas gratuitas: entrega semanal, videos y vencimientos."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.seguridad import TIPO_CONFIRMACION, crear_token
from app.modelos.lote_tokens import EstadoLote, OrigenLote, TipoSaldo
from app.modelos.parametro import ParametroSistema
from app.modelos.usuario import EstadoCuenta
from app.modelos.video_visto import VideoVisto
from app.servicios import entradas, tokens
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


def _gratis(db: Session, usuario) -> int:
    return tokens.calcular_saldo(db, usuario.id, TipoSaldo.GRATIS)


# --- Entrega semanal ----------------------------------------------------------


def test_la_entrega_semanal_llena_hasta_el_tope(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)

    entregados = entradas.entregar_semanal(db_prueba, usuario.id)

    assert entregados == 10
    assert _gratis(db_prueba, usuario) == 10


def test_la_entrega_semanal_rellena_y_no_suma(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    tokens.otorgar(db_prueba, usuario.id, 4, TipoSaldo.GRATIS, OrigenLote.VIDEO, 7)

    entregados = entradas.entregar_semanal(db_prueba, usuario.id)

    assert entregados == 6
    assert _gratis(db_prueba, usuario) == 10


def test_con_el_saldo_gratuito_lleno_no_se_entrega_nada(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    entradas.entregar_semanal(db_prueba, usuario.id)

    assert entradas.entregar_semanal(db_prueba, usuario.id) == 0
    assert _gratis(db_prueba, usuario) == 10


def test_los_tokens_pagados_no_cuentan_para_el_tope(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    tokens.otorgar(db_prueba, usuario.id, 30, TipoSaldo.PAGADO, OrigenLote.COMPRA, 30)

    assert entradas.entregar_semanal(db_prueba, usuario.id) == 10


def test_la_entrega_de_los_lunes_salta_las_cuentas_no_activas(db_prueba: Session) -> None:
    activa = crear_usuario(db_prueba)
    pendiente = crear_usuario(db_prueba, estado=EstadoCuenta.PENDIENTE_CONFIRMACION)

    entradas.entregar_semanal_a_todos(db_prueba)

    assert _gratis(db_prueba, activa) == 10
    assert _gratis(db_prueba, pendiente) == 0


def test_al_confirmar_el_correo_llega_la_primera_entrega(
    cliente_db: TestClient, db_prueba: Session
) -> None:
    usuario = crear_usuario(db_prueba, estado=EstadoCuenta.PENDIENTE_CONFIRMACION)
    enlace = crear_token(sujeto=str(usuario.id), tipo=TIPO_CONFIRMACION)

    respuesta = cliente_db.get(f"/auth/confirmar/{enlace}")

    assert respuesta.status_code == 200
    assert _gratis(db_prueba, usuario) == 10


# --- Videos ------------------------------------------------------------------------


def test_un_video_entrega_un_token_gratuito(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)

    video = entradas.ver_video(db_prueba, usuario.id)

    assert video.tokens_otorgados == 1
    assert _gratis(db_prueba, usuario) == 1


def test_no_se_pueden_ver_mas_de_tres_videos_en_24_horas(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    for _ in range(3):
        entradas.ver_video(db_prueba, usuario.id)

    with pytest.raises(entradas.TopeDeVideos):
        entradas.ver_video(db_prueba, usuario.id)


def test_los_videos_de_ayer_no_cuentan_para_el_tope(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    for _ in range(3):
        video = entradas.ver_video(db_prueba, usuario.id)
        video.fecha = video.fecha - timedelta(hours=25)
    db_prueba.flush()

    entradas.ver_video(db_prueba, usuario.id)

    assert entradas.videos_vistos_hoy(db_prueba, usuario.id) == 1


def test_con_el_saldo_gratuito_lleno_el_video_no_entrega(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    entradas.entregar_semanal(db_prueba, usuario.id)

    with pytest.raises(entradas.SaldoGratisCompleto):
        entradas.ver_video(db_prueba, usuario.id)
    assert db_prueba.query(VideoVisto).filter_by(usuario_id=usuario.id).count() == 0


def test_el_video_entrega_solo_lo_que_falta_para_el_tope(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    db_prueba.get(ParametroSistema, entradas.PARAM_TOKENS_POR_VIDEO).valor = "3"
    tokens.otorgar(db_prueba, usuario.id, 9, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)

    video = entradas.ver_video(db_prueba, usuario.id)

    assert video.tokens_otorgados == 1
    assert _gratis(db_prueba, usuario) == 10


# --- Vencimientos -------------------------------------------------------------------


def test_vencer_lotes_marca_solo_los_que_ya_vencieron(db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    viejo = tokens.otorgar(db_prueba, usuario.id, 3, TipoSaldo.GRATIS, OrigenLote.VIDEO, 7)
    nuevo = tokens.otorgar(db_prueba, usuario.id, 5, TipoSaldo.PAGADO, OrigenLote.COMPRA, 30)
    viejo.fecha_vencimiento = tokens.ahora() - timedelta(minutes=1)
    db_prueba.flush()

    entradas.vencer_lotes(db_prueba)
    db_prueba.refresh(viejo)
    db_prueba.refresh(nuevo)

    assert viejo.estado == EstadoLote.VENCIDO
    assert nuevo.estado == EstadoLote.VIGENTE


# --- Endpoints --------------------------------------------------------------


def test_el_saldo_muestra_cada_tipo_y_los_lotes(cliente_db: TestClient, db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)
    tokens.otorgar(db_prueba, usuario.id, 6, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    tokens.otorgar(db_prueba, usuario.id, 8, TipoSaldo.PAGADO, OrigenLote.COMPRA, 30)
    tokens.retener(db_prueba, usuario.id, 2)

    datos = cliente_db.get("/tokens/saldo", headers=cabecera(usuario)).json()

    assert (datos["gratis"], datos["pagado"], datos["total"], datos["retenidos"]) == (4, 8, 12, 2)
    assert [lote["tipo_saldo"] for lote in datos["lotes"]] == ["gratis", "pagado"]


def test_ver_video_por_la_api(cliente_db: TestClient, db_prueba: Session) -> None:
    usuario = crear_usuario(db_prueba)

    for numero in (1, 2, 3):
        respuesta = cliente_db.post("/tokens/videos", headers=cabecera(usuario))
        assert respuesta.status_code == 201
        assert respuesta.json()["videos_vistos_hoy"] == numero

    assert cliente_db.post("/tokens/videos", headers=cabecera(usuario)).status_code == 429
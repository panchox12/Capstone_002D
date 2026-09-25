"""Pruebas del modelo de lotes: la base de datos protege la integridad."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.seguridad import hashear_contrasena
from app.modelos.lote_tokens import LoteDeTokens, OrigenLote, TipoSaldo
from app.modelos.usuario import EstadoCuenta, Usuario


def _usuario(db):
    u = Usuario(
        correo=f"{uuid.uuid4()}@duocuc.cl",
        contrasena_hash=hashear_contrasena("cachai12345"),
        nombre_visible="Usuario Prueba",
        estado_cuenta=EstadoCuenta.ACTIVA,
        consentimiento_grabacion=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _lote(usuario_id, cantidad_original, cantidad_restante):
    ahora = datetime.now(timezone.utc)
    return LoteDeTokens(
        usuario_id=usuario_id,
        tipo_saldo=TipoSaldo.GRATIS,
        origen=OrigenLote.ENTREGA_SEMANAL,
        cantidad_original=cantidad_original,
        cantidad_restante=cantidad_restante,
        fecha_recepcion=ahora,
        fecha_vencimiento=ahora + timedelta(days=7),
    )


def test_un_lote_normal_se_crea_sin_problema(db_prueba) -> None:
    usuario = _usuario(db_prueba)
    db_prueba.add(_lote(usuario.id, 10, 10))
    db_prueba.commit()


def test_no_se_puede_crear_un_lote_con_saldo_negativo(db_prueba) -> None:
    usuario = _usuario(db_prueba)
    db_prueba.add(_lote(usuario.id, 10, -1))
    with pytest.raises(IntegrityError):
        db_prueba.commit()


def test_no_se_puede_crear_un_lote_que_gasto_mas_de_lo_que_tenia(db_prueba) -> None:
    usuario = _usuario(db_prueba)
    db_prueba.add(_lote(usuario.id, 10, 15))
    with pytest.raises(IntegrityError):
        db_prueba.commit()
"""Pruebas del motor de tokens: saldo, orden de consumo, retenciones,
"""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos.lote_tokens import EstadoLote, LoteDeTokens, OrigenLote, TipoSaldo
from app.modelos.parametro import ParametroSistema
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.transaccion import TipoTransaccion, Transaccion
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import tokens

# ---------------------------------------------------------------------------
# Preparacion
# ---------------------------------------------------------------------------


@pytest.fixture()
def parametros_base(db_prueba: Session) -> None:
    #Valores que el motor necessita.
    for nombre, valor in [
        (tokens.PARAM_DIAS_GRATIS, "7"),
        (tokens.PARAM_DIAS_COMPRADO, "30"),
        (tokens.PARAM_DIAS_ENSENADO, "15"),
    ]:
        db_prueba.add(ParametroSistema(nombre=nombre, valor=valor))
    db_prueba.flush()


def _usuario(db: Session) -> Usuario:
    usuario = Usuario(
        correo=f"{uuid.uuid4()}@prueba.cl",
        contrasena_hash="no-aplica",
        nombre_visible="Usuario Prueba",
        estado_cuenta=EstadoCuenta.ACTIVA,
        consentimiento_grabacion=True,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _lote(db: Session, usuario: Usuario, cantidad: int, tipo: TipoSaldo, vence_en_dias: int) -> LoteDeTokens:
    origen = OrigenLote.ENTREGA_SEMANAL if tipo == TipoSaldo.GRATIS else OrigenLote.COMPRA
    return tokens.otorgar(db, usuario.id, cantidad, tipo, origen, vence_en_dias)

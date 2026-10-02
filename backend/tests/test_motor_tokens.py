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


# ---------------------------------------------------------------------------
# Saldo
# ---------------------------------------------------------------------------


def test_saldo_suma_solo_lotes_vigentes(db_prueba: Session) -> None:
    usuario = _usuario(db_prueba)
    _lote(db_prueba, usuario, 5, TipoSaldo.PAGADO, vence_en_dias=10)
    vencido = _lote(db_prueba, usuario, 3, TipoSaldo.GRATIS, vence_en_dias=10)
    vencido.fecha_vencimiento = tokens.ahora() - timedelta(days=1)
    db_prueba.flush()

    assert tokens.calcular_saldo(db_prueba, usuario.id) == 5


def test_saldo_se_puede_consultar_por_tipo(db_prueba: Session) -> None:
    usuario = _usuario(db_prueba)
    _lote(db_prueba, usuario, 4, TipoSaldo.GRATIS, vence_en_dias=7)
    _lote(db_prueba, usuario, 6, TipoSaldo.PAGADO, vence_en_dias=30)

    assert tokens.calcular_saldo(db_prueba, usuario.id, TipoSaldo.GRATIS) == 4
    assert tokens.calcular_saldo(db_prueba, usuario.id, TipoSaldo.PAGADO) == 6


# ---------------------------------------------------------------------------
# Orden de consumo
# ---------------------------------------------------------------------------


def test_consume_primero_el_lote_que_vence_antes(db_prueba: Session) -> None:
    usuario = _usuario(db_prueba)
    pagado_lejano = _lote(db_prueba, usuario, 5, TipoSaldo.PAGADO, vence_en_dias=20)
    gratis_cercano = _lote(db_prueba, usuario, 5, TipoSaldo.GRATIS, vence_en_dias=3)

    tokens.retener(db_prueba, usuario.id, 3)

    assert gratis_cercano.cantidad_restante == 2
    assert pagado_lejano.cantidad_restante == 5


def test_en_empate_consume_primero_el_gratuito(db_prueba: Session) -> None:
    usuario = _usuario(db_prueba)
    pagado = _lote(db_prueba, usuario, 5, TipoSaldo.PAGADO, vence_en_dias=7)
    gratis = _lote(db_prueba, usuario, 5, TipoSaldo.GRATIS, vence_en_dias=7)
    gratis.fecha_vencimiento = pagado.fecha_vencimiento
    db_prueba.flush()

    tokens.retener(db_prueba, usuario.id, 3)

    assert gratis.cantidad_restante == 2
    assert pagado.cantidad_restante == 5


def test_un_consumo_puede_cruzar_varios_lotes(db_prueba: Session) -> None:
    usuario = _usuario(db_prueba)
    primero = _lote(db_prueba, usuario, 2, TipoSaldo.GRATIS, vence_en_dias=2)
    segundo = _lote(db_prueba, usuario, 3, TipoSaldo.PAGADO, vence_en_dias=9)

    retencion = tokens.retener(db_prueba, usuario.id, 4)

    assert primero.cantidad_restante == 0
    assert primero.estado == EstadoLote.AGOTADO
    assert segundo.cantidad_restante == 1
    consumos = db_prueba.execute(
        select(Transaccion).where(Transaccion.retencion_id == retencion.id)
    ).scalars().all()
    assert sorted(t.cantidad for t in consumos) == [2, 2]


def test_saldo_insuficiente_no_toca_nada(db_prueba: Session) -> None:
    usuario = _usuario(db_prueba)
    lote = _lote(db_prueba, usuario, 2, TipoSaldo.GRATIS, vence_en_dias=7)

    with pytest.raises(tokens.SaldoInsuficiente):
        tokens.retener(db_prueba, usuario.id, 5)

    assert lote.cantidad_restante == 2
    retenciones = db_prueba.execute(
        select(func.count()).select_from(Retencion).where(Retencion.usuario_id == usuario.id)
    ).scalar_one()
    assert retenciones == 0


# ---------------------------------------------------------------------------
# Liberacion y reembolso
# ---------------------------------------------------------------------------


def test_liberar_entrega_al_tutor_un_lote_ganado_por_ensenar(db_prueba: Session, parametros_base) -> None:
    aprendiz = _usuario(db_prueba)
    tutor = _usuario(db_prueba)
    _lote(db_prueba, aprendiz, 5, TipoSaldo.PAGADO, vence_en_dias=30)
    retencion = tokens.retener(db_prueba, aprendiz.id, 3)

    lote_tutor = tokens.liberar(db_prueba, retencion.id, tutor.id)

    assert lote_tutor.usuario_id == tutor.id
    assert lote_tutor.cantidad_original == 3
    assert lote_tutor.tipo_saldo == TipoSaldo.PAGADO
    assert lote_tutor.origen == OrigenLote.PAGO_POR_ENSENAR
    assert (lote_tutor.fecha_vencimiento - lote_tutor.fecha_recepcion).days == 15
    assert retencion.estado == EstadoRetencion.LIBERADA


def test_reembolso_devuelve_cada_token_a_su_lote_original(db_prueba: Session, parametros_base) -> None:
    usuario = _usuario(db_prueba)
    gratis = _lote(db_prueba, usuario, 2, TipoSaldo.GRATIS, vence_en_dias=3)
    pagado = _lote(db_prueba, usuario, 5, TipoSaldo.PAGADO, vence_en_dias=20)
    vencimiento_original = pagado.fecha_vencimiento
    retencion = tokens.retener(db_prueba, usuario.id, 4)

    tokens.reembolsar(db_prueba, retencion.id, "tutor no respondio")

    assert gratis.cantidad_restante == 2
    assert pagado.cantidad_restante == 5
    assert pagado.fecha_vencimiento == vencimiento_original
    assert retencion.estado == EstadoRetencion.REEMBOLSADA


def test_reembolso_con_lote_vencido_crea_un_lote_nuevo(db_prueba: Session, parametros_base) -> None:
    usuario = _usuario(db_prueba)
    lote = _lote(db_prueba, usuario, 3, TipoSaldo.PAGADO, vence_en_dias=5)
    retencion = tokens.retener(db_prueba, usuario.id, 3)
    lote.fecha_vencimiento = tokens.ahora() - timedelta(hours=1)
    db_prueba.flush()

    tokens.reembolsar(db_prueba, retencion.id, "resolucion de soporte")

    assert tokens.calcular_saldo(db_prueba, usuario.id) == 3
    compensaciones = db_prueba.execute(
        select(func.count()).select_from(Transaccion).where(Transaccion.tipo == TipoTransaccion.COMPENSACION)
    ).scalar_one()
    assert compensaciones == 0


def test_una_retencion_no_se_puede_resolver_dos_veces(db_prueba: Session, parametros_base) -> None:
    aprendiz = _usuario(db_prueba)
    tutor = _usuario(db_prueba)
    _lote(db_prueba, aprendiz, 5, TipoSaldo.PAGADO, vence_en_dias=30)
    retencion = tokens.retener(db_prueba, aprendiz.id, 3)
    tokens.liberar(db_prueba, retencion.id, tutor.id)

    with pytest.raises(tokens.RetencionNoActiva):
        tokens.liberar(db_prueba, retencion.id, tutor.id)
    with pytest.raises(tokens.RetencionNoActiva):
        tokens.reembolsar(db_prueba, retencion.id, "intento tardio")


# ---------------------------------------------------------------------------
# Ningun token se crea ni se elimina
# ---------------------------------------------------------------------------


def test_ningun_token_se_crea_ni_se_pierde_en_una_sesion(db_prueba: Session, parametros_base) -> None:
    aprendiz = _usuario(db_prueba)
    tutor = _usuario(db_prueba)
    _lote(db_prueba, aprendiz, 10, TipoSaldo.GRATIS, vence_en_dias=7)

    retencion = tokens.retener(db_prueba, aprendiz.id, 4)
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 6

    tokens.liberar(db_prueba, retencion.id, tutor.id)
    total = tokens.calcular_saldo(db_prueba, aprendiz.id) + tokens.calcular_saldo(db_prueba, tutor.id)
    assert total == 10


def test_la_base_de_datos_impide_devolver_mas_de_lo_que_salio(db_prueba: Session) -> None:

    usuario = _usuario(db_prueba)
    lote = _lote(db_prueba, usuario, 3, TipoSaldo.PAGADO, vence_en_dias=5)

    with pytest.raises(IntegrityError):
        with db_prueba.begin_nested():
            lote.cantidad_restante = 4
            db_prueba.flush()
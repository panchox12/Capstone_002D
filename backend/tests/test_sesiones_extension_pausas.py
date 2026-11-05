"""Pruebas de las sesiones: extension, pausas por caida y cierre anticipado.

Usa la sala falsa y los accesorios de test_sesiones.py. El tiempo se mueve
cambiando las fechas guardadas, igual que en esas pruebas.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.sesion import Bloque, EstadoBloque, EstadoPausa, EstadoSesion, PausaSesion
from app.servicios import sesiones, tokens
from tests.test_sesiones import _aviso, _conectar_ambos, _lotes_por_ensenar, aprendiz, sala, sesion, tutor  # noqa: F401
from tests.utilidades import cabecera

pytestmark = pytest.mark.usefixtures("parametros_iniciales")


@pytest.fixture()
def en_curso(db_prueba: Session, sesion, aprendiz, tutor):
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    return sesion


def _bloques(db: Session, sesion) -> list[Bloque]:
    return list(db.execute(select(Bloque).where(Bloque.sesion_id == sesion.id).order_by(Bloque.numero_orden)).scalars())


def _retenciones(db: Session, sesion) -> list[Retencion]:
    return list(db.execute(select(Retencion).where(Retencion.sesion_id == sesion.id)).scalars())


def _pausas(db: Session, sesion) -> list[PausaSesion]:
    return list(db.execute(select(PausaSesion).where(PausaSesion.sesion_id == sesion.id)).scalars())


def _extender(db: Session, sesion, aprendiz, tutor) -> None:
    sesiones.proponer_extension(db, aprendiz.id, sesion.id)
    sesiones.aceptar_extension(db, tutor.id, sesion.id)


# ---------------------------------------------------------------------------
# Extension
# ---------------------------------------------------------------------------


def test_la_extension_agrega_un_bloque_justo_despues_del_actual(db_prueba: Session, en_curso, aprendiz, tutor) -> None:
    _extender(db_prueba, en_curso, aprendiz, tutor)

    primero, segundo = _bloques(db_prueba, en_curso)
    assert segundo.numero_orden == 2
    assert segundo.hora_inicio == primero.hora_termino
    assert segundo.hora_termino - segundo.hora_inicio == timedelta(minutes=15)
    assert en_curso.bloques_cobrados == 2
    assert en_curso.extension_propuesta_por is None


def test_el_aprendiz_paga_la_extension_aunque_la_proponga_el_tutor(
    db_prueba: Session, en_curso, aprendiz, tutor
) -> None:
    sesiones.proponer_extension(db_prueba, tutor.id, en_curso.id)
    sesiones.aceptar_extension(db_prueba, aprendiz.id, en_curso.id)

    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 4
    assert all(r.usuario_id == aprendiz.id for r in _retenciones(db_prueba, en_curso))


def test_quien_propone_no_puede_aceptar(db_prueba: Session, en_curso, aprendiz) -> None:
    sesiones.proponer_extension(db_prueba, aprendiz.id, en_curso.id)

    with pytest.raises(sesiones.ExtensionPropia):
        sesiones.aceptar_extension(db_prueba, aprendiz.id, en_curso.id)


def test_no_se_proponen_dos_extensiones_a_la_vez(db_prueba: Session, en_curso, aprendiz, tutor) -> None:
    sesiones.proponer_extension(db_prueba, aprendiz.id, en_curso.id)

    with pytest.raises(sesiones.ExtensionYaPropuesta):
        sesiones.proponer_extension(db_prueba, tutor.id, en_curso.id)


def test_rechazar_descarta_la_propuesta_sin_cobrar(db_prueba: Session, en_curso, aprendiz, tutor) -> None:
    sesiones.proponer_extension(db_prueba, aprendiz.id, en_curso.id)
    sesiones.rechazar_extension(db_prueba, tutor.id, en_curso.id)

    assert en_curso.extension_propuesta_por is None
    assert len(_bloques(db_prueba, en_curso)) == 1
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 7


def test_sin_saldo_la_extension_se_descarta(db_prueba: Session, en_curso, aprendiz, tutor) -> None:
    tokens.retener(db_prueba, aprendiz.id, 7)
    sesiones.proponer_extension(db_prueba, tutor.id, en_curso.id)

    with pytest.raises(tokens.SaldoInsuficiente):
        sesiones.aceptar_extension(db_prueba, aprendiz.id, en_curso.id)
    assert en_curso.extension_propuesta_por is None
    assert len(_bloques(db_prueba, en_curso)) == 1


def test_no_se_extiende_una_sesion_que_no_ha_empezado(db_prueba: Session, sesion, aprendiz) -> None:
    with pytest.raises(sesiones.SesionNoEnCurso):
        sesiones.proponer_extension(db_prueba, aprendiz.id, sesion.id)


def test_con_tiempo_extendido_la_sesion_no_se_cierra_al_acabar_el_primer_bloque(
    db_prueba: Session, en_curso, aprendiz, tutor, sala
) -> None:
    _extender(db_prueba, en_curso, aprendiz, tutor)
    primero, segundo = _bloques(db_prueba, en_curso)
    primero.hora_termino = tokens.ahora() - timedelta(seconds=1)
    segundo.hora_inicio = primero.hora_termino
    db_prueba.flush()

    assert sesiones.cerrar_bloques_terminados(db_prueba, sala) == 0

    segundo.hora_termino = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()
    assert sesiones.cerrar_bloques_terminados(db_prueba, sala) == 1
    assert en_curso.estado == EstadoSesion.TERMINADA


def test_al_tutor_se_le_pagan_todos_los_bloques(db_prueba: Session, en_curso, aprendiz, tutor) -> None:
    _extender(db_prueba, en_curso, aprendiz, tutor)
    primero, segundo = _bloques(db_prueba, en_curso)
    segundo.hora_inicio = tokens.ahora() - timedelta(minutes=1)
    sesiones.terminar(db_prueba, en_curso, "prueba")
    en_curso.fecha_cierre = tokens.ahora() - timedelta(minutes=11)
    db_prueba.flush()

    assert sesiones.liberar_pagos(db_prueba) == 2
    assert sum(lote.cantidad_original for lote in _lotes_por_ensenar(db_prueba, tutor)) == 6


# ---------------------------------------------------------------------------
# Terminar antes de tiempo
# ---------------------------------------------------------------------------


def test_terminar_antes_cobra_el_bloque_empezado_y_devuelve_la_extension(
    db_prueba: Session, en_curso, aprendiz, tutor, sala
) -> None:
    _extender(db_prueba, en_curso, aprendiz, tutor)

    sesiones.terminar_por_participante(db_prueba, sala, aprendiz.id, en_curso.id)

    primero, segundo = _bloques(db_prueba, en_curso)
    assert en_curso.estado == EstadoSesion.TERMINADA
    assert en_curso.motivo_cierre == "el aprendiz termino la sesion"
    assert primero.estado == EstadoBloque.COMPLETADO
    assert segundo.estado == EstadoBloque.ANULADO
    assert en_curso.bloques_cobrados == 1
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 7
    assert en_curso.nombre_sala in sala.cerradas


def test_terminar_mientras_se_espera_cancela_y_devuelve_todo(db_prueba: Session, sesion, aprendiz, tutor, sala) -> None:
    sesiones.terminar_por_participante(db_prueba, sala, tutor.id, sesion.id)

    assert sesion.estado == EstadoSesion.CANCELADA
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 10


def test_una_sesion_terminada_no_se_vuelve_a_terminar(db_prueba: Session, en_curso, aprendiz, sala) -> None:
    sesiones.terminar_por_participante(db_prueba, sala, aprendiz.id, en_curso.id)

    with pytest.raises(sesiones.SesionNoEnCurso):
        sesiones.terminar_por_participante(db_prueba, sala, aprendiz.id, en_curso.id)


# ---------------------------------------------------------------------------
# Pausas por caida de conexion
# ---------------------------------------------------------------------------


def test_una_caida_abre_una_pausa_de_90_segundos(db_prueba: Session, en_curso, tutor) -> None:
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))

    (pausa,) = _pausas(db_prueba, en_curso)
    assert pausa.estado == EstadoPausa.ABIERTA
    assert pausa.usuario_id == tutor.id
    assert pausa.limite_reconexion - pausa.inicio == timedelta(seconds=90)


def test_al_volver_el_reloj_se_corre_lo_que_estuvo_detenido(db_prueba: Session, en_curso, tutor) -> None:
    (bloque,) = _bloques(db_prueba, en_curso)
    termino_original = bloque.hora_termino
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))
    (pausa,) = _pausas(db_prueba, en_curso)
    pausa.inicio = tokens.ahora() - timedelta(seconds=60)
    db_prueba.flush()

    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", en_curso, tutor))

    assert pausa.estado == EstadoPausa.RECONECTADA
    corrido = bloque.hora_termino - termino_original
    assert timedelta(seconds=59) <= corrido <= timedelta(seconds=62)


def test_si_se_caen_los_dos_el_reloj_se_corre_una_sola_vez(db_prueba: Session, en_curso, aprendiz, tutor) -> None:
    (bloque,) = _bloques(db_prueba, en_curso)
    termino_original = bloque.hora_termino
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, aprendiz))
    primera, segunda = sorted(_pausas(db_prueba, en_curso), key=lambda p: p.usuario_id == aprendiz.id)
    primera.inicio = tokens.ahora() - timedelta(seconds=50)
    segunda.inicio = tokens.ahora() - timedelta(seconds=30)
    db_prueba.flush()

    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", en_curso, tutor))
    assert bloque.hora_termino == termino_original
    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", en_curso, aprendiz))

    corrido = bloque.hora_termino - termino_original
    assert timedelta(seconds=49) <= corrido <= timedelta(seconds=52)


def test_con_alguien_caido_la_sesion_no_se_cierra_por_tiempo(db_prueba: Session, en_curso, tutor, sala) -> None:
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))
    (bloque,) = _bloques(db_prueba, en_curso)
    bloque.hora_termino = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()

    assert sesiones.cerrar_bloques_terminados(db_prueba, sala) == 0


def test_si_el_tutor_no_vuelve_la_sesion_termina_y_el_aprendiz_no_paga(
    db_prueba: Session, en_curso, aprendiz, tutor, sala
) -> None:
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))
    (pausa,) = _pausas(db_prueba, en_curso)
    pausa.limite_reconexion = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()

    assert sesiones.vencer_pausas(db_prueba, sala) == 1
    assert en_curso.estado == EstadoSesion.TERMINADA
    assert pausa.estado == EstadoPausa.VENCIDA
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 10
    assert all(r.estado == EstadoRetencion.REEMBOLSADA for r in _retenciones(db_prueba, en_curso))


def test_si_el_aprendiz_no_vuelve_el_tutor_igual_cobra(db_prueba: Session, en_curso, aprendiz, tutor, sala) -> None:
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, aprendiz))
    (pausa,) = _pausas(db_prueba, en_curso)
    pausa.limite_reconexion = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()

    sesiones.vencer_pausas(db_prueba, sala)

    assert en_curso.estado == EstadoSesion.TERMINADA
    assert all(r.estado == EstadoRetencion.ACTIVA for r in _retenciones(db_prueba, en_curso))


def test_a_la_cuarta_caida_la_sesion_termina(db_prueba: Session, en_curso, tutor) -> None:
    for _ in range(3):
        sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))
        sesiones.registrar_evento(db_prueba, _aviso("participant_joined", en_curso, tutor))
    assert en_curso.estado == EstadoSesion.EN_CURSO

    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))

    assert en_curso.estado == EstadoSesion.TERMINADA
    assert en_curso.motivo_cierre == "se acabaron las pausas por caidas de conexion"
    assert len(_pausas(db_prueba, en_curso)) == 3


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_la_extension_completa_por_la_api(
    db_prueba: Session, cliente_db: TestClient, en_curso, aprendiz, tutor
) -> None:
    propuesta = cliente_db.post(f"/sesiones/{en_curso.id}/extension", headers=cabecera(aprendiz))
    assert propuesta.status_code == 200
    assert propuesta.json()["extension_propuesta_por"] == str(aprendiz.id)

    propia = cliente_db.post(f"/sesiones/{en_curso.id}/extension/aceptar", headers=cabecera(aprendiz))
    assert propia.status_code == 409

    aceptada = cliente_db.post(f"/sesiones/{en_curso.id}/extension/aceptar", headers=cabecera(tutor))
    assert aceptada.status_code == 200
    assert aceptada.json()["bloques_cobrados"] == 2
    assert aceptada.json()["segundos_restantes_bloque"] > 15 * 60


def test_la_api_muestra_la_pausa(db_prueba: Session, cliente_db: TestClient, en_curso, aprendiz, tutor) -> None:
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", en_curso, tutor))

    datos = cliente_db.get(f"/sesiones/{en_curso.id}", headers=cabecera(aprendiz)).json()

    assert datos["pausa_activa"] is True
    assert datos["usuario_caido_id"] == str(tutor.id)
    assert 0 < datos["segundos_para_reconectar"] <= 90
    assert datos["pausas_usadas"] == 1
    assert datos["pausas_maximas"] == 3


def test_terminar_por_la_api(db_prueba: Session, cliente_db: TestClient, en_curso, tutor, sala) -> None:
    respuesta = cliente_db.post(f"/sesiones/{en_curso.id}/terminar", headers=cabecera(tutor))

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "terminada"
    otra_vez = cliente_db.post(f"/sesiones/{en_curso.id}/terminar", headers=cabecera(tutor))
    assert otra_vez.status_code == 409
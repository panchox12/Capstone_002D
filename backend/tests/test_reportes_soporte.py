"""Pruebas de los reportes, la bandeja de soporte, las resoluciones y las sanciones."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.lote_tokens import OrigenLote
from app.modelos.moderacion import EstadoReporte, MotivoReporte, Sancion, TipoSancion
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.usuario import EstadoCuenta, RolUsuario
from app.servicios import reportes, sesiones, tokens
from tests.test_sesiones import _conectar_ambos, _lotes_por_ensenar, aprendiz, sala, sesion, tutor  # noqa: F401
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")

DESCRIPCION = "El tutor no explico nada y corto antes"


@pytest.fixture()
def terminada(db_prueba: Session, sesion, aprendiz, tutor):
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    sesiones.terminar(db_prueba, sesion, "prueba")
    return sesion


@pytest.fixture()
def soporte(db_prueba: Session):
    usuario = crear_usuario(db_prueba, nombre="Equipo Soporte")
    usuario.rol = RolUsuario.SOPORTE
    db_prueba.flush()
    return usuario


def _reportar(db: Session, sesion, quien) -> object:
    return reportes.crear(db, quien.id, sesion.id, MotivoReporte.INCUMPLIMIENTO, DESCRIPCION)


def _retencion(db: Session, sesion) -> Retencion:
    return db.execute(select(Retencion).where(Retencion.sesion_id == sesion.id)).scalar_one()


# ---------------------------------------------------------------------------
# Reportar
# ---------------------------------------------------------------------------


def test_el_aprendiz_reporta_al_tutor_y_congela_el_pago(db_prueba: Session, terminada, aprendiz, tutor) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)

    assert reporte.reportado_id == tutor.id
    assert reporte.estado == EstadoReporte.ABIERTO
    assert reporte.congela_pago is True


def test_un_reporte_abierto_frena_el_pago_al_tutor(db_prueba: Session, terminada, aprendiz) -> None:
    _reportar(db_prueba, terminada, aprendiz)
    terminada.fecha_cierre = tokens.ahora() - timedelta(minutes=11)
    db_prueba.flush()

    assert sesiones.liberar_pagos(db_prueba) == 0
    assert _retencion(db_prueba, terminada).estado == EstadoRetencion.ACTIVA


def test_reportar_despues_del_pago_no_congela_nada(db_prueba: Session, terminada, aprendiz) -> None:
    terminada.fecha_cierre = tokens.ahora() - timedelta(minutes=11)
    db_prueba.flush()
    sesiones.liberar_pagos(db_prueba)

    assert _reportar(db_prueba, terminada, aprendiz).congela_pago is False


def test_no_se_reporta_pasadas_48_horas(db_prueba: Session, terminada, aprendiz) -> None:
    terminada.fecha_cierre = tokens.ahora() - timedelta(hours=49)
    db_prueba.flush()

    with pytest.raises(reportes.PlazoDeReporteVencido):
        _reportar(db_prueba, terminada, aprendiz)


def test_solo_se_reporta_una_sesion_terminada_y_propia(db_prueba: Session, sesion, aprendiz) -> None:
    ajeno = crear_usuario(db_prueba)
    with pytest.raises(reportes.SesionNoReportable):
        _reportar(db_prueba, sesion, aprendiz)
    with pytest.raises(reportes.SesionNoReportable):
        _reportar(db_prueba, sesion, ajeno)


def test_cada_uno_reporta_una_sola_vez(db_prueba: Session, terminada, aprendiz) -> None:
    _reportar(db_prueba, terminada, aprendiz)

    with pytest.raises(reportes.ReporteDuplicado):
        _reportar(db_prueba, terminada, aprendiz)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def test_reporte_fundado_con_pago_congelado_devuelve_los_tokens(
    db_prueba: Session, terminada, aprendiz, tutor, soporte
) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)

    reportes.resolver(db_prueba, soporte.id, reporte.id, True, "El tutor no se presento a explicar")

    assert reporte.estado == EstadoReporte.FUNDADO
    assert reporte.revisor_id == soporte.id
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 10
    assert _lotes_por_ensenar(db_prueba, tutor) == []


def test_reporte_fundado_despues_del_pago_compensa_desde_la_plataforma(
    db_prueba: Session, terminada, aprendiz, tutor, soporte
) -> None:
    terminada.fecha_cierre = tokens.ahora() - timedelta(minutes=11)
    db_prueba.flush()
    sesiones.liberar_pagos(db_prueba)
    reporte = _reportar(db_prueba, terminada, aprendiz)

    reportes.resolver(db_prueba, soporte.id, reporte.id, True, "Se comprobo el incumplimiento")

    # El tutor conserva lo cobrado y el aprendiz recibe un lote de compensacion.
    assert sum(lote.cantidad_original for lote in _lotes_por_ensenar(db_prueba, tutor)) == 3
    lotes = tokens.lotes_vigentes(db_prueba, aprendiz.id)
    assert any(lote.origen == OrigenLote.COMPENSACION and lote.cantidad_original == 3 for lote in lotes)
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 10


def test_reporte_desestimado_libera_el_pago_en_la_siguiente_revision(
    db_prueba: Session, terminada, aprendiz, soporte
) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)
    terminada.fecha_cierre = tokens.ahora() - timedelta(minutes=11)
    reportes.resolver(db_prueba, soporte.id, reporte.id, False, "La grabacion muestra que si explico")

    assert sesiones.liberar_pagos(db_prueba) == 1


def test_no_se_resuelve_dos_veces(db_prueba: Session, terminada, aprendiz, soporte) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)
    reportes.resolver(db_prueba, soporte.id, reporte.id, False, "Sin evidencia suficiente")

    with pytest.raises(reportes.ReporteYaResuelto):
        reportes.resolver(db_prueba, soporte.id, reporte.id, True, "Cambio de opinion")


def test_la_suspension_temporal_queda_con_folio_revisor_y_fecha_de_fin(
    db_prueba: Session, terminada, aprendiz, tutor, soporte
) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)

    reportes.resolver(db_prueba, soporte.id, reporte.id, True, "Conducta inapropiada", TipoSancion.TEMPORAL, 7)

    sancion = db_prueba.execute(select(Sancion).where(Sancion.usuario_id == tutor.id)).scalar_one()
    assert sancion.reporte_id == reporte.id
    assert sancion.revisor_id == soporte.id
    assert sancion.fecha_fin - sancion.fecha_inicio == timedelta(days=7)
    assert tutor.estado_cuenta == EstadoCuenta.SUSPENDIDA


def test_la_suspension_definitiva_no_tiene_fin(db_prueba: Session, terminada, aprendiz, tutor, soporte) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)

    reportes.resolver(db_prueba, soporte.id, reporte.id, True, "Fraude comprobado", TipoSancion.DEFINITIVA)

    assert tutor.estado_cuenta == EstadoCuenta.SUSPENDIDA
    assert tutor.suspendido_hasta is None
    assert reportes.reactivar_suspensiones(db_prueba) == 0


def test_no_se_sanciona_con_un_reporte_desestimado(db_prueba: Session, terminada, aprendiz, soporte) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)

    with pytest.raises(reportes.SancionSinFundamento):
        reportes.resolver(db_prueba, soporte.id, reporte.id, False, "No corresponde", TipoSancion.DEFINITIVA)


def test_la_suspension_temporal_vencida_reactiva_la_cuenta(
    db_prueba: Session, terminada, aprendiz, tutor, soporte
) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)
    reportes.resolver(db_prueba, soporte.id, reporte.id, True, "Conducta inapropiada", TipoSancion.TEMPORAL, 1)
    tutor.suspendido_hasta = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()

    assert reportes.reactivar_suspensiones(db_prueba) == 1
    assert tutor.estado_cuenta == EstadoCuenta.ACTIVA


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_reportar_por_la_api(cliente_db: TestClient, terminada, aprendiz) -> None:
    cuerpo = {"sesion_id": str(terminada.id), "motivo": "conducta", "descripcion": DESCRIPCION}

    creado = cliente_db.post("/reportes", json=cuerpo, headers=cabecera(aprendiz))
    repetido = cliente_db.post("/reportes", json=cuerpo, headers=cabecera(aprendiz))
    mios = cliente_db.get("/reportes/mios", headers=cabecera(aprendiz))

    assert creado.status_code == 201
    assert creado.json()["folio"] >= 1000
    assert repetido.status_code == 409
    assert [r["id"] for r in mios.json()] == [creado.json()["id"]]


def test_la_bandeja_es_solo_para_el_personal(cliente_db: TestClient, aprendiz, soporte) -> None:
    assert cliente_db.get("/soporte/reportes", headers=cabecera(aprendiz)).status_code == 403
    assert cliente_db.get("/soporte/reportes", headers=cabecera(soporte)).status_code == 200


def test_soporte_ve_el_caso_y_lo_resuelve(
    db_prueba: Session, cliente_db: TestClient, terminada, aprendiz, soporte
) -> None:
    reporte = _reportar(db_prueba, terminada, aprendiz)

    abiertos = cliente_db.get("/soporte/reportes?estado=abierto", headers=cabecera(soporte)).json()
    assert [r["folio"] for r in abiertos] == [reporte.folio]

    detalle = cliente_db.get(f"/soporte/reportes/{reporte.id}", headers=cabecera(soporte)).json()
    assert detalle["pago"] == {"retenido": 3, "pagado": 0, "devuelto": 0}
    assert detalle["reportado"]["nombre_visible"] == "Rodrigo Salas"

    sin_dias = {"fundado": True, "resolucion": "Se comprobo la falta", "tipo_sancion": "temporal"}
    assert cliente_db.post(f"/soporte/reportes/{reporte.id}/resolver", json=sin_dias, headers=cabecera(soporte)).status_code == 422

    resuelto = cliente_db.post(
        f"/soporte/reportes/{reporte.id}/resolver",
        json={**sin_dias, "dias_suspension": 3},
        headers=cabecera(soporte),
    )
    assert resuelto.status_code == 200
    assert resuelto.json()["estado"] == "fundado"
    assert resuelto.json()["pago"] == {"retenido": 0, "pagado": 0, "devuelto": 3}
    assert resuelto.json()["sanciones_previas_reportado"] == 1
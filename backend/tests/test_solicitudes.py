"""Pruebas de las solicitudes: modalidades, retencion, respuestas, cancelacion y vencimiento."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelos.habilidad import EstadoHabilidad
from app.modelos.lote_tokens import OrigenLote, TipoSaldo
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.solicitud import EstadoSolicitud, ModalidadSolicitud, Solicitud
from app.modelos.usuario import Usuario
from app.servicios import habilidades, presencia, solicitudes, temas, tokens
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")

# ---------------------------------------------------------------------------
# Preparacion: un tutor conectado que cobra 3 por Algebra y un aprendiz con 10 tokens
# ---------------------------------------------------------------------------


@pytest.fixture()
def algebra(db_prueba: Session):
    raiz = temas.crear(db_prueba, "Ciencias exactas")
    grupo = temas.crear(db_prueba, "Matematicas", raiz.id)
    return temas.crear(db_prueba, "Algebra", grupo.id)


@pytest.fixture()
def tutor(db_prueba: Session, redis_falso):
    usuario = crear_usuario(db_prueba, nombre="Rodrigo Salas", verificado=True)
    presencia.marcar_en_linea(redis_falso, usuario.id)
    return usuario


@pytest.fixture()
def habilidad(db_prueba: Session, tutor, algebra):
    return habilidades.publicar(db_prueba, tutor.id, algebra.id, 3)


@pytest.fixture()
def aprendiz(db_prueba: Session):
    usuario = crear_usuario(db_prueba, nombre="Valentina Rojas", verificado=True)
    tokens.otorgar(db_prueba, usuario.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    return usuario


def _saldo(db: Session, usuario) -> int:
    return tokens.calcular_saldo(db, usuario.id)


def _retencion(db: Session, solicitud: Solicitud) -> Retencion:
    return db.execute(select(Retencion).where(Retencion.solicitud_id == solicitud.id)).scalar_one()


def _otro_tutor(db: Session, r, algebra, precio: int = 2, conectado: bool = True):
    otro = crear_usuario(db, nombre="Diego Contreras", verificado=True)
    if conectado:
        presencia.marcar_en_linea(r, otro.id)
    return habilidades.publicar(db, otro.id, algebra.id, precio)


# ---------------------------------------------------------------------------
# Enviar
# ---------------------------------------------------------------------------


def test_enviar_retiene_el_precio_del_primer_bloque(db_prueba: Session, redis_falso, aprendiz, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")

    assert solicitud.estado == EstadoSolicitud.PENDIENTE
    assert solicitud.precio_bloque == 3
    assert _saldo(db_prueba, aprendiz) == 7
    assert _retencion(db_prueba, solicitud).estado == EstadoRetencion.ACTIVA


def test_el_plazo_para_responder_es_de_cinco_minutos(db_prueba: Session, redis_falso, aprendiz, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")

    assert solicitud.fecha_limite_respuesta - solicitud.fecha_envio == timedelta(minutes=5)


def test_sin_saldo_suficiente_no_se_envia_nada(db_prueba: Session, redis_falso, habilidad) -> None:
    pobre = crear_usuario(db_prueba, verificado=True)
    tokens.otorgar(db_prueba, pobre.id, 2, TipoSaldo.GRATIS, OrigenLote.VIDEO, 7)

    with pytest.raises(tokens.SaldoInsuficiente):
        solicitudes.enviar(db_prueba, redis_falso, pobre.id, habilidad.id, "Duda")

    assert db_prueba.execute(select(Solicitud).where(Solicitud.aprendiz_id == pobre.id)).first() is None
    assert _saldo(db_prueba, pobre) == 2


def test_nadie_se_pide_ayuda_a_si_mismo(db_prueba: Session, redis_falso, tutor, habilidad) -> None:
    tokens.otorgar(db_prueba, tutor.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)

    with pytest.raises(solicitudes.SolicitudAPropia):
        solicitudes.enviar(db_prueba, redis_falso, tutor.id, habilidad.id, "Duda")


def test_una_habilidad_pausada_no_recibe_solicitudes(db_prueba: Session, redis_falso, aprendiz, habilidad) -> None:
    habilidad.estado = EstadoHabilidad.PAUSADA
    db_prueba.flush()

    with pytest.raises(solicitudes.HabilidadNoDisponible):
        solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")


def test_no_se_insiste_al_mismo_tutor_mientras_espera(db_prueba: Session, redis_falso, aprendiz, habilidad) -> None:
    solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")

    with pytest.raises(solicitudes.SolicitudDuplicada):
        solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Otra vez")


def test_el_precio_queda_fijo_aunque_el_tutor_lo_cambie(db_prueba: Session, redis_falso, aprendiz, tutor, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")

    habilidades.actualizar(db_prueba, tutor.id, habilidad.id, precio=5)

    assert solicitud.precio_bloque == 3


# ---------------------------------------------------------------------------
# Aceptar
# ---------------------------------------------------------------------------


def test_aceptar_mantiene_los_tokens_retenidos(db_prueba: Session, redis_falso, aprendiz, tutor, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")

    solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)

    assert solicitud.estado == EstadoSolicitud.ACEPTADA
    assert _retencion(db_prueba, solicitud).estado == EstadoRetencion.ACTIVA
    assert _saldo(db_prueba, aprendiz) == 7
    assert _saldo(db_prueba, tutor) == 0


def test_aceptar_una_cancela_las_demas_del_aprendiz(
    db_prueba: Session, redis_falso, aprendiz, tutor, habilidad, algebra
) -> None:
    otra_habilidad = _otro_tutor(db_prueba, redis_falso, algebra, precio=2)
    elegida = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    descartada = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, otra_habilidad.id, "Duda")
    assert _saldo(db_prueba, aprendiz) == 5

    solicitudes.aceptar(db_prueba, tutor.id, elegida.id)

    assert descartada.estado == EstadoSolicitud.CANCELADA
    assert _retencion(db_prueba, descartada).estado == EstadoRetencion.REEMBOLSADA
    assert _saldo(db_prueba, aprendiz) == 7


def test_solo_el_tutor_de_la_solicitud_la_acepta(db_prueba: Session, redis_falso, aprendiz, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    intruso = crear_usuario(db_prueba, verificado=True)

    for quien in (intruso, aprendiz):
        with pytest.raises(solicitudes.SolicitudNoEncontrada):
            solicitudes.aceptar(db_prueba, quien.id, solicitud.id)


def test_no_se_acepta_dos_veces(db_prueba: Session, redis_falso, aprendiz, tutor, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)

    with pytest.raises(solicitudes.SolicitudYaResuelta):
        solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)


def test_pasado_el_plazo_ya_no_se_puede_aceptar(db_prueba: Session, redis_falso, aprendiz, tutor, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    solicitud.fecha_limite_respuesta = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()

    with pytest.raises(solicitudes.SolicitudVencida):
        solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)


# ---------------------------------------------------------------------------
# Rechazar, cancelar y vencer: los tres devuelven los tokens
# ---------------------------------------------------------------------------


def test_rechazar_devuelve_los_tokens(db_prueba: Session, redis_falso, aprendiz, tutor, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")

    solicitudes.rechazar(db_prueba, tutor.id, solicitud.id)

    assert solicitud.estado == EstadoSolicitud.RECHAZADA
    assert _saldo(db_prueba, aprendiz) == 10


def test_solo_el_aprendiz_cancela_su_solicitud(db_prueba: Session, redis_falso, aprendiz, tutor, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")

    with pytest.raises(solicitudes.SolicitudNoEncontrada):
        solicitudes.cancelar(db_prueba, tutor.id, solicitud.id)

    solicitudes.cancelar(db_prueba, aprendiz.id, solicitud.id)
    assert solicitud.estado == EstadoSolicitud.CANCELADA
    assert _saldo(db_prueba, aprendiz) == 10


def test_el_proceso_vence_solo_las_atrasadas(db_prueba: Session, redis_falso, aprendiz, habilidad, algebra) -> None:
    atrasada = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    a_tiempo = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, _otro_tutor(db_prueba, redis_falso, algebra).id, "Duda")
    atrasada.fecha_limite_respuesta = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()

    vencidas = solicitudes.vencer_atrasadas(db_prueba)

    assert vencidas == 1
    assert atrasada.estado == EstadoSolicitud.VENCIDA
    assert a_tiempo.estado == EstadoSolicitud.PENDIENTE
    assert _saldo(db_prueba, aprendiz) == 8


def test_el_proceso_no_toca_las_aceptadas(db_prueba: Session, redis_falso, aprendiz, tutor, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)
    solicitud.fecha_limite_respuesta = tokens.ahora() - timedelta(minutes=1)
    db_prueba.flush()

    assert solicitudes.vencer_atrasadas(db_prueba) == 0
    assert solicitud.estado == EstadoSolicitud.ACEPTADA


def test_ningun_token_se_pierde_en_el_ciclo_completo(
    db_prueba: Session, redis_falso, aprendiz, tutor, habilidad, algebra
) -> None:
    def total() -> int:
        return _saldo(db_prueba, aprendiz) + tokens.calcular_retenido(db_prueba, aprendiz.id)

    otra = _otro_tutor(db_prueba, redis_falso, algebra)
    primera = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    assert total() == 10
    solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, otra.id, "Duda")
    assert total() == 10
    solicitudes.aceptar(db_prueba, tutor.id, primera.id)
    assert total() == 10


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def test_sin_identidad_verificada_no_se_envian_solicitudes(
    cliente_db: TestClient, db_prueba: Session, habilidad
) -> None:
    sin_verificar = crear_usuario(db_prueba, verificado=False)

    respuesta = cliente_db.post(
        "/solicitudes",
        json={"habilidad_id": str(habilidad.id), "mensaje": "Duda"},
        headers=cabecera(sin_verificar),
    )

    assert respuesta.status_code == 403


def test_flujo_completo_por_la_api(cliente_db: TestClient, db_prueba: Session, aprendiz, tutor, habilidad) -> None:
    enviada = cliente_db.post(
        "/solicitudes",
        json={"habilidad_id": str(habilidad.id), "mensaje": "No entiendo factorizar por agrupacion"},
        headers=cabecera(aprendiz),
    )
    assert enviada.status_code == 201
    assert 295 <= enviada.json()["segundos_restantes"] <= 300

    recibidas = cliente_db.get("/solicitudes/recibidas", headers=cabecera(tutor)).json()
    assert recibidas[0]["aprendiz"]["nombre_visible"] == "Valentina Rojas"
    assert recibidas[0]["tema_nombre"] == "Algebra"

    aceptada = cliente_db.post(f"/solicitudes/{enviada.json()['id']}/aceptar", headers=cabecera(tutor))
    assert aceptada.status_code == 200
    assert aceptada.json()["estado"] == "aceptada"
    assert aceptada.json()["segundos_restantes"] == 0

    mias = cliente_db.get("/solicitudes/enviadas", headers=cabecera(aprendiz)).json()
    assert mias[0]["estado"] == "aceptada"


def test_sin_saldo_la_api_explica_cuanto_falta(cliente_db: TestClient, db_prueba: Session, habilidad) -> None:
    pobre = crear_usuario(db_prueba, verificado=True)

    respuesta = cliente_db.post(
        "/solicitudes",
        json={"habilidad_id": str(habilidad.id), "mensaje": "Duda"},
        headers=cabecera(pobre),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "No te alcanza: tienes 0 tokens y esta consulta cuesta 3"


def test_un_mensaje_vacio_se_rechaza(cliente_db: TestClient, db_prueba: Session, aprendiz, habilidad) -> None:
    respuesta = cliente_db.post(
        "/solicitudes",
        json={"habilidad_id": str(habilidad.id), "mensaje": "   "},
        headers=cabecera(aprendiz),
    )

    assert respuesta.status_code == 422


def test_responder_una_solicitud_ya_resuelta_devuelve_409(
    cliente_db: TestClient, db_prueba: Session, redis_falso, aprendiz, tutor, habilidad
) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")
    solicitudes.rechazar(db_prueba, tutor.id, solicitud.id)

    respuesta = cliente_db.post(f"/solicitudes/{solicitud.id}/aceptar", headers=cabecera(tutor))

    assert respuesta.status_code == 409


# ---------------------------------------------------------------------------
# Modalidad diferida: el tutor esta desconectado
# ---------------------------------------------------------------------------


def test_al_tutor_conectado_la_solicitud_va_en_vivo(db_prueba: Session, redis_falso, aprendiz, habilidad) -> None:
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Duda")

    assert solicitud.modalidad == ModalidadSolicitud.EN_VIVO


def test_al_tutor_desconectado_la_solicitud_va_diferida_y_no_retiene(
    db_prueba: Session, redis_falso, aprendiz, algebra
) -> None:
    ausente = _otro_tutor(db_prueba, redis_falso, algebra, precio=3, conectado=False)

    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, ausente.id, "Duda")

    assert solicitud.modalidad == ModalidadSolicitud.DIFERIDA
    assert _saldo(db_prueba, aprendiz) == 10
    assert tokens.calcular_retenido(db_prueba, aprendiz.id) == 0
    assert solicitud.fecha_limite_respuesta - solicitud.fecha_envio == timedelta(hours=24)


def test_sin_saldo_tampoco_se_envia_una_diferida(db_prueba: Session, redis_falso, algebra) -> None:
    ausente = _otro_tutor(db_prueba, redis_falso, algebra, precio=3, conectado=False)
    pobre = crear_usuario(db_prueba, verificado=True)
    tokens.otorgar(db_prueba, pobre.id, 2, TipoSaldo.GRATIS, OrigenLote.VIDEO, 7)

    with pytest.raises(tokens.SaldoInsuficiente):
        solicitudes.enviar(db_prueba, redis_falso, pobre.id, ausente.id, "Duda")


def test_si_redis_no_responde_la_solicitud_queda_diferida(
    db_prueba: Session, aprendiz, habilidad
) -> None:
    class RedisCaido:
        def mget(self, *_args, **_kwargs):
            raise solicitudes.redis.ConnectionError("sin conexion")

    solicitud = solicitudes.enviar(db_prueba, RedisCaido(), aprendiz.id, habilidad.id, "Duda")

    assert solicitud.modalidad == ModalidadSolicitud.DIFERIDA


def test_aceptar_una_diferida_retiene_en_ese_momento(db_prueba: Session, redis_falso, aprendiz, algebra) -> None:
    ausente = _otro_tutor(db_prueba, redis_falso, algebra, precio=3, conectado=False)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, ausente.id, "Duda")

    solicitudes.aceptar(db_prueba, ausente.usuario_id, solicitud.id)

    assert solicitud.estado == EstadoSolicitud.ACEPTADA
    assert _retencion(db_prueba, solicitud).estado == EstadoRetencion.ACTIVA
    assert _saldo(db_prueba, aprendiz) == 7


def test_aceptar_una_diferida_cancela_las_demas_y_usa_sus_tokens(
    db_prueba: Session, redis_falso, algebra, habilidad
) -> None:
    # Los 3 tokens retenidos por la en vivo terminan pagando la diferida.
    justo = crear_usuario(db_prueba, verificado=True)
    tokens.otorgar(db_prueba, justo.id, 3, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    ausente = _otro_tutor(db_prueba, redis_falso, algebra, precio=3, conectado=False)
    diferida = solicitudes.enviar(db_prueba, redis_falso, justo.id, ausente.id, "Duda")
    en_vivo = solicitudes.enviar(db_prueba, redis_falso, justo.id, habilidad.id, "Duda")
    assert _saldo(db_prueba, justo) == 0

    solicitudes.aceptar(db_prueba, ausente.usuario_id, diferida.id)

    assert en_vivo.estado == EstadoSolicitud.CANCELADA
    assert diferida.estado == EstadoSolicitud.ACEPTADA
    assert tokens.calcular_retenido(db_prueba, justo.id) == 3
    assert _saldo(db_prueba, justo) == 0


def test_rechazar_o_vencer_una_diferida_no_mueve_tokens(
    db_prueba: Session, redis_falso, aprendiz, algebra
) -> None:
    ausente = _otro_tutor(db_prueba, redis_falso, algebra, precio=3, conectado=False)
    rechazada = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, ausente.id, "Duda")
    solicitudes.rechazar(db_prueba, ausente.usuario_id, rechazada.id)

    vencida = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, ausente.id, "Otra")
    vencida.fecha_limite_respuesta = tokens.ahora() - timedelta(seconds=1)
    db_prueba.flush()

    assert solicitudes.vencer_atrasadas(db_prueba) == 1
    assert rechazada.estado == EstadoSolicitud.RECHAZADA
    assert vencida.estado == EstadoSolicitud.VENCIDA
    assert _saldo(db_prueba, aprendiz) == 10


def test_si_el_aprendiz_ya_no_tiene_saldo_la_diferida_no_se_acepta(
    cliente_db: TestClient, db_prueba: Session, redis_falso, aprendiz, algebra
) -> None:
    ausente = _otro_tutor(db_prueba, redis_falso, algebra, precio=3, conectado=False)
    tutor_ausente = db_prueba.get(Usuario, ausente.usuario_id)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, ausente.id, "Duda")
    # Mientras esperaba, el aprendiz gasto casi todo en otra parte.
    tokens.retener(db_prueba, aprendiz.id, 9)

    respuesta = cliente_db.post(f"/solicitudes/{solicitud.id}/aceptar", headers=cabecera(tutor_ausente))

    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == (
        "La persona que te escribio ya no tiene saldo: tiene 1 tokens y la consulta cuesta 3"
    )


def test_la_api_informa_la_modalidad(cliente_db: TestClient, db_prueba: Session, redis_falso, aprendiz, algebra) -> None:
    ausente = _otro_tutor(db_prueba, redis_falso, algebra, precio=3, conectado=False)

    respuesta = cliente_db.post(
        "/solicitudes",
        json={"habilidad_id": str(ausente.id), "mensaje": "Te dejo mi duda"},
        headers=cabecera(aprendiz),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["modalidad"] == "diferida"
    assert respuesta.json()["precio_bloque"] == 3
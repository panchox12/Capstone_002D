"""Pruebas de las sesiones: sala, primer bloque, cancelacion, cierre y pago al tutor.

LiveKit se reemplaza por una sala falsa: los avisos se mandan a mano con
el mismo formato que usa la API, y el tiempo se mueve cambiando las fechas.
"""

import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import app
from app.modelos.lote_tokens import LoteDeTokens, OrigenLote, TipoSaldo
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.sesion import Bloque, EstadoBloque, EstadoSesion, EventoConexion, Sesion
from app.servicios import habilidades, presencia, sesiones, solicitudes, temas, tokens
from app.servicios.sala import EventoInvalido, EventoSala, obtener_sala
from tests.utilidades import cabecera, crear_usuario

pytestmark = pytest.mark.usefixtures("parametros_iniciales")

FIRMA_VALIDA = "firma-de-livekit"


class SalaFalsa:
    # Imita a SalaLiveKit sin red: anota lo que se le pide.
    def __init__(self):
        self.cerradas = []

    def crear_permiso(self, nombre_sala: str, identidad: str, nombre: str) -> str:
        return f"permiso:{nombre_sala}:{identidad}"

    def leer_evento(self, cuerpo: str, autorizacion: str) -> EventoSala:
        if autorizacion != FIRMA_VALIDA:
            raise EventoInvalido()
        datos = json.loads(cuerpo)
        return EventoSala(tipo=datos["tipo"], sala=datos["sala"], identidad=datos.get("identidad"))

    def cerrar(self, nombre_sala: str) -> None:
        self.cerradas.append(nombre_sala)


@pytest.fixture()
def sala():
    falsa = SalaFalsa()
    app.dependency_overrides[obtener_sala] = lambda: falsa
    yield falsa
    app.dependency_overrides.pop(obtener_sala, None)


# ---------------------------------------------------------------------------
# Preparacion: una solicitud en vivo de 3 tokens ya aceptada
# ---------------------------------------------------------------------------


@pytest.fixture()
def tutor(db_prueba: Session, redis_falso):
    usuario = crear_usuario(db_prueba, nombre="Rodrigo Salas", verificado=True)
    presencia.marcar_en_linea(redis_falso, usuario.id)
    return usuario


@pytest.fixture()
def aprendiz(db_prueba: Session):
    usuario = crear_usuario(db_prueba, nombre="Valentina Rojas", verificado=True)
    tokens.otorgar(db_prueba, usuario.id, 10, TipoSaldo.GRATIS, OrigenLote.ENTREGA_SEMANAL, 7)
    return usuario


@pytest.fixture()
def sesion(db_prueba: Session, redis_falso, tutor, aprendiz) -> Sesion:
    raiz = temas.crear(db_prueba, "Ciencias exactas")
    grupo = temas.crear(db_prueba, "Matematicas", raiz.id)
    algebra = temas.crear(db_prueba, "Algebra", grupo.id)
    habilidad = habilidades.publicar(db_prueba, tutor.id, algebra.id, 3)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "No entiendo factorizar")
    solicitudes.aceptar(db_prueba, tutor.id, solicitud.id)
    return db_prueba.execute(select(Sesion).where(Sesion.solicitud_id == solicitud.id)).scalar_one()


def _aviso(tipo: str, sesion: Sesion, usuario=None) -> EventoSala:
    return EventoSala(tipo=tipo, sala=sesion.nombre_sala, identidad=str(usuario.id) if usuario else None)


def _conectar_ambos(db: Session, sesion: Sesion, aprendiz, tutor) -> None:
    sesiones.registrar_evento(db, _aviso("participant_joined", sesion, aprendiz))
    sesiones.registrar_evento(db, _aviso("participant_joined", sesion, tutor))


def _retencion(db: Session, sesion: Sesion) -> Retencion:
    return db.execute(select(Retencion).where(Retencion.sesion_id == sesion.id)).scalar_one()


def _bloques(db: Session, sesion: Sesion) -> list[Bloque]:
    return list(db.execute(select(Bloque).where(Bloque.sesion_id == sesion.id)).scalars())


def _lotes_por_ensenar(db: Session, usuario) -> list[LoteDeTokens]:
    return list(
        db.execute(
            select(LoteDeTokens).where(
                LoteDeTokens.usuario_id == usuario.id, LoteDeTokens.origen == OrigenLote.PAGO_POR_ENSENAR
            )
        ).scalars()
    )


# ---------------------------------------------------------------------------
# Abrir y entrar
# ---------------------------------------------------------------------------


def test_aceptar_abre_una_sesion_que_espera_cinco_minutos(db_prueba: Session, sesion) -> None:
    assert sesion.estado == EstadoSesion.ESPERANDO
    assert sesion.fecha_limite_conexion - sesion.fecha_apertura_sala == timedelta(minutes=5)
    assert sesion.bloques_cobrados == 0


def test_la_retencion_de_la_solicitud_pasa_a_la_sesion(db_prueba: Session, sesion) -> None:
    retencion = _retencion(db_prueba, sesion)

    assert retencion.estado == EstadoRetencion.ACTIVA
    assert retencion.cantidad == 3


def test_aceptar_una_diferida_tambien_abre_la_sesion(db_prueba: Session, redis_falso, aprendiz) -> None:
    desconectado = crear_usuario(db_prueba, nombre="Diego Contreras", verificado=True)
    raiz = temas.crear(db_prueba, "Oficios")
    grupo = temas.crear(db_prueba, "Electricidad", raiz.id)
    tema = temas.crear(db_prueba, "Enchufes", grupo.id)
    habilidad = habilidades.publicar(db_prueba, desconectado.id, tema.id, 2)
    solicitud = solicitudes.enviar(db_prueba, redis_falso, aprendiz.id, habilidad.id, "Un enchufe suelta chispas")

    solicitudes.aceptar(db_prueba, desconectado.id, solicitud.id)

    nueva = db_prueba.execute(select(Sesion).where(Sesion.solicitud_id == solicitud.id)).scalar_one()
    assert _retencion(db_prueba, nueva).cantidad == 2


def test_los_participantes_reciben_permiso_para_entrar(
    db_prueba: Session, cliente_db: TestClient, sala, sesion, aprendiz
) -> None:
    respuesta = cliente_db.post(f"/sesiones/{sesion.id}/entrar", headers=cabecera(aprendiz))

    assert respuesta.status_code == 200
    assert respuesta.json()["token"] == f"permiso:{sesion.nombre_sala}:{aprendiz.id}"
    assert respuesta.json()["nombre_sala"] == sesion.nombre_sala


def test_alguien_ajeno_no_puede_entrar(db_prueba: Session, cliente_db: TestClient, sala, sesion) -> None:
    intruso = crear_usuario(db_prueba, nombre="Intruso")

    respuesta = cliente_db.post(f"/sesiones/{sesion.id}/entrar", headers=cabecera(intruso))

    assert respuesta.status_code == 404


def test_no_se_entra_a_una_sesion_terminada(
    db_prueba: Session, cliente_db: TestClient, sala, sesion, aprendiz
) -> None:
    sesiones.terminar(db_prueba, sesion, "prueba")

    respuesta = cliente_db.post(f"/sesiones/{sesion.id}/entrar", headers=cabecera(aprendiz))

    assert respuesta.status_code == 409


# ---------------------------------------------------------------------------
# Avisos de LiveKit
# ---------------------------------------------------------------------------


def test_con_uno_solo_conectado_no_empieza_el_cobro(db_prueba: Session, sesion, aprendiz) -> None:
    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", sesion, aprendiz))

    assert sesion.estado == EstadoSesion.ESPERANDO
    assert _bloques(db_prueba, sesion) == []


def test_con_los_dos_conectados_empieza_el_primer_bloque(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)

    [bloque] = _bloques(db_prueba, sesion)
    assert sesion.estado == EstadoSesion.EN_CURSO
    assert sesion.bloques_cobrados == 1
    assert bloque.tokens_cobrados == 3
    assert bloque.hora_termino - bloque.hora_inicio == timedelta(minutes=15)


def test_reconectarse_no_abre_otro_bloque(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", sesion, tutor))
    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", sesion, tutor))

    assert len(_bloques(db_prueba, sesion)) == 1
    assert sesion.bloques_cobrados == 1


def test_si_uno_salio_antes_de_que_llegara_el_otro_no_empieza(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", sesion, aprendiz))
    sesiones.registrar_evento(db_prueba, _aviso("participant_left", sesion, aprendiz))
    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", sesion, tutor))

    assert sesion.estado == EstadoSesion.ESPERANDO


def test_llegar_despues_del_plazo_no_inicia_la_sesion(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    sesion.fecha_limite_conexion = tokens.ahora() - timedelta(seconds=1)

    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)

    assert sesion.estado == EstadoSesion.ESPERANDO


def test_los_avisos_de_alguien_ajeno_se_ignoran(db_prueba: Session, sesion, aprendiz) -> None:
    intruso = crear_usuario(db_prueba, nombre="Intruso")
    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", sesion, aprendiz))
    sesiones.registrar_evento(db_prueba, _aviso("participant_joined", sesion, intruso))

    assert sesion.estado == EstadoSesion.ESPERANDO
    eventos = db_prueba.scalar(select(func.count()).where(EventoConexion.sesion_id == sesion.id))
    assert eventos == 1


def test_si_livekit_cierra_la_sala_la_sesion_termina(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)

    sesiones.registrar_evento(db_prueba, _aviso("room_finished", sesion))

    assert sesion.estado == EstadoSesion.TERMINADA
    assert _bloques(db_prueba, sesion)[0].estado == EstadoBloque.COMPLETADO


def test_el_webhook_registra_la_conexion(
    db_prueba: Session, cliente_db: TestClient, sala, sesion, aprendiz, tutor
) -> None:
    for usuario in (aprendiz, tutor):
        cuerpo = json.dumps({"tipo": "participant_joined", "sala": sesion.nombre_sala, "identidad": str(usuario.id)})
        respuesta = cliente_db.post(
            "/sesiones/webhook", content=cuerpo, headers={"Authorization": FIRMA_VALIDA}
        )
        assert respuesta.status_code == 204

    assert sesion.estado == EstadoSesion.EN_CURSO


def test_el_webhook_rechaza_avisos_sin_firma_valida(cliente_db: TestClient, sala, sesion) -> None:
    cuerpo = json.dumps({"tipo": "room_finished", "sala": sesion.nombre_sala})

    respuesta = cliente_db.post("/sesiones/webhook", content=cuerpo, headers={"Authorization": "inventada"})

    assert respuesta.status_code == 401


def test_el_webhook_ignora_salas_que_no_son_de_cachai(cliente_db: TestClient, sala) -> None:
    cuerpo = json.dumps({"tipo": "room_finished", "sala": "otra-sala"})

    respuesta = cliente_db.post("/sesiones/webhook", content=cuerpo, headers={"Authorization": FIRMA_VALIDA})

    assert respuesta.status_code == 204


# ---------------------------------------------------------------------------
# Procesos programados
# ---------------------------------------------------------------------------


def test_si_no_se_conectan_a_tiempo_se_cancela_y_se_reembolsa(db_prueba: Session, sesion, aprendiz) -> None:
    sala = SalaFalsa()
    sesion.fecha_limite_conexion = tokens.ahora() - timedelta(seconds=1)

    assert sesiones.vencer_salas(db_prueba, sala) == 1

    assert sesion.estado == EstadoSesion.CANCELADA
    assert _retencion(db_prueba, sesion).estado == EstadoRetencion.REEMBOLSADA
    assert tokens.calcular_saldo(db_prueba, aprendiz.id) == 10
    assert sala.cerradas == [sesion.nombre_sala]


def test_antes_del_plazo_la_sala_sigue_abierta(db_prueba: Session, sesion) -> None:
    assert sesiones.vencer_salas(db_prueba, SalaFalsa()) == 0
    assert sesion.estado == EstadoSesion.ESPERANDO


def test_al_acabarse_el_bloque_la_sesion_termina(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    sala = SalaFalsa()
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    [bloque] = _bloques(db_prueba, sesion)
    bloque.hora_termino = tokens.ahora() - timedelta(seconds=1)

    assert sesiones.cerrar_bloques_terminados(db_prueba, sala) == 1

    assert sesion.estado == EstadoSesion.TERMINADA
    assert bloque.estado == EstadoBloque.COMPLETADO
    assert sala.cerradas == [sesion.nombre_sala]


def test_un_bloque_en_curso_no_se_cierra(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)

    assert sesiones.cerrar_bloques_terminados(db_prueba, SalaFalsa()) == 0
    assert sesion.estado == EstadoSesion.EN_CURSO


def test_si_livekit_no_responde_la_sesion_igual_se_cancela(db_prueba: Session, sesion) -> None:
    class SalaCaida(SalaFalsa):
        def cerrar(self, nombre_sala: str) -> None:
            raise ConnectionError("sin red")

    sesion.fecha_limite_conexion = tokens.ahora() - timedelta(seconds=1)

    assert sesiones.vencer_salas(db_prueba, SalaCaida()) == 1
    assert sesion.estado == EstadoSesion.CANCELADA


def test_el_pago_espera_el_plazo_de_reporte(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    sesiones.terminar(db_prueba, sesion, "prueba")

    assert sesiones.liberar_pagos(db_prueba) == 0
    assert _retencion(db_prueba, sesion).estado == EstadoRetencion.ACTIVA


def test_pasado_el_plazo_el_tutor_recibe_el_pago(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    sesiones.terminar(db_prueba, sesion, "prueba")
    sesion.fecha_cierre = tokens.ahora() - timedelta(minutes=11)

    assert sesiones.liberar_pagos(db_prueba) == 1

    [lote] = _lotes_por_ensenar(db_prueba, tutor)
    assert lote.cantidad_original == 3
    assert lote.tipo_saldo == TipoSaldo.PAGADO
    assert _retencion(db_prueba, sesion).estado == EstadoRetencion.LIBERADA
    assert sesiones.liberar_pagos(db_prueba) == 0


def test_ningun_token_se_crea_ni_se_pierde(db_prueba: Session, sesion, aprendiz, tutor) -> None:
    total_antes = tokens.calcular_saldo(db_prueba, aprendiz.id) + 3
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)
    sesiones.terminar(db_prueba, sesion, "prueba")
    sesion.fecha_cierre = tokens.ahora() - timedelta(minutes=11)
    sesiones.liberar_pagos(db_prueba)

    total_despues = tokens.calcular_saldo(db_prueba, aprendiz.id) + tokens.calcular_saldo(db_prueba, tutor.id)
    assert total_despues == total_antes


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def test_cada_uno_ve_sus_sesiones_con_el_tiempo_calculado_por_el_servidor(
    db_prueba: Session, cliente_db: TestClient, sesion, aprendiz, tutor
) -> None:
    for usuario in (aprendiz, tutor):
        [vista] = cliente_db.get("/sesiones", headers=cabecera(usuario)).json()
        assert vista["id"] == str(sesion.id)
        assert vista["estado"] == "esperando"
        assert 0 < vista["segundos_para_conectarse"] <= 300

    otro = crear_usuario(db_prueba, nombre="Otra Persona")
    assert cliente_db.get("/sesiones", headers=cabecera(otro)).json() == []


def test_en_curso_muestra_cuanto_queda_del_bloque(
    db_prueba: Session, cliente_db: TestClient, sesion, aprendiz, tutor
) -> None:
    _conectar_ambos(db_prueba, sesion, aprendiz, tutor)

    vista = cliente_db.get(f"/sesiones/{sesion.id}", headers=cabecera(aprendiz)).json()

    assert vista["estado"] == "en_curso"
    assert 0 < vista["segundos_restantes_bloque"] <= 900
"""Sesiones: abrir la sala, contar el tiempo con los avisos de LiveKit y pagar.

Reglas que este modulo garantiza:
- El bloque 1 empieza cuando los dos estan conectados, con la hora del servidor.
- Si no se conectan los dos a tiempo, la sesion se cancela y el aprendiz recupera sus tokens.
- El bloque se cobra completo aunque la sesion termine antes.
- El tutor recibe el pago unos minutos despues del cierre, para dar tiempo a reportar.
Ninguna funcion hace commit: quien la llama confirma todo junto, o nada.
"""

import logging
import uuid
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modelos.habilidad import HabilidadOfrecida
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.sesion import Bloque, EstadoBloque, EstadoSesion, EventoConexion, Sesion, TipoEventoConexion
from app.modelos.solicitud import Solicitud
from app.modelos.tema import Tema
from app.modelos.usuario import Usuario
from app.servicios import parametros, tokens
from app.servicios.sala import EventoSala, SalaLiveKit

PARAM_VENTANA_CONEXION = "ventana_conexion_sala_minutos"
PARAM_DURACION_BLOQUE = "duracion_bloque_minutos"
PARAM_RETENCION_POSTERIOR = "retencion_posterior_sesion_minutos"

registro = logging.getLogger("uvicorn.error")


class SesionNoEncontrada(Exception):
    # No existe, o el usuario no participa en ella.
    pass


class SalaCerrada(Exception):
    # La sesion ya termino o se cancelo: no se puede entrar.
    pass


# ---------------------------------------------------------------------------
# Abrir
# ---------------------------------------------------------------------------


def _retencion_de_solicitud(db: Session, solicitud_id: uuid.UUID) -> Retencion:
    return db.execute(select(Retencion).where(Retencion.solicitud_id == solicitud_id)).scalar_one()


def abrir(db: Session, solicitud: Solicitud) -> Sesion:
    # La llama solicitudes.aceptar(), cuando la retencion del primer bloque ya existe.
    momento = tokens.ahora()
    minutos = parametros.obtener_entero(db, PARAM_VENTANA_CONEXION)
    sesion_id = uuid.uuid4()
    sesion = Sesion(
        id=sesion_id,
        solicitud_id=solicitud.id,
        nombre_sala=f"cachai-{sesion_id}",
        estado=EstadoSesion.ESPERANDO,
        fecha_apertura_sala=momento,
        fecha_limite_conexion=momento + timedelta(minutes=minutos),
        bloques_cobrados=0,
    )
    db.add(sesion)
    db.flush()

    # Desde ahora los tokens retenidos pertenecen a la sesion.
    _retencion_de_solicitud(db, solicitud.id).sesion_id = sesion.id
    db.flush()
    return sesion


# ---------------------------------------------------------------------------
# Entrar a la sala
# ---------------------------------------------------------------------------


def _sesion_y_solicitud(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> tuple[Sesion, Solicitud]:
    fila = db.execute(
        select(Sesion, Solicitud)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .where(
            Sesion.id == sesion_id,
            or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id),
        )
    ).first()
    if fila is None:
        raise SesionNoEncontrada()
    return fila[0], fila[1]


def entrar(db: Session, sala: SalaLiveKit, usuario: Usuario, sesion_id: uuid.UUID) -> tuple[Sesion, str]:
    # Devuelve la sesion y el permiso de LiveKit para que el usuario entre.
    sesion, _ = _sesion_y_solicitud(db, usuario.id, sesion_id)
    if sesion.estado not in (EstadoSesion.ESPERANDO, EstadoSesion.EN_CURSO):
        raise SalaCerrada()
    permiso = sala.crear_permiso(sesion.nombre_sala, str(usuario.id), usuario.nombre_visible)
    return sesion, permiso


# ---------------------------------------------------------------------------
# Avisos de LiveKit
# ---------------------------------------------------------------------------

TIPOS_DE_CONEXION = {
    "participant_joined": TipoEventoConexion.ENTRO,
    "participant_left": TipoEventoConexion.SALIO,
}


def _ambos_presentes(db: Session, sesion: Sesion, solicitud: Solicitud) -> bool:
    # Esta presente quien ha entrado mas veces de las que ha salido.
    for usuario_id in (solicitud.aprendiz_id, solicitud.tutor_id):
        entradas = db.scalar(
            select(func.count()).where(
                EventoConexion.sesion_id == sesion.id,
                EventoConexion.usuario_id == usuario_id,
                EventoConexion.tipo_evento == TipoEventoConexion.ENTRO,
            )
        )
        salidas = db.scalar(
            select(func.count()).where(
                EventoConexion.sesion_id == sesion.id,
                EventoConexion.usuario_id == usuario_id,
                EventoConexion.tipo_evento == TipoEventoConexion.SALIO,
            )
        )
        if entradas <= salidas:
            return False
    return True


def _iniciar(db: Session, sesion: Sesion, solicitud: Solicitud) -> None:
    # El primer bloque ya esta pagado: es la retencion de la solicitud.
    momento = tokens.ahora()
    minutos = parametros.obtener_entero(db, PARAM_DURACION_BLOQUE)
    sesion.estado = EstadoSesion.EN_CURSO
    sesion.fecha_conexion_ambos = momento
    sesion.bloques_cobrados = 1
    db.add(
        Bloque(
            sesion_id=sesion.id,
            numero_orden=1,
            hora_inicio=momento,
            hora_termino=momento + timedelta(minutes=minutos),
            tokens_cobrados=solicitud.precio_bloque,
            estado=EstadoBloque.EN_CURSO,
        )
    )
    db.flush()


def registrar_evento(db: Session, evento: EventoSala) -> None:
    # Procesa un aviso de LiveKit. Los avisos de salas ajenas se ignoran.
    sesion = db.execute(
        select(Sesion).where(Sesion.nombre_sala == evento.sala).with_for_update()
    ).scalar_one_or_none()
    if sesion is None or sesion.estado not in (EstadoSesion.ESPERANDO, EstadoSesion.EN_CURSO):
        return

    if evento.tipo == "room_finished":
        if sesion.estado == EstadoSesion.EN_CURSO:
            terminar(db, sesion, "la sala se cerro")
        return

    tipo = TIPOS_DE_CONEXION.get(evento.tipo)
    if tipo is None or evento.identidad is None:
        return
    try:
        usuario_id = uuid.UUID(evento.identidad)
    except ValueError:
        return
    solicitud = db.get(Solicitud, sesion.solicitud_id)
    if usuario_id not in (solicitud.aprendiz_id, solicitud.tutor_id):
        return

    db.add(
        EventoConexion(
            sesion_id=sesion.id,
            usuario_id=usuario_id,
            tipo_evento=tipo,
            marca_temporal=tokens.ahora(),
        )
    )
    db.flush()

    # Si alguien llega despues del plazo, el planificador cancela la sesion.
    a_tiempo = tokens.ahora() < sesion.fecha_limite_conexion
    if (
        tipo == TipoEventoConexion.ENTRO
        and sesion.estado == EstadoSesion.ESPERANDO
        and a_tiempo
        and _ambos_presentes(db, sesion, solicitud)
    ):
        _iniciar(db, sesion, solicitud)
    # Quedan faltando las pausas por desconexion.


# ---------------------------------------------------------------------------
# Cierre
# ---------------------------------------------------------------------------


def terminar(db: Session, sesion: Sesion, motivo: str) -> None:
    momento = tokens.ahora()
    sesion.estado = EstadoSesion.TERMINADA
    sesion.fecha_cierre = momento
    sesion.motivo_cierre = motivo
    abiertos = db.execute(
        select(Bloque).where(Bloque.sesion_id == sesion.id, Bloque.estado == EstadoBloque.EN_CURSO)
    ).scalars()
    for bloque in abiertos:
        # El bloque se cobra completo; solo se anota la hora real de termino.
        bloque.estado = EstadoBloque.COMPLETADO
        bloque.hora_termino = min(bloque.hora_termino, momento)
    db.flush()


def _cerrar_sala(sala: SalaLiveKit, sesion: Sesion) -> None:
    # Si LiveKit no responde, la sesion igual queda cerrada en Cachai.
    try:
        sala.cerrar(sesion.nombre_sala)
    except Exception:
        registro.warning("No se pudo cerrar la sala %s en LiveKit", sesion.nombre_sala)


# ---------------------------------------------------------------------------
# Procesos programados
# ---------------------------------------------------------------------------


def vencer_salas(db: Session, sala: SalaLiveKit) -> int:
    # Cancela las sesiones donde no se conectaron los dos a tiempo y devuelve los tokens.
    vencidas = db.execute(
        select(Sesion)
        .where(Sesion.estado == EstadoSesion.ESPERANDO, Sesion.fecha_limite_conexion <= tokens.ahora())
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for sesion in vencidas:
        motivo = "no se conectaron los dos a tiempo"
        sesion.estado = EstadoSesion.CANCELADA
        sesion.fecha_cierre = tokens.ahora()
        sesion.motivo_cierre = motivo
        retencion = db.execute(select(Retencion).where(Retencion.sesion_id == sesion.id)).scalar_one()
        if retencion.estado == EstadoRetencion.ACTIVA:
            tokens.reembolsar(db, retencion.id, motivo)
        _cerrar_sala(sala, sesion)
    db.flush()
    return len(vencidas)


def cerrar_bloques_terminados(db: Session, sala: SalaLiveKit) -> int:
    # Termina las sesiones cuyo bloque pagado ya se acabo. La extension queda faltando.
    sesiones = db.execute(
        select(Sesion)
        .join(Bloque, Bloque.sesion_id == Sesion.id)
        .where(
            Sesion.estado == EstadoSesion.EN_CURSO,
            Bloque.estado == EstadoBloque.EN_CURSO,
            Bloque.hora_termino <= tokens.ahora(),
        )
        .with_for_update(of=Sesion, skip_locked=True)
    ).scalars().all()

    for sesion in sesiones:
        terminar(db, sesion, "termino el bloque pagado")
        _cerrar_sala(sala, sesion)
    return len(sesiones)


def liberar_pagos(db: Session) -> int:
    # Paga al tutor las sesiones cerradas hace mas del plazo de reporte.
    minutos = parametros.obtener_entero(db, PARAM_RETENCION_POSTERIOR)
    limite = tokens.ahora() - timedelta(minutes=minutos)
    pendientes = db.execute(
        select(Retencion.id, Solicitud.tutor_id)
        .join(Sesion, Sesion.id == Retencion.sesion_id)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .where(
            Sesion.estado == EstadoSesion.TERMINADA,
            Sesion.fecha_cierre <= limite,
            Retencion.estado == EstadoRetencion.ACTIVA,
        )
    ).all()

    for retencion_id, tutor_id in pendientes:
        tokens.liberar(db, retencion_id, tutor_id, motivo="sesion completada")
    return len(pendientes)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def _consulta():
    aprendiz = aliased(Usuario)
    tutor = aliased(Usuario)
    return (
        select(Sesion, Solicitud, Tema.nombre, aprendiz, tutor)
        .join(Solicitud, Solicitud.id == Sesion.solicitud_id)
        .join(HabilidadOfrecida, HabilidadOfrecida.id == Solicitud.habilidad_id)
        .join(Tema, Tema.id == HabilidadOfrecida.tema_id)
        .join(aprendiz, aprendiz.id == Solicitud.aprendiz_id)
        .join(tutor, tutor.id == Solicitud.tutor_id)
    )


def listar(db: Session, usuario_id: uuid.UUID, limite: int = 20) -> list[tuple]:
    sentencia = (
        _consulta()
        .where(or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id))
        .order_by(Sesion.fecha_apertura_sala.desc())
        .limit(limite)
    )
    return [tuple(fila) for fila in db.execute(sentencia).all()]


def detalle(db: Session, usuario_id: uuid.UUID, sesion_id: uuid.UUID) -> tuple:
    fila = db.execute(
        _consulta().where(
            Sesion.id == sesion_id,
            or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id),
        )
    ).first()
    if fila is None:
        raise SesionNoEncontrada()
    return tuple(fila)


def bloque_actual(db: Session, sesion_id: uuid.UUID) -> Bloque | None:
    return db.execute(
        select(Bloque).where(Bloque.sesion_id == sesion_id).order_by(Bloque.numero_orden.desc()).limit(1)
    ).scalar_one_or_none()
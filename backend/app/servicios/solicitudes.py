"""Solicitudes de sesion: enviar, aceptar, rechazar, cancelar y vencer.

La modalidad la decide el servidor: en vivo si el tutor esta conectado,
diferida si no. Rechazar, cancelar y vencer devuelven lo que estaba retenido.
Ninguna funcion hace commit: quien la llama confirma todo junto, o nada.
"""

import uuid
from datetime import timedelta

import redis
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.modelos.habilidad import EstadoHabilidad, HabilidadOfrecida
from app.modelos.retencion import Retencion
from app.modelos.solicitud import EstadoSolicitud, ModalidadSolicitud, Solicitud
from app.modelos.tema import Tema
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import parametros, presencia, tokens

PARAM_VENTANA_EN_VIVO = "ventana_respuesta_solicitud_minutos"
PARAM_VENTANA_DIFERIDA = "ventana_respuesta_diferida_horas"


# ---------------------------------------------------------------------------
# Errores propios de las solicitudes
# ---------------------------------------------------------------------------


class HabilidadNoDisponible(Exception):
    pass


class SolicitudAPropia(Exception):
    pass


class SolicitudDuplicada(Exception):
    pass


class SolicitudNoEncontrada(Exception):
    pass


class SolicitudYaResuelta(Exception):
    pass


class SolicitudVencida(Exception):
    pass


# ---------------------------------------------------------------------------
# Enviar
# ---------------------------------------------------------------------------


def enviar(
    db: Session, r: redis.Redis, aprendiz_id: uuid.UUID, habilidad_id: uuid.UUID, mensaje: str
) -> Solicitud:
    habilidad = db.get(HabilidadOfrecida, habilidad_id)
    if habilidad is None or habilidad.estado != EstadoHabilidad.PUBLICADA:
        raise HabilidadNoDisponible()

    tutor = db.get(Usuario, habilidad.usuario_id)
    if tutor.estado_cuenta != EstadoCuenta.ACTIVA:
        raise HabilidadNoDisponible()
    if tutor.id == aprendiz_id:
        raise SolicitudAPropia()

    ya_pendiente = db.execute(
        select(Solicitud.id).where(
            Solicitud.aprendiz_id == aprendiz_id,
            Solicitud.tutor_id == tutor.id,
            Solicitud.estado == EstadoSolicitud.PENDIENTE,
        )
    ).first()
    if ya_pendiente is not None:
        raise SolicitudDuplicada()

    precio = habilidad.precio_por_bloque
    momento = tokens.ahora()

    # Si Redis no responde, el tutor aparece desconectado y la solicitud queda diferida.
    if presencia.esta_en_linea(r, tutor.id):
        modalidad = ModalidadSolicitud.EN_VIVO
        limite = momento + timedelta(minutes=parametros.obtener_entero(db, PARAM_VENTANA_EN_VIVO))
    else:
        modalidad = ModalidadSolicitud.DIFERIDA
        limite = momento + timedelta(hours=parametros.obtener_entero(db, PARAM_VENTANA_DIFERIDA))

    # Aunque la diferida no retiene, igual se exige que el saldo alcance.
    disponible = tokens.calcular_saldo(db, aprendiz_id)
    if disponible < precio:
        raise tokens.SaldoInsuficiente(disponible, precio)

    solicitud = Solicitud(
        aprendiz_id=aprendiz_id,
        tutor_id=tutor.id,
        habilidad_id=habilidad.id,
        mensaje=mensaje.strip(),
        modalidad=modalidad,
        precio_bloque=precio,
        estado=EstadoSolicitud.PENDIENTE,
        fecha_envio=momento,
        fecha_limite_respuesta=limite,
    )
    db.add(solicitud)
    db.flush()

    if modalidad == ModalidadSolicitud.EN_VIVO:
        tokens.retener(db, aprendiz_id, precio, solicitud_id=solicitud.id)
    return solicitud


# ---------------------------------------------------------------------------
# Piezas comunes de las transiciones
# ---------------------------------------------------------------------------


def _obtener_bloqueada(db: Session, solicitud_id: uuid.UUID) -> Solicitud:
    # Bloquea la fila para que dos acciones no la cambien al mismo tiempo.
    solicitud = db.get(Solicitud, solicitud_id, with_for_update=True)
    if solicitud is None:
        raise SolicitudNoEncontrada()
    return solicitud


def _exigir_pendiente(solicitud: Solicitud) -> None:
    if solicitud.estado != EstadoSolicitud.PENDIENTE:
        raise SolicitudYaResuelta()


def _retencion_de(db: Session, solicitud: Solicitud) -> Retencion | None:
    # Una diferida que nadie ha aceptado no tiene retencion.
    return db.execute(
        select(Retencion).where(Retencion.solicitud_id == solicitud.id)
    ).scalar_one_or_none()


def _cerrar_con_reembolso(db: Session, solicitud: Solicitud, estado: EstadoSolicitud, motivo: str) -> None:
    solicitud.estado = estado
    solicitud.fecha_resolucion = tokens.ahora()
    retencion = _retencion_de(db, solicitud)
    if retencion is not None:
        tokens.reembolsar(db, retencion.id, motivo)
    db.flush()


# ---------------------------------------------------------------------------
# Respuestas del tutor
# ---------------------------------------------------------------------------


def aceptar(db: Session, tutor_id: uuid.UUID, solicitud_id: uuid.UUID) -> Solicitud:
    solicitud = _obtener_bloqueada(db, solicitud_id)
    if solicitud.tutor_id != tutor_id:
        raise SolicitudNoEncontrada()
    _exigir_pendiente(solicitud)
    if solicitud.fecha_limite_respuesta <= tokens.ahora():
        raise SolicitudVencida()

    solicitud.estado = EstadoSolicitud.ACEPTADA
    solicitud.fecha_resolucion = tokens.ahora()

    # Las otras pendientes del aprendiz se cancelan antes de retener, para liberar su saldo.
    otras = db.execute(
        select(Solicitud)
        .where(
            Solicitud.aprendiz_id == solicitud.aprendiz_id,
            Solicitud.estado == EstadoSolicitud.PENDIENTE,
            Solicitud.id != solicitud.id,
        )
        .with_for_update()
    ).scalars().all()
    for otra in otras:
        _cerrar_con_reembolso(db, otra, EstadoSolicitud.CANCELADA, "al aprendiz le aceptaron otra solicitud")

    # La diferida retiene recien ahora; si no alcanza, se lanza SaldoInsuficiente.
    if solicitud.modalidad == ModalidadSolicitud.DIFERIDA:
        tokens.retener(db, solicitud.aprendiz_id, solicitud.precio_bloque, solicitud_id=solicitud.id)

    db.flush()
    return solicitud


def rechazar(db: Session, tutor_id: uuid.UUID, solicitud_id: uuid.UUID) -> Solicitud:
    solicitud = _obtener_bloqueada(db, solicitud_id)
    if solicitud.tutor_id != tutor_id:
        raise SolicitudNoEncontrada()
    _exigir_pendiente(solicitud)
    if solicitud.fecha_limite_respuesta <= tokens.ahora():
        raise SolicitudVencida()

    _cerrar_con_reembolso(db, solicitud, EstadoSolicitud.RECHAZADA, "el tutor rechazo la solicitud")
    return solicitud


# ---------------------------------------------------------------------------
# Acciones del aprendiz
# ---------------------------------------------------------------------------


def cancelar(db: Session, aprendiz_id: uuid.UUID, solicitud_id: uuid.UUID) -> Solicitud:
    solicitud = _obtener_bloqueada(db, solicitud_id)
    if solicitud.aprendiz_id != aprendiz_id:
        raise SolicitudNoEncontrada()
    _exigir_pendiente(solicitud)

    _cerrar_con_reembolso(db, solicitud, EstadoSolicitud.CANCELADA, "el aprendiz cancelo la solicitud")
    return solicitud


# ---------------------------------------------------------------------------
# Vencimiento, lo llama el proceso programado
# ---------------------------------------------------------------------------


def vencer_atrasadas(db: Session) -> int:
    # SKIP LOCKED: se salta las que un tutor esta respondiendo en ese momento.
    atrasadas = db.execute(
        select(Solicitud)
        .where(
            Solicitud.estado == EstadoSolicitud.PENDIENTE,
            Solicitud.fecha_limite_respuesta <= tokens.ahora(),
        )
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for solicitud in atrasadas:
        _cerrar_con_reembolso(db, solicitud, EstadoSolicitud.VENCIDA, "el tutor no respondio a tiempo")
    return len(atrasadas)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def listar(db: Session, usuario_id: uuid.UUID, rol: str, limite: int = 50) -> list[tuple]:
    # Enviadas (rol "aprendiz") o recibidas (rol "tutor"), la mas nueva primero.
    aprendiz = aliased(Usuario)
    tutor = aliased(Usuario)
    columna = Solicitud.aprendiz_id if rol == "aprendiz" else Solicitud.tutor_id

    sentencia = (
        select(Solicitud, Tema.nombre, aprendiz, tutor)
        .join(HabilidadOfrecida, HabilidadOfrecida.id == Solicitud.habilidad_id)
        .join(Tema, Tema.id == HabilidadOfrecida.tema_id)
        .join(aprendiz, aprendiz.id == Solicitud.aprendiz_id)
        .join(tutor, tutor.id == Solicitud.tutor_id)
        .where(columna == usuario_id)
        .order_by(Solicitud.fecha_envio.desc())
        .limit(limite)
    )
    return [tuple(fila) for fila in db.execute(sentencia).all()]


def detalle(db: Session, usuario_id: uuid.UUID, solicitud_id: uuid.UUID) -> tuple:
    # Solo la ve el aprendiz o el tutor de la solicitud.
    aprendiz = aliased(Usuario)
    tutor = aliased(Usuario)
    fila = db.execute(
        select(Solicitud, Tema.nombre, aprendiz, tutor)
        .join(HabilidadOfrecida, HabilidadOfrecida.id == Solicitud.habilidad_id)
        .join(Tema, Tema.id == HabilidadOfrecida.tema_id)
        .join(aprendiz, aprendiz.id == Solicitud.aprendiz_id)
        .join(tutor, tutor.id == Solicitud.tutor_id)
        .where(
            Solicitud.id == solicitud_id,
            or_(Solicitud.aprendiz_id == usuario_id, Solicitud.tutor_id == usuario_id),
        )
    ).first()
    if fila is None:
        raise SolicitudNoEncontrada()
    return tuple(fila)
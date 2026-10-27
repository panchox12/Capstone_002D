"""Enviar solicitudes, verlas, y responderlas."""

import uuid

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.redis import obtener_redis
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo, usuario_verificado
from app.esquemas.solicitud import Participante, SolicitudCrear, SolicitudLeer
from app.modelos.solicitud import EstadoSolicitud, Solicitud
from app.modelos.usuario import Usuario
from app.servicios import solicitudes as servicio
from app.servicios import tokens

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])

NO_ENCONTRADA = HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
YA_RESUELTA = HTTPException(status.HTTP_409_CONFLICT, "Esta solicitud ya fue respondida")
VENCIDA = HTTPException(status.HTTP_409_CONFLICT, "Se acabo el tiempo para responder esta solicitud")


def _leer(fila: tuple) -> SolicitudLeer:
    solicitud, tema_nombre, aprendiz, tutor = fila
    restantes = 0
    if solicitud.estado == EstadoSolicitud.PENDIENTE:
        restantes = max(0, int((solicitud.fecha_limite_respuesta - tokens.ahora()).total_seconds()))
    return SolicitudLeer(
        id=solicitud.id,
        estado=solicitud.estado,
        modalidad=solicitud.modalidad,
        mensaje=solicitud.mensaje,
        precio_bloque=solicitud.precio_bloque,
        tema_nombre=tema_nombre,
        aprendiz=Participante(id=aprendiz.id, nombre_visible=aprendiz.nombre_visible),
        tutor=Participante(id=tutor.id, nombre_visible=tutor.nombre_visible),
        fecha_envio=solicitud.fecha_envio,
        fecha_limite_respuesta=solicitud.fecha_limite_respuesta,
        fecha_resolucion=solicitud.fecha_resolucion,
        segundos_restantes=restantes,
    )


@router.post("", response_model=SolicitudLeer, status_code=status.HTTP_201_CREATED, summary="Enviar una solicitud")
def enviar(
    datos: SolicitudCrear,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(obtener_db),
    r: redis.Redis = Depends(obtener_redis),
) -> SolicitudLeer:
    try:
        solicitud = servicio.enviar(db, r, usuario.id, datos.habilidad_id, datos.mensaje)
    except servicio.HabilidadNoDisponible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa habilidad no esta disponible") from None
    except servicio.SolicitudAPropia:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No puedes pedirte ayuda a ti mismo") from None
    except servicio.SolicitudDuplicada:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya tienes una solicitud esperando respuesta de esta persona"
        ) from None
    except tokens.SaldoInsuficiente as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No te alcanza: tienes {error.disponible} tokens y esta consulta cuesta {error.requerido}",
        ) from None
    except IntegrityError:
        # Dos envios al mismo tutor en el mismo instante: el indice unico frena al segundo.
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya tienes una solicitud esperando respuesta de esta persona"
        ) from None

    db.commit()
    return _leer(servicio.detalle(db, usuario.id, solicitud.id))


@router.get("/enviadas", response_model=list[SolicitudLeer], summary="Solicitudes que envie")
def enviadas(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> list[SolicitudLeer]:
    return [_leer(fila) for fila in servicio.listar(db, usuario.id, rol="aprendiz")]


@router.get("/recibidas", response_model=list[SolicitudLeer], summary="Solicitudes que me enviaron")
def recibidas(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> list[SolicitudLeer]:
    return [_leer(fila) for fila in servicio.listar(db, usuario.id, rol="tutor")]


def _responder(db: Session, usuario: Usuario, accion, solicitud_id: uuid.UUID) -> SolicitudLeer:
    # Ejecuta aceptar, rechazar o cancelar y traduce sus errores a respuestas HTTP.
    try:
        solicitud: Solicitud = accion(db, usuario.id, solicitud_id)
    except servicio.SolicitudNoEncontrada:
        raise NO_ENCONTRADA from None
    except servicio.SolicitudYaResuelta:
        raise YA_RESUELTA from None
    except servicio.SolicitudVencida:
        raise VENCIDA from None
    except tokens.SaldoInsuficiente as error:
        # Solo pasa al aceptar una diferida; sin commit no se guarda nada.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La persona que te escribio ya no tiene saldo: tiene {error.disponible} tokens "
            f"y la consulta cuesta {error.requerido}",
        ) from None

    db.commit()
    return _leer(servicio.detalle(db, usuario.id, solicitud.id))


@router.post("/{solicitud_id}/aceptar", response_model=SolicitudLeer, summary="Aceptar (tutor)")
def aceptar(
    solicitud_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(obtener_db),
) -> SolicitudLeer:
    return _responder(db, usuario, servicio.aceptar, solicitud_id)


@router.post("/{solicitud_id}/rechazar", response_model=SolicitudLeer, summary="Rechazar (tutor)")
def rechazar(
    solicitud_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> SolicitudLeer:
    return _responder(db, usuario, servicio.rechazar, solicitud_id)


@router.post("/{solicitud_id}/cancelar", response_model=SolicitudLeer, summary="Cancelar (aprendiz)")
def cancelar(
    solicitud_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> SolicitudLeer:
    return _responder(db, usuario, servicio.cancelar, solicitud_id)
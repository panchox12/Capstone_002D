"""Grabaciones: empezar cuando empieza la sesion, borrar a las 24 horas y dejarlas ver a soporte.

Reglas que este modulo garantiza:
- Se graba solo si GRABACION_ACTIVA=true y los dos dieron su consentimiento al registrarse.
- Si LiveKit no puede grabar, la sesion sigue igual: la grabacion queda como fallida.
- El archivo se borra pasadas las horas del parametro, salvo que la sesion tenga un reporte abierto.
- Solo soporte la ve, con un reporte abierto, y cada acceso queda anotado.
Ninguna funcion hace commit: quien la llama confirma todo junto, o nada.
"""

import logging
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.modelos.grabacion import AccesoGrabacion, EstadoGrabacion, Grabacion
from app.modelos.moderacion import EstadoReporte, Reporte
from app.modelos.sesion import Sesion
from app.modelos.solicitud import Solicitud
from app.modelos.usuario import Usuario
from app.servicios import parametros, tokens
from app.servicios.almacen import AlmacenS3
from app.servicios.sala import SalaLiveKit

PARAM_RETENCION_GRABACIONES = "retencion_grabaciones_horas"

registro = logging.getLogger("uvicorn.error")


class GrabacionNoDisponible(Exception):
    pass


class ReporteSinAcceso(Exception):
    # El reporte no existe o ya se resolvio: la grabacion no se puede abrir.
    pass


def de_sesion(db: Session, sesion_id: uuid.UUID) -> Grabacion | None:
    return db.execute(select(Grabacion).where(Grabacion.sesion_id == sesion_id)).scalar_one_or_none()


def iniciar(db: Session, sala: SalaLiveKit, sesion: Sesion) -> Grabacion | None:
    if not configuracion.grabacion_activa:
        return None
    solicitud = db.get(Solicitud, sesion.solicitud_id)
    participantes = [db.get(Usuario, solicitud.aprendiz_id), db.get(Usuario, solicitud.tutor_id)]
    if not all(usuario.consentimiento_grabacion for usuario in participantes):
        return None

    grabacion = Grabacion(sesion_id=sesion.id, clave_archivo=f"grabaciones/{sesion.id}.mp4")
    try:
        grabacion.egress_id = sala.iniciar_grabacion(sesion.nombre_sala, grabacion.clave_archivo)
        grabacion.estado = EstadoGrabacion.GRABANDO
    except Exception:
        registro.exception("No se pudo iniciar la grabacion de %s", sesion.nombre_sala)
        grabacion.estado = EstadoGrabacion.FALLIDA
    db.add(grabacion)
    db.flush()
    return grabacion


def registrar_termino(db: Session, egress_id: str, completa: bool) -> None:
    # Aviso de LiveKit: el archivo ya esta en el bucket, o la grabacion fallo.
    grabacion = db.execute(select(Grabacion).where(Grabacion.egress_id == egress_id)).scalar_one_or_none()
    if grabacion is None or grabacion.estado != EstadoGrabacion.GRABANDO:
        return
    grabacion.estado = EstadoGrabacion.DISPONIBLE if completa else EstadoGrabacion.FALLIDA
    db.flush()


def fijar_vencimiento(db: Session, sesion: Sesion) -> None:
    # Lo llama sesiones.terminar(): el plazo de 24 horas corre desde el cierre.
    grabacion = de_sesion(db, sesion.id)
    if grabacion is not None:
        horas = parametros.obtener_entero(db, PARAM_RETENCION_GRABACIONES)
        grabacion.fecha_expiracion = sesion.fecha_cierre + timedelta(hours=horas)
        db.flush()


def borrar_vencidas(db: Session, almacen: AlmacenS3) -> int:
    reportada = (
        select(Reporte.id)
        .where(Reporte.sesion_id == Grabacion.sesion_id, Reporte.estado == EstadoReporte.ABIERTO)
        .exists()
    )
    vencidas = db.execute(
        select(Grabacion)
        .where(
            Grabacion.estado != EstadoGrabacion.BORRADA,
            Grabacion.fecha_expiracion <= tokens.ahora(),
            ~reportada,
        )
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for grabacion in vencidas:
        if grabacion.estado != EstadoGrabacion.FALLIDA:
            almacen.borrar(grabacion.clave_archivo)
        grabacion.estado = EstadoGrabacion.BORRADA
        grabacion.fecha_borrado = tokens.ahora()
    db.flush()
    return len(vencidas)


def abrir_para_soporte(db: Session, almacen: AlmacenS3, soporte_id: uuid.UUID, reporte_id: uuid.UUID) -> str:
    reporte = db.get(Reporte, reporte_id)
    if reporte is None or reporte.estado != EstadoReporte.ABIERTO:
        raise ReporteSinAcceso()
    grabacion = de_sesion(db, reporte.sesion_id)
    if grabacion is None or grabacion.estado != EstadoGrabacion.DISPONIBLE:
        raise GrabacionNoDisponible()
    db.add(AccesoGrabacion(grabacion_id=grabacion.id, usuario_id=soporte_id, reporte_id=reporte.id, fecha=tokens.ahora()))
    db.flush()
    return almacen.enlace_temporal(grabacion.clave_archivo)


def accesos(db: Session, reporte_id: uuid.UUID) -> list[tuple[AccesoGrabacion, str]]:
    filas = db.execute(
        select(AccesoGrabacion, Usuario.nombre_visible)
        .join(Usuario, Usuario.id == AccesoGrabacion.usuario_id)
        .where(AccesoGrabacion.reporte_id == reporte_id)
        .order_by(AccesoGrabacion.fecha.desc())
    ).all()
    return [tuple(fila) for fila in filas]
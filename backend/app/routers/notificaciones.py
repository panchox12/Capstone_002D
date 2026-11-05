"""Campana de avisos: ver los propios y marcarlos como leidos."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.notificacion import Bandeja, NotificacionLeer
from app.modelos.usuario import Usuario
from app.servicios import notificaciones as servicio

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


@router.get("", response_model=Bandeja, summary="Mis avisos, el mas nuevo primero")
def mis_avisos(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> Bandeja:
    return Bandeja(
        no_leidas=servicio.contar_no_leidas(db, usuario.id),
        avisos=servicio.listar(db, usuario.id),
    )


@router.post("/leer-todas", status_code=status.HTTP_204_NO_CONTENT, summary="Marcar todos como leidos")
def leer_todas(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> None:
    servicio.marcar_todas(db, usuario.id)
    db.commit()


@router.post("/{notificacion_id}/leida", response_model=NotificacionLeer, summary="Marcar un aviso como leido")
def marcar_leida(
    notificacion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> NotificacionLeer:
    try:
        aviso = servicio.marcar_leida(db, usuario.id, notificacion_id)
    except servicio.NotificacionNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aviso no encontrado") from None
    db.commit()
    return aviso
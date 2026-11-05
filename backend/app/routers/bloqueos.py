"""Bloqueos: dejar de ver a alguien y que no te pueda escribir."""
 
import uuid
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
 
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.valoracion import BloqueadoLeer, BloqueoCrear
from app.modelos.usuario import Usuario
from app.servicios import bloqueos as servicio
 
router = APIRouter(prefix="/bloqueos", tags=["Bloqueos"])
 
 
@router.get("", response_model=list[BloqueadoLeer], summary="Personas que bloquee")
def mis_bloqueos(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> list[BloqueadoLeer]:
    return [
        BloqueadoLeer(usuario_id=bloqueado.id, nombre_visible=bloqueado.nombre_visible, desde=bloqueo.creado_en)
        for bloqueo, bloqueado in servicio.listar(db, usuario.id)
    ]
 
 
@router.post("", status_code=status.HTTP_204_NO_CONTENT, summary="Bloquear a alguien")
def bloquear(
    datos: BloqueoCrear,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> None:
    try:
        servicio.bloquear(db, usuario.id, datos.usuario_id)
    except servicio.BloqueoAPropio:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No puedes bloquearte a ti mismo") from None
    except servicio.UsuarioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado") from None
    db.commit()
 
 
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desbloquear")
def desbloquear(
    usuario_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> None:
    servicio.desbloquear(db, usuario.id, usuario_id)
    db.commit()
"""Valoraciones: calificar a la otra persona al terminar una sesion."""
 
import uuid
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
 
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.valoracion import EstadoValoracion, ValoracionCrear, ValoracionLeer
from app.modelos.usuario import Usuario
from app.servicios import valoraciones as servicio
 
router = APIRouter(prefix="/valoraciones", tags=["Valoraciones"])
 
 
@router.post("", response_model=ValoracionLeer, status_code=status.HTTP_201_CREATED, summary="Valorar una sesion")
def valorar(
    datos: ValoracionCrear,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> ValoracionLeer:
    try:
        valoracion = servicio.valorar(db, usuario.id, datos.sesion_id, datos.estrellas, datos.comentario)
    except servicio.SesionNoValorable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solo se valora una sesion tuya que ya termino") from None
    except servicio.ValoracionDuplicada:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya valoraste esta sesion") from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya valoraste esta sesion") from None
    db.commit()
    return valoracion
 
 
@router.get("/sesion/{sesion_id}", response_model=EstadoValoracion, summary="Mi valoracion de una sesion")
def mi_valoracion(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> EstadoValoracion:
    valoracion = servicio.de_sesion(db, usuario.id, sesion_id)
    return EstadoValoracion(valorada=valoracion is not None, valoracion=valoracion)
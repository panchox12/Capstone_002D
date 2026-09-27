"""Publicar, listar y editar las habilidades propias."""
 
import uuid
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
 
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo, usuario_verificado
from app.esquemas.habilidad import HabilidadActualizar, HabilidadCrear, HabilidadLeer
from app.modelos.habilidad import HabilidadOfrecida
from app.modelos.tema import Tema
from app.modelos.usuario import Usuario
from app.servicios import habilidades as servicio
 
router = APIRouter(prefix="/habilidades", tags=["Habilidades"])
 
 
def _leer(habilidad: HabilidadOfrecida, tema: Tema) -> HabilidadLeer:
    return HabilidadLeer(
        id=habilidad.id,
        tema_id=tema.id,
        tema_nombre=tema.nombre,
        precio_por_bloque=habilidad.precio_por_bloque,
        estado=habilidad.estado,
    )
 
 
@router.post("", response_model=HabilidadLeer, status_code=status.HTTP_201_CREATED, summary="Publicar una habilidad")
def publicar(
    datos: HabilidadCrear,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(obtener_db),
) -> HabilidadLeer:
    try:
        habilidad = servicio.publicar(db, usuario.id, datos.tema_id, datos.precio_por_bloque)
    except servicio.TemaNoOfrecible:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Solo se pueden ofrecer temas especificos del catalogo, como Algebra, no Matematicas",
        ) from None
    except servicio.PrecioInvalido as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from None
    except servicio.HabilidadDuplicada:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya ofreces este tema; edita su precio en vez de publicarlo de nuevo") from None
 
    db.commit()
    return _leer(habilidad, db.get(Tema, habilidad.tema_id))
 
 
@router.get("/mias", response_model=list[HabilidadLeer], summary="Mis habilidades")
def mis_habilidades(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
) -> list[HabilidadLeer]:
    return [_leer(habilidad, tema) for habilidad, tema in servicio.listar(db, usuario.id)]
 
 
@router.patch("/{habilidad_id}", response_model=HabilidadLeer, summary="Cambiar precio o estado")
def actualizar(
    habilidad_id: uuid.UUID,
    datos: HabilidadActualizar,
    usuario: Usuario = Depends(usuario_verificado),
    db: Session = Depends(obtener_db),
) -> HabilidadLeer:
    try:
        habilidad = servicio.actualizar(db, usuario.id, habilidad_id, datos.precio_por_bloque, datos.estado)
    except servicio.HabilidadNoEncontrada:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Habilidad no encontrada") from None
    except servicio.PrecioInvalido as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from None
 
    db.commit()
    return _leer(habilidad, db.get(Tema, habilidad.tema_id))
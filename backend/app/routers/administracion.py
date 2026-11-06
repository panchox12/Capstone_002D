"""Panel del administrador: parametros de la economia e indicadores. Solo administradores."""
 
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
 
from app.db.sesion import obtener_db
from app.dependencias import usuario_con_rol
from app.esquemas.administracion import Indicadores, ParametroCambiar, ParametroLeer
from app.modelos.usuario import RolUsuario, Usuario
from app.servicios import indicadores as servicio
 
router = APIRouter(prefix="/admin", tags=["Administracion"])
 
administrador = usuario_con_rol(RolUsuario.ADMINISTRADOR)
 
 
@router.get("/parametros", response_model=list[ParametroLeer], summary="Parametros de la economia")
def parametros(
    _admin: Usuario = Depends(administrador),
    db: Session = Depends(obtener_db),
) -> list[ParametroLeer]:
    return servicio.listar_parametros(db)
 
 
@router.put("/parametros/{nombre}", response_model=ParametroLeer, summary="Cambiar un parametro")
def cambiar_parametro(
    nombre: str,
    datos: ParametroCambiar,
    _admin: Usuario = Depends(administrador),
    db: Session = Depends(obtener_db),
) -> ParametroLeer:
    try:
        parametro = servicio.cambiar_parametro(db, nombre, datos.valor)
    except servicio.ParametroNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese parametro no existe") from None
    db.commit()
    return parametro
 
 
@router.get("/indicadores", response_model=Indicadores, summary="Indicadores de la economia")
def indicadores(
    _admin: Usuario = Depends(administrador),
    db: Session = Depends(obtener_db),
) -> Indicadores:
    return Indicadores(**servicio.calcular(db))
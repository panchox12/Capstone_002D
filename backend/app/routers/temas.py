"""Catalogo de temas, publico."""
 
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
 
from app.db.sesion import obtener_db
from app.esquemas.tema import TemaNodo
from app.servicios import temas as servicio
 
router = APIRouter(prefix="/temas", tags=["Catalogo de temas"])
 
 
@router.get("", response_model=list[TemaNodo], summary="Catalogo completo de temas")
def listar_catalogo(db: Session = Depends(obtener_db)) -> list[dict]:
    return servicio.arbol(db)
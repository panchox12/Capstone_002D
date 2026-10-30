"""Rutas del buscador de habilidades."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.esquemas.buscador import ResultadoHabilidad
from app.servicios import buscador

router = APIRouter(prefix="/buscador", tags=["Buscador"])


@router.get(
    "/habilidades",
    response_model=list[ResultadoHabilidad],
    summary="Buscar habilidades publicadas",
)
def buscar_habilidades(
    q: Annotated[str | None, Query(description="Texto para búsqueda léxica")] = None,
    db: Session = Depends(obtener_db),
) -> list[ResultadoHabilidad]:
    """Retorna las habilidades disponibles que coincidan con el término de búsqueda."""
    return buscador.buscar_habilidades(db, texto=q)
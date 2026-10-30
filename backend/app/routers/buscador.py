"""Rutas del buscador de habilidades."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.sesion import obtener_db
from app.esquemas.buscador import ResultadoHabilidad
from app.servicios import buscador, vectorizador

router = APIRouter(prefix="/buscador", tags=["Buscador"])


@router.get(
    "/habilidades",
    response_model=list[ResultadoHabilidad],
    summary="Buscar habilidades publicadas",
)
def buscar_habilidades(
    q: Annotated[str | None, Query(description="Texto para coincidencia léxica por nombre")] = None,
    semantica: Annotated[
        str | None, Query(description="Frase en lenguaje natural para búsqueda semántica")
    ] = None,
    db: Session = Depends(obtener_db),
) -> list[ResultadoHabilidad]:
    """Busca habilidades activas. Si se especifica 'semantica', calcula el vector de la consulta."""
    embedding = None
    if semantica:
        embedding = vectorizador.vectorizar_texto(semantica)

    return buscador.buscar_habilidades(db, texto=q, embedding=embedding)
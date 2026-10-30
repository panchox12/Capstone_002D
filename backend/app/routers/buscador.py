"""Buscar especialistas escribiendo la duda con palabras propias."""

import redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.redis import obtener_redis
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.esquemas.busqueda import RespuestaBusqueda, ResultadoBusqueda
from app.modelos.usuario import Usuario
from app.servicios import buscador as servicio

router = APIRouter(prefix="/buscar", tags=["Buscador"])


@router.get("", response_model=RespuestaBusqueda, summary="Buscar especialistas para una duda")
def buscar(
    q: str = Query(min_length=3, max_length=200, description="La duda, escrita como se le contaria a alguien"),
    modo: servicio.Modo = servicio.Modo.SEMANTICO,
    solo_en_linea: bool = False,
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
    r: redis.Redis = Depends(obtener_redis),
) -> RespuestaBusqueda:
    modo_usado, resultados = servicio.buscar(db, r, usuario.id, q, modo, solo_en_linea)
    return RespuestaBusqueda(modo=modo_usado, resultados=[ResultadoBusqueda(**fila) for fila in resultados])
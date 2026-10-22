"""Latido de presencia: el navegador avisa que el usuario sigue en Cachai."""

import redis
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.redis import obtener_redis
from app.dependencias import usuario_activo
from app.modelos.usuario import Usuario
from app.servicios import presencia as servicio

router = APIRouter(prefix="/presencia", tags=["Presencia"])

SIN_REDIS = HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "La presencia no esta disponible")


@router.post("/latido", status_code=status.HTTP_204_NO_CONTENT, summary="Sigo en linea")
def latido(
    usuario: Usuario = Depends(usuario_activo),
    r: redis.Redis = Depends(obtener_redis),
) -> Response:
    try:
        servicio.marcar_en_linea(r, usuario.id)
    except redis.RedisError:
        raise SIN_REDIS from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Me desconecto")
def desconectar(
    usuario: Usuario = Depends(usuario_activo),
    r: redis.Redis = Depends(obtener_redis),
) -> Response:
    try:
        servicio.marcar_desconectado(r, usuario.id)
    except redis.RedisError:
        raise SIN_REDIS from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)

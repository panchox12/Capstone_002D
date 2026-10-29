"""Latido de presencia: el navegador avisa que el usuario sigue en Cachai."""

import redis
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.redis import obtener_redis
from app.db.sesion import obtener_db
from app.dependencias import usuario_activo
from app.modelos.usuario import Usuario
from app.servicios import perfiles
from app.servicios import presencia as servicio

router = APIRouter(prefix="/presencia", tags=["Presencia"])

SIN_REDIS = HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "La presencia no esta disponible")


@router.post("/latido", status_code=status.HTTP_204_NO_CONTENT, summary="Sigo en linea")
def latido(
    usuario: Usuario = Depends(usuario_activo),
    db: Session = Depends(obtener_db),
    r: redis.Redis = Depends(obtener_redis),
) -> Response:
    # Quien eligio no aparecer conectado sigue usando Cachai, pero nadie lo ve en linea.
    mostrar = perfiles.preferencias(db, usuario.id).mostrar_en_linea
    try:
        if mostrar:
            servicio.marcar_en_linea(r, usuario.id)
        else:
            servicio.marcar_desconectado(r, usuario.id)
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

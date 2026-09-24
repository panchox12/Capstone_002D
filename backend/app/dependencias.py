"""Dependencias compartidas por los routers."""

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.seguridad import TIPO_ACCESO, decodificar_token
from app.db.sesion import obtener_db
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import usuarios as servicio_usuarios

esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")

CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar la credencial",
    headers={"WWW-Authenticate": "Bearer"},
)


def usuario_actual(
    token: str = Depends(esquema_oauth2),
    db: Session = Depends(obtener_db),
) -> Usuario:
    """Extrae el usuario desde el token. Lanza 401 si algo no cuadra."""
    try:
        carga = decodificar_token(token, tipo_esperado=TIPO_ACCESO)
        usuario_id = uuid.UUID(carga["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise CREDENCIALES_INVALIDAS from None

    usuario = servicio_usuarios.obtener_por_id(db, usuario_id)
    if usuario is None:
        raise CREDENCIALES_INVALIDAS

    return usuario


def usuario_activo(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Exige ademas que la cuenta este confirmada y no suspendida."""
    if usuario.estado_cuenta == EstadoCuenta.PENDIENTE_CONFIRMACION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes confirmar tu correo antes de operar en la plataforma",
        )

    if usuario.estado_cuenta != EstadoCuenta.ACTIVA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no se encuentra activa",
        )

    return usuario
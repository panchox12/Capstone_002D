"""Registro, confirmacion de correo e inicio de sesion."""

import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.core.seguridad import (
    TIPO_ACCESO,
    TIPO_CONFIRMACION,
    crear_token,
    decodificar_token,
)
from app.db.sesion import obtener_db
from app.dependencias import usuario_actual
from app.esquemas.usuario import TokenRespuesta, UsuarioCrear, UsuarioLeer
from app.modelos.usuario import EstadoCuenta, Usuario
from app.servicios import usuarios as servicio_usuarios

router = APIRouter(prefix="/auth", tags=["Autenticacion"])

MINUTOS_VIGENCIA_CONFIRMACION = 60 * 24  # 24 horas


@router.post(
    "/registro",
    response_model=UsuarioLeer,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una cuenta nueva",
)
def registrar(datos: UsuarioCrear, db: Session = Depends(obtener_db)) -> Usuario:
    try:
        usuario = servicio_usuarios.crear_usuario(db, datos)
    except servicio_usuarios.CorreoYaRegistrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo",
        ) from None

    token_confirmacion = crear_token(
        sujeto=str(usuario.id),
        tipo=TIPO_CONFIRMACION,
        minutos_vigencia=MINUTOS_VIGENCIA_CONFIRMACION,
    )

    enlace = f"http://localhost:8000/auth/confirmar/{token_confirmacion}"

    if configuracion.es_desarrollo:
        print("\n" + "=" * 70)
        print(f"CONFIRMACION DE CORREO PARA {usuario.correo}")
        print(enlace)
        print("=" * 70 + "\n")
    else:
        # Fase 13: reemplazar por envio real via AWS SES
        pass

    return usuario


@router.get("/confirmar/{token}", summary="Confirmar la direccion de correo")
def confirmar_correo(token: str, db: Session = Depends(obtener_db)) -> dict:
    try:
        carga = decodificar_token(token, tipo_esperado=TIPO_CONFIRMACION)
        usuario_id = uuid.UUID(carga["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de confirmacion vencio. Solicita uno nuevo",
        ) from None
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enlace de confirmacion invalido",
        ) from None

    usuario = servicio_usuarios.obtener_por_id(db, usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if usuario.estado_cuenta == EstadoCuenta.ACTIVA:
        return {"mensaje": "La cuenta ya estaba confirmada"}

    if usuario.estado_cuenta != EstadoCuenta.PENDIENTE_CONFIRMACION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta no puede ser confirmada en su estado actual",
        )

    usuario.fecha_consentimiento_grabacion = datetime.now(timezone.utc)
    servicio_usuarios.activar_cuenta(db, usuario)

    return {"mensaje": "Cuenta confirmada. Ya puedes iniciar sesion"}


@router.post("/login", response_model=TokenRespuesta, summary="Iniciar sesion")
def iniciar_sesion(
    formulario: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(obtener_db),
) -> TokenRespuesta:
    usuario = servicio_usuarios.autenticar(
        db, correo=formulario.username, contrasena=formulario.password
    )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if usuario.estado_cuenta == EstadoCuenta.SUSPENDIDA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta se encuentra suspendida",
        )

    usuario.ultima_conexion = datetime.now(timezone.utc)
    db.commit()

    token = crear_token(sujeto=str(usuario.id), tipo=TIPO_ACCESO)
    return TokenRespuesta(access_token=token)


@router.get("/yo", response_model=UsuarioLeer, summary="Datos del usuario autenticado")
def mis_datos(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    return usuario
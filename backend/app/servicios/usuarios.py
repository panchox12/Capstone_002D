"""Logica de negocio de usuarios."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguridad import hashear_contrasena, verificar_contrasena
from app.esquemas.usuario import UsuarioCrear
from app.modelos.usuario import EstadoCuenta, Usuario


class CorreoYaRegistrado(Exception):
    """El correo ya fue utilizado."""


def obtener_por_correo(db: Session, correo: str) -> Usuario | None:
    sentencia = select(Usuario).where(Usuario.correo == correo.lower().strip())
    return db.execute(sentencia).scalar_one_or_none()


def obtener_por_id(db: Session, usuario_id: uuid.UUID) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def crear_usuario(db: Session, datos: UsuarioCrear) -> Usuario:
    """Registra un usuario nuevo en estado pendiente de confirmacion."""
    correo_normalizado = datos.correo.lower().strip()

    if obtener_por_correo(db, correo_normalizado) is not None:
        raise CorreoYaRegistrado(correo_normalizado)

    usuario = Usuario(
        correo=correo_normalizado,
        contrasena_hash=hashear_contrasena(datos.contrasena),
        nombre_visible=datos.nombre_visible.strip(),
        estado_cuenta=EstadoCuenta.PENDIENTE_CONFIRMACION,
        consentimiento_grabacion=datos.consentimiento_grabacion,
        fecha_consentimiento_grabacion=None,
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def autenticar(db: Session, correo: str, contrasena: str) -> Usuario | None:
    """Devuelve el usuario si las credenciales son correctas, None si no."""
    usuario = obtener_por_correo(db, correo)

    if usuario is None:
        # Hasheamos igual, para que el tiempo de respuesta no revele
        # si el correo existe o no en la base de datos.
        hashear_contrasena(contrasena)
        return None

    if not verificar_contrasena(contrasena, usuario.contrasena_hash):
        return None

    return usuario


def activar_cuenta(db: Session, usuario: Usuario) -> Usuario:
    usuario.estado_cuenta = EstadoCuenta.ACTIVA
    db.commit()
    db.refresh(usuario)
    return usuario
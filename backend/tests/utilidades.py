"""Ayudas compartidas por las pruebas: crear usuarios y armar cabeceras.

No es un archivo de pruebas, solo lo importan las pruebas que lo necesitan.
"""
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.seguridad import crear_token
from app.modelos.usuario import EstadoCuenta, Usuario
from app.modelos.verificacion import ResultadoVerificacion, VerificacionIdentidad


def crear_usuario(
    db: Session,
    nombre: str = "Usuario Prueba",
    verificado: bool = False,
    estado: EstadoCuenta = EstadoCuenta.ACTIVA,
) -> Usuario:
    usuario = Usuario(
        correo=f"{uuid.uuid4()}@prueba.cl",
        contrasena_hash="no-aplica",
        nombre_visible=nombre,
        estado_cuenta=estado,
        consentimiento_grabacion=True,
    )
    db.add(usuario)
    db.flush()
    if verificado:
        db.add(
            VerificacionIdentidad(
                usuario_id=usuario.id,
                resultado=ResultadoVerificacion.APROBADO,
                nivel_confianza=Decimal("92.50"),
                hash_documento=uuid.uuid4().hex + uuid.uuid4().hex,
            )
        )
        db.flush()
    return usuario


def cabecera(usuario: Usuario) -> dict:
    return {"Authorization": f"Bearer {crear_token(sujeto=str(usuario.id))}"}

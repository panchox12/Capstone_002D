"""Perfil publico y generacion de codigos QR."""

import io
import re
import uuid

import qrcode
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.modelos.perfil import PerfilPublico
from app.modelos.usuario import EstadoCuenta, Usuario

PATRON_ENLACE = re.compile(r"^[a-z0-9_-]{3,30}$")


class EnlaceInvalido(Exception):
    """Solo minusculas, numeros, guiones y guiones bajos, de 3 a 30 caracteres."""


class EnlaceEnUso(Exception):
    pass


class PerfilNoEncontrado(Exception):
    pass


def obtener_o_crear(db: Session, usuario_id: uuid.UUID) -> PerfilPublico:
    perfil = db.get(PerfilPublico, usuario_id)
    if perfil is None:
        perfil = PerfilPublico(usuario_id=usuario_id)
        db.add(perfil)
        db.flush()
    return perfil


def actualizar_propio(
    db: Session,
    usuario_id: uuid.UUID,
    biografia: str | None = None,
    enlace_personalizado: str | None = None,
) -> PerfilPublico:
    perfil = obtener_o_crear(db, usuario_id)

    if enlace_personalizado is not None:
        enlace_limpio = enlace_personalizado.strip().lower()
        if not PATRON_ENLACE.match(enlace_limpio):
            raise EnlaceInvalido()
        existente = db.execute(
            select(PerfilPublico).where(
                PerfilPublico.enlace_personalizado == enlace_limpio,
                PerfilPublico.usuario_id != usuario_id,
            )
        ).scalar_one_or_none()
        if existente is not None:
            raise EnlaceEnUso()
        perfil.enlace_personalizado = enlace_limpio

    if biografia is not None:
        perfil.biografia = biografia.strip()

    db.flush()
    return perfil


def obtener_publico(db: Session, identificador: str) -> tuple[Usuario, PerfilPublico]:
    """Busca por enlace personalizado o por UUID. Solo usuarios activos."""
    perfil: PerfilPublico | None = None

    try:
        id_uuid = uuid.UUID(identificador)
        perfil = db.get(PerfilPublico, id_uuid)
    except ValueError:
        pass

    if perfil is None:
        perfil = db.execute(
            select(PerfilPublico).where(PerfilPublico.enlace_personalizado == identificador.lower())
        ).scalar_one_or_none()

    if perfil is None:
        raise PerfilNoEncontrado()

    usuario = db.get(Usuario, perfil.usuario_id)
    if usuario is None or usuario.estado_cuenta != EstadoCuenta.ACTIVA:
        raise PerfilNoEncontrado()

    return usuario, perfil


def url_perfil(identificador: str) -> str:
    return f"{configuracion.url_frontend}/u/{identificador}"


def generar_qr_png(contenido: str) -> bytes:
    """Genera una imagen PNG con correccion de error media."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(contenido)
    qr.make(fit=True)
    imagen = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()
"""Avisos para el usuario: aparecen en la campana de la aplicacion.

Algunos ademas salen por correo (por ejemplo, una solicitud diferida o una
sancion), porque la persona puede no estar conectada.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class Notificacion(Base, MezclaTiempos):
    __tablename__ = "notificacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Clave corta para que el frontend elija el icono.
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(500), nullable=False)
    # Ruta del frontend a la que lleva el aviso.
    enlace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
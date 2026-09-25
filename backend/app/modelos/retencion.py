"""Tokens retenidos mientras una solicitud espera respuesta, o una sesion
recien terminada espera el plazo de reporte.
"""

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class EstadoRetencion(str, enum.Enum):
    ACTIVA = "activa"
    LIBERADA = "liberada"
    REEMBOLSADA = "reembolsada"


class Retencion(Base, MezclaTiempos):
    __tablename__ = "retencion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Sin FK todavia: las tablas que corresponden a estas columnas aun no existen.
    solicitud_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    sesion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoRetencion] = mapped_column(
        Enum(EstadoRetencion, name="estado_retencion"), nullable=False, default=EstadoRetencion.ACTIVA
    )

    fecha_creacion: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_liberacion: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_resolucion: Mapped[str | None] = mapped_column(String(120), nullable=True)
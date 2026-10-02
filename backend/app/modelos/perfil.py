"""Perfil publico de un usuario.

Contiene biografia, enlace personalizado opcional y metricas de reputacion
calculadas a partir de las consultas terminadas.
"""

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class PerfilPublico(Base, MezclaTiempos):
    __tablename__ = "perfil_publico"
    __table_args__ = (
        CheckConstraint(
            "enlace_personalizado ~ '^[a-z0-9_-]{3,30}$'",
            name="ck_perfil_enlace_formato",
        ),
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        primary_key=True,
    )
    biografia: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enlace_personalizado: Mapped[str | None] = mapped_column(
        String(30), unique=True, nullable=True, index=True
    )
    reputacion_promedio: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.00")
    )
    total_evaluaciones: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consultas_completadas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
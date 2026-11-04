"""Reputacion y moderacion: valoraciones, bloqueos, reportes y sanciones.

Las valoraciones alimentan el promedio del perfil. Un bloqueo impide que dos
personas se encuentren en el buscador o se envien solicitudes. Un reporte
congela el pago del tutor si llega dentro del plazo de retencion, y soporte lo
resuelve; si sanciona, la sancion queda con el folio del reporte y el revisor.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Identity, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos

LARGO_MAXIMO_COMENTARIO = 500
LARGO_MAXIMO_DESCRIPCION = 1000


def _valores(enum_python):
    return [miembro.value for miembro in enum_python]


class MotivoReporte(str, enum.Enum):
    CONDUCTA = "conducta"
    INCUMPLIMIENTO = "incumplimiento"
    FRAUDE = "fraude"
    OTRO = "otro"


class EstadoReporte(str, enum.Enum):
    ABIERTO = "abierto"
    FUNDADO = "fundado"
    DESESTIMADO = "desestimado"


class TipoSancion(str, enum.Enum):
    TEMPORAL = "temporal"
    DEFINITIVA = "definitiva"


class Valoracion(Base, MezclaTiempos):
    __tablename__ = "valoracion"
    __table_args__ = (
        UniqueConstraint("sesion_id", "evaluador_id", name="uq_valoracion_una_por_sesion"),
        CheckConstraint("estrellas BETWEEN 1 AND 5", name="ck_valoracion_estrellas"),
        CheckConstraint("evaluador_id <> evaluado_id", name="ck_valoracion_no_a_si_mismo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sesion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sesion.id"), nullable=False)
    evaluador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    evaluado_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, index=True
    )
    estrellas: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str | None] = mapped_column(String(LARGO_MAXIMO_COMENTARIO), nullable=True)


class Bloqueo(Base, MezclaTiempos):
    __tablename__ = "bloqueo"
    __table_args__ = (
        UniqueConstraint("bloqueador_id", "bloqueado_id", name="uq_bloqueo_pareja"),
        CheckConstraint("bloqueador_id <> bloqueado_id", name="ck_bloqueo_no_a_si_mismo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bloqueador_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bloqueado_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True
    )


class Reporte(Base, MezclaTiempos):
    __tablename__ = "reporte"
    __table_args__ = (
        UniqueConstraint("sesion_id", "reportante_id", name="uq_reporte_uno_por_sesion"),
        CheckConstraint("reportante_id <> reportado_id", name="ck_reporte_no_a_si_mismo"),
        CheckConstraint(
            f"char_length(descripcion) BETWEEN 10 AND {LARGO_MAXIMO_DESCRIPCION}", name="ck_reporte_largo_descripcion"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Numero correlativo que soporte usa para referirse al caso.
    folio: Mapped[int] = mapped_column(Integer, Identity(start=1000), unique=True, nullable=False)
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesion.id"), nullable=False, index=True
    )
    reportante_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    reportado_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    motivo: Mapped[MotivoReporte] = mapped_column(
        Enum(MotivoReporte, name="motivo_reporte", values_callable=_valores), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(String(LARGO_MAXIMO_DESCRIPCION), nullable=False)
    estado: Mapped[EstadoReporte] = mapped_column(
        Enum(EstadoReporte, name="estado_reporte", values_callable=_valores),
        nullable=False,
        default=EstadoReporte.ABIERTO,
        index=True,
    )
    # Verdadero si llego cuando el pago del tutor todavia estaba retenido.
    congela_pago: Mapped[bool] = mapped_column(nullable=False, default=False)
    revisor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=True)
    resolucion: Mapped[str | None] = mapped_column(String(LARGO_MAXIMO_DESCRIPCION), nullable=True)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Sancion(Base, MezclaTiempos):
    __tablename__ = "sancion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, index=True
    )
    # El reporte de origen: de ahi salen el folio y la evidencia.
    reporte_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reporte.id"), nullable=False)
    revisor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    tipo: Mapped[TipoSancion] = mapped_column(
        Enum(TipoSancion, name="tipo_sancion", values_callable=_valores), nullable=False
    )
    justificacion: Mapped[str] = mapped_column(String(LARGO_MAXIMO_DESCRIPCION), nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Vacia en las definitivas.
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
"""Lotes de tokens: unidad de vencimiento.

Cada entrega de tokens (compra, entrega semanal, video, pago por enseñar)
genera un lote propio con su propia fecha de vencimiento. El saldo de un
usuario nunca se guarda como campo: se calcula sumando cantidad_restante
de sus lotes vigentes.
"""

import enum
import uuid

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class TipoSaldo(str, enum.Enum):
    GRATIS = "gratis"
    PAGADO = "pagado"


class OrigenLote(str, enum.Enum):
    ENTREGA_SEMANAL = "entrega_semanal"
    VIDEO = "video"
    COMPRA = "compra"
    PAGO_POR_ENSENAR = "pago_por_ensenar"
    COMPENSACION = "compensacion"


class EstadoLote(str, enum.Enum):
    VIGENTE = "vigente"
    AGOTADO = "agotado"
    VENCIDO = "vencido"


class LoteDeTokens(Base, MezclaTiempos):
    __tablename__ = "lote_tokens"

    __table_args__ = (
        CheckConstraint("cantidad_restante >= 0", name="ck_lote_cantidad_no_negativa"),
        CheckConstraint("cantidad_restante <= cantidad_original", name="ck_lote_restante_no_supera_original"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True
    )

    tipo_saldo: Mapped[TipoSaldo] = mapped_column(Enum(TipoSaldo, name="tipo_saldo"), nullable=False)
    origen: Mapped[OrigenLote] = mapped_column(Enum(OrigenLote, name="origen_lote"), nullable=False)

    cantidad_original: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_restante: Mapped[int] = mapped_column(Integer, nullable=False)

    fecha_recepcion: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_vencimiento: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    estado: Mapped[EstadoLote] = mapped_column(
        Enum(EstadoLote, name="estado_lote"), nullable=False, default=EstadoLote.VIGENTE
    )
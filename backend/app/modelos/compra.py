"""Compras de tokens en la tienda.

Cada compra pagada crea su propio lote de tokens pagados. La compra guarda
el monto en pesos y el medio de pago para poder cuadrar lo vendido con lo
cobrado, y apunta al lote para saber cuanto queda de lo que se compro.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class EstadoCompra(str, enum.Enum):
    PENDIENTE = "pendiente"
    PAGADA = "pagada"
    RECHAZADA = "rechazada"


class Compra(Base, MezclaTiempos):
    __tablename__ = "compra"
    __table_args__ = (
        CheckConstraint("cantidad_tokens > 0", name="ck_compra_tokens_positivos"),
        CheckConstraint("monto_pesos > 0", name="ck_compra_monto_positivo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, index=True
    )

    # Codigo del paquete comprado, ya sea el popular o el caro.
    paquete: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    monto_pesos: Mapped[int] = mapped_column(Integer, nullable=False)
    medio_pago: Mapped[str] = mapped_column(String(30), nullable=False)

    estado: Mapped[EstadoCompra] = mapped_column(
        Enum(EstadoCompra, name="estado_compra", values_callable=lambda enum: [m.value for m in enum]),
        nullable=False,
        default=EstadoCompra.PENDIENTE,
    )

    # Queda vacio hasta que el pago se confirma y se crea el lote.
    lote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lote_tokens.id"), nullable=True
    )

    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
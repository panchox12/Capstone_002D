"""Registro de solo agregado de todo movimiento de tokens.

Nunca se modifica ni se elimina una fila. Cualquier correccion se hace
con una transaccion compensatoria nueva, nunca editando una existente.
"""

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class TipoTransaccion(str, enum.Enum):
    CONSUMO = "consumo"
    ENTREGA = "entrega"
    COMPRA = "compra"
    REEMBOLSO = "reembolso"
    COMPENSACION = "compensacion"


class Transaccion(Base, MezclaTiempos):
    __tablename__ = "transaccion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Nulo cuando el origen es el sistema (entrega semanal, compensacion).
    usuario_origen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=True
    )
    usuario_destino_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, index=True
    )

    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    lote_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lote_tokens.id"), nullable=False)
    tipo: Mapped[TipoTransaccion] = mapped_column(Enum(TipoTransaccion, name="tipo_transaccion"), nullable=False)

    # Sin FK todavia: la tabla que corresponde a esta columna aun no existe.
    sesion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    fecha: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    saldo_resultante: Mapped[int] = mapped_column(Integer, nullable=False)
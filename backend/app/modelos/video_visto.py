"""Videos publicitarios vistos.

Cada video visto entrega tokens gratuitos. Esta tabla existe para contar
cuantos videos vio un usuario en las ultimas 24 horas y hacer cumplir el
tope diario, y para saber de donde salio cada lote de origen video.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class VideoVisto(Base, MezclaTiempos):
    __tablename__ = "video_visto"
    __table_args__ = (
        CheckConstraint("tokens_otorgados > 0", name="ck_video_tokens_positivos"),
        # La consulta del tope diario filtra por usuario y fecha: este indice la hace inmediata.
        Index("ix_video_visto_usuario_fecha", "usuario_id", "fecha"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tokens_otorgados: Mapped[int] = mapped_column(Integer, nullable=False)
    lote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lote_tokens.id"), nullable=False
    )
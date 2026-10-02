"""Habilidades que un usuario ofrece, con su precio por bloque.
 
El precio es por habilidad, no por usuario: la misma persona puede cobrar
3 tokens por Algebra y 1 por explicaciones de peliculas.
"""
 
import enum
import uuid
 
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
 
from app.db.base import Base, MezclaTiempos
 
 
class EstadoHabilidad(str, enum.Enum):
    PUBLICADA = "publicada"
    PAUSADA = "pausada"
 
 
class HabilidadOfrecida(Base, MezclaTiempos):
    __tablename__ = "habilidad_ofrecida"
    __table_args__ = (
        # Seccion 3.6: no se puede cobrar cero tokens.
        CheckConstraint("precio_por_bloque > 0", name="ck_habilidad_precio_positivo"),
        # Un usuario ofrece cada tema una sola vez; para cambiar el precio se edita.
        UniqueConstraint("usuario_id", "tema_id", name="uq_habilidad_usuario_tema"),
    )
 
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tema_id: Mapped[int] = mapped_column(ForeignKey("tema.id"), nullable=False, index=True)
    precio_por_bloque: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoHabilidad] = mapped_column(
        Enum(EstadoHabilidad, name="estado_habilidad", values_callable=lambda enum: [m.value for m in enum]),
        nullable=False,
        default=EstadoHabilidad.PUBLICADA,
    )
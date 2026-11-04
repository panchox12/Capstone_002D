"""Grabaciones de las sesiones y el registro de quien las vio.

LiveKit graba la sala y deja el archivo en S3. Cachai guarda donde quedo y
cuando se borra: a las 24 horas del cierre, salvo que haya un reporte abierto.
Solo soporte puede verla, y cada vez que lo hace queda anotado.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class EstadoGrabacion(str, enum.Enum):
    GRABANDO = "grabando"
    DISPONIBLE = "disponible"
    FALLIDA = "fallida"
    BORRADA = "borrada"


class Grabacion(Base, MezclaTiempos):
    __tablename__ = "grabacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesion.id"), nullable=False, unique=True
    )
    # Identificador de la grabacion en LiveKit; con el se reconoce su aviso de termino.
    egress_id: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    # Ruta del archivo dentro del bucket.
    clave_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[EstadoGrabacion] = mapped_column(
        Enum(EstadoGrabacion, name="estado_grabacion", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=EstadoGrabacion.GRABANDO,
        index=True,
    )
    # Se fija al cerrar la sesion.
    fecha_expiracion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_borrado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccesoGrabacion(Base, MezclaTiempos):
    __tablename__ = "acceso_a_grabacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grabacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grabacion.id"), nullable=False, index=True
    )
    # Funcionario de soporte que la abrio y el reporte que lo justifica.
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    reporte_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reporte.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
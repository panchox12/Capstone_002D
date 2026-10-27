"""Solicitud de sesion: un aprendiz le pide ayuda a un tutor por una habilidad.

Si el tutor esta conectado la solicitud es en vivo: se retiene el primer bloque
y hay unos minutos para responder. Si esta desconectado es diferida: no se
retiene nada al enviar, hay varias horas para responder y se retiene al aceptar.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos

LARGO_MAXIMO_MENSAJE = 280


class EstadoSolicitud(str, enum.Enum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    VENCIDA = "vencida"
    CANCELADA = "cancelada"


class ModalidadSolicitud(str, enum.Enum):
    EN_VIVO = "en_vivo"
    DIFERIDA = "diferida"


class Solicitud(Base, MezclaTiempos):
    __tablename__ = "solicitud"
    __table_args__ = (
        # Nadie se puede pedir ayuda a si mismo.
        CheckConstraint("aprendiz_id <> tutor_id", name="ck_solicitud_no_a_si_mismo"),
        # El precio del bloque tiene que ser mayor que cero.
        CheckConstraint("precio_bloque > 0", name="ck_solicitud_precio_positivo"),
        # El mensaje no puede venir vacio ni pasar el largo maximo.
        CheckConstraint(
            f"char_length(mensaje) BETWEEN 1 AND {LARGO_MAXIMO_MENSAJE}",
            name="ck_solicitud_largo_mensaje",
        ),
        # Una sola solicitud pendiente por pareja de aprendiz y tutor.
        Index(
            "uq_solicitud_pendiente_por_pareja",
            "aprendiz_id",
            "tutor_id",
            unique=True,
            postgresql_where=text("estado = 'pendiente'"),
        ),
        # Para encontrar rapido las pendientes que ya vencieron.
        Index(
            "ix_solicitud_pendiente_por_limite",
            "fecha_limite_respuesta",
            postgresql_where=text("estado = 'pendiente'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aprendiz_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, index=True
    )
    tutor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, index=True
    )
    habilidad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habilidad_ofrecida.id"), nullable=False
    )
    mensaje: Mapped[str] = mapped_column(String(LARGO_MAXIMO_MENSAJE), nullable=False)
    modalidad: Mapped[ModalidadSolicitud] = mapped_column(
        Enum(ModalidadSolicitud, name="modalidad_solicitud", values_callable=lambda enum: [m.value for m in enum]),
        nullable=False,
    )
    # Precio copiado al enviar: si el tutor lo cambia despues, esta solicitud no cambia.
    precio_bloque: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoSolicitud] = mapped_column(
        Enum(EstadoSolicitud, name="estado_solicitud", values_callable=lambda enum: [m.value for m in enum]),
        nullable=False,
        default=EstadoSolicitud.PENDIENTE,
    )
    fecha_envio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_limite_respuesta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
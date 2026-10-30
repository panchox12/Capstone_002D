"""Sesiones de videollamada, sus bloques cobrados y los eventos de conexion.

Una sesion nace cuando el tutor acepta una solicitud. El tiempo lo decide el
servidor con los avisos (webhooks) de LiveKit: el primer bloque empieza recien
cuando los dos estan conectados, nunca cuando el navegador dice que empezo.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class EstadoSesion(str, enum.Enum):
    ESPERANDO = "esperando"
    EN_CURSO = "en_curso"
    TERMINADA = "terminada"
    CANCELADA = "cancelada"


class EstadoBloque(str, enum.Enum):
    EN_CURSO = "en_curso"
    COMPLETADO = "completado"


class TipoEventoConexion(str, enum.Enum):
    ENTRO = "entro"
    SALIO = "salio"


def _valores(enum_python):
    return [miembro.value for miembro in enum_python]


class Sesion(Base, MezclaTiempos):
    __tablename__ = "sesion"
    __table_args__ = (CheckConstraint("bloques_cobrados >= 0", name="ck_sesion_bloques_no_negativos"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Una solicitud aceptada abre una sola sesion.
    solicitud_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("solicitud.id"), nullable=False, unique=True
    )
    # Nombre de la sala en LiveKit; asi se reconoce la sesion cuando llega un webhook.
    nombre_sala: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    estado: Mapped[EstadoSesion] = mapped_column(
        Enum(EstadoSesion, name="estado_sesion", values_callable=_valores),
        nullable=False,
        default=EstadoSesion.ESPERANDO,
        index=True,
    )
    fecha_apertura_sala: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_limite_conexion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_conexion_ambos: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bloques_cobrados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    motivo_cierre: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Bloque(Base, MezclaTiempos):
    __tablename__ = "bloque"
    __table_args__ = (
        UniqueConstraint("sesion_id", "numero_orden", name="uq_bloque_orden_por_sesion"),
        CheckConstraint("tokens_cobrados > 0", name="ck_bloque_tokens_positivos"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesion.id"), nullable=False, index=True
    )
    numero_orden: Mapped[int] = mapped_column(Integer, nullable=False)
    hora_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Al abrir el bloque es la hora en que termina; si se cierra antes, la hora real.
    hora_termino: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tokens_cobrados: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoBloque] = mapped_column(
        Enum(EstadoBloque, name="estado_bloque", values_callable=_valores),
        nullable=False,
        default=EstadoBloque.EN_CURSO,
    )


class EventoConexion(Base, MezclaTiempos):
    __tablename__ = "evento_de_conexion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sesion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sesion.id"), nullable=False, index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    tipo_evento: Mapped[TipoEventoConexion] = mapped_column(
        Enum(TipoEventoConexion, name="tipo_evento_conexion", values_callable=_valores), nullable=False
    )
    # Hora del servidor de Cachai al recibir el aviso.
    marca_temporal: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
"""Modelo de base de datos para la verificacion de identidad."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.modelos import Base


class EstadoVerificacion(str, enum.Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class VerificacionIdentidad(Base):
    __tablename__ = "verificaciones_identidad"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False, unique=True)
    
    tipo_documento = Column(String(50), nullable=False) # ej: "RUT", "Pasaporte"
    numero_documento = Column(String(50), nullable=False)
    url_foto_documento = Column(String(255), nullable=False)
    url_foto_rostro = Column(String(255), nullable=False)
    
    estado = Column(Enum(EstadoVerificacion), default=EstadoVerificacion.PENDIENTE, nullable=False)
    notas_revision = Column(Text, nullable=True)
    
    fecha_solicitud = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    fecha_resolucion = Column(DateTime(timezone=True), nullable=True)

    # Relación inversa: permite acceder al usuario desde la verificacion y viceversa
    usuario = relationship("Usuario", backref="verificacion_identidad")
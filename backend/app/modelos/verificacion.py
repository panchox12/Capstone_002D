"""Verificacion de identidad.
 
Esta tabla no tiene, ni debe tener nunca, una columna que guarde o apunte
a una imagen, ni el numero de documento en claro (seccion 4.3 de la
especificacion y ley 21.719). Solo persiste el resultado.
"""
 
import uuid
from decimal import Decimal
from enum import Enum as EnumPython
 
from sqlalchemy import ForeignKey, Index, Numeric, String, text
from sqlalchemy import Enum as EnumSQL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
 
from app.db.base import Base, MezclaTiempos
 
 
class ResultadoVerificacion(str, EnumPython):
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
 
 
class VerificacionIdentidad(Base, MezclaTiempos):
    __tablename__ = "verificacion_identidad"
 
    __table_args__ = (
        # Un mismo documento solo puede quedar APROBADO en una cuenta.
        # Los intentos rechazados no cuentan: el usuario puede reintentar.
        Index(
            "uq_verificacion_documento_aprobado",
            "hash_documento",
            unique=True,
            postgresql_where=text("resultado = 'aprobado'"),
        ),
    )
 
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
 
    # Sin unique: un usuario puede tener varios intentos.
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuario.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
 
    resultado: Mapped[ResultadoVerificacion] = mapped_column(
        EnumSQL(
            ResultadoVerificacion,
            name="resultado_verificacion",
            values_callable=lambda enum: [miembro.value for miembro in enum],
        ),
        nullable=False,
    )
 
    # Nivel de confianza devuelto por el comparador de rostros, de 0 a 100.
    nivel_confianza: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
 
    # Hash con sal del numero de documento. Nunca el numero en claro.
    hash_documento: Mapped[str] = mapped_column(String(64), nullable=False)
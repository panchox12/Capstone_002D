"""Modelo de usuario.

No existen cuentas separadas de tutor y aprendiz. Un mismo usuario
busca ayuda y ofrece ayuda desde la misma cuenta.
Por eso esta tabla no tiene un campo 'rol'.
"""

import uuid
from datetime import datetime
from enum import Enum as EnumPython

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy import Enum as EnumSQL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos


class EstadoCuenta(str, EnumPython):
    """Estados posibles de una cuenta.

    El valor inicial es PENDIENTE_CONFIRMACION: una cuenta nace sin poder
    operar hasta confirmar su correo.
    """

    PENDIENTE_CONFIRMACION = "pendiente_confirmacion"
    ACTIVA = "activa"
    SUSPENDIDA = "suspendida"
    ELIMINADA = "eliminada"


class Usuario(Base, MezclaTiempos):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    correo: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    nombre_visible: Mapped[str] = mapped_column(String(80), nullable=False)

    estado_cuenta: Mapped[EstadoCuenta] = mapped_column(
        EnumSQL(
            EstadoCuenta,
            name="estado_cuenta",
            values_callable=lambda enum: [miembro.value for miembro in enum],
        ),
        default=EstadoCuenta.PENDIENTE_CONFIRMACION,
        nullable=False,
        index=True,
    )

    consentimiento_grabacion: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    fecha_consentimiento_grabacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ultima_conexion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Usuario {self.correo}>"
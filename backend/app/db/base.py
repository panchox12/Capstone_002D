"""Clase base de la que heredan todos los modelos del sistema."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa. Todos los modelos de Cachai heredan de aca.

    SQLAlchemy usa esta clase para llevar un registro de todas las tablas,
    y Alembic lee ese registro para saber que migraciones generar.
    """


class MezclaTiempos:
    """Agrega a cualquier modelo las marcas de creacion y actualizacion.

    En un sistema con dinero de por medio, saber cuando se creo y cuando se
    modifico cada fila no es opcional: es parte de la trazabilidad.
    """

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
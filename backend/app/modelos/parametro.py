"""Parametros configurables del sistema.

Guarda valores (tokens gratis semanales,
dias de vencimiento, precio maximo por bloque, etc) para que se puedan
ajustar sin modificar ni una linea de Python.
"""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from app.db.base import Base, MezclaTiempos


class ParametroSistema(Base, MezclaTiempos):
    __tablename__ = "parametro_sistema"

    nombre: Mapped[str] = mapped_column(String(80), primary_key=True)
    valor: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=True)
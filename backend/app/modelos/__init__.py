"""Registro central de modelos.

Alembic genera migraciones comparando Base.metadata con la base real.
Si no se anota aca el modelo Alembic no lo vera asi que no creara
la tabla.
"""

from app.db.base import Base
from app.modelos.usuario import EstadoCuenta, Usuario
from app.modelos.parametro import ParametroSistema

__all__ = ["Base", "EstadoCuenta", "Usuario", "ParametroSistema"]
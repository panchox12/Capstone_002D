"""Registro central de modelos.

Alembic genera migraciones comparando Base.metadata con la base real.
Si no se anota aca el modelo Alembic no lo vera asi que no creara
la tabla.
"""

from app.db.base import Base
from app.modelos.usuario import EstadoCuenta, Usuario
from app.modelos.parametro import ParametroSistema
from app.modelos.lote_tokens import EstadoLote, LoteDeTokens, OrigenLote, TipoSaldo
from app.modelos.transaccion import TipoTransaccion, Transaccion
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.verificacion import ResultadoVerificacion, VerificacionIdentidad

__all__ = ["Base", "EstadoCuenta", "Usuario", "ParametroSistema", "EstadoLote", "LoteDeTokens",
           "OrigenLote", "TipoSaldo", "TipoTransaccion", "Transaccion", "EstadoRetencion", "Retencion", "ResultadoVerificacion", "VerificacionIdentidad"]
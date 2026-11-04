"""Registro central de modelos.

Alembic genera migraciones comparando Base.metadata con la base real.
Si no se anota aca el modelo Alembic no lo vera asi que no creara
la tabla.
"""

from app.db.base import Base
from app.modelos.usuario import EstadoCuenta, RolUsuario, Usuario
from app.modelos.parametro import ParametroSistema
from app.modelos.lote_tokens import EstadoLote, LoteDeTokens, OrigenLote, TipoSaldo
from app.modelos.transaccion import TipoTransaccion, Transaccion
from app.modelos.retencion import EstadoRetencion, Retencion
from app.modelos.verificacion import ResultadoVerificacion, VerificacionIdentidad
from app.modelos.tema import EstadoTema, Tema
from app.modelos.habilidad import EstadoHabilidad, HabilidadOfrecida
from app.modelos.perfil import PerfilPublico
from app.modelos.compra import Compra, EstadoCompra
from app.modelos.video_visto import VideoVisto
from app.modelos.solicitud import EstadoSolicitud, ModalidadSolicitud, Solicitud
from app.modelos.embedding import EmbeddingTema
from app.modelos.sesion import (
    Bloque, EstadoBloque, EstadoPausa, EstadoSesion, EventoConexion, PausaSesion, Sesion, TipoEventoConexion,
)
from app.modelos.moderacion import Bloqueo, EstadoReporte, MotivoReporte, Reporte, Sancion, TipoSancion, Valoracion
from app.modelos.grabacion import AccesoGrabacion, EstadoGrabacion, Grabacion
from app.modelos.notificacion import Notificacion


__all__ = ["Base", "EstadoCuenta", "RolUsuario", "Usuario", "ParametroSistema", "EstadoLote", "LoteDeTokens",
           "OrigenLote", "TipoSaldo", "TipoTransaccion", "Transaccion", "EstadoRetencion", "Retencion", "ResultadoVerificacion", "VerificacionIdentidad", "EstadoTema", "Tema",
           "EstadoHabilidad", "HabilidadOfrecida", "PerfilPublico", "Compra", "EstadoCompra", "VideoVisto",
           "EstadoSolicitud", "ModalidadSolicitud", "Solicitud", "EmbeddingTema",
           "Bloque", "EstadoBloque", "EstadoSesion", "EventoConexion", "Sesion", "TipoEventoConexion",
           "EstadoPausa", "PausaSesion", "Bloqueo", "EstadoReporte", "MotivoReporte", "Reporte", "Sancion",
           "TipoSancion", "Valoracion", "AccesoGrabacion", "EstadoGrabacion", "Grabacion", "Notificacion"]
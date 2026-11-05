"""Avisos para los usuarios: la campana de la aplicacion y, si hace falta, un correo.

Los demas servicios llaman a avisar() cuando pasa algo que el usuario debe saber.
Ninguna funcion hace commit: el aviso se guarda junto con la operacion que lo causo.
"""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import configuracion
from app.modelos.notificacion import Notificacion
from app.modelos.usuario import Usuario
from app.servicios import correo

LIMITE_LISTADO = 30


class NotificacionNoEncontrada(Exception):
    pass


def avisar(
    db: Session,
    usuario_id: uuid.UUID,
    tipo: str,
    titulo: str,
    mensaje: str,
    enlace: str | None = None,
    por_correo: bool = False,
) -> Notificacion:
    aviso = Notificacion(usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensaje=mensaje, enlace=enlace, leida=False)
    db.add(aviso)
    db.flush()
    # El correo es para quien puede no estar mirando la aplicacion.
    if por_correo:
        usuario = db.get(Usuario, usuario_id)
        texto = mensaje
        if enlace:
            texto += f"\n\n{configuracion.url_frontend}{enlace}"
        correo.enviar(usuario.correo, f"Cachai: {titulo}", texto)
    return aviso


def listar(db: Session, usuario_id: uuid.UUID) -> list[Notificacion]:
    return list(
        db.execute(
            select(Notificacion)
            .where(Notificacion.usuario_id == usuario_id)
            .order_by(Notificacion.creado_en.desc(), Notificacion.id)
            .limit(LIMITE_LISTADO)
        ).scalars()
    )


def contar_no_leidas(db: Session, usuario_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).where(Notificacion.usuario_id == usuario_id, Notificacion.leida.is_(False))
    )


def marcar_leida(db: Session, usuario_id: uuid.UUID, notificacion_id: uuid.UUID) -> Notificacion:
    aviso = db.get(Notificacion, notificacion_id)
    if aviso is None or aviso.usuario_id != usuario_id:
        raise NotificacionNoEncontrada()
    aviso.leida = True
    db.flush()
    return aviso


def marcar_todas(db: Session, usuario_id: uuid.UUID) -> int:
    resultado = db.execute(
        update(Notificacion)
        .where(Notificacion.usuario_id == usuario_id, Notificacion.leida.is_(False))
        .values(leida=True)
    )
    db.flush()
    return resultado.rowcount
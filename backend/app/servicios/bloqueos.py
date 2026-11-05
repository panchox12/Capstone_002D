"""Bloqueos entre usuarios.

Si una persona bloquea a otra, ninguna de las dos puede enviarle solicitudes
a la otra, sin importar quien bloqueo a quien.
"""

import uuid

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.modelos.moderacion import Bloqueo
from app.modelos.usuario import Usuario

class BloqueoAPropio(Exception):
    pass

class UsuarioNoEncontrado(Exception):
    pass

def existe_entre(db: Session, uno: uuid.UUID, otro: uuid.UUID) -> bool:
    # Vale en las dos direcciones.
    return (
        db.execute(
            select(Bloqueo.id).where(
                or_(
                    and_(Bloqueo.bloqueador_id == uno, Bloqueo.bloqueado_id == otro),
                    and_(Bloqueo.bloqueador_id == otro, Bloqueo.bloqueado_id == uno),
                )
            )
        ).first()
        is not None
    )

def relacionados(db: Session, usuario_id: uuid.UUID) -> set[uuid.UUID]:
    # Todos los que bloqueo esta persona y todos los que la bloquearon.
    filas = db.execute(
        select(Bloqueo.bloqueador_id, Bloqueo.bloqueado_id).where(
            or_(Bloqueo.bloqueador_id == usuario_id, Bloqueo.bloqueado_id == usuario_id)
        )
    ).all()
    return {otro for fila in filas for otro in fila if otro != usuario_id}

def bloquear(db: Session, bloqueador_id: uuid.UUID, bloqueado_id: uuid.UUID) -> None:
    if bloqueador_id == bloqueado_id:
        raise BloqueoAPropio()
    if db.get(Usuario, bloqueado_id) is None:
        raise UsuarioNoEncontrado()
    ya = db.execute(
        select(Bloqueo.id).where(Bloqueo.bloqueador_id == bloqueador_id, Bloqueo.bloqueado_id == bloqueado_id)
    ).first()
    # Bloquear dos veces no es un error: queda igual.
    if ya is None:
        db.add(Bloqueo(bloqueador_id=bloqueador_id, bloqueado_id=bloqueado_id))
        db.flush()

def desbloquear(db: Session, bloqueador_id: uuid.UUID, bloqueado_id: uuid.UUID) -> None:
    db.execute(delete(Bloqueo).where(Bloqueo.bloqueador_id == bloqueador_id, Bloqueo.bloqueado_id == bloqueado_id))
    db.flush()

def listar(db: Session, bloqueador_id: uuid.UUID) -> list[tuple[Bloqueo, Usuario]]:
    filas = db.execute(
        select(Bloqueo, Usuario)
        .join(Usuario, Usuario.id == Bloqueo.bloqueado_id)
        .where(Bloqueo.bloqueador_id == bloqueador_id)
        .order_by(Bloqueo.creado_en.desc())
    ).all()
    return [tuple(fila) for fila in filas]
"""Bloqueos entre usuarios.

Si una persona bloquea a otra, ninguna de las dos puede enviarle solicitudes
a la otra, sin importar quien bloqueo a quien.
"""

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.modelos.moderacion import Bloqueo


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
"""Servicio de búsqueda léxica y semántica de habilidades."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modelos.habilidad import EstadoHabilidad, HabilidadOfrecida
from app.modelos.tema import Tema


def buscar_habilidades(
    db: Session,
    texto: str | None = None,
    embedding: list[float] | None = None,
    limite: int = 20,
) -> list[HabilidadOfrecida]:
    """Busca habilidades activas ordenadas por relevancia semántica o coincidencia léxica."""
    consulta = (
        select(HabilidadOfrecida)
        .join(HabilidadOfrecida.tema)
        .options(joinedload(HabilidadOfrecida.tema), joinedload(HabilidadOfrecida.usuario))
        .where(HabilidadOfrecida.estado == EstadoHabilidad.PUBLICADA)
    )

    if embedding is not None:
        consulta = consulta.where(HabilidadOfrecida.embedding.isnot(None))
        consulta = consulta.order_by(HabilidadOfrecida.embedding.cosine_distance(embedding))
    elif texto:
        consulta = consulta.where(Tema.nombre.ilike(f"%{texto.strip()}%"))

    return list(db.scalars(consulta.limit(limite)).all())
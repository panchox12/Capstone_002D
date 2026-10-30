"""Representacion numerica (embedding) de cada tema del catalogo.

El buscador semantico convierte la duda del aprendiz en un vector y busca
los temas cuyo vector se le parece mas. Solo se guardan vectores de temas,
nunca de las consultas de los usuarios.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, MezclaTiempos

# Largo del vector que entrega el modelo paraphrase-multilingual-MiniLM-L12-v2.
DIMENSIONES = 384


class EmbeddingTema(Base, MezclaTiempos):
    __tablename__ = "embedding_tema"

    tema_id: Mapped[int] = mapped_column(ForeignKey("tema.id", ondelete="CASCADE"), primary_key=True)
    vector: Mapped[list[float]] = mapped_column(Vector(DIMENSIONES), nullable=False)
    # Con que modelo y a partir de que texto se calculo: si cambia uno, se recalcula.
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    texto: Mapped[str] = mapped_column(String(400), nullable=False)
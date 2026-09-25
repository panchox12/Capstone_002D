"""Catalogo jerarquico de temas, de tres niveles (seccion 5.1).
 
Ejemplo: Ciencias exactas (nivel 1) > Matematicas (nivel 2) > Algebra (nivel 3).
Solo los temas del nivel 3 se pueden ofrecer como habilidad.
"""
 
import enum
 
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
 
from app.db.base import Base, MezclaTiempos
 
NIVEL_MAXIMO = 3
 
 
class EstadoTema(str, enum.Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
 
 
class Tema(Base, MezclaTiempos):
    __tablename__ = "tema"
    __table_args__ = (
        CheckConstraint("nivel BETWEEN 1 AND 3", name="ck_tema_nivel_valido"),
        CheckConstraint(
            "(nivel = 1 AND tema_padre_id IS NULL) OR (nivel > 1 AND tema_padre_id IS NOT NULL)",
            name="ck_tema_padre_segun_nivel",
        ),
        # Bajo un mismo padre no se repiten nombres.
        UniqueConstraint("tema_padre_id", "nombre", name="uq_tema_nombre_por_padre"),
        # La restriccion anterior no cubre los temas raiz: PostgreSQL considera
        # distintos dos valores nulos. Este indice parcial si los cubre.
        Index(
            "uq_tema_raiz_nombre",
            "nombre",
            unique=True,
            postgresql_where=text("tema_padre_id IS NULL"),
        ),
    )
 
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    tema_padre_id: Mapped[int | None] = mapped_column(ForeignKey("tema.id"), nullable=True, index=True)
    nivel: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado: Mapped[EstadoTema] = mapped_column(
        Enum(EstadoTema, name="estado_tema", values_callable=lambda enum: [m.value for m in enum]),
        nullable=False,
        default=EstadoTema.ACTIVO,
    )
"""extension pgvector y embeddings de habilidades

Revision ID: a1b2c3d4e5f6
Revises: 6322e6cebac1
Create Date: 2026-10-30 16:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6322e6cebac1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Habilitar la extension vector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Agregar columna de embedding vectorial a habilidad_ofrecida (dimensión 384 para modelo standard de embeddings)
    op.add_column(
        'habilidad_ofrecida',
        sa.Column('embedding', Vector(384), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('habilidad_ofrecida', 'embedding')
    # Opcional: drop extension solo si ninguna otra tabla la usa
    # op.execute("DROP EXTENSION IF EXISTS vector;")
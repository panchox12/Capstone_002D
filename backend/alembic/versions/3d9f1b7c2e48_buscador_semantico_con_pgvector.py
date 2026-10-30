"""buscador semantico con pgvector

Revision ID: 3d9f1b7c2e48
Revises: 6322e6cebac1
Create Date: 2026-10-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '3d9f1b7c2e48'
down_revision: Union[str, Sequence[str], None] = '6322e6cebac1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # El tipo vector viene en la extension pgvector (incluida en RDS y en la imagen pgvector/pgvector).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('embedding_tema',
    sa.Column('tema_id', sa.Integer(), nullable=False),
    sa.Column('vector', Vector(dim=384), nullable=False),
    sa.Column('modelo', sa.String(length=120), nullable=False),
    sa.Column('texto', sa.String(length=400), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tema_id'], ['tema.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tema_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('embedding_tema')
    op.execute("DROP EXTENSION IF EXISTS vector")
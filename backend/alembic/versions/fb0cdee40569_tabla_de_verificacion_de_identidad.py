"""tabla de verificacion de identidad

Revision ID: fb0cdee40569
Revises: c6192ba681e6
Create Date: 2026-09-24 22:38:23.386930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fb0cdee40569'
down_revision: Union[str, Sequence[str], None] = 'c6192ba681e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('verificacion_identidad',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('usuario_id', sa.UUID(), nullable=False),
    sa.Column('resultado', sa.Enum('aprobado', 'rechazado', name='resultado_verificacion'), nullable=False),
    sa.Column('nivel_confianza', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('hash_documento', sa.String(length=64), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verificacion_identidad_usuario_id'), 'verificacion_identidad', ['usuario_id'], unique=False)
    op.create_index('uq_verificacion_documento_aprobado', 'verificacion_identidad', ['hash_documento'], unique=True, postgresql_where=sa.text("resultado = 'aprobado'"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_verificacion_documento_aprobado', table_name='verificacion_identidad', postgresql_where=sa.text("resultado = 'aprobado'"))
    op.drop_index(op.f('ix_verificacion_identidad_usuario_id'), table_name='verificacion_identidad')
    op.drop_table('verificacion_identidad')
    op.execute("DROP TYPE IF EXISTS resultado_verificacion")
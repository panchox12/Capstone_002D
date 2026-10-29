"""preferencias de presencia
 
Revision ID: 6322e6cebac1
Revises: b91824405234
Create Date: 2026-10-27 22:16:46.198075
 
"""
from typing import Sequence, Union
 
from alembic import op
import sqlalchemy as sa
 
 
# revision identifiers, used by Alembic.
revision: str = '6322e6cebac1'
down_revision: Union[str, Sequence[str], None] = 'b91824405234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
 
 
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('perfil_publico', sa.Column('mostrar_en_linea', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('perfil_publico', sa.Column('acepta_diferidas', sa.Boolean(), server_default=sa.text('true'), nullable=False))
 
 
def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('perfil_publico', 'acepta_diferidas')
    op.drop_column('perfil_publico', 'mostrar_en_linea')
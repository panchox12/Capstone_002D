"""une migracion de tokens y verificacion

Revision ID: 94fc7d1800f3
Revises: 083d3b7ad411, fb0cdee40569
Create Date: 2026-09-24 23:18:37.306293

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94fc7d1800f3'
down_revision: Union[str, Sequence[str], None] = ('083d3b7ad411', 'fb0cdee40569')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

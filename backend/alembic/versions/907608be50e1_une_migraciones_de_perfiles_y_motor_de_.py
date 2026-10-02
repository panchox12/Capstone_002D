"""une migraciones de perfiles y motor de tokens

Revision ID: 907608be50e1
Revises: 001163164f2d, 7072acf2e577
Create Date: 2026-10-02 03:37:15.385596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '907608be50e1'
down_revision: Union[str, Sequence[str], None] = ('001163164f2d', '7072acf2e577')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

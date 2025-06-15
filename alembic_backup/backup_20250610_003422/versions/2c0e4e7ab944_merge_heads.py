"""merge_heads

Revision ID: 2c0e4e7ab944
Revises: 31e099c1cae6, security_models_migration
Create Date: 2025-06-09 23:49:33.216540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2c0e4e7ab944'
down_revision: Union[str, None] = ('31e099c1cae6', 'security_models_migration')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass

"""add_book_model

Revision ID: 31e099c1cae6
Revises: security_models_migration
Create Date: 2025-06-09 00:05:10.551098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '31e099c1cae6'
down_revision: Union[str, None] = 'bbeffc275826'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create books table
    op.create_table(
        'books',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=False),
        sa.Column('isbn', sa.String(length=255), nullable=False),
        sa.Column('pages', sa.Integer(), nullable=False),
        sa.Column('published_date', sa.Date(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_books_id'), 'books', ['id'], unique=False)

def downgrade() -> None:
    # Drop books table
    op.drop_index(op.f('ix_books_id'), table_name='books')
    op.drop_table('books')

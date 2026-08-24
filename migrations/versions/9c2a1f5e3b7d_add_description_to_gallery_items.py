"""Add description and highlights to gallery_items

Revision ID: 9c2a1f5e3b7d
Revises: 0147fcecb877
Create Date: 2026-08-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c2a1f5e3b7d'
down_revision = '0147fcecb877'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('gallery_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('highlights', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('gallery_items', schema=None) as batch_op:
        batch_op.drop_column('highlights')
        batch_op.drop_column('description')

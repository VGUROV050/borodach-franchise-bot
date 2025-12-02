"""Add is_owner and position fields to partners

Revision ID: 20241202_position
Revises: 20241201_add_client_stats
Create Date: 2024-12-02
"""
from alembic import op
import sqlalchemy as sa

revision = '20241202_position'
down_revision = '20241201_add_client_stats'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('partners', sa.Column('is_owner', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('partners', sa.Column('position', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('partners', 'position')
    op.drop_column('partners', 'is_owner')


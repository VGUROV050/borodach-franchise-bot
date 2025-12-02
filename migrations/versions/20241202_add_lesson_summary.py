"""Add summary field to knowledge_lessons

Revision ID: 20241202_summary
Revises: 20241202_position
Create Date: 2024-12-02

"""
from alembic import op
import sqlalchemy as sa


revision = '20241202_summary'
down_revision = '20241202_position'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('knowledge_lessons', sa.Column('summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('knowledge_lessons', 'summary')


"""Add client statistics fields to network_rating tables

Revision ID: add_client_stats
Revises: 
Create Date: 2024-12-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_client_stats'
down_revision = '20241130_kb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NetworkRating - добавляем клиентскую статистику
    op.add_column('network_rating', sa.Column('new_clients_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('network_rating', sa.Column('return_clients_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('network_rating', sa.Column('total_clients_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('network_rating', sa.Column('client_base_return_pct', sa.Float(), server_default='0', nullable=False))
    
    # NetworkRatingHistory - добавляем те же поля
    op.add_column('network_rating_history', sa.Column('new_clients_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('network_rating_history', sa.Column('return_clients_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('network_rating_history', sa.Column('total_clients_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('network_rating_history', sa.Column('client_base_return_pct', sa.Float(), server_default='0', nullable=False))


def downgrade() -> None:
    # NetworkRatingHistory
    op.drop_column('network_rating_history', 'client_base_return_pct')
    op.drop_column('network_rating_history', 'total_clients_count')
    op.drop_column('network_rating_history', 'return_clients_count')
    op.drop_column('network_rating_history', 'new_clients_count')
    
    # NetworkRating
    op.drop_column('network_rating', 'client_base_return_pct')
    op.drop_column('network_rating', 'total_clients_count')
    op.drop_column('network_rating', 'return_clients_count')
    op.drop_column('network_rating', 'new_clients_count')


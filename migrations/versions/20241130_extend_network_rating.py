"""Extend NetworkRating with detailed metrics

Revision ID: extend_rating_001
Revises: 
Create Date: 2024-11-30
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'extend_rating_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === NetworkRating table ===
    
    # Add city column
    op.add_column('network_rating', 
        sa.Column('city', sa.String(100), nullable=True)
    )
    op.create_index('ix_network_rating_city', 'network_rating', ['city'])
    
    # Add is_million_city column
    op.add_column('network_rating',
        sa.Column('is_million_city', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add services_revenue column
    op.add_column('network_rating',
        sa.Column('services_revenue', sa.Float(), nullable=False, server_default='0')
    )
    
    # Add products_revenue column
    op.add_column('network_rating',
        sa.Column('products_revenue', sa.Float(), nullable=False, server_default='0')
    )
    
    # Add completed_count column
    op.add_column('network_rating',
        sa.Column('completed_count', sa.Integer(), nullable=False, server_default='0')
    )
    
    # Add repeat_visitors_pct column
    op.add_column('network_rating',
        sa.Column('repeat_visitors_pct', sa.Float(), nullable=False, server_default='0')
    )
    
    # === NetworkRatingHistory table ===
    
    # Add city column
    op.add_column('network_rating_history',
        sa.Column('city', sa.String(100), nullable=True)
    )
    
    # Add services_revenue column
    op.add_column('network_rating_history',
        sa.Column('services_revenue', sa.Float(), nullable=False, server_default='0')
    )
    
    # Add products_revenue column
    op.add_column('network_rating_history',
        sa.Column('products_revenue', sa.Float(), nullable=False, server_default='0')
    )
    
    # Add completed_count column
    op.add_column('network_rating_history',
        sa.Column('completed_count', sa.Integer(), nullable=False, server_default='0')
    )
    
    # Add repeat_visitors_pct column
    op.add_column('network_rating_history',
        sa.Column('repeat_visitors_pct', sa.Float(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    # === NetworkRating table ===
    op.drop_index('ix_network_rating_city', 'network_rating')
    op.drop_column('network_rating', 'city')
    op.drop_column('network_rating', 'is_million_city')
    op.drop_column('network_rating', 'services_revenue')
    op.drop_column('network_rating', 'products_revenue')
    op.drop_column('network_rating', 'completed_count')
    op.drop_column('network_rating', 'repeat_visitors_pct')
    
    # === NetworkRatingHistory table ===
    op.drop_column('network_rating_history', 'city')
    op.drop_column('network_rating_history', 'services_revenue')
    op.drop_column('network_rating_history', 'products_revenue')
    op.drop_column('network_rating_history', 'completed_count')
    op.drop_column('network_rating_history', 'repeat_visitors_pct')


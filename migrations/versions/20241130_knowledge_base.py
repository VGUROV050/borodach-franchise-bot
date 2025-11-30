"""add knowledge base tables

Revision ID: 20241130_kb
Revises: 
Create Date: 2024-11-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20241130_kb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Knowledge Modules
    op.create_table(
        'knowledge_modules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Knowledge Lessons
    op.create_table(
        'knowledge_lessons',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('module_id', sa.Integer(), sa.ForeignKey('knowledge_modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('video_filename', sa.String(255), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), default=0),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('is_transcribed', sa.Boolean(), default=False),
        sa.Column('is_embedded', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('transcribed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_knowledge_lessons_module_id', 'knowledge_lessons', ['module_id'])
    
    # Knowledge Chunks (for RAG)
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lesson_id', sa.Integer(), sa.ForeignKey('knowledge_lessons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Float(), default=0.0),
        sa.Column('end_time', sa.Float(), default=0.0),
        sa.Column('chunk_index', sa.Integer(), default=0),
        sa.Column('embedding_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_knowledge_chunks_lesson_id', 'knowledge_chunks', ['lesson_id'])


def downgrade() -> None:
    op.drop_table('knowledge_chunks')
    op.drop_table('knowledge_lessons')
    op.drop_table('knowledge_modules')


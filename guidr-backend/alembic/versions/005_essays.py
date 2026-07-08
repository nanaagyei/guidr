"""Add essays, essay_versions, and essay_reviews tables

Revision ID: 005_essays
Revises: 004_documents
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_essays'
down_revision = '004_documents'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create essays table
    op.create_table(
        'essays',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('essay_type', sa.String(), nullable=True),
        sa.Column('target_program_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programs.id'), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_essays_user_id', 'essays', ['user_id'])

    # Create essay_versions table
    op.create_table(
        'essay_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('essay_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('essays.id'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_essay_versions_essay_id', 'essay_versions', ['essay_id'])

    # Create essay_reviews table
    op.create_table(
        'essay_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('essay_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('essays.id'), nullable=False),
        sa.Column('essay_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('essay_versions.id'), nullable=False),
        sa.Column('overall_score', sa.Numeric(3, 1), nullable=True),
        sa.Column('clarity_score', sa.Numeric(3, 1), nullable=True),
        sa.Column('structure_score', sa.Numeric(3, 1), nullable=True),
        sa.Column('content_score', sa.Numeric(3, 1), nullable=True),
        sa.Column('grammar_score', sa.Numeric(3, 1), nullable=True),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('weaknesses', sa.Text(), nullable=True),
        sa.Column('suggestions', sa.Text(), nullable=True),
        sa.Column('detailed_feedback', sa.Text(), nullable=True),
        sa.Column('review_metadata', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_essay_reviews_essay_id', 'essay_reviews', ['essay_id'])


def downgrade() -> None:
    op.drop_index('ix_essay_reviews_essay_id', table_name='essay_reviews')
    op.drop_table('essay_reviews')
    op.drop_index('ix_essay_versions_essay_id', table_name='essay_versions')
    op.drop_table('essay_versions')
    op.drop_index('ix_essays_user_id', table_name='essays')
    op.drop_table('essays')

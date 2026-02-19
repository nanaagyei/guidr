"""Add recommendation_sessions and recommendation_results tables

Revision ID: 008_recommendations
Revises: 007_password_history
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_recommendations'
down_revision = '007_password_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create recommendation_sessions table
    op.create_table(
        'recommendation_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trigger_source', sa.String(), nullable=True),
        sa.Column('input_profile_snapshot', postgresql.JSON, nullable=True),
        sa.Column('algorithm_version', sa.String(), nullable=False, server_default='mvp_v1'),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='recommendationstatus'), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    
    # Create recommendation_results table
    op.create_table(
        'recommendation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('recommendation_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('score', sa.Numeric(5, 2), nullable=False),
        sa.Column('tier', sa.Enum('dream', 'reach', 'target', 'safety', name='recommendationtier'), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('reason_features', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Add foreign keys
    op.create_foreign_key(
        'fk_recommendation_sessions_user_id',
        'recommendation_sessions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_recommendation_results_session_id',
        'recommendation_results',
        'recommendation_sessions',
        ['recommendation_session_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_recommendation_results_program_id',
        'recommendation_results',
        'programs',
        ['program_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create indexes
    op.create_index('idx_recommendation_sessions_user_id', 'recommendation_sessions', ['user_id'])
    op.create_index('idx_recommendation_sessions_status', 'recommendation_sessions', ['status'])
    op.create_index('idx_recommendation_results_session_id', 'recommendation_results', ['recommendation_session_id'])
    op.create_index('idx_recommendation_results_program_id', 'recommendation_results', ['program_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_recommendation_results_program_id', table_name='recommendation_results')
    op.drop_index('idx_recommendation_results_session_id', table_name='recommendation_results')
    op.drop_index('idx_recommendation_sessions_status', table_name='recommendation_sessions')
    op.drop_index('idx_recommendation_sessions_user_id', table_name='recommendation_sessions')
    
    # Drop tables
    op.drop_table('recommendation_results')
    op.drop_table('recommendation_sessions')
    
    # Drop enums
    sa.Enum(name='recommendationtier').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='recommendationstatus').drop(op.get_bind(), checkfirst=True)


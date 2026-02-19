"""Add user_profiles and academic_records tables

Revision ID: 002_profile_academic
Revises: 001_initial_users
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_profile_academic'
down_revision = '001_initial_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('country_of_citizenship', sa.String(), nullable=True),
        sa.Column('current_country', sa.String(), nullable=True),
        sa.Column('current_city', sa.String(), nullable=True),
        sa.Column('intended_degree', sa.String(), nullable=True),
        sa.Column('primary_field_of_study', sa.String(), nullable=True),
        sa.Column('secondary_fields', postgresql.JSON, nullable=True),
        sa.Column('preferred_start_term', sa.String(), nullable=True),
        sa.Column('preferred_start_year', sa.Integer(), nullable=True),
        sa.Column('preferred_countries', postgresql.JSON, nullable=True),
        sa.Column('preferred_cities', postgresql.JSON, nullable=True),
        sa.Column('funding_priority', sa.String(), nullable=True),
        sa.Column('program_style_preference', sa.String(), nullable=True),
        sa.Column('profile_completion_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('profile_embedding', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'])
    
    # Create academic_records table
    op.create_table(
        'academic_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('institution_name', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('degree_level', sa.String(), nullable=False),
        sa.Column('field_of_study', sa.String(), nullable=True),
        sa.Column('gpa_value', sa.Numeric(3, 2), nullable=True),
        sa.Column('gpa_scale', sa.Numeric(4, 2), nullable=True),
        sa.Column('normalized_gpa', sa.Numeric(3, 2), nullable=True),
        sa.Column('start_year', sa.Integer(), nullable=True),
        sa.Column('end_year', sa.Integer(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('source', sa.String(), nullable=False, server_default='manual'),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_academic_records_user_id', 'academic_records', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_academic_records_user_id', table_name='academic_records')
    op.drop_table('academic_records')
    op.drop_index('ix_user_profiles_user_id', table_name='user_profiles')
    op.drop_table('user_profiles')


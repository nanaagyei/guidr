"""Add institutions and programs tables

Revision ID: 003_institutions_programs
Revises: 002_profile_academic
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_institutions_programs'
down_revision = '002_profile_academic'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create institutions table
    op.create_table(
        'institutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('short_name', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('state_or_province', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('website_url', sa.String(), nullable=True),
        sa.Column('institution_type', sa.String(), nullable=True),
        sa.Column('public_private', sa.String(), nullable=True),
        sa.Column('overall_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_institutions_name', 'institutions', ['name'])
    op.create_index('ix_institutions_country', 'institutions', ['country'])
    op.create_index('ix_institutions_city', 'institutions', ['city'])

    # Create programs table
    op.create_table(
        'programs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('degree_level', sa.String(), nullable=False),
        sa.Column('delivery_mode', sa.String(), nullable=True),
        sa.Column('field_of_study', sa.String(), nullable=True),
        sa.Column('research_or_coursework', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('application_deadline_primary', sa.Date(), nullable=True),
        sa.Column('application_deadline_secondary', sa.Date(), nullable=True),
        sa.Column('tuition_estimate_per_year', sa.Numeric(10, 2), nullable=True),
        sa.Column('application_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('website_url', sa.String(), nullable=True),
        sa.Column('program_features', postgresql.JSON, nullable=True),
        sa.Column('data_completeness_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_programs_institution_id', 'programs', ['institution_id'])
    op.create_index('ix_programs_degree_level', 'programs', ['degree_level'])
    op.create_index('ix_programs_field_of_study', 'programs', ['field_of_study'])

    # Create program_tags table
    op.create_table(
        'program_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('programs.id'), nullable=False),
        sa.Column('tag_type', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_program_tags_program_id', 'program_tags', ['program_id'])


def downgrade() -> None:
    op.drop_index('ix_program_tags_program_id', table_name='program_tags')
    op.drop_table('program_tags')
    op.drop_index('ix_programs_field_of_study', table_name='programs')
    op.drop_index('ix_programs_degree_level', table_name='programs')
    op.drop_index('ix_programs_institution_id', table_name='programs')
    op.drop_table('programs')
    op.drop_index('ix_institutions_city', table_name='institutions')
    op.drop_index('ix_institutions_country', table_name='institutions')
    op.drop_index('ix_institutions_name', table_name='institutions')
    op.drop_table('institutions')

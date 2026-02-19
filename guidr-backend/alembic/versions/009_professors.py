"""Add professors, professor_research_tags, and outreach_emails tables

Revision ID: 009_professors
Revises: 008_recommendations
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_professors'
down_revision = '008_recommendations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create professors table
    op.create_table(
        'professors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('personal_page_url', sa.String(), nullable=True),
        sa.Column('scholar_profile_url', sa.String(), nullable=True),
        sa.Column('research_summary', sa.String(), nullable=True),
        sa.Column('interests_tags', postgresql.JSON, nullable=True),
        sa.Column('professor_embedding', postgresql.JSON, nullable=True),
        sa.Column('is_accepting_students', sa.Boolean(), nullable=True),
        sa.Column('last_scraped_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Create professor_research_tags table
    op.create_table(
        'professor_research_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('professor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Create outreach_emails table
    op.create_table(
        'outreach_emails',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('professor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('program_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('generation_context', sa.Text(), nullable=True),
        sa.Column('is_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Add foreign keys
    op.create_foreign_key(
        'fk_professors_institution_id',
        'professors',
        'institutions',
        ['institution_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_professor_research_tags_professor_id',
        'professor_research_tags',
        'professors',
        ['professor_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_outreach_emails_user_id',
        'outreach_emails',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_outreach_emails_professor_id',
        'outreach_emails',
        'professors',
        ['professor_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_outreach_emails_program_id',
        'outreach_emails',
        'programs',
        ['program_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes
    op.create_index('idx_professors_institution_id', 'professors', ['institution_id'])
    op.create_index('idx_professors_full_name', 'professors', ['full_name'])
    op.create_index('idx_professor_research_tags_professor_id', 'professor_research_tags', ['professor_id'])
    op.create_index('idx_professor_research_tags_tag', 'professor_research_tags', ['tag'])
    op.create_index('idx_outreach_emails_user_id', 'outreach_emails', ['user_id'])
    op.create_index('idx_outreach_emails_professor_id', 'outreach_emails', ['professor_id'])
    op.create_index('idx_outreach_emails_program_id', 'outreach_emails', ['program_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_outreach_emails_program_id', table_name='outreach_emails')
    op.drop_index('idx_outreach_emails_professor_id', table_name='outreach_emails')
    op.drop_index('idx_outreach_emails_user_id', table_name='outreach_emails')
    op.drop_index('idx_professor_research_tags_tag', table_name='professor_research_tags')
    op.drop_index('idx_professor_research_tags_professor_id', table_name='professor_research_tags')
    op.drop_index('idx_professors_full_name', table_name='professors')
    op.drop_index('idx_professors_institution_id', table_name='professors')
    
    # Drop tables
    op.drop_table('outreach_emails')
    op.drop_table('professor_research_tags')
    op.drop_table('professors')


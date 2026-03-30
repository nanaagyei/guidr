"""Add pipeline models: scrape_jobs, funding_opportunities, and new columns.

Revision ID: 012_pipeline_models
Revises: 011_institution_rankings
Create Date: 2026-02-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '012_pipeline_models'
down_revision = '011_institution_rankings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create scrape_jobs table
    # ------------------------------------------------------------------
    op.create_table(
        'scrape_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', UUID(as_uuid=True), nullable=True),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('pages_scraped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_extracted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('raw_data_path', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_scrape_jobs_institution_id', 'scrape_jobs', ['institution_id'])
    op.create_index('ix_scrape_jobs_job_type', 'scrape_jobs', ['job_type'])
    op.create_index('ix_scrape_jobs_status', 'scrape_jobs', ['status'])

    # ------------------------------------------------------------------
    # Create funding_opportunities table
    # ------------------------------------------------------------------
    op.create_table(
        'funding_opportunities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('institution_id', UUID(as_uuid=True), sa.ForeignKey('institutions.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('funding_type', sa.String(), nullable=False),
        sa.Column('amount_min', sa.Numeric(12, 2), nullable=True),
        sa.Column('amount_max', sa.Numeric(12, 2), nullable=True),
        sa.Column('amount_period', sa.String(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('eligibility_criteria', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website_url', sa.String(), nullable=True),
        sa.Column('is_need_based', sa.Boolean(), nullable=True),
        sa.Column('is_merit_based', sa.Boolean(), nullable=True),
        sa.Column('covers_tuition', sa.Boolean(), nullable=True),
        sa.Column('covers_stipend', sa.Boolean(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=False, server_default='web_scrape'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_funding_opportunities_institution_id', 'funding_opportunities', ['institution_id'])
    op.create_index('ix_funding_opportunities_funding_type', 'funding_opportunities', ['funding_type'])

    # ------------------------------------------------------------------
    # Add new columns to institutions
    # ------------------------------------------------------------------
    op.add_column('institutions', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('institutions', sa.Column('acceptance_rate', sa.Numeric(5, 2), nullable=True))
    op.add_column('institutions', sa.Column('enrollment_total', sa.Integer(), nullable=True))
    op.add_column('institutions', sa.Column('grad_enrollment', sa.Integer(), nullable=True))
    op.add_column('institutions', sa.Column('campus_setting', sa.String(), nullable=True))
    op.add_column('institutions', sa.Column('academic_calendar', sa.String(), nullable=True))
    op.add_column('institutions', sa.Column('last_scraped_at', sa.DateTime(), nullable=True))
    op.add_column('institutions', sa.Column('scrape_status', sa.String(), nullable=True))

    # ------------------------------------------------------------------
    # Add new columns to programs
    # ------------------------------------------------------------------
    op.add_column('programs', sa.Column('duration_months', sa.Integer(), nullable=True))
    op.add_column('programs', sa.Column('gre_required', sa.Boolean(), nullable=True))
    op.add_column('programs', sa.Column('minimum_gpa', sa.Numeric(3, 2), nullable=True))
    op.add_column('programs', sa.Column('last_scraped_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Drop new program columns
    op.drop_column('programs', 'last_scraped_at')
    op.drop_column('programs', 'minimum_gpa')
    op.drop_column('programs', 'gre_required')
    op.drop_column('programs', 'duration_months')

    # Drop new institution columns
    op.drop_column('institutions', 'scrape_status')
    op.drop_column('institutions', 'last_scraped_at')
    op.drop_column('institutions', 'academic_calendar')
    op.drop_column('institutions', 'campus_setting')
    op.drop_column('institutions', 'grad_enrollment')
    op.drop_column('institutions', 'enrollment_total')
    op.drop_column('institutions', 'acceptance_rate')
    op.drop_column('institutions', 'description')

    # Drop funding_opportunities table
    op.drop_index('ix_funding_opportunities_funding_type', table_name='funding_opportunities')
    op.drop_index('ix_funding_opportunities_institution_id', table_name='funding_opportunities')
    op.drop_table('funding_opportunities')

    # Drop scrape_jobs table
    op.drop_index('ix_scrape_jobs_status', table_name='scrape_jobs')
    op.drop_index('ix_scrape_jobs_job_type', table_name='scrape_jobs')
    op.drop_index('ix_scrape_jobs_institution_id', table_name='scrape_jobs')
    op.drop_table('scrape_jobs')

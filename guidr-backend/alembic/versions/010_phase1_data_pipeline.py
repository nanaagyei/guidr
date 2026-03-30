"""Phase 1 data pipeline upgrades

Revision ID: 010_phase1_data_pipeline
Revises: 009_professors
Create Date: 2025-12-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '010_phase1_data_pipeline'
down_revision = '009_professors'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column('institutions', sa.Column('ipeds_unit_id', sa.String(), nullable=True))
    op.add_column('institutions', sa.Column('scorecard_school_id', sa.String(), nullable=True))
    op.add_column('institutions', sa.Column('average_cost', sa.Numeric(12, 2), nullable=True))
    op.add_column('institutions', sa.Column('in_state_tuition', sa.Numeric(12, 2), nullable=True))
    op.add_column('institutions', sa.Column('out_of_state_tuition', sa.Numeric(12, 2), nullable=True))
    op.add_column('institutions', sa.Column('graduation_rate', sa.Numeric(5, 2), nullable=True))
    op.add_column('institutions', sa.Column('median_earnings', sa.Numeric(12, 2), nullable=True))
    op.add_column('institutions', sa.Column('data_source', sa.String(), nullable=False, server_default='manual'))
    op.add_column('institutions', sa.Column('data_completeness_score', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('institutions', sa.Column('embedding', Vector(384), nullable=True))

    op.create_index('ix_institutions_ipeds_unit_id', 'institutions', ['ipeds_unit_id'], unique=True)
    op.create_index('ix_institutions_scorecard_school_id', 'institutions', ['scorecard_school_id'], unique=True)

    op.add_column('programs', sa.Column('data_source', sa.String(), nullable=False, server_default='manual'))
    op.add_column('programs', sa.Column('embedding', Vector(384), nullable=True))

    op.alter_column('institutions', 'data_source', server_default=None)
    op.alter_column('institutions', 'data_completeness_score', server_default=None)
    op.alter_column('programs', 'data_source', server_default=None)


def downgrade() -> None:
    op.drop_column('programs', 'embedding')
    op.drop_column('programs', 'data_source')

    op.drop_index('ix_institutions_scorecard_school_id', table_name='institutions')
    op.drop_index('ix_institutions_ipeds_unit_id', table_name='institutions')

    op.drop_column('institutions', 'embedding')
    op.drop_column('institutions', 'data_completeness_score')
    op.drop_column('institutions', 'data_source')
    op.drop_column('institutions', 'median_earnings')
    op.drop_column('institutions', 'graduation_rate')
    op.drop_column('institutions', 'out_of_state_tuition')
    op.drop_column('institutions', 'in_state_tuition')
    op.drop_column('institutions', 'average_cost')
    op.drop_column('institutions', 'scorecard_school_id')
    op.drop_column('institutions', 'ipeds_unit_id')


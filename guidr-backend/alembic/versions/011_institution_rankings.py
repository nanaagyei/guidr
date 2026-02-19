"""Add institution ranking columns and is_deleted flag.

Revision ID: 011_institution_rankings
Revises: 010_phase1_data_pipeline
Create Date: 2024-12-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_institution_rankings'
down_revision = '010_phase1_data_pipeline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new ranking columns to institutions table
    op.add_column('institutions', sa.Column('qs_world_rank', sa.Integer(), nullable=True))
    op.add_column('institutions', sa.Column('the_world_rank', sa.Integer(), nullable=True))
    op.add_column('institutions', sa.Column('arwu_rank', sa.Integer(), nullable=True))
    op.add_column('institutions', sa.Column('usnews_rank', sa.Integer(), nullable=True))
    op.add_column('institutions', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create indexes for ranking columns
    op.create_index('ix_institutions_qs_world_rank', 'institutions', ['qs_world_rank'])
    op.create_index('ix_institutions_the_world_rank', 'institutions', ['the_world_rank'])
    
    # Remove server default after column is created
    op.alter_column('institutions', 'is_deleted', server_default=None)


def downgrade() -> None:
    op.drop_index('ix_institutions_the_world_rank', table_name='institutions')
    op.drop_index('ix_institutions_qs_world_rank', table_name='institutions')
    op.drop_column('institutions', 'is_deleted')
    op.drop_column('institutions', 'usnews_rank')
    op.drop_column('institutions', 'arwu_rank')
    op.drop_column('institutions', 'the_world_rank')
    op.drop_column('institutions', 'qs_world_rank')


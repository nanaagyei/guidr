"""Add prompt_variant column to extraction_runs.

Revision ID: 021_prompt_variant_column
Revises: 020_research_cache_table
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "021_prompt_variant_column"
down_revision = "020_research_cache_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extraction_runs",
        sa.Column("prompt_variant", sa.String(), nullable=True, server_default="a"),
    )


def downgrade() -> None:
    op.drop_column("extraction_runs", "prompt_variant")

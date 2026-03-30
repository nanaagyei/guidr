"""Add enrichment tracking columns to canonical entity tables.

Adds last_enriched_at, last_enrichment_confidence, and data_version to:
- institutions
- programs
- professors
- funding_opportunities

These columns are written by the promote_write node in the LangGraph orchestrator
and consumed by the frontend to show enrichment freshness badges.

Revision ID: 015_add_enrich_tracking
Revises: 014_pipeline_tables_v2
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa


revision = "015_add_enrich_tracking"
down_revision = "014_pipeline_tables_v2"
branch_labels = None
depends_on = None


_TABLES = ["institutions", "programs", "professors", "funding_opportunities"]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("last_enrichment_confidence", sa.Numeric(4, 3), nullable=True))
        op.add_column(table, sa.Column("data_version", sa.Integer(), nullable=False, server_default="1"))

    # Index for staleness queries (find entities enriched before a threshold)
    op.create_index("ix_institutions_last_enriched_at", "institutions", ["last_enriched_at"])
    op.create_index("ix_programs_last_enriched_at", "programs", ["last_enriched_at"])


def downgrade() -> None:
    op.drop_index("ix_programs_last_enriched_at", table_name="programs")
    op.drop_index("ix_institutions_last_enriched_at", table_name="institutions")

    for table in _TABLES:
        op.drop_column(table, "data_version")
        op.drop_column(table, "last_enrichment_confidence")
        op.drop_column(table, "last_enriched_at")

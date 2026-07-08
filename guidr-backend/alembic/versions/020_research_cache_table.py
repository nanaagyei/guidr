"""Add research_cache table for PostgreSQL-backed deduplication.

Revision ID: 020_research_cache_table
Revises: 019_validation_confidence_tables
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020_research_cache_table"
down_revision = "019_validation_confidence_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("dedupe_key", sa.String(64), nullable=False, unique=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(), nullable=False, server_default="URL_DISCOVERY"),
        sa.Column("latest_result_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("citations_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("provider_name", sa.String(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(8, 4), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_research_cache_dedupe_key", "research_cache", ["dedupe_key"], unique=True)
    op.create_index("ix_research_cache_entity", "research_cache", ["entity_type", "entity_id"])
    op.create_index("ix_research_cache_category", "research_cache", ["category"])
    op.create_index("ix_research_cache_expires", "research_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_research_cache_expires", table_name="research_cache")
    op.drop_index("ix_research_cache_category", table_name="research_cache")
    op.drop_index("ix_research_cache_entity", table_name="research_cache")
    op.drop_index("ix_research_cache_dedupe_key", table_name="research_cache")
    op.drop_table("research_cache")

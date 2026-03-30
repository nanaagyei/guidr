"""Add research_areas/career_goals to user_profiles; add user_id to enrichment_cache.

- user_profiles: research_areas JSONB (array of strings), career_goals TEXT
- enrichment_cache: user_id UUID NULL (enables per-user dossier caching)

Revision ID: 017_user_profile_research_areas
Revises: 016_dossier_system
Create Date: 2026-03-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "017_user_profile_research_areas"
down_revision = "016_dossier_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_profiles: research interests and career goals
    op.add_column(
        "user_profiles",
        sa.Column("research_areas", JSONB, nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("career_goals", sa.Text, nullable=True),
    )

    # enrichment_cache: per-user scope (NULL = global/shared)
    op.add_column(
        "enrichment_cache",
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_enrichment_cache_user_id",
        "enrichment_cache",
        ["user_id"],
    )
    # Composite index to speed up per-user cache lookups
    op.create_index(
        "ix_enrichment_cache_entity_user",
        "enrichment_cache",
        ["entity_kind", "entity_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_enrichment_cache_entity_user", table_name="enrichment_cache")
    op.drop_index("ix_enrichment_cache_user_id", table_name="enrichment_cache")
    op.drop_column("enrichment_cache", "user_id")
    op.drop_column("user_profiles", "career_goals")
    op.drop_column("user_profiles", "research_areas")

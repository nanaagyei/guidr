"""Add dossier system columns for agentic enrichment.

Adds:
- extraction_runs: evidence_map_json JSONB
- professors: openalex_id, semantic_scholar_id, orcid_id (all indexed)
- enrichment_cache: citations_json JSONB, evidence_map_json JSONB
- recommendation_sessions: pipeline_job_id FK, citations_json JSONB
- recommendation_results: citations_json JSONB, evidence_map_json JSONB

Revision ID: 016_dossier_system
Revises: 015_add_enrich_tracking
Create Date: 2026-03-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "016_dossier_system"
down_revision = "015_add_enrich_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # extraction_runs: evidence_map_json
    op.add_column(
        "extraction_runs",
        sa.Column("evidence_map_json", JSONB, nullable=False, server_default="{}"),
    )

    # professors: academic identifiers
    op.add_column("professors", sa.Column("openalex_id", sa.String(64), nullable=True))
    op.add_column("professors", sa.Column("semantic_scholar_id", sa.String(64), nullable=True))
    op.add_column("professors", sa.Column("orcid_id", sa.String(32), nullable=True))
    op.create_index("ix_professors_openalex_id", "professors", ["openalex_id"])
    op.create_index("ix_professors_semantic_scholar_id", "professors", ["semantic_scholar_id"])
    op.create_index("ix_professors_orcid_id", "professors", ["orcid_id"])

    # enrichment_cache: citations + evidence
    op.add_column(
        "enrichment_cache",
        sa.Column("citations_json", JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "enrichment_cache",
        sa.Column("evidence_map_json", JSONB, nullable=False, server_default="{}"),
    )

    # recommendation_sessions: pipeline_job_id FK + citations
    op.add_column(
        "recommendation_sessions",
        sa.Column("pipeline_job_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_rec_sessions_pipeline_job",
        "recommendation_sessions",
        "pipeline_jobs",
        ["pipeline_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "recommendation_sessions",
        sa.Column("citations_json", JSONB, nullable=False, server_default="[]"),
    )

    # recommendation_results: citations + evidence
    op.add_column(
        "recommendation_results",
        sa.Column("citations_json", JSONB, nullable=False, server_default="[]"),
    )
    op.add_column(
        "recommendation_results",
        sa.Column("evidence_map_json", JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    # recommendation_results
    op.drop_column("recommendation_results", "evidence_map_json")
    op.drop_column("recommendation_results", "citations_json")

    # recommendation_sessions
    op.drop_constraint("fk_rec_sessions_pipeline_job", "recommendation_sessions", type_="foreignkey")
    op.drop_column("recommendation_sessions", "citations_json")
    op.drop_column("recommendation_sessions", "pipeline_job_id")

    # enrichment_cache
    op.drop_column("enrichment_cache", "evidence_map_json")
    op.drop_column("enrichment_cache", "citations_json")

    # professors
    op.drop_index("ix_professors_orcid_id", table_name="professors")
    op.drop_index("ix_professors_semantic_scholar_id", table_name="professors")
    op.drop_index("ix_professors_openalex_id", table_name="professors")
    op.drop_column("professors", "orcid_id")
    op.drop_column("professors", "semantic_scholar_id")
    op.drop_column("professors", "openalex_id")

    # extraction_runs
    op.drop_column("extraction_runs", "evidence_map_json")

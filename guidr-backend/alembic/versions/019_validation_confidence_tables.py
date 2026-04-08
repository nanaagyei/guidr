"""Add validation_reports and confidence_scores tables.

Revision ID: 019_validation_confidence_tables
Revises: 018_recommendation_ai_columns
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "019_validation_confidence_tables"
down_revision = "018_recommendation_ai_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create validation_reports table
    op.create_table(
        "validation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("extraction_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pipeline_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_kind", sa.String(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("validator_name", sa.String(), nullable=False),
        sa.Column("validator_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("overall_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("field_results_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("warnings_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("errors_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_foreign_key(
        "fk_validation_reports_extraction_run",
        "validation_reports",
        "extraction_runs",
        ["extraction_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_validation_reports_pipeline_job",
        "validation_reports",
        "pipeline_jobs",
        ["pipeline_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_validation_reports_extraction_run", "validation_reports", ["extraction_run_id"])
    op.create_index("ix_validation_reports_entity", "validation_reports", ["entity_kind", "entity_id"])
    op.create_index("ix_validation_reports_created", "validation_reports", ["created_at"])

    # 2. Create confidence_scores table
    op.create_table(
        "confidence_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("extraction_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pipeline_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_kind", sa.String(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scorer_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("overall_confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("source_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("extraction_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("validation_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("staleness_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("weights_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("details_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_foreign_key(
        "fk_confidence_scores_extraction_run",
        "confidence_scores",
        "extraction_runs",
        ["extraction_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_confidence_scores_pipeline_job",
        "confidence_scores",
        "pipeline_jobs",
        ["pipeline_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_confidence_scores_extraction_run", "confidence_scores", ["extraction_run_id"])
    op.create_index("ix_confidence_scores_entity", "confidence_scores", ["entity_kind", "entity_id"])
    op.create_index("ix_confidence_scores_created", "confidence_scores", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_confidence_scores_created", table_name="confidence_scores")
    op.drop_index("ix_confidence_scores_entity", table_name="confidence_scores")
    op.drop_index("ix_confidence_scores_extraction_run", table_name="confidence_scores")
    op.drop_table("confidence_scores")

    op.drop_index("ix_validation_reports_created", table_name="validation_reports")
    op.drop_index("ix_validation_reports_entity", table_name="validation_reports")
    op.drop_index("ix_validation_reports_extraction_run", table_name="validation_reports")
    op.drop_table("validation_reports")

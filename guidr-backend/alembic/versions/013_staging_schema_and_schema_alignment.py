"""Add staging schema, staging tables, and Phase 6 schema alignment.

Creates:
- staging schema with staging tables for pipeline data
- program_id on funding_opportunities
- professor_programs association table

Revision ID: 013_staging_schema
Revises: 012_pipeline_models
Create Date: 2026-02-02 19:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "013_staging_schema"
down_revision = "012_pipeline_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create staging schema
    # ------------------------------------------------------------------
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")

    # ------------------------------------------------------------------
    # Staging table: generic pipeline records pending promotion
    # ------------------------------------------------------------------
    op.create_table(
        "staging_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("institution_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("program_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("validation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("validation_errors", JSONB, nullable=True),
        sa.Column("diff_summary", JSONB, nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("raw_data_path", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        schema="staging",
    )
    op.create_index(
        "ix_staging_records_validation_status",
        "staging_records",
        ["validation_status"],
        schema="staging",
    )

    # ------------------------------------------------------------------
    # Phase 6: Add program_id to funding_opportunities
    # ------------------------------------------------------------------
    op.add_column(
        "funding_opportunities",
        sa.Column("program_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_funding_opportunities_program_id",
        "funding_opportunities",
        "programs",
        ["program_id"],
        ["id"],
    )
    op.create_index("ix_funding_opportunities_program_id", "funding_opportunities", ["program_id"])

    # ------------------------------------------------------------------
    # Phase 6: Professor-Program association table
    # ------------------------------------------------------------------
    op.create_table(
        "professor_programs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("professor_id", UUID(as_uuid=True), sa.ForeignKey("professors.id"), nullable=False),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("programs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_professor_programs_professor_id", "professor_programs", ["professor_id"])
    op.create_index("ix_professor_programs_program_id", "professor_programs", ["program_id"])
    op.create_unique_constraint(
        "uq_professor_programs",
        "professor_programs",
        ["professor_id", "program_id"],
    )


def downgrade() -> None:
    op.drop_table("professor_programs")
    op.drop_index("ix_funding_opportunities_program_id", table_name="funding_opportunities")
    op.drop_constraint("fk_funding_opportunities_program_id", "funding_opportunities", type_="foreignkey")
    op.drop_column("funding_opportunities", "program_id")
    op.drop_table("staging_records", schema="staging")
    op.execute("DROP SCHEMA IF EXISTS staging")

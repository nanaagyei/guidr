"""Add pipeline tables for Research Gateway + LangGraph orchestrator.

Creates:
- Extensions: pgcrypto, citext
- Enums: job_status, job_priority, artifact_type, extraction_status, entity_kind, research_provider
- Tables: source_documents, pipeline_jobs, raw_artifacts, extraction_runs, entity_promotions,
  enrichment_cache, recommendation_cache, domain_health
- Triggers: pipeline_jobs updated_at

Revision ID: 014_pipeline_tables_v2
Revises: 013_staging_schema
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM


revision = "014_pipeline_tables_v2"
down_revision = "013_staging_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ------------------------------------------------------------------
    # Enums (idempotent)
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE job_status AS ENUM ('queued','running','succeeded','failed','canceled','skipped');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE job_priority AS ENUM ('critical','high','bulk');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE artifact_type AS ENUM ('html','pdf','json','text','image','other');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE extraction_status AS ENUM ('draft','validated','promoted','rejected');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE entity_kind AS ENUM ('school','program','professor','department','funding','deadline','other');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE research_provider AS ENUM ('perplexity','open_deep_research','langchain_custom','manual');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """)

    # Reusable enum types (create_type=False - types already created above)
    job_status_enum = ENUM("queued", "running", "succeeded", "failed", "canceled", "skipped", name="job_status", create_type=False)
    job_priority_enum = ENUM("critical", "high", "bulk", name="job_priority", create_type=False)
    entity_kind_enum = ENUM("school", "program", "professor", "department", "funding", "deadline", "other", name="entity_kind", create_type=False)
    artifact_type_enum = ENUM("html", "pdf", "json", "text", "image", "other", name="artifact_type", create_type=False)
    extraction_status_enum = ENUM("draft", "validated", "promoted", "rejected", name="extraction_status", create_type=False)

    # ------------------------------------------------------------------
    # source_documents (with generated columns via raw SQL)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS source_documents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_kind entity_kind NOT NULL,
            entity_id uuid NULL,
            canonical_url text NOT NULL,
            url_hash text GENERATED ALWAYS AS (encode(digest(lower(canonical_url), 'sha256'), 'hex')) STORED,
            host text GENERATED ALWAYS AS (split_part(replace(replace(canonical_url,'https://',''),'http://',''), '/', 1)) STORED,
            purpose text NULL,
            discovered_by research_provider DEFAULT 'manual',
            discovered_at timestamptz NOT NULL DEFAULT now(),
            last_seen_at timestamptz NULL,
            last_crawled_at timestamptz NULL,
            is_active boolean NOT NULL DEFAULT true,
            notes text NULL,
            UNIQUE(entity_kind, entity_id, url_hash)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_source_documents_entity ON source_documents(entity_kind, entity_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_source_documents_host ON source_documents(host)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_source_documents_url_hash ON source_documents(url_hash)")

    # ------------------------------------------------------------------
    # pipeline_jobs
    # ------------------------------------------------------------------
    op.create_table(
        "pipeline_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("priority", job_priority_enum, nullable=False, server_default="high"),
        sa.Column("status", job_status_enum, nullable=False, server_default="queued"),
        sa.Column("entity_kind", entity_kind_enum, nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_document_id", UUID(as_uuid=True), nullable=True),
        sa.Column("target_url", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("freshness_bucket", sa.String(), nullable=False, server_default="default"),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("dedup_group", sa.String(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_by", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("input_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("metrics_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_pipeline_jobs_source_document",
        "pipeline_jobs",
        "source_documents",
        ["source_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint("uq_pipeline_jobs_fingerprint", "pipeline_jobs", ["fingerprint"])
    op.create_index("ix_pipeline_jobs_status_priority", "pipeline_jobs", ["status", "priority"])
    op.create_index("ix_pipeline_jobs_entity", "pipeline_jobs", ["entity_kind", "entity_id"])
    op.create_index("ix_pipeline_jobs_source_doc", "pipeline_jobs", ["source_document_id"])
    op.create_index("ix_pipeline_jobs_queued", "pipeline_jobs", ["queued_at"])

    # ------------------------------------------------------------------
    # raw_artifacts
    # ------------------------------------------------------------------
    op.create_table(
        "raw_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_document_id", UUID(as_uuid=True), nullable=True),
        sa.Column("fetched_from_url", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("artifact_type", artifact_type_enum, nullable=False, server_default="html"),
        sa.Column("content_sha256", sa.String(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("etag", sa.String(), nullable=True),
        sa.Column("last_modified", sa.String(), nullable=True),
        sa.Column("request_headers", JSONB, nullable=False, server_default="{}"),
        sa.Column("response_headers", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_parsed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("parse_notes", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_raw_artifacts_source_document",
        "raw_artifacts",
        "source_documents",
        ["source_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint("uq_raw_artifacts_content_sha256", "raw_artifacts", ["content_sha256"])
    op.create_index("ix_raw_artifacts_source_doc", "raw_artifacts", ["source_document_id"])
    op.create_index("ix_raw_artifacts_fetched_at", "raw_artifacts", ["fetched_at"])

    # ------------------------------------------------------------------
    # extraction_runs
    # ------------------------------------------------------------------
    op.create_table(
        "extraction_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), nullable=True),
        sa.Column("raw_artifact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_kind", entity_kind_enum, nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("extractor_name", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("extracted_json", JSONB, nullable=False),
        sa.Column("citations_json", JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("status", extraction_status_enum, nullable=False, server_default="draft"),
        sa.Column("validation_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("token_usage_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_extraction_runs_job",
        "extraction_runs",
        "pipeline_jobs",
        ["job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_extraction_runs_raw_artifact",
        "extraction_runs",
        "raw_artifacts",
        ["raw_artifact_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_extraction_runs_artifact", "extraction_runs", ["raw_artifact_id"])
    op.create_index("ix_extraction_runs_entity", "extraction_runs", ["entity_kind", "entity_id"])
    op.create_index("ix_extraction_runs_status", "extraction_runs", ["status"])

    # ------------------------------------------------------------------
    # entity_promotions
    # ------------------------------------------------------------------
    op.create_table(
        "entity_promotions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("extraction_run_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_kind", entity_kind_enum, nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("promoted_by", sa.String(), nullable=False, server_default="system"),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("promotion_notes", sa.Text(), nullable=True),
        sa.Column("diff_json", JSONB, nullable=False, server_default="{}"),
    )
    op.create_foreign_key(
        "fk_entity_promotions_extraction_run",
        "entity_promotions",
        "extraction_runs",
        ["extraction_run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_entity_promotions_entity", "entity_promotions", ["entity_kind", "entity_id"])

    # ------------------------------------------------------------------
    # enrichment_cache
    # ------------------------------------------------------------------
    op.create_table(
        "enrichment_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_kind", entity_kind_enum, nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("freshness_bucket", sa.String(), nullable=False, server_default="30d"),
        sa.Column("value_json", JSONB, nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_extraction_run_ids", sa.ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}"),
        sa.Column("hit_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_enrichment_cache",
        "enrichment_cache",
        ["entity_kind", "entity_id", "schema_version", "freshness_bucket"],
    )
    op.create_index("ix_enrichment_cache_entity", "enrichment_cache", ["entity_kind", "entity_id"])
    op.create_index("ix_enrichment_cache_expires", "enrichment_cache", ["expires_at"])

    # ------------------------------------------------------------------
    # recommendation_cache (optional)
    # ------------------------------------------------------------------
    op.create_table(
        "recommendation_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_profile_fingerprint", sa.String(), nullable=False),
        sa.Column("algo_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("result_json", JSONB, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hit_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_recommendation_cache",
        "recommendation_cache",
        ["user_profile_fingerprint", "algo_version"],
    )
    op.create_index("ix_reco_cache_expires", "recommendation_cache", ["expires_at"])

    # ------------------------------------------------------------------
    # domain_health
    # ------------------------------------------------------------------
    op.create_table(
        "domain_health",
        sa.Column("host", sa.String(), primary_key=True),
        sa.Column("last_ok_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("block_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ------------------------------------------------------------------
    # Trigger: pipeline_jobs updated_at
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_pipeline_jobs_updated_at ON pipeline_jobs;
        CREATE TRIGGER trg_pipeline_jobs_updated_at
        BEFORE UPDATE ON pipeline_jobs
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)


def downgrade() -> None:
    # Trigger
    op.execute("DROP TRIGGER IF EXISTS trg_pipeline_jobs_updated_at ON pipeline_jobs")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    # Tables in reverse dependency order
    op.drop_table("domain_health")
    op.drop_table("recommendation_cache")
    op.drop_table("enrichment_cache")
    op.drop_table("entity_promotions")
    op.drop_table("extraction_runs")
    op.drop_table("raw_artifacts")
    op.drop_table("pipeline_jobs")
    op.drop_table("source_documents")

    # Enums
    op.execute("DROP TYPE IF EXISTS research_provider")
    op.execute("DROP TYPE IF EXISTS entity_kind")
    op.execute("DROP TYPE IF EXISTS extraction_status")
    op.execute("DROP TYPE IF EXISTS artifact_type")
    op.execute("DROP TYPE IF EXISTS job_priority")
    op.execute("DROP TYPE IF EXISTS job_status")

    # Extensions (optional - may be used elsewhere)
    # op.execute("DROP EXTENSION IF EXISTS citext")
    # op.execute("DROP EXTENSION IF EXISTS pgcrypto")

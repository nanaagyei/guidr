"""Make recommendation_results.program_id nullable, add AI metadata columns,
create saved_recommendations table, convert PG enums to varchar.

Revision ID: 018_recommendation_ai_columns
Revises: 017_user_profile_research_areas
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018_recommendation_ai_columns"
down_revision = "017_user_profile_research_areas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0. Add 'user' to entity_kind enum (needed for recommendation_run cache entries)
    # ALTER TYPE ADD VALUE cannot run inside a transaction block,
    # so we commit the current transaction and re-open it.
    op.execute("COMMIT")
    op.execute("ALTER TYPE entity_kind ADD VALUE IF NOT EXISTS 'user'")
    op.execute("BEGIN")

    # 1. Convert recommendation_results.tier from PG enum to VARCHAR(20)
    op.execute(
        "ALTER TABLE recommendation_results "
        "ALTER COLUMN tier TYPE VARCHAR(20) USING tier::text"
    )
    op.execute("DROP TYPE IF EXISTS recommendationtier")

    # 2. Convert recommendation_sessions.status from PG enum to VARCHAR(20)
    # Drop the server default first (it references the enum type)
    op.execute(
        "ALTER TABLE recommendation_sessions "
        "ALTER COLUMN status DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE recommendation_sessions "
        "ALTER COLUMN status TYPE VARCHAR(20) USING status::text"
    )
    op.execute(
        "ALTER TABLE recommendation_sessions "
        "ALTER COLUMN status SET DEFAULT 'pending'"
    )
    op.execute("DROP TYPE IF EXISTS recommendationstatus")

    # 3. Make program_id nullable
    op.drop_constraint(
        "fk_recommendation_results_program_id",
        "recommendation_results",
        type_="foreignkey",
    )
    op.alter_column(
        "recommendation_results",
        "program_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_recommendation_results_program_id",
        "recommendation_results",
        "programs",
        ["program_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Add AI metadata columns to recommendation_results
    op.add_column(
        "recommendation_results",
        sa.Column("school_name", sa.String(), nullable=True),
    )
    op.add_column(
        "recommendation_results",
        sa.Column("program_name", sa.String(), nullable=True),
    )
    op.add_column(
        "recommendation_results",
        sa.Column("institution_city", sa.String(), nullable=True),
    )
    op.add_column(
        "recommendation_results",
        sa.Column("institution_country", sa.String(), nullable=True),
    )
    op.add_column(
        "recommendation_results",
        sa.Column("funding_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "recommendation_results",
        sa.Column("deadline", sa.String(), nullable=True),
    )
    op.add_column(
        "recommendation_results",
        sa.Column("website_url", sa.String(), nullable=True),
    )

    # 5. Create saved_recommendations table
    op.create_table(
        "saved_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "recommendation_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("school_dossier_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("professor_match_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("funding_dossier_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "research_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("saved_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # Foreign keys for saved_recommendations
    op.create_foreign_key(
        "fk_saved_rec_user",
        "saved_recommendations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_saved_rec_result",
        "saved_recommendations",
        "recommendation_results",
        ["recommendation_result_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_saved_rec_institution",
        "saved_recommendations",
        "institutions",
        ["institution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_saved_rec_program",
        "saved_recommendations",
        "programs",
        ["program_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_saved_rec_dossier_job",
        "saved_recommendations",
        "pipeline_jobs",
        ["school_dossier_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_saved_rec_prof_job",
        "saved_recommendations",
        "pipeline_jobs",
        ["professor_match_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_saved_rec_funding_job",
        "saved_recommendations",
        "pipeline_jobs",
        ["funding_dossier_job_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Indexes
    op.create_index("idx_saved_rec_user_id", "saved_recommendations", ["user_id"])
    op.create_index(
        "idx_saved_rec_result_id",
        "saved_recommendations",
        ["recommendation_result_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop saved_recommendations
    op.drop_index("idx_saved_rec_result_id", table_name="saved_recommendations")
    op.drop_index("idx_saved_rec_user_id", table_name="saved_recommendations")
    op.drop_table("saved_recommendations")

    # Drop AI metadata columns
    op.drop_column("recommendation_results", "website_url")
    op.drop_column("recommendation_results", "deadline")
    op.drop_column("recommendation_results", "funding_summary")
    op.drop_column("recommendation_results", "institution_country")
    op.drop_column("recommendation_results", "institution_city")
    op.drop_column("recommendation_results", "program_name")
    op.drop_column("recommendation_results", "school_name")

    # Restore program_id to NOT NULL
    op.drop_constraint(
        "fk_recommendation_results_program_id",
        "recommendation_results",
        type_="foreignkey",
    )
    op.alter_column(
        "recommendation_results",
        "program_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_recommendation_results_program_id",
        "recommendation_results",
        "programs",
        ["program_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Recreate PG enums
    tier_enum = sa.Enum("dream", "reach", "target", "safety", name="recommendationtier")
    tier_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE recommendation_results "
        "ALTER COLUMN tier TYPE recommendationtier USING tier::recommendationtier"
    )

    status_enum = sa.Enum("pending", "running", "completed", "failed", name="recommendationstatus")
    status_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE recommendation_sessions "
        "ALTER COLUMN status TYPE recommendationstatus USING status::recommendationstatus"
    )

"""Add ai_research_consent_at to user_profiles.

Records when an applicant agreed that research areas, preferred countries and funding
priority may be sent to research model providers. Null means no consent.

Revision ID: 022_ai_research_consent
Revises: 021_prompt_variant_column
Create Date: 2026-11-07
"""
from alembic import op
import sqlalchemy as sa

revision = "022_ai_research_consent"
down_revision = "021_prompt_variant_column"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("ai_research_consent_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "ai_research_consent_at")

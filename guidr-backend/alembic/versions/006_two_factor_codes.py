"""Add two_factor_codes table

Revision ID: 006_two_factor_codes
Revises: 005_essays
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_two_factor_codes'
down_revision = '005_essays'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create two_factor_codes table
    op.create_table(
        'two_factor_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),  # Nullable for registration
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('used_at', sa.DateTime(), nullable=True),
    )
    
    # Add foreign key
    op.create_foreign_key(
        'fk_two_factor_codes_user_id',
        'two_factor_codes',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create indexes
    op.create_index('ix_two_factor_codes_user_id', 'two_factor_codes', ['user_id'])
    op.create_index('ix_two_factor_codes_code', 'two_factor_codes', ['code'])
    op.create_index('ix_two_factor_codes_email', 'two_factor_codes', ['email'])


def downgrade() -> None:
    op.drop_index('ix_two_factor_codes_email', table_name='two_factor_codes')
    op.drop_index('ix_two_factor_codes_code', table_name='two_factor_codes')
    op.drop_index('ix_two_factor_codes_user_id', table_name='two_factor_codes')
    op.drop_table('two_factor_codes')


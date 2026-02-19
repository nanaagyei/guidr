"""Add password_history table

Revision ID: 007_password_history
Revises: 006_two_factor_codes
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_password_history'
down_revision = '006_two_factor_codes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create password_history table
    op.create_table(
        'password_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Add foreign key
    op.create_foreign_key(
        'fk_password_history_user_id',
        'password_history',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index
    op.create_index('ix_password_history_user_id', 'password_history', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_password_history_user_id', table_name='password_history')
    op.drop_table('password_history')


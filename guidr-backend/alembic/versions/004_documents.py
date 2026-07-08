"""Add documents and document_processing_logs tables

Revision ID: 004_documents
Revises: 003_institutions_programs
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_documents'
down_revision = '003_institutions_programs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('document_type', sa.String(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('processing_status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('processing_error_message', sa.String(), nullable=True),
        sa.Column('is_scanned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ocr_confidence', sa.Numeric(5, 2), nullable=True),
        sa.Column('extracted_summary', postgresql.JSON, nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])
    op.create_index('ix_documents_processing_status', 'documents', ['processing_status'])

    # Create document_processing_logs table
    op.create_table(
        'document_processing_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='queued'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('worker_id', sa.String(), nullable=True),
    )
    op.create_index('ix_document_processing_logs_document_id', 'document_processing_logs', ['document_id'])


def downgrade() -> None:
    op.drop_index('ix_document_processing_logs_document_id', table_name='document_processing_logs')
    op.drop_table('document_processing_logs')
    op.drop_index('ix_documents_processing_status', table_name='documents')
    op.drop_index('ix_documents_user_id', table_name='documents')
    op.drop_table('documents')

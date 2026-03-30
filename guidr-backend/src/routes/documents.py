"""Document routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from src.db import get_db
from src.models.document import Document
from src.models.user import User
from src.schemas.document import (
    DocumentUploadUrlRequest,
    DocumentUploadUrlResponse,
    DocumentResponse
)
from src.dependencies.auth import get_current_user
from src.services.storage import storage_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload-url", response_model=DocumentUploadUrlResponse)
async def get_upload_url(
    request: DocumentUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a presigned URL for uploading a document.
    
    Args:
        request: Upload request with filename and document type
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Upload URL, document ID, and storage key
        
    Raises:
        HTTPException: If storage not configured or invalid document type
    """
    # Validate document type
    valid_types = ['transcript', 'resume', 'essay', 'other']
    if request.document_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"document_type must be one of: {', '.join(valid_types)}"
        )
    
    # Generate storage key
    document_id = uuid4()
    storage_key = f"user/{current_user.id}/documents/{document_id}-{request.filename}"
    
    # Create document record
    document = Document(
        id=document_id,
        user_id=current_user.id,
        document_type=request.document_type,
        original_filename=request.filename,
        storage_key=storage_key,
        file_size_bytes=0,  # Will be updated after upload
        processing_status="pending",
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Generate presigned URL
    upload_url = storage_service.generate_upload_url(storage_key)
    
    if not upload_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service not configured"
        )
    
    return {
        "upload_url": upload_url,
        "document_id": document_id,
        "storage_key": storage_key,
    }


@router.post("/{document_id}/confirm")
async def confirm_upload(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm document upload and enqueue processing.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Confirmation response
        
    Raises:
        HTTPException: If document not found or not owned by user
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update status to processing (worker will handle actual processing)
    document.processing_status = "processing"
    db.commit()
    
    # Enqueue background processing via Celery
    from src.workers.document_processor import process_document_task
    process_document_task.delay(str(document_id))

    return {
        "status": "queued",
        "document_id": str(document_id)
    }


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of documents
    """
    documents = db.query(Document).filter(
        Document.user_id == current_user.id
    ).order_by(Document.uploaded_at.desc()).all()
    
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Document details
        
    Raises:
        HTTPException: If document not found or not owned by user
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update last accessed
    document.last_accessed_at = datetime.utcnow()
    db.commit()
    
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If document not found or not owned by user
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete from storage
    storage_service.delete_file(document.storage_key)
    
    # Delete from database
    db.delete(document)
    db.commit()


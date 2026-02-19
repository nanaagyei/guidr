"""Worker job for processing documents with LLM extraction."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.config import settings
from src.db import SessionLocal
from src.models.academic_record import AcademicRecord
from src.models.document import Document
from src.models.document_processing_log import DocumentProcessingLog
from src.services.storage import storage_service
from src.utils.gpa import normalize_gpa

logger = logging.getLogger(__name__)

# Try to import PDF/document parsing libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# LLM clients
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class DocumentExtractor:
    """LLM-powered document extraction service."""
    
    def __init__(self):
        self._groq = None
        self._openai = None
        
        if settings.groq_api_key and GROQ_AVAILABLE:
            self._groq = Groq(api_key=settings.groq_api_key)
        if settings.openai_api_key and OPENAI_AVAILABLE:
            self._openai = OpenAI(api_key=settings.openai_api_key)
    
    def extract_text_from_pdf(self, file_data: bytes) -> str:
        """Extract text from PDF file."""
        if not PDF_AVAILABLE:
            logger.warning("PyPDF2 not available for PDF extraction")
            return ""
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""
    
    def extract_text_from_docx(self, file_data: bytes) -> str:
        """Extract text from DOCX file."""
        if not DOCX_AVAILABLE:
            logger.warning("python-docx not available for DOCX extraction")
            return ""
        
        try:
            doc = DocxDocument(io.BytesIO(file_data))
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return ""
    
    def extract_text(self, file_data: bytes, filename: str) -> str:
        """Extract text based on file type."""
        filename_lower = filename.lower()
        
        if filename_lower.endswith(".pdf"):
            return self.extract_text_from_pdf(file_data)
        elif filename_lower.endswith((".docx", ".doc")):
            return self.extract_text_from_docx(file_data)
        elif filename_lower.endswith(".txt"):
            return file_data.decode("utf-8", errors="ignore")
        else:
            # Try to decode as text
            try:
                return file_data.decode("utf-8", errors="ignore")
            except:
                return ""
    
    def extract_transcript_with_llm(self, text: str) -> Dict:
        """Use LLM to extract structured transcript data."""
        if not text or len(text) < 50:
            return self._fallback_transcript_extraction(text)
        
        prompt = """Analyze this academic transcript and extract the following information as JSON:

{
    "institution_name": "Name of the university/college",
    "country": "Country where institution is located",
    "degree_level": "bachelors, masters, or phd",
    "field_of_study": "Major/field of study",
    "gpa_value": numeric GPA value,
    "gpa_scale": GPA scale (e.g., 4.0, 5.0, 10.0),
    "start_year": graduation year or start year if available,
    "end_year": end year if available,
    "courses": ["list of course names if visible"],
    "honors": "any honors, distinctions, or awards mentioned"
}

Only include fields where you have high confidence. Use null for uncertain values.

Transcript text:
"""
        
        try:
            response = self._call_llm(prompt + text[:8000])
            if response:
                # Parse JSON from response
                json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"LLM transcript extraction error: {e}")
        
        return self._fallback_transcript_extraction(text)
    
    def extract_resume_with_llm(self, text: str) -> Dict:
        """Use LLM to extract structured resume data."""
        if not text or len(text) < 50:
            return {"skills": [], "education": [], "experiences": []}
        
        prompt = """Analyze this resume and extract the following information as JSON:

{
    "name": "Full name of the person",
    "email": "Email address if visible",
    "phone": "Phone number if visible",
    "skills": ["list of technical and soft skills"],
    "education": [
        {
            "institution": "School name",
            "degree": "Degree type",
            "field": "Field of study",
            "year": "Graduation year"
        }
    ],
    "experiences": [
        {
            "company": "Company name",
            "title": "Job title",
            "duration": "Time period",
            "description": "Brief description"
        }
    ],
    "research_interests": ["list of research interests if mentioned"],
    "publications": ["list of publications if mentioned"]
}

Resume text:
"""
        
        try:
            response = self._call_llm(prompt + text[:8000])
            if response:
                json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"LLM resume extraction error: {e}")
        
        return {"skills": [], "education": [], "experiences": []}
    
    def extract_essay_with_llm(self, text: str) -> Dict:
        """Extract and summarize essay content."""
        if not text:
            return {"text": "", "summary": "", "word_count": 0}
        
        summary = ""
        if len(text) > 500:
            prompt = """Provide a 2-3 sentence summary of this essay, focusing on the main themes and the author's goals:

"""
            try:
                summary = self._call_llm(prompt + text[:6000]) or ""
            except Exception as e:
                logger.error(f"LLM essay extraction error: {e}")
        
        return {
            "text": text,
            "summary": summary,
            "word_count": len(text.split()),
        }
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM provider."""
        try:
            if self._groq:
                response = self._groq.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000,
                )
                return response.choices[0].message.content
            
            elif self._openai:
                response = self._openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000,
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call error: {e}")
        
        return None
    
    def _fallback_transcript_extraction(self, text: str) -> Dict:
        """Fallback heuristic extraction when LLM unavailable."""
        result = {
            "institution_name": None,
            "country": None,
            "degree_level": None,
            "field_of_study": None,
            "gpa_value": None,
            "gpa_scale": None,
        }
        
        if not text:
            return result
        
        text_lower = text.lower()
        
        # Try to find GPA
        gpa_match = re.search(r"(?:gpa|grade point average)[:\s]*(\d+\.?\d*)\s*/?\s*(\d+\.?\d*)?", text_lower)
        if gpa_match:
            result["gpa_value"] = float(gpa_match.group(1))
            if gpa_match.group(2):
                result["gpa_scale"] = float(gpa_match.group(2))
            else:
                result["gpa_scale"] = 4.0 if result["gpa_value"] <= 4.0 else 10.0
        
        # Detect degree level
        if "ph.d" in text_lower or "doctorate" in text_lower:
            result["degree_level"] = "phd"
        elif "master" in text_lower:
            result["degree_level"] = "masters"
        elif "bachelor" in text_lower or "b.s." in text_lower or "b.a." in text_lower:
            result["degree_level"] = "bachelors"
        
        return result


# Global extractor instance
_extractor = None

def get_extractor() -> DocumentExtractor:
    """Get or create document extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = DocumentExtractor()
    return _extractor


def process_document(document_id: str, attempt: int = 1):
    """Process a document: download, extract, and store results.
    
    Args:
        document_id: Document UUID as string
        attempt: Attempt number for retries
    """
    db = SessionLocal()
    log = None
    
    try:
        doc_uuid = UUID(document_id)
        
        # Fetch document
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        # Check if already completed (idempotency)
        if document.processing_status == "completed":
            logger.info(f"Document {document_id} already processed")
            return
        
        # Update status
        document.processing_status = "processing"
        db.commit()
        
        # Create processing log
        log = DocumentProcessingLog(
            document_id=doc_uuid,
            job_type="document.process",
            status="running",
            started_at=datetime.utcnow(),
            attempt_number=attempt,
        )
        db.add(log)
        db.commit()
        
        # Download file
        file_data = storage_service.download_file(document.storage_key)
        if not file_data:
            raise Exception("Failed to download file from storage")
        
        # Get extractor
        extractor = get_extractor()
        
        # Extract text first
        text = extractor.extract_text(file_data, document.original_filename)
        
        # Route by document type
        if document.document_type == "transcript":
            extracted_data = extractor.extract_transcript_with_llm(text)
        elif document.document_type == "resume":
            extracted_data = extractor.extract_resume_with_llm(text)
        elif document.document_type == "essay":
            extracted_data = extractor.extract_essay_with_llm(text)
        else:
            extracted_data = {"text": text[:5000]}
        
        # Update document
        document.extracted_summary = extracted_data
        document.processing_status = "completed"
        document.processed_at = datetime.utcnow()
        
        # For transcripts, create AcademicRecord
        if document.document_type == "transcript" and extracted_data:
            create_academic_record_from_transcript(db, document, extracted_data)
        
        # Update log
        log.status = "succeeded"
        log.finished_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Document {document_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        db.rollback()
        
        # Update document status
        try:
            document = db.query(Document).filter(Document.id == UUID(document_id)).first()
            if document:
                document.processing_status = "failed"
                document.processing_error_message = str(e)
                db.commit()
        except:
            pass
        
        # Update log
        if log:
            try:
                log.status = "failed"
                log.error_message = str(e)
                log.finished_at = datetime.utcnow()
                db.commit()
            except:
                pass
        
        raise  # Re-raise for retry handling
    finally:
        db.close()


def create_academic_record_from_transcript(
    db: Session,
    document: Document,
    extracted_data: dict
):
    """Create AcademicRecord from extracted transcript data.
    
    Args:
        db: Database session
        document: Document object
        extracted_data: Extracted transcript data
    """
    institution_name = extracted_data.get("institution_name")
    if not institution_name:
        logger.warning("No institution name extracted from transcript")
        return
    
    # Check if record already exists
    existing = db.query(AcademicRecord).filter(
        AcademicRecord.user_id == document.user_id,
        AcademicRecord.institution_name == institution_name,
        AcademicRecord.source == "transcript_extraction"
    ).first()
    
    gpa_value = extracted_data.get("gpa_value")
    gpa_scale = extracted_data.get("gpa_scale")
    
    if existing:
        # Update existing record
        if gpa_value and gpa_scale:
            existing.gpa_value = gpa_value
            existing.gpa_scale = gpa_scale
            existing.normalized_gpa = normalize_gpa(gpa_value, gpa_scale)
        if extracted_data.get("field_of_study"):
            existing.field_of_study = extracted_data["field_of_study"]
        if extracted_data.get("degree_level"):
            existing.degree_level = extracted_data["degree_level"]
        logger.info(f"Updated existing academic record for {institution_name}")
        return
    
    # Calculate normalized GPA
    normalized_gpa = None
    if gpa_value and gpa_scale:
        normalized_gpa = normalize_gpa(gpa_value, gpa_scale)
    
    # Create new record
    record = AcademicRecord(
        user_id=document.user_id,
        institution_name=institution_name,
        country=extracted_data.get("country", "Unknown"),
        degree_level=extracted_data.get("degree_level", "bachelors"),
        field_of_study=extracted_data.get("field_of_study"),
        gpa_value=gpa_value,
        gpa_scale=gpa_scale,
        normalized_gpa=normalized_gpa,
        start_year=extracted_data.get("start_year"),
        end_year=extracted_data.get("end_year"),
        source="transcript_extraction",
        notes=f"Extracted from document: {document.original_filename}",
    )
    
    db.add(record)
    logger.info(f"Created academic record for {institution_name}")


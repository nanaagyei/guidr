"""Orchestrator graph nodes — real implementations."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any

from src.pipeline.orchestrator.state import OrchestratorState
from src.pipeline.research_gateway import ResearchGatewayService, ResearchRequest
from src.pipeline.research_gateway.schemas import EntityContext, Constraints

logger = logging.getLogger(__name__)


def _progress(state: dict, step: str) -> dict:
    p = list(state.get("progress", []))
    p.append(step)
    return {"progress": p}


def _get_db():
    from src.db import SessionLocal
    return SessionLocal()


# ------------------------------------------------------------------
# Node: load_context
# ------------------------------------------------------------------

def load_context(state: OrchestratorState) -> dict:
    """Load entity + known_sources from DB. Set need_discovery."""
    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")

    entity_name = state.get("entity_name", "Unknown")
    website_hint = state.get("website_hint")
    known_sources: list[dict] = []

    db = _get_db()
    try:
        # Load entity from DB for name and website
        if entity_id:
            if entity_kind == "school":
                from src.models.institution import Institution
                inst = db.query(Institution).filter(Institution.id == uuid.UUID(entity_id)).first()
                if inst:
                    entity_name = inst.name
                    website_hint = website_hint or inst.website_url
            elif entity_kind == "program":
                from src.models.program import Program
                prog = db.query(Program).filter(Program.id == uuid.UUID(entity_id)).first()
                if prog:
                    entity_name = prog.name
                    if prog.institution:
                        website_hint = website_hint or prog.institution.website_url
            elif entity_kind == "professor":
                from src.models.professor import Professor
                prof = db.query(Professor).filter(Professor.id == uuid.UUID(entity_id)).first()
                if prof:
                    entity_name = prof.full_name
                    website_hint = website_hint or prof.personal_page_url

        # Load known source_documents
        from src.models.source_document import SourceDocument
        if entity_id:
            docs = (
                db.query(SourceDocument)
                .filter(
                    SourceDocument.entity_kind == entity_kind,
                    SourceDocument.entity_id == uuid.UUID(entity_id),
                    SourceDocument.is_active == True,
                )
                .all()
            )
            known_sources = [
                {"url": d.canonical_url, "purpose": d.purpose, "id": str(d.id)}
                for d in docs
            ]
    except Exception as exc:
        logger.warning("load_context DB error: %s", exc)
    finally:
        db.close()

    need = not known_sources and not website_hint
    return {
        "entity_name": entity_name,
        "website_hint": website_hint,
        "known_sources": known_sources,
        "need_discovery": need,
        **_progress(state, "load_context"),
    }


# ------------------------------------------------------------------
# Node: discover_urls
# ------------------------------------------------------------------

def discover_urls(state: OrchestratorState) -> dict:
    """Call Research Gateway URL_DISCOVERY."""
    entity_name = state.get("entity_name", "Unknown")
    category = state.get("category", "SCHOOL_OVERVIEW")
    website_hint = state.get("website_hint")

    req = ResearchRequest(
        job_type="URL_DISCOVERY",
        entity=EntityContext(
            entity_type=state.get("entity_kind", "school").upper(),
            entity_id=state.get("entity_id"),
            name=entity_name,
            website_hint=website_hint,
        ),
        category=category,
        constraints=Constraints(max_results=10),
    )
    service = ResearchGatewayService()
    resp = service.run(req)
    urls = [r.url for r in resp.results]

    # Persist discovered URLs as source_documents
    db = _get_db()
    try:
        from src.models.source_document import SourceDocument, research_provider_label
        entity_id = state.get("entity_id")
        for url_result in resp.results[:5]:
            doc = SourceDocument(
                entity_kind=state.get("entity_kind", "school"),
                entity_id=uuid.UUID(entity_id) if entity_id else None,
                canonical_url=url_result.url,
                purpose=category,
                discovered_by=research_provider_label(url_result.source),
            )
            db.add(doc)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to persist source_documents: %s", exc)
    finally:
        db.close()

    return {
        "candidate_urls": urls,
        "target_url": urls[0] if urls else None,
        **_progress(state, "discover_urls"),
    }


# ------------------------------------------------------------------
# Node: repair_extraction
# ------------------------------------------------------------------

def repair_extraction(state: OrchestratorState) -> dict:
    """Call Research Gateway REPAIR_EXTRACTION for alternate URLs."""
    entity_name = state.get("entity_name", "Unknown")
    category = state.get("category", "SCHOOL_OVERVIEW")
    website_hint = state.get("website_hint")

    req = ResearchRequest(
        job_type="REPAIR_EXTRACTION",
        entity=EntityContext(
            entity_type=state.get("entity_kind", "school").upper(),
            entity_id=state.get("entity_id"),
            name=entity_name,
            website_hint=website_hint,
        ),
        category=category,
    )
    service = ResearchGatewayService()
    resp = service.run(req)
    urls = [r.url for r in resp.results]
    return {
        "candidate_urls": urls,
        "target_url": urls[0] if urls else None,
        "repair": False,
        **_progress(state, "repair_extraction"),
    }


# ------------------------------------------------------------------
# Node: canonicalize_urls
# ------------------------------------------------------------------

def canonicalize_urls(state: OrchestratorState) -> dict:
    """Normalize URLs, pick target. Use candidate_urls or first known_source."""
    candidates = state.get("candidate_urls", [])
    target = state.get("target_url") or (candidates[0] if candidates else None)
    if not target and state.get("known_sources"):
        src = state["known_sources"][0]
        target = src.get("url") or src.get("canonical_url") if isinstance(src, dict) else None
    if not target and state.get("website_hint"):
        target = state["website_hint"]
    return {
        "target_url": target,
        **_progress(state, "canonicalize_urls"),
    }


# ------------------------------------------------------------------
# Node: fetch_page
# ------------------------------------------------------------------

def fetch_page(state: OrchestratorState) -> dict:
    """Fetch URL via EnhancedFirecrawlClient with rate limiting and domain health checks."""
    url = state.get("target_url")
    if not url:
        return {"error": "No target URL", "status": "failed", **_progress(state, "fetch_page")}

    from urllib.parse import urlparse
    from src.pipeline.services.domain_health_service import DomainHealthService
    from src.pipeline.redis_keyspace import take_token_for_url

    host = urlparse(url).netloc
    domain_health = DomainHealthService()

    # Check domain health (Redis circuit breaker + DB block flag)
    if domain_health.is_blocked(host):
        return {
            "error": f"Domain blocked: {host}",
            "status": "failed",
            **_progress(state, "fetch_page"),
        }

    # Apply per-domain token-bucket rate limit
    token_result = take_token_for_url(url)
    if not token_result.allowed:
        logger.warning("Rate limited for %s, adding short delay", url)
        import time
        time.sleep(2)

    # Fetch via Firecrawl
    from src.pipeline.clients import EnhancedFirecrawlClient
    client = EnhancedFirecrawlClient()
    http_status: int = 0

    try:
        data = client.scrape_url(url)
        http_status = data.get("metadata", {}).get("statusCode", 200) if data else 0
    except Exception as exc:
        domain_health.record_error(host, http_status=0)
        logger.error("fetch_page exception for %s: %s", url, exc)
        return {"error": str(exc), "status": "failed", **_progress(state, "fetch_page")}

    if not data or not data.get("markdown"):
        domain_health.record_error(host, http_status=http_status or 0)
        return {
            "error": f"No content from {url} (HTTP {http_status})",
            "status": "failed",
            **_progress(state, "fetch_page"),
        }

    domain_health.record_success(host)

    raw_content = data.get("markdown", "")
    content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    fetched_at = datetime.utcnow().isoformat()

    return {
        "raw_content": raw_content,
        "content_hash": content_hash,
        "fetched_at": fetched_at,
        **_progress(state, "fetch_page"),
    }


# ------------------------------------------------------------------
# Node: store_raw
# ------------------------------------------------------------------

def _ensure_source_document(db, state: dict, url: str):
    """Return the id of the source_documents row for ``url``, creating it if needed."""
    if not url:
        return None
    from src.models.source_document import SourceDocument

    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")
    entity_uuid = uuid.UUID(entity_id) if entity_id else None

    query = db.query(SourceDocument).filter(
        SourceDocument.entity_kind == entity_kind,
        SourceDocument.canonical_url == url,
    )
    query = query.filter(
        SourceDocument.entity_id == entity_uuid if entity_uuid else SourceDocument.entity_id.is_(None)
    )
    doc = query.first()
    now = datetime.utcnow()
    if doc is None:
        doc = SourceDocument(
            entity_kind=entity_kind,
            entity_id=entity_uuid,
            canonical_url=url,
            purpose=state.get("category"),
            # The URL came from the catalog (website_url) or a known source, not a model.
            # `discovered_by` is the `research_provider` enum, so it must be one of its values.
            discovered_by="manual",
        )
        db.add(doc)
    doc.last_crawled_at = now
    doc.last_seen_at = now
    db.flush()
    return doc.id


def store_raw(state: OrchestratorState) -> dict:
    """Store raw content to MinIO and create raw_artifacts row."""
    content = state.get("raw_content")
    if not content:
        return {"error": "No raw content", "status": "failed", **_progress(state, "store_raw")}

    entity_id = state.get("entity_id") or "unknown"
    entity_kind = state.get("entity_kind", "school")
    content_hash = state.get("content_hash") or hashlib.sha256(content.encode()).hexdigest()
    target_url = state.get("target_url", "")

    # Store to MinIO
    from src.pipeline.clients import DataLakeStorageClient
    storage = DataLakeStorageClient()
    storage_key = storage.store_text(
        institution_id=str(entity_id),
        job_type=entity_kind,
        filename=f"{content_hash[:16]}.md",
        text=content,
    )
    storage_uri = f"minio://{storage_key}" if storage_key else f"memory://{content_hash[:16]}"

    # Create (or reuse) the raw_artifacts row, linked to its source_documents row
    artifact_id = None
    source_document_id = None
    db = _get_db()
    try:
        from src.models.raw_artifact import RawArtifact
        source_document_id = _ensure_source_document(db, state, target_url)
        artifact = (
            db.query(RawArtifact).filter(RawArtifact.content_sha256 == content_hash).first()
        )
        if artifact is None:
            artifact = RawArtifact(
                source_document_id=source_document_id,
                fetched_from_url=target_url,
                artifact_type="html",
                content_sha256=content_hash,
                byte_size=len(content.encode("utf-8")),
                storage_uri=storage_uri,
            )
            db.add(artifact)
        elif artifact.source_document_id is None and source_document_id is not None:
            artifact.source_document_id = source_document_id
        db.commit()
        artifact_id = str(artifact.id)
    except Exception as exc:
        db.rollback()
        # Leave artifact_id unset: a made-up id would break the extraction_runs foreign key.
        logger.warning("Failed to create raw_artifact: %s", exc)
    finally:
        db.close()

    return {
        "raw_artifact_id": artifact_id,
        "source_document_id": str(source_document_id) if source_document_id else None,
        **_progress(state, "store_raw"),
    }


# ------------------------------------------------------------------
# Node: extract_structured
# ------------------------------------------------------------------

def _as_dict(item: Any) -> dict:
    if item is None:
        return {}
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json", exclude_none=True)
    return dict(item) if isinstance(item, dict) else {}


def _normalize_extracted(result: Any, entity_kind: str, entity_name: str | None) -> dict:
    """Turn an extractor's output into the single dict this entity's nodes expect.

    The program, faculty and funding extractors return a *list* of records found on the
    page. Enrichment is for one entity, so only the record whose name matches that entity
    is kept. If no record matches, nothing is returned rather than another entity's data.
    """
    if not isinstance(result, list):
        return _as_dict(result)

    items = [d for d in (_as_dict(i) for i in result) if d]
    if not items:
        return {}
    name_key = "full_name" if entity_kind == "professor" else "name"
    target = (entity_name or "").strip().lower()
    if not target or target == "unknown":
        return items[0] if len(items) == 1 else {}
    for item in items:
        if str(item.get(name_key) or "").strip().lower() == target:
            return item
    for item in items:
        name = str(item.get(name_key) or "").strip().lower()
        if name and (name in target or target in name):
            return item
    return {}


def extract_structured(state: OrchestratorState) -> dict:
    """Call the appropriate extractor based on entity_kind/category."""
    content = state.get("raw_content", "")
    entity_kind = state.get("entity_kind", "school")
    category = state.get("category", "SCHOOL_OVERVIEW")
    target_url = state.get("target_url", "")
    entity_name = state.get("entity_name")

    extracted: dict[str, Any] = {}
    update: dict[str, Any] = {}

    try:
        if entity_kind == "funding" or "FUNDING" in category:
            from src.pipeline.extractors import FundingExtractor
            result = FundingExtractor().extract_from_markdown(content, source_url=target_url)
        elif entity_kind == "professor" or "FACULTY" in category:
            from src.pipeline.extractors import FacultyExtractor
            result = FacultyExtractor().extract_from_markdown(content, source_url=target_url)
        elif entity_kind == "program" or "PROGRAM" in category:
            from src.pipeline.extractors import ProgramExtractor
            result = ProgramExtractor().extract_from_markdown(content, source_url=target_url)
        else:
            from src.pipeline.extractors import OverviewExtractor
            result = OverviewExtractor().extract_from_markdown(content)
        extracted = _normalize_extracted(result, entity_kind, entity_name)
    except Exception as exc:
        # No fallback values: page text must never be staged or promoted as a fact.
        logger.error("Extraction failed for %s/%s: %s", entity_kind, category, exc)
        extracted = {}
        update["error"] = f"Extraction failed: {exc}"

    return {"extracted": extracted, **update, **_progress(state, "extract_structured")}


# ------------------------------------------------------------------
# Node: validate_payload
# ------------------------------------------------------------------

def validate_payload(state: OrchestratorState) -> dict:
    """Run DataValidator for the entity type."""
    extracted = state.get("extracted") or {}
    entity_kind = state.get("entity_kind", "school")

    from src.pipeline.processors import DataValidator
    validator = DataValidator()
    result = validator.validate_generic(entity_kind, extracted)

    errors = result.errors if not result.passed else []
    return {
        "validation_errors": errors,
        "validation_warnings": result.warnings,
        "validation_passed": result.passed,
        **_progress(state, "validate"),
    }


# ------------------------------------------------------------------
# Node: score_confidence
# ------------------------------------------------------------------

def score_confidence(state: OrchestratorState) -> dict:
    """Compute confidence using ConfidenceScorer, set promote/repair flags."""
    extracted = state.get("extracted")
    errors = state.get("validation_errors", [])
    entity_kind = state.get("entity_kind", "school")
    target_url = state.get("target_url")
    website_hint = state.get("website_hint")
    fetched_at_str = state.get("fetched_at")

    from src.pipeline.processors import ConfidenceScorer
    from src.pipeline.processors.validator import ValidationResult

    fetched_at = datetime.fromisoformat(fetched_at_str) if fetched_at_str else None
    validation_result = ValidationResult(
        passed=not errors,
        status="failed" if errors else "passed",
        errors=errors,
    )

    scorer = ConfidenceScorer()
    breakdown = scorer.compute_breakdown(
        entity_kind=entity_kind,
        extracted=extracted or {},
        validation_result=validation_result,
        source_url=target_url,
        entity_website=website_hint,
        fetched_at=fetched_at,
    )
    conf = breakdown["overall"]

    promote = scorer.should_promote(conf) and not errors
    # Repair is on-demand only (see confidence_scorer): it runs when an admin/paid trigger
    # set `repair_requested`, the result is not promotable, and attempts remain.
    repair = (
        bool(state.get("repair_requested"))
        and not promote
        and state.get("retry_count", 0) < 2
    )

    return {
        "confidence": conf,
        "confidence_breakdown": breakdown,
        "promote": promote,
        "repair": repair,
        **_progress(state, "score_confidence"),
    }


# ------------------------------------------------------------------
# Helpers: persist validation + confidence to dedicated tables
# ------------------------------------------------------------------

def _write_validation_report(db, extraction_run_id, state, entity_kind, entity_id):
    """Persist a ValidationReport row linked to the extraction run."""
    from src.models.validation_report import ValidationReport
    report = ValidationReport(
        extraction_run_id=extraction_run_id,
        pipeline_job_id=uuid.UUID(state["pipeline_job_id"]) if state.get("pipeline_job_id") else None,
        entity_kind=entity_kind,
        entity_id=uuid.UUID(entity_id) if entity_id else None,
        validator_name="DataValidator",
        passed=state.get("validation_passed", not state.get("validation_errors")),
        overall_score=None,
        errors_json=state.get("validation_errors", []),
        warnings_json=state.get("validation_warnings", []),
    )
    db.add(report)


def _write_confidence_score(db, extraction_run_id, state, entity_kind, entity_id, confidence):
    """Persist a ConfidenceScore row (with its four sub-scores) linked to the extraction run."""
    from src.models.confidence_score import ConfidenceScore
    breakdown = state.get("confidence_breakdown") or {}
    score = ConfidenceScore(
        extraction_run_id=extraction_run_id,
        pipeline_job_id=uuid.UUID(state["pipeline_job_id"]) if state.get("pipeline_job_id") else None,
        entity_kind=entity_kind,
        entity_id=uuid.UUID(entity_id) if entity_id else None,
        overall_confidence=confidence,
        source_score=breakdown.get("source"),
        extraction_score=breakdown.get("extraction"),
        validation_score=breakdown.get("validation"),
        staleness_score=breakdown.get("staleness"),
        weights_json={"source": 0.35, "extraction": 0.35, "validation": 0.25, "staleness": 0.05},
    )
    db.add(score)


# ------------------------------------------------------------------
# Node: stage_write
# ------------------------------------------------------------------

def stage_write(state: OrchestratorState) -> dict:
    """Write to enrichment_cache + create extraction_runs row."""
    extracted = state.get("extracted") or {}
    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")
    confidence = state.get("confidence", 0.0)
    raw_artifact_id = state.get("raw_artifact_id")

    db = _get_db()
    extraction_run_id = None
    try:
        # Create extraction_run
        if raw_artifact_id:
            from src.models.extraction_run import ExtractionRun
            run = ExtractionRun(
                job_id=uuid.UUID(state.get("pipeline_job_id")) if state.get("pipeline_job_id") else None,
                raw_artifact_id=uuid.UUID(raw_artifact_id),
                entity_kind=entity_kind,
                entity_id=uuid.UUID(entity_id) if entity_id else None,
                extractor_name=f"{entity_kind}_extractor",
                extracted_json=extracted,
                confidence=confidence,
                status="validated" if state.get("promote") else "draft",
                validation_json={"errors": state.get("validation_errors", [])},
            )
            db.add(run)
            db.flush()
            extraction_run_id = str(run.id)

            # Persist validation report
            _write_validation_report(db, run.id, state, entity_kind, entity_id)

            # Persist confidence score
            _write_confidence_score(db, run.id, state, entity_kind, entity_id, confidence)

        # Upsert enrichment_cache
        from src.models.enrichment_cache import EnrichmentCache
        from src.services.enrichment_service import FRESHNESS_BUCKETS
        from datetime import timedelta

        freshness_bucket = FRESHNESS_BUCKETS.get(entity_kind, "30d")
        days = int(freshness_bucket.replace("d", "")) if freshness_bucket.endswith("d") else 30
        expires_at = datetime.utcnow() + timedelta(days=days)

        if entity_id:
            existing = (
                db.query(EnrichmentCache)
                .filter(
                    EnrichmentCache.entity_kind == entity_kind,
                    EnrichmentCache.entity_id == uuid.UUID(entity_id),
                    EnrichmentCache.freshness_bucket == freshness_bucket,
                )
                .first()
            )
            if existing:
                existing.value_json = extracted
                existing.confidence = confidence
                existing.computed_at = datetime.utcnow()
                existing.expires_at = expires_at
                if extraction_run_id:
                    existing.source_extraction_run_ids = [uuid.UUID(extraction_run_id)]
            else:
                cache_entry = EnrichmentCache(
                    entity_kind=entity_kind,
                    entity_id=uuid.UUID(entity_id),
                    freshness_bucket=freshness_bucket,
                    value_json=extracted,
                    confidence=confidence,
                    expires_at=expires_at,
                    source_extraction_run_ids=[uuid.UUID(extraction_run_id)] if extraction_run_id else [],
                )
                db.add(cache_entry)

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("stage_write failed: %s", exc)
    finally:
        db.close()

    return {"extraction_run_id": extraction_run_id, **_progress(state, "stage_write")}


# ------------------------------------------------------------------
# Node: promote_write
# ------------------------------------------------------------------

def promote_write(state: OrchestratorState) -> dict:
    """Promote extracted data to production tables and create audit row."""
    extracted = state.get("extracted") or {}
    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")
    extraction_run_id = state.get("extraction_run_id")

    if not entity_id:
        return {"status": "success", **_progress(state, "promote_write")}

    db = _get_db()
    try:
        entity_uuid = uuid.UUID(entity_id)
        diff = {}

        confidence = state.get("confidence", 0.0)
        now = datetime.utcnow()

        if entity_kind == "school":
            from src.models.institution import Institution
            inst = db.query(Institution).get(entity_uuid)
            if inst:
                for field in ["description", "acceptance_rate", "enrollment_total",
                              "grad_enrollment", "campus_setting", "academic_calendar"]:
                    new_val = extracted.get(field)
                    if new_val is not None:
                        old_val = getattr(inst, field, None)
                        if old_val != new_val:
                            diff[field] = {"old": str(old_val), "new": str(new_val)}
                            setattr(inst, field, new_val)
                inst.last_scraped_at = now
                inst.scrape_status = "completed"
                inst.last_enriched_at = now
                inst.last_enrichment_confidence = confidence
                inst.data_version = (inst.data_version or 0) + 1

        elif entity_kind == "program":
            from src.models.program import Program
            prog = db.query(Program).get(entity_uuid)
            if prog:
                for field in ["description", "duration_months", "gre_required",
                              "minimum_gpa", "tuition_estimate_per_year"]:
                    new_val = extracted.get(field)
                    if new_val is not None:
                        old_val = getattr(prog, field, None)
                        if old_val != new_val:
                            diff[field] = {"old": str(old_val), "new": str(new_val)}
                            setattr(prog, field, new_val)
                prog.last_scraped_at = now
                prog.last_enriched_at = now
                prog.last_enrichment_confidence = confidence
                prog.data_version = (prog.data_version or 0) + 1

        elif entity_kind == "professor":
            from src.models.professor import Professor
            prof = db.query(Professor).get(entity_uuid)
            if prof:
                for field in ["title", "email", "research_summary", "is_accepting_students"]:
                    new_val = extracted.get(field)
                    if new_val is not None:
                        old_val = getattr(prof, field, None)
                        if old_val != new_val:
                            diff[field] = {"old": str(old_val), "new": str(new_val)}
                            setattr(prof, field, new_val)
                prof.last_scraped_at = now
                prof.last_enriched_at = now
                prof.last_enrichment_confidence = confidence
                prof.data_version = (prof.data_version or 0) + 1

        elif entity_kind == "funding":
            from src.models.funding_opportunity import FundingOpportunity
            opp = db.query(FundingOpportunity).get(entity_uuid)
            if opp:
                for field in ["name", "description", "amount_min", "amount_max",
                              "deadline", "eligibility_criteria", "covers_tuition", "covers_stipend"]:
                    new_val = extracted.get(field)
                    if new_val is not None:
                        old_val = getattr(opp, field, None)
                        if str(old_val) != str(new_val):
                            diff[field] = {"old": str(old_val), "new": str(new_val)}
                            setattr(opp, field, new_val)
                opp.last_enriched_at = now
                opp.last_enrichment_confidence = confidence
                opp.data_version = (opp.data_version or 0) + 1

        # Create entity_promotions audit row
        if diff and extraction_run_id:
            from src.models.entity_promotion import EntityPromotion
            promotion = EntityPromotion(
                extraction_run_id=uuid.UUID(extraction_run_id),
                entity_kind=entity_kind,
                entity_id=entity_uuid,
                diff_json=diff,
            )
            db.add(promotion)

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("promote_write failed: %s", exc)
    finally:
        db.close()

    return {"status": "success", **_progress(state, "promote_write")}


# ------------------------------------------------------------------
# Node: retry_backoff
# ------------------------------------------------------------------

def retry_backoff(state: OrchestratorState) -> dict:
    """Create a new pipeline_job with incremented attempt + exponential delay."""
    retry_count = state.get("retry_count", 0) + 1
    max_attempts = state.get("max_attempts", 5)

    if retry_count >= max_attempts:
        return {
            "status": "failed",
            "error": "Max retries exceeded",
            "retry_count": retry_count,
            **_progress(state, "retry_backoff"),
        }

    # Create a retry job with delay
    db = _get_db()
    try:
        from src.pipeline.repositories.job_repository import JobRepository
        repo = JobRepository(db)
        delay_seconds = min(30 * (2 ** retry_count), 600)  # 30s to 10min

        repo.create_job(
            job_type="enrichment_retry",
            entity_kind=state.get("entity_kind", "school"),
            entity_id=state.get("entity_id"),
            target_url=state.get("target_url"),
            priority="bulk",
            input_json={
                "retry_count": retry_count,
                "delay_seconds": delay_seconds,
                "parent_job_id": state.get("pipeline_job_id"),
            },
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to create retry job: %s", exc)
    finally:
        db.close()

    return {
        "status": "retrying",
        "retry_count": retry_count,
        **_progress(state, "retry_backoff"),
    }


# ------------------------------------------------------------------
# Node: fail_final
# ------------------------------------------------------------------

def fail_final(state: OrchestratorState) -> dict:
    """Mark job failed."""
    return {"status": "failed", **_progress(state, "fail_final")}

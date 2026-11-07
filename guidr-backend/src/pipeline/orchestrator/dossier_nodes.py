"""Dossier graph nodes for agentic enrichment pipeline."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from src.pipeline.orchestrator.dossier_state import DossierState

logger = logging.getLogger(__name__)

# Fields that carry high-stakes information (deadlines, requirements, funding).
# If citation coverage is below the threshold, these fields are nulled to prevent
# hallucinated data from reaching users.
CRITICAL_FIELDS = [
    "application_deadline",
    "requirements",
    "gre_required",
    "funding_details",
    "funding_links",
    # Nested paths in school dossier JSON (dot-notation)
    "graduate_school.general_deadlines",
    "graduate_school.general_requirements",
    "funding_opportunities",
]

# Citation coverage threshold below which critical fields are nulled
_CRITICAL_COVERAGE_THRESHOLD = 0.30


def canonical_fields(dossier_json: dict, job_type: str) -> dict:
    """Map a dossier's JSON onto the canonical field names scoring and promotion use.

    The school dossier prompt nests institution facts under ``overview`` (and calls
    enrollment ``total_enrollment``), while ``EXPECTED_FIELDS["school"]`` and
    ``promote_write`` use top-level ``description``, ``enrollment_total`` and so on.
    Other dossier types are returned unchanged.
    """
    if job_type != "school_dossier" or not isinstance(dossier_json, dict):
        return dossier_json or {}
    overview = dossier_json.get("overview")
    if not isinstance(overview, dict):
        return dossier_json
    return {
        "description": overview.get("description"),
        "acceptance_rate": overview.get("acceptance_rate"),
        "enrollment_total": overview.get("total_enrollment", overview.get("enrollment_total")),
        "grad_enrollment": overview.get("grad_enrollment"),
        "campus_setting": overview.get("campus_setting"),
        "academic_calendar": overview.get("academic_calendar"),
    }


def _get_db():
    from src.db import SessionLocal
    return SessionLocal()


def _progress(state: dict, step: str) -> dict:
    p = list(state.get("progress", []))
    p.append(step)
    return {"progress": p}


# ------------------------------------------------------------------
# Node: load_dossier_context
# ------------------------------------------------------------------

def load_dossier_context(state: DossierState) -> dict:
    """Load entity context from DB. For recommendation_run, also loads user profile."""
    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")
    job_type = state.get("job_type", "school_dossier")
    user_id = state.get("user_id")

    entity_name = state.get("entity_name", "Unknown")
    website_hint = state.get("website_hint")
    existing_data: dict = {}
    user_profile: dict = {}

    db = _get_db()
    try:
        if entity_id:
            if entity_kind == "school":
                from src.models.institution import Institution
                inst = db.query(Institution).filter(
                    Institution.id == uuid.UUID(entity_id)
                ).first()
                if inst:
                    entity_name = inst.name
                    website_hint = website_hint or inst.website_url
                    existing_data = {
                        "description": inst.description,
                        "acceptance_rate": str(inst.acceptance_rate) if inst.acceptance_rate else None,
                        "enrollment_total": inst.enrollment_total,
                    }

        # Load the minimised profile for recommendation runs. Only fields on the
        # personal-field allow-list are copied (never GPA, citizenship or free text).
        if job_type == "recommendation_run" and user_id:
            from src.models.user_profile import UserProfile
            from src.pipeline.prompts.personal_fields import minimised_profile
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == uuid.UUID(user_id)
            ).first()
            if profile:
                user_profile = minimised_profile(profile)

    except Exception as exc:
        logger.warning("load_dossier_context DB error: %s", exc)
    finally:
        db.close()

    return {
        "entity_name": entity_name,
        "website_hint": website_hint,
        "existing_data": existing_data,
        "user_profile": user_profile,
        **_progress(state, "load_dossier_context"),
    }


# ------------------------------------------------------------------
# Node: research_extract
# ------------------------------------------------------------------

def research_extract(state: DossierState) -> dict:
    """Render prompt via PromptRegistry and call ResearchGateway for dossier extraction."""
    job_type = state.get("job_type", "school_dossier")
    entity_name = state.get("entity_name", "Unknown")
    website_hint = state.get("website_hint", "")
    existing_data = state.get("existing_data", {})
    user_profile = state.get("user_profile", {})

    from src.pipeline.prompts.registry import PromptRegistry
    from src.pipeline.research_gateway import ResearchGatewayService
    from src.pipeline.research_gateway.schemas import (
        ResearchRequest, EntityContext, Budget, CacheConfig,
    )

    # Select prompt template based on job type
    template_map = {
        "school_dossier": "school_dossier",
        "funding_dossier": "funding_dossier",
        "recommendation_run": "recommendation_run",
    }
    template_name = template_map.get(job_type, "school_dossier")

    # Build template variables. Personal fields come only from the allow-list in
    # src/pipeline/prompts/personal_fields.py; consent-gated fields need recorded consent.
    from src.pipeline.prompts.personal_fields import personal_template_vars
    personal_vars = personal_template_vars(
        template_name, user_profile, consented=bool(user_profile.get("ai_research_consent"))
    )
    if job_type == "recommendation_run":
        template_vars = dict(personal_vars)
    elif job_type == "funding_dossier":
        template_vars = {
            "school_name": entity_name,
            "program_name": state.get("program_name", ""),
            "existing_funding": json.dumps(existing_data, default=str),
            **personal_vars,
        }
        # The program's degree level, when known, takes precedence over the applicant's.
        if state.get("degree_level"):
            template_vars["degree_level"] = str(state["degree_level"])
    else:
        template_vars = {
            "school_name": entity_name,
            "school_website": website_hint or "",
            "existing_data": json.dumps(existing_data, default=str),
        }

    # Use variant-aware prompt loading for A/B testing
    variant_seed = state.get("entity_id") or state.get("user_id")
    prompt, prompt_variant = PromptRegistry.render_with_variant(
        template_name, "v1", variant_seed=variant_seed, **template_vars
    )

    # Map job_type to gateway job_type
    gateway_job_type_map = {
        "school_dossier": "DOSSIER_EXTRACTION",
        "funding_dossier": "FUNDING_DOSSIER",
        "recommendation_run": "RECOMMENDATION_RUN",
    }

    req = ResearchRequest(
        job_type=gateway_job_type_map.get(job_type, "DOSSIER_EXTRACTION"),
        entity=EntityContext(
            entity_type=state.get("entity_kind", "school").upper(),
            entity_id=state.get("entity_id"),
            name=entity_name,
            website_hint=website_hint,
        ),
        category=job_type,
        budget=Budget(max_tokens=12000),
        cache=CacheConfig(use_cache=True),
        prompt_override=prompt,
    )

    service = ResearchGatewayService()
    response = service.run(req)

    # DossierResponse
    from src.pipeline.research_gateway.schemas import DossierResponse
    if isinstance(response, DossierResponse):
        return {
            "dossier_json": response.final_json,
            "dossier_citations": [c.model_dump() for c in response.citations],
            "dossier_evidence_map": response.evidence_map,
            "dossier_report": response.report_markdown,
            "dossier_metrics": response.metrics.model_dump(),
            "dossier_errors": response.errors,
            "prompt_version": "v1",
            "prompt_variant": prompt_variant,
            **_progress(state, "research_extract"),
        }

    # Fallback if not a DossierResponse
    return {
        "dossier_json": {},
        "dossier_citations": [],
        "dossier_evidence_map": {},
        "dossier_errors": response.errors if hasattr(response, "errors") else ["Unexpected response type"],
        "prompt_version": "v1",
        "prompt_variant": prompt_variant,
        **_progress(state, "research_extract"),
    }


# ------------------------------------------------------------------
# Node: validate_citations
# ------------------------------------------------------------------

def validate_citations(state: DossierState) -> dict:
    """Check that critical fields have citations. Compute citation_coverage_ratio."""
    dossier_json = state.get("dossier_json", {})
    evidence_map = state.get("dossier_evidence_map", {})
    citations = state.get("dossier_citations", [])

    if not dossier_json:
        return {
            "citation_coverage": 0.0,
            "citation_issues": ["No dossier data extracted"],
            **_progress(state, "validate_citations"),
        }

    # Count total fields and cited fields
    total_fields = 0
    cited_fields = 0
    issues = []

    def count_fields(obj: Any, path: str = "") -> None:
        nonlocal total_fields, cited_fields
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_path = f"{path}.{k}" if path else k
                if isinstance(v, (dict, list)):
                    count_fields(v, full_path)
                elif v is not None and v != "" and v != []:
                    total_fields += 1
                    if full_path in evidence_map:
                        cited_fields += 1
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                count_fields(v, f"{path}[{i}]")

    count_fields(dossier_json)

    coverage = cited_fields / max(total_fields, 1)

    if not citations:
        issues.append("No citations returned by provider")
    if coverage < 0.3:
        issues.append(f"Low citation coverage: {coverage:.0%}")

    # Null out critical fields when coverage is below threshold to prevent
    # hallucinated deadlines, requirements, or funding data reaching users.
    nulled_fields: list[str] = []
    if coverage < _CRITICAL_COVERAGE_THRESHOLD and dossier_json:
        dossier_json = dict(dossier_json)  # shallow copy to avoid mutating shared state
        for field_path in CRITICAL_FIELDS:
            if "." not in field_path:
                if field_path in dossier_json and dossier_json[field_path] is not None:
                    dossier_json[field_path] = None
                    nulled_fields.append(field_path)
            else:
                parent_key, child_key = field_path.split(".", 1)
                parent = dossier_json.get(parent_key)
                if isinstance(parent, dict) and child_key in parent and parent[child_key] is not None:
                    parent = dict(parent)  # copy nested dict
                    parent[child_key] = None
                    dossier_json[parent_key] = parent
                    nulled_fields.append(field_path)

        if nulled_fields:
            issues.append(
                f"Nulled critical fields due to low citation coverage ({coverage:.0%}): {nulled_fields}"
            )
            logger.warning(
                "validate_citations: nulled %d critical field(s) due to coverage=%.2f: %s",
                len(nulled_fields), coverage, nulled_fields,
            )

    result: dict = {
        "citation_coverage": round(coverage, 3),
        "citation_issues": issues,
        **_progress(state, "validate_citations"),
    }
    if nulled_fields:
        result["dossier_json"] = dossier_json
    return result


# ------------------------------------------------------------------
# Node: score_dossier_confidence
# ------------------------------------------------------------------

def score_dossier_confidence(state: DossierState) -> dict:
    """Compute confidence for dossier results using citation-based scoring."""
    dossier_json = state.get("dossier_json", {})
    citation_coverage = state.get("citation_coverage", 0.0)
    citations = state.get("dossier_citations", [])
    errors = state.get("dossier_errors", [])
    entity_kind = state.get("entity_kind", "school")

    if not dossier_json or errors:
        return {
            "confidence": 0.0,
            "promote": False,
            "needs_fallback": True,
            **_progress(state, "score_dossier_confidence"),
        }

    # Citation quality score — use broader trust model from ConfidenceScorer
    from src.pipeline.processors.confidence_scorer import (
        EXPECTED_FIELDS, _AGGREGATOR_DOMAINS, _REPUTABLE_DOMAINS,
        AUTO_PROMOTE_THRESHOLD, STAGE_THRESHOLD,
    )

    citation_score = 0.0
    if citations:
        trusted_count = 0
        for c in citations:
            url = c.get("url", "")
            try:
                from urllib.parse import urlparse
                host = urlparse(url).netloc.lower().removeprefix("www.")
            except Exception:
                host = ""
            if ".edu" in host or ".gov" in host:
                trusted_count += 2  # max weight for official academic sources
            elif any(host == d or host.endswith(f".{d}") for d in _AGGREGATOR_DOMAINS):
                trusted_count += 1.6
            elif any(host == d or host.endswith(f".{d}") for d in _REPUTABLE_DOMAINS):
                trusted_count += 1.0
            else:
                trusted_count += 0.6
        max_score = len(citations) * 2  # if all were .edu
        citation_score = min(1.0, trusted_count / max(max_score, 1))

    # Field completeness. Only school dossiers map onto EXPECTED_FIELDS; other dossier
    # types (funding, recommendations) have their own shapes, so count non-empty keys.
    job_type = state.get("job_type", "school_dossier")
    expected = EXPECTED_FIELDS.get(entity_kind, []) if job_type == "school_dossier" else []
    if expected:
        fields = canonical_fields(dossier_json, job_type)
        populated = sum(1 for f in expected if fields.get(f) not in (None, "", []))
        extraction_score = populated / max(len(expected), 1)
    else:
        non_null = sum(1 for v in dossier_json.values() if v is not None and v != "")
        extraction_score = min(1.0, non_null / max(len(dossier_json), 1))

    # Composite: 40% citation quality, 30% coverage, 30% extraction
    confidence = round(
        0.4 * citation_score + 0.3 * citation_coverage + 0.3 * extraction_score,
        3,
    )
    confidence = min(1.0, max(0.0, confidence))

    # Use centralised thresholds (0.78 promote, 0.55 stage)
    promote = confidence >= AUTO_PROMOTE_THRESHOLD
    needs_fallback = confidence < STAGE_THRESHOLD

    logger.info(
        "Dossier confidence: cite=%.2f cov=%.2f ext=%.2f -> %.3f "
        "(promote=%s [>=%.2f], needs_fallback=%s [<%.2f])",
        citation_score, citation_coverage, extraction_score, confidence,
        promote, AUTO_PROMOTE_THRESHOLD, needs_fallback, STAGE_THRESHOLD,
    )

    return {
        "confidence": confidence,
        "confidence_breakdown": {
            "citation_quality": citation_score,
            "citation_coverage": citation_coverage,
            "extraction": extraction_score,
        },
        "promote": promote,
        "needs_fallback": needs_fallback,
        **_progress(state, "score_dossier_confidence"),
    }


# ------------------------------------------------------------------
# Node: stage_dossier
# ------------------------------------------------------------------

def stage_dossier(state: DossierState) -> dict:
    """Write dossier results to enrichment_cache with citations and evidence_map.

    Cache entries are scoped per-user (user_id is stored on the row).
    """
    dossier_json = state.get("dossier_json", {})
    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")
    user_id = state.get("user_id")
    confidence = state.get("confidence", 0.0)
    job_type = state.get("job_type", "school_dossier")
    citations = state.get("dossier_citations", [])
    evidence_map = state.get("dossier_evidence_map", {})

    # Freshness bucket encodes category
    freshness_buckets = {
        "recommendation_run": "recommendation_run:7d",
        "school_dossier": "school_dossier:30d",
        "professor_matches": "professor_matches:30d",
        "funding_dossier": "funding_dossier:14d",
    }
    freshness_bucket = freshness_buckets.get(job_type, "school_dossier:30d")

    # Parse days from bucket
    days_str = freshness_bucket.split(":")[-1].replace("d", "")
    days = int(days_str) if days_str.isdigit() else 30

    if not entity_id and job_type == "recommendation_run":
        # For recommendations, use user_id as entity_id
        entity_id = state.get("user_id")
        entity_kind = "user"

    db = _get_db()
    raw_artifact_id = None
    extraction_run_id = None
    try:
        from src.models.enrichment_cache import EnrichmentCache

        # Provenance: the research response is the raw artifact, the dossier JSON its
        # extraction run. promote_dossier links its entity_promotions row to this run.
        raw_artifact_id, extraction_run_id = _record_dossier_provenance(
            db, state, entity_kind, entity_id, job_type, dossier_json, citations, evidence_map,
            confidence,
        )

        expires_at = datetime.utcnow() + timedelta(days=days)
        user_uuid = uuid.UUID(user_id) if user_id else None

        if entity_id:
            filter_conditions = [
                EnrichmentCache.entity_kind == entity_kind,
                EnrichmentCache.entity_id == uuid.UUID(entity_id),
                EnrichmentCache.freshness_bucket == freshness_bucket,
            ]
            if user_uuid is not None:
                filter_conditions.append(EnrichmentCache.user_id == user_uuid)
            else:
                filter_conditions.append(EnrichmentCache.user_id.is_(None))

            existing = db.query(EnrichmentCache).filter(*filter_conditions).first()
            if existing:
                existing.value_json = dossier_json
                existing.confidence = confidence
                existing.computed_at = datetime.utcnow()
                existing.expires_at = expires_at
                existing.citations_json = citations
                existing.evidence_map_json = evidence_map
                if extraction_run_id:
                    existing.source_extraction_run_ids = [extraction_run_id]
            else:
                cache_entry = EnrichmentCache(
                    entity_kind=entity_kind,
                    entity_id=uuid.UUID(entity_id),
                    user_id=user_uuid,
                    freshness_bucket=freshness_bucket,
                    value_json=dossier_json,
                    confidence=confidence,
                    expires_at=expires_at,
                    citations_json=citations,
                    evidence_map_json=evidence_map,
                    source_extraction_run_ids=[extraction_run_id] if extraction_run_id else [],
                )
                db.add(cache_entry)

        # Write validation report (citation validation results)
        from src.models.validation_report import ValidationReport
        citation_issues = state.get("citation_issues", [])
        citation_coverage = state.get("citation_coverage", 0.0)
        validation_passed = not citation_issues or citation_coverage >= _CRITICAL_COVERAGE_THRESHOLD

        report = ValidationReport(
            extraction_run_id=extraction_run_id,
            pipeline_job_id=uuid.UUID(state["pipeline_job_id"]) if state.get("pipeline_job_id") else None,
            entity_kind=entity_kind,
            entity_id=uuid.UUID(entity_id) if entity_id else None,
            validator_name="CitationValidator",
            passed=validation_passed,
            overall_score=citation_coverage,
            field_results_json=[],
            warnings_json=citation_issues,
            errors_json=[],
            metadata_json={"job_type": job_type, "citation_count": len(citations)},
        )
        db.add(report)

        # Write confidence score
        from src.models.confidence_score import ConfidenceScore
        breakdown = state.get("confidence_breakdown") or {}
        score_record = ConfidenceScore(
            extraction_run_id=extraction_run_id,
            pipeline_job_id=uuid.UUID(state["pipeline_job_id"]) if state.get("pipeline_job_id") else None,
            entity_kind=entity_kind,
            entity_id=uuid.UUID(entity_id) if entity_id else None,
            overall_confidence=confidence,
            # Dossier sub-scores: source = citation quality, extraction = field completeness,
            # validation = citation coverage, staleness = 1.0 (researched just now).
            source_score=breakdown.get("citation_quality"),
            extraction_score=breakdown.get("extraction"),
            validation_score=citation_coverage,
            staleness_score=1.0,
            weights_json={"citation_quality": 0.4, "citation_coverage": 0.3, "extraction": 0.3},
            details_json={"job_type": job_type, "citation_issues": citation_issues},
        )
        db.add(score_record)

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("stage_dossier failed: %s", exc)
        raw_artifact_id = extraction_run_id = None
    finally:
        db.close()

    return {
        "raw_artifact_id": str(raw_artifact_id) if raw_artifact_id else None,
        "extraction_run_id": str(extraction_run_id) if extraction_run_id else None,
        **_progress(state, "stage_dossier"),
    }


def _record_dossier_provenance(
    db, state, entity_kind, entity_id, job_type, dossier_json, citations, evidence_map, confidence,
):
    """Store the research response as a raw artifact and the dossier as an extraction run.

    Returns:
        ``(raw_artifact_id, extraction_run_id)`` as UUIDs.
    """
    import hashlib

    from src.models.extraction_run import ExtractionRun
    from src.models.raw_artifact import RawArtifact

    payload = json.dumps(
        {"dossier": dossier_json, "citations": citations, "report": state.get("dossier_report")},
        sort_keys=True, default=str,
    )
    content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    artifact = db.query(RawArtifact).filter(RawArtifact.content_sha256 == content_hash).first()
    if artifact is None:
        artifact = RawArtifact(
            id=uuid.uuid4(),
            fetched_from_url=f"research-gateway://{job_type}",
            artifact_type="json",
            content_sha256=content_hash,
            byte_size=len(payload.encode("utf-8")),
            # The response itself is kept in extraction_runs.extracted_json/citations_json.
            storage_uri=f"research-gateway://{job_type}/{content_hash[:16]}",
            content_type="application/json",
        )
        db.add(artifact)
        db.flush()

    run = ExtractionRun(
        id=uuid.uuid4(),
        job_id=uuid.UUID(state["pipeline_job_id"]) if state.get("pipeline_job_id") else None,
        raw_artifact_id=artifact.id,
        entity_kind=entity_kind,
        entity_id=uuid.UUID(entity_id) if entity_id else None,
        extractor_name=f"research_gateway:{job_type}",
        prompt_version=state.get("prompt_version") or "v1",
        prompt_variant=state.get("prompt_variant"),
        extracted_json=dossier_json or {},
        citations_json=citations or [],
        evidence_map_json=evidence_map or {},
        confidence=confidence,
        status="validated" if state.get("promote") else "draft",
        validation_json={"citation_issues": state.get("citation_issues", [])},
    )
    db.add(run)
    db.flush()
    return artifact.id, run.id


# ------------------------------------------------------------------
# Node: fallback_scrape
# ------------------------------------------------------------------

def fallback_scrape(state: DossierState) -> dict:
    """Fallback to existing fetch -> extract -> merge flow when confidence < STAGE_THRESHOLD."""
    from src.config import settings

    if not settings.enable_scrape_fallback:
        return {
            "fallback_used": False,
            **_progress(state, "fallback_scrape"),
        }

    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")
    website_hint = state.get("website_hint")

    if not website_hint:
        return {
            "fallback_used": False,
            "fallback_error": "No website hint for scrape fallback",
            **_progress(state, "fallback_scrape"),
        }

    # Run existing fetch -> extract flow
    from src.pipeline.orchestrator.nodes import (
        fetch_page,
        extract_structured,
    )

    # Build minimal state for existing nodes
    fetch_state = {
        "target_url": website_hint,
        "entity_kind": entity_kind,
        "entity_id": entity_id,
        "progress": state.get("progress", []),
    }
    fetch_result = fetch_page(fetch_state)

    if fetch_result.get("error"):
        return {
            "fallback_used": True,
            "fallback_error": fetch_result["error"],
            **_progress(state, "fallback_scrape"),
        }

    extract_state = {
        **fetch_state,
        **fetch_result,
        "category": state.get("job_type", "SCHOOL_OVERVIEW").upper(),
    }
    extract_result = extract_structured(extract_state)
    scraped_data = extract_result.get("extracted", {})

    # Merge scraped data into dossier_json (scraped fills gaps)
    dossier_json = dict(state.get("dossier_json", {}))
    for key, value in scraped_data.items():
        if value is not None and value != "" and value != []:
            existing = dossier_json.get(key)
            if existing is None or existing == "" or existing == []:
                dossier_json[key] = value

    return {
        "dossier_json": dossier_json,
        "fallback_used": True,
        **_progress(state, "fallback_scrape"),
    }


# ------------------------------------------------------------------
# Node: promote_dossier
# ------------------------------------------------------------------

def promote_dossier(state: DossierState) -> dict:
    """Promote dossier data to canonical tables. Reuses promote_write pattern."""
    dossier_json = state.get("dossier_json", {})
    entity_kind = state.get("entity_kind", "school")
    entity_id = state.get("entity_id")
    confidence = state.get("confidence", 0.0)
    job_type = state.get("job_type", "school_dossier")

    if not entity_id:
        return {"status": "success", **_progress(state, "promote_dossier")}

    # For recommendations, write to recommendation_sessions
    if job_type == "recommendation_run":
        return _promote_recommendations(state)

    # Only school dossiers map onto canonical institution fields. Other dossier types
    # (e.g. funding, which runs against a school entity) have no canonical columns to
    # write, so they stay in enrichment_cache only.
    if job_type != "school_dossier":
        return {"status": "success", **_progress(state, "promote_dossier")}

    from src.pipeline.orchestrator.nodes import promote_write

    promote_state = {
        "extracted": canonical_fields(dossier_json, job_type),
        "entity_kind": entity_kind,
        "entity_id": entity_id,
        "confidence": confidence,
        "extraction_run_id": state.get("extraction_run_id"),
        "progress": state.get("progress", []),
    }
    return promote_write(promote_state)


def _extract_citation_refs(text: str, citations: list[dict]) -> list[dict]:
    """Extract [c1], [c2] markers from text and return matching citation dicts."""
    import re
    refs = re.findall(r"\[c(\d+)\]", str(text))
    valid_ids = {c.get("id") for c in citations}
    matched = []
    seen = set()
    for ref_num in refs:
        cid = f"c{ref_num}"
        if cid in valid_ids and cid not in seen:
            seen.add(cid)
            matched.append(next(c for c in citations if c.get("id") == cid))
    return matched


def _promote_recommendations(state: DossierState) -> dict:
    """Parse AI recommendation JSON into RecommendationResult rows."""
    dossier_json = state.get("dossier_json", {})
    user_id = state.get("user_id")
    citations = state.get("dossier_citations", [])
    pipeline_job_id = state.get("pipeline_job_id")
    session_id = state.get("recommendation_session_id")

    if not user_id:
        return {"status": "failed", "error": "No user_id", **_progress(state, "promote_dossier")}

    db = _get_db()
    try:
        from decimal import Decimal
        from src.models.recommendation_session import RecommendationSession
        from src.models.recommendation_result import RecommendationResult

        # Find pre-created session (from route handler) or create a new one
        session = None
        if session_id:
            session = db.query(RecommendationSession).filter(
                RecommendationSession.id == uuid.UUID(session_id)
            ).first()

        if session:
            session.status = "completed"
            session.algorithm_version = "dossier_v1"
            try:
                session.pipeline_job_id = uuid.UUID(pipeline_job_id) if pipeline_job_id else None
            except (ValueError, AttributeError):
                session.pipeline_job_id = None
            session.citations_json = citations
            session.completed_at = datetime.utcnow()
        else:
            try:
                pj_id = uuid.UUID(pipeline_job_id) if pipeline_job_id else None
            except (ValueError, AttributeError):
                pj_id = None
            session = RecommendationSession(
                user_id=uuid.UUID(user_id),
                trigger_source="dossier_pipeline",
                input_profile_snapshot=state.get("user_profile", {}),
                algorithm_version="dossier_v1",
                status="completed",
                pipeline_job_id=pj_id,
                citations_json=citations,
                completed_at=datetime.utcnow(),
            )
            db.add(session)
            db.flush()

        # Parse AI JSON output into RecommendationResult rows
        recommendations = dossier_json.get("recommendations", [])
        if not recommendations:
            logger.warning("promote_recommendations: no recommendations in dossier_json")

        for rank, rec in enumerate(recommendations, start=1):
            # Handle both "school_name" and "school" keys (stub compat)
            school_name = rec.get("school_name") or rec.get("school") or ""
            program_name = rec.get("program_name") or ""
            score_raw = rec.get("score") or rec.get("fit_score") or 50
            tier = rec.get("tier", "target")
            explanation = rec.get("explanation") or rec.get("reason") or ""

            result = RecommendationResult(
                recommendation_session_id=session.id,
                program_id=None,
                rank=rank,
                score=Decimal(str(min(100, max(0, float(score_raw))))),
                tier=tier if tier in ("dream", "reach", "target", "safety") else "target",
                explanation=explanation,
                reason_features=[],
                school_name=school_name,
                program_name=program_name,
                institution_city=rec.get("institution_city"),
                institution_country=rec.get("institution_country"),
                funding_summary=rec.get("funding_summary"),
                deadline=rec.get("deadline"),
                website_url=rec.get("website_url"),
                citations_json=_extract_citation_refs(explanation, citations),
                evidence_map_json={},
            )
            db.add(result)

        db.commit()
        logger.info(
            "promote_recommendations: wrote %d results for session %s",
            len(recommendations), session.id,
        )
    except Exception as exc:
        db.rollback()
        logger.error("promote_recommendations failed: %s", exc)
        # Mark session as failed if it exists
        if session_id:
            try:
                s = db.query(RecommendationSession).filter(
                    RecommendationSession.id == uuid.UUID(session_id)
                ).first()
                if s:
                    s.status = "failed"
                    s.error_message = str(exc)[:500]
                    db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()

    return {"status": "success", **_progress(state, "promote_dossier")}

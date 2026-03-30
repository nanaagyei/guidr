"""Professor match graph nodes."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from src.pipeline.orchestrator.professor_state import ProfessorMatchState

logger = logging.getLogger(__name__)


def _progress(state: dict, step: str) -> dict:
    p = list(state.get("progress", []))
    p.append(step)
    return {"progress": p}


def _get_db():
    from src.db import SessionLocal
    return SessionLocal()


# ------------------------------------------------------------------
# Node: load_professor_context
# ------------------------------------------------------------------

def load_professor_context(state: ProfessorMatchState) -> dict:
    """Load institution info and user research interests."""
    entity_id = state.get("entity_id")
    user_id = state.get("user_id")

    institution_name = state.get("institution_name", "Unknown")
    department = state.get("department")
    user_interests: list[str] = list(state.get("user_interests", []))

    db = _get_db()
    try:
        if entity_id:
            from src.models.institution import Institution
            inst = db.query(Institution).filter(
                Institution.id == uuid.UUID(entity_id)
            ).first()
            if inst:
                institution_name = inst.name

        # Load user interests from profile
        if user_id and not user_interests:
            from src.models.user_profile import UserProfile
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == uuid.UUID(user_id)
            ).first()
            if profile:
                # research_areas is the most specific signal — use it first
                if profile.research_areas:
                    user_interests.extend(profile.research_areas)
                if profile.primary_field_of_study:
                    user_interests.append(profile.primary_field_of_study)
                if profile.secondary_fields:
                    user_interests.extend(profile.secondary_fields)
                # De-duplicate while preserving order
                seen: set[str] = set()
                user_interests = [
                    x for x in user_interests
                    if x and not (x in seen or seen.add(x))  # type: ignore[func-returns-value]
                ]

    except Exception as exc:
        logger.warning("load_professor_context DB error: %s", exc)
    finally:
        db.close()

    return {
        "institution_name": institution_name,
        "department": department,
        "user_interests": user_interests,
        **_progress(state, "load_professor_context"),
    }


# ------------------------------------------------------------------
# Node: query_openalex
# ------------------------------------------------------------------

def query_openalex(state: ProfessorMatchState) -> dict:
    """Search OpenAlex for authors at the institution matching user interests."""
    institution_name = state.get("institution_name", "Unknown")
    user_interests = state.get("user_interests", [])
    openalex_institution_id = state.get("openalex_institution_id")

    from src.pipeline.clients.openalex import OpenAlexClient
    client = OpenAlexClient()

    candidates = []
    try:
        # Build search query — use up to 5 interests for richer results
        query = " ".join(user_interests[:5]) if user_interests else institution_name

        results = client.search_authors(
            query=query,
            affiliation_id=openalex_institution_id,
            limit=25,
        )

        for author in results:
            candidates.append({
                "openalex_id": author.get("id", ""),
                "name": author.get("display_name", ""),
                "affiliations": [
                    inst.get("display_name", "")
                    for inst in author.get("last_known_institutions", [])
                ],
                "works_count": author.get("works_count", 0),
                "cited_by_count": author.get("cited_by_count", 0),
                "topics": [
                    t.get("display_name", "")
                    for t in (author.get("topics", []) or [])[:5]
                ],
            })
    except Exception as exc:
        logger.error("query_openalex failed: %s", exc)
    finally:
        client.close()

    logger.info("OpenAlex returned %d candidates for %s", len(candidates), institution_name)
    return {
        "openalex_candidates": candidates,
        **_progress(state, "query_openalex"),
    }


# ------------------------------------------------------------------
# Node: enrich_semantic_scholar
# ------------------------------------------------------------------

def enrich_semantic_scholar(state: ProfessorMatchState) -> dict:
    """Enrich candidates with Semantic Scholar data (h-index, recent papers)."""
    candidates = state.get("openalex_candidates", [])

    from src.pipeline.clients.semantic_scholar import SemanticScholarClient
    client = SemanticScholarClient()

    enriched = []
    # Limit to 20 to respect rate limits
    for candidate in candidates[:20]:
        name = candidate.get("name", "")
        enriched_candidate = dict(candidate)

        try:
            # Search by name
            s2_results = client.search_author(name, limit=3)

            # Find best match (by name similarity)
            best_match = None
            for s2_author in s2_results:
                if s2_author.get("name", "").lower() == name.lower():
                    best_match = s2_author
                    break
            if not best_match and s2_results:
                best_match = s2_results[0]

            if best_match:
                s2_id = best_match.get("authorId", "")
                enriched_candidate["semantic_scholar_id"] = s2_id
                enriched_candidate["h_index"] = best_match.get("hIndex", 0)
                enriched_candidate["paper_count"] = best_match.get("paperCount", 0)
                enriched_candidate["citation_count"] = best_match.get("citationCount", 0)

                # Get recent papers
                if s2_id:
                    papers = client.get_author_papers(s2_id, limit=5)
                    enriched_candidate["recent_papers"] = [
                        {
                            "title": p.get("title", ""),
                            "year": p.get("year"),
                            "citation_count": p.get("citationCount", 0),
                        }
                        for p in papers
                    ]
        except Exception as exc:
            logger.debug("S2 enrichment failed for %s: %s", name, exc)

        enriched.append(enriched_candidate)

    client.close()
    logger.info("Enriched %d/%d candidates with S2 data", len(enriched), len(candidates))

    return {
        "enriched_candidates": enriched,
        **_progress(state, "enrich_semantic_scholar"),
    }


# ------------------------------------------------------------------
# Node: synthesize_rank
# ------------------------------------------------------------------

def synthesize_rank(state: ProfessorMatchState) -> dict:
    """Render professor_synthesis prompt and call Perplexity to rank candidates."""
    institution_name = state.get("institution_name", "Unknown")
    department = state.get("department", "")
    user_interests = state.get("user_interests", [])
    candidates = state.get("enriched_candidates", [])

    from src.pipeline.prompts.registry import PromptRegistry
    from src.pipeline.research_gateway import ResearchGatewayService
    from src.pipeline.research_gateway.schemas import (
        ResearchRequest, EntityContext, Budget, CacheConfig,
    )

    prompt = PromptRegistry.render(
        "professor_synthesis", "v1",
        school_name=institution_name,
        department=department or "Not specified",
        user_interests=", ".join(user_interests),
        candidates_json=json.dumps(candidates, indent=2, default=str),
    )

    req = ResearchRequest(
        job_type="PROFESSOR_SYNTHESIS",
        entity=EntityContext(
            entity_type="SCHOOL",
            entity_id=state.get("entity_id"),
            name=institution_name,
        ),
        category="professor_matches",
        budget=Budget(max_tokens=12000),
        cache=CacheConfig(use_cache=True),
        prompt_override=prompt,
    )

    service = ResearchGatewayService()
    response = service.run(req)

    from src.pipeline.research_gateway.schemas import DossierResponse
    if isinstance(response, DossierResponse):
        ranked = response.final_json.get("ranked_professors", [])
        return {
            "ranked_professors": ranked,
            "synthesis_citations": [c.model_dump() for c in response.citations],
            "synthesis_evidence_map": response.evidence_map,
            "confidence": 0.80 if ranked else 0.30,
            **_progress(state, "synthesize_rank"),
        }

    return {
        "ranked_professors": [],
        "synthesis_citations": [],
        "synthesis_evidence_map": {},
        "confidence": 0.0,
        "error": "Synthesis failed",
        **_progress(state, "synthesize_rank"),
    }


# ------------------------------------------------------------------
# Node: stage_professor_matches
# ------------------------------------------------------------------

def stage_professor_matches(state: ProfessorMatchState) -> dict:
    """Write professor matches to enrichment_cache and upsert professors with academic IDs."""
    ranked = state.get("ranked_professors", [])
    entity_id = state.get("entity_id")
    user_id = state.get("user_id")
    confidence = state.get("confidence", 0.0)
    citations = state.get("synthesis_citations", [])
    evidence_map = state.get("synthesis_evidence_map", {})

    freshness_bucket = "professor_matches:30d"

    db = _get_db()
    try:
        # Write to enrichment_cache (per-user)
        from src.models.enrichment_cache import EnrichmentCache

        if entity_id:
            user_uuid = uuid.UUID(user_id) if user_id else None
            filter_conditions = [
                EnrichmentCache.entity_kind == "school",
                EnrichmentCache.entity_id == uuid.UUID(entity_id),
                EnrichmentCache.freshness_bucket == freshness_bucket,
            ]
            if user_uuid is not None:
                filter_conditions.append(EnrichmentCache.user_id == user_uuid)
            else:
                filter_conditions.append(EnrichmentCache.user_id.is_(None))

            existing = db.query(EnrichmentCache).filter(*filter_conditions).first()

            cache_data = {"ranked_professors": ranked}
            expires_at = datetime.utcnow() + timedelta(days=30)

            if existing:
                existing.value_json = cache_data
                existing.confidence = confidence
                existing.computed_at = datetime.utcnow()
                existing.expires_at = expires_at
                existing.citations_json = citations
                existing.evidence_map_json = evidence_map
            else:
                cache_entry = EnrichmentCache(
                    entity_kind="school",
                    entity_id=uuid.UUID(entity_id),
                    user_id=user_uuid,
                    freshness_bucket=freshness_bucket,
                    value_json=cache_data,
                    confidence=confidence,
                    expires_at=expires_at,
                    citations_json=citations,
                    evidence_map_json=evidence_map,
                    source_extraction_run_ids=[],
                )
                db.add(cache_entry)

        # Upsert professors with academic IDs
        from src.models.professor import Professor
        for prof_data in ranked:
            openalex_id = prof_data.get("openalex_id")
            s2_id = prof_data.get("semantic_scholar_id")
            name = prof_data.get("name", "")

            if not name or not entity_id:
                continue

            # Try to find existing professor
            existing_prof = None
            if openalex_id:
                existing_prof = db.query(Professor).filter(
                    Professor.openalex_id == openalex_id
                ).first()
            if not existing_prof and s2_id:
                existing_prof = db.query(Professor).filter(
                    Professor.semantic_scholar_id == s2_id
                ).first()
            if not existing_prof:
                existing_prof = db.query(Professor).filter(
                    Professor.full_name == name,
                    Professor.institution_id == uuid.UUID(entity_id),
                ).first()

            if existing_prof:
                if openalex_id:
                    existing_prof.openalex_id = openalex_id
                if s2_id:
                    existing_prof.semantic_scholar_id = s2_id
                if prof_data.get("title"):
                    existing_prof.title = prof_data["title"]
                if prof_data.get("research_summary"):
                    existing_prof.research_summary = prof_data["research_summary"]
                if prof_data.get("email"):
                    existing_prof.email = prof_data["email"]
                if prof_data.get("personal_page_url"):
                    existing_prof.personal_page_url = prof_data["personal_page_url"]
                existing_prof.last_enriched_at = datetime.utcnow()
                existing_prof.last_enrichment_confidence = confidence
                existing_prof.data_version = (existing_prof.data_version or 0) + 1
            # Don't create new professors from synthesis alone — only update existing

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("stage_professor_matches failed: %s", exc)
    finally:
        db.close()

    return {**_progress(state, "stage_professor_matches")}


# ------------------------------------------------------------------
# Node: promote_professor_matches
# ------------------------------------------------------------------

def promote_professor_matches(state: ProfessorMatchState) -> dict:
    """Create/update professor rows in canonical table."""
    ranked = state.get("ranked_professors", [])
    entity_id = state.get("entity_id")
    confidence = state.get("confidence", 0.0)

    if not entity_id or not ranked:
        return {"status": "success", **_progress(state, "promote_professor_matches")}

    db = _get_db()
    try:
        from src.models.professor import Professor

        for prof_data in ranked:
            name = prof_data.get("name", "")
            if not name:
                continue

            # Check if professor already exists
            existing = db.query(Professor).filter(
                Professor.full_name == name,
                Professor.institution_id == uuid.UUID(entity_id),
            ).first()

            if not existing:
                # Create new professor
                new_prof = Professor(
                    institution_id=uuid.UUID(entity_id),
                    full_name=name,
                    title=prof_data.get("title"),
                    email=prof_data.get("email"),
                    personal_page_url=prof_data.get("personal_page_url"),
                    openalex_id=prof_data.get("openalex_id"),
                    semantic_scholar_id=prof_data.get("semantic_scholar_id"),
                    research_summary=prof_data.get("research_summary"),
                    interests_tags=prof_data.get("key_papers", []),
                    is_accepting_students=prof_data.get("is_likely_accepting"),
                    last_enriched_at=datetime.utcnow(),
                    last_enrichment_confidence=confidence,
                    data_version=1,
                )
                db.add(new_prof)

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("promote_professor_matches failed: %s", exc)
    finally:
        db.close()

    return {"status": "success", **_progress(state, "promote_professor_matches")}

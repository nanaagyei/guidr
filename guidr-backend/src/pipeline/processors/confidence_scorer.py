"""Confidence scorer for pipeline extraction results.

Formula: 0.35 * source + 0.35 * extraction + 0.25 * validation + 0.05 * staleness

Thresholds:
  >= 0.85 -> auto-promote to production tables
  0.70-0.84 -> stage in enrichment_cache, schedule re-check
  < 0.70 -> trigger repair flow or flag for manual review
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from src.pipeline.processors.validator import ValidationResult

logger = logging.getLogger(__name__)

# Weights
W_SOURCE = 0.35
W_EXTRACTION = 0.35
W_VALIDATION = 0.25
W_STALENESS = 0.05

# Thresholds
AUTO_PROMOTE_THRESHOLD = 0.85
STAGE_THRESHOLD = 0.70

# Expected field counts per entity kind
EXPECTED_FIELDS: Dict[str, list[str]] = {
    "school": [
        "description", "acceptance_rate", "enrollment_total",
        "grad_enrollment", "campus_setting", "academic_calendar",
    ],
    "program": [
        "name", "degree_level", "field_of_study", "description",
        "duration_months", "application_deadline_primary",
        "tuition_estimate_per_year", "gre_required",
    ],
    "professor": [
        "full_name", "title", "email", "research_summary",
        "interests_tags", "is_accepting_students",
    ],
    "funding": [
        "name", "funding_type", "amount_min", "amount_max",
        "deadline", "eligibility_criteria", "description",
    ],
}


class ConfidenceScorer:
    """Computes a composite confidence score for extracted data."""

    def compute(
        self,
        entity_kind: str,
        extracted: Dict[str, Any],
        validation_result: Optional[ValidationResult] = None,
        source_url: Optional[str] = None,
        entity_website: Optional[str] = None,
        fetched_at: Optional[datetime] = None,
    ) -> float:
        """Compute confidence score (0.0 - 1.0).

        Args:
            entity_kind: school, program, professor, funding
            extracted: The extracted data dict.
            validation_result: Result of DataValidator.
            source_url: URL data was fetched from.
            entity_website: Official website of the entity.
            fetched_at: When the raw content was fetched.

        Returns:
            Composite confidence float between 0.0 and 1.0.
        """
        s_source = self.score_source(source_url, entity_website)
        s_extraction = self.score_extraction(extracted, entity_kind)
        s_validation = self.score_validation(validation_result)
        s_staleness = self.score_staleness(fetched_at)

        composite = (
            W_SOURCE * s_source
            + W_EXTRACTION * s_extraction
            + W_VALIDATION * s_validation
            + W_STALENESS * s_staleness
        )
        composite = round(min(1.0, max(0.0, composite)), 3)

        logger.debug(
            "Confidence for %s: source=%.2f ext=%.2f val=%.2f stale=%.2f -> %.3f",
            entity_kind, s_source, s_extraction, s_validation, s_staleness, composite,
        )
        return composite

    def should_promote(self, confidence: float) -> bool:
        """Whether the confidence is high enough for auto-promotion."""
        return confidence >= AUTO_PROMOTE_THRESHOLD

    def should_stage(self, confidence: float) -> bool:
        """Whether data should be staged (not promoted but not rejected)."""
        return STAGE_THRESHOLD <= confidence < AUTO_PROMOTE_THRESHOLD

    def should_repair(self, confidence: float) -> bool:
        """Whether a repair flow should be triggered."""
        return confidence < STAGE_THRESHOLD

    @staticmethod
    def score_source(source_url: Optional[str], entity_website: Optional[str]) -> float:
        """Score how trustworthy the source URL is.

        1.0 = source is on the entity's official domain
        0.7 = source is .edu or .gov
        0.4 = other domain
        0.0 = no URL
        """
        if not source_url:
            return 0.0

        try:
            source_host = urlparse(source_url).netloc.lower()
        except Exception:
            return 0.2

        # Check if same domain as entity
        if entity_website:
            try:
                entity_host = urlparse(
                    entity_website if "://" in entity_website else f"https://{entity_website}"
                ).netloc.lower()
                # Strip www. for comparison
                source_clean = source_host.replace("www.", "")
                entity_clean = entity_host.replace("www.", "")
                if source_clean == entity_clean or source_clean.endswith(f".{entity_clean}"):
                    return 1.0
            except Exception:
                pass

        # Trust .edu and .gov domains
        if source_host.endswith(".edu") or source_host.endswith(".gov"):
            return 0.7

        return 0.4

    @staticmethod
    def score_extraction(extracted: Optional[Dict[str, Any]], entity_kind: str) -> float:
        """Score field completeness of extracted data.

        Returns ratio of populated expected fields.
        """
        if not extracted:
            return 0.0

        expected = EXPECTED_FIELDS.get(entity_kind, [])
        if not expected:
            # Unknown kind — count any non-None fields as partial success
            populated = sum(1 for v in extracted.values() if v is not None and v != "")
            return min(1.0, populated / max(len(extracted), 1))

        populated = 0
        for field_name in expected:
            val = extracted.get(field_name)
            if val is not None and val != "" and val != []:
                populated += 1

        return populated / len(expected)

    @staticmethod
    def score_validation(validation_result: Optional[ValidationResult]) -> float:
        """Score based on validation outcome.

        1.0 = passed with no warnings
        0.8 = passed with warnings
        0.3 = failed (some checks passed)
        0.0 = no validation result
        """
        if validation_result is None:
            return 0.0

        if validation_result.passed and not validation_result.warnings:
            return 1.0
        if validation_result.passed:
            return 0.8
        # Failed: partial credit based on error count
        error_count = len(validation_result.errors)
        if error_count <= 1:
            return 0.3
        return 0.1

    @staticmethod
    def score_staleness(fetched_at: Optional[datetime]) -> float:
        """Score freshness — decays over time.

        1.0 = fetched within 24 hours
        0.8 = within 7 days
        0.5 = within 30 days
        0.2 = older than 30 days
        0.0 = no fetch time
        """
        if fetched_at is None:
            return 0.0

        age = datetime.utcnow() - fetched_at
        if age <= timedelta(hours=24):
            return 1.0
        if age <= timedelta(days=7):
            return 0.8
        if age <= timedelta(days=30):
            return 0.5
        return 0.2

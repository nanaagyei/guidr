"""Unit tests for ConfidenceScorer: source, extraction, validation, staleness scoring."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List


class TestConfidenceScorer:
    """Tests for ConfidenceScorer scoring methods and thresholds."""

    def _make_scorer(self):
        from src.pipeline.processors.confidence_scorer import ConfidenceScorer
        return ConfidenceScorer()

    def _make_validation_result(self, passed, errors=None, warnings=None, status=None):
        from src.pipeline.processors.validator import ValidationResult
        return ValidationResult(
            passed=passed,
            status=status or ("passed" if passed else "failed"),
            errors=errors or [],
            warnings=warnings or [],
        )

    # ── compute() ──────────────────────────────────────────────────────

    def test_compute_all_perfect_returns_high_confidence(self):
        scorer = self._make_scorer()
        vr = self._make_validation_result(passed=True)
        extracted = {
            "description": "A great school",
            "acceptance_rate": 0.15,
            "enrollment_total": 11000,
            "grad_enrollment": 6000,
            "campus_setting": "City",
            "academic_calendar": "Semester",
        }
        now = datetime.utcnow()

        result = scorer.compute(
            entity_kind="school",
            extracted=extracted,
            validation_result=vr,
            source_url="https://mit.edu/about",
            entity_website="mit.edu",
            fetched_at=now,
        )

        # source=1.0, extraction=1.0, validation=1.0, staleness=1.0
        # 0.35*1 + 0.35*1 + 0.25*1 + 0.05*1 = 1.0
        assert result == 1.0

    def test_compute_no_inputs_returns_zero(self):
        scorer = self._make_scorer()

        result = scorer.compute(
            entity_kind="school",
            extracted={},
            validation_result=None,
            source_url=None,
            entity_website=None,
            fetched_at=None,
        )

        # source=0, extraction=0, validation=0, staleness=0
        assert result == 0.0

    # ── score_source() ─────────────────────────────────────────────────

    def test_score_source_same_domain(self):
        scorer = self._make_scorer()
        result = scorer.score_source("https://mit.edu/page", "mit.edu")
        assert result == 1.0

    def test_score_source_edu_domain(self):
        scorer = self._make_scorer()
        result = scorer.score_source("https://harvard.edu/info", "stanford.edu")
        assert result == 0.7

    def test_score_source_aggregator_domain(self):
        scorer = self._make_scorer()
        result = scorer.score_source("https://usnews.com/best-grad-schools/mit", "mit.edu")
        assert result == 0.8

    def test_score_source_reputable_domain(self):
        scorer = self._make_scorer()
        result = scorer.score_source("https://wikipedia.org/wiki/MIT", "mit.edu")
        assert result == 0.5

    def test_score_source_other_domain(self):
        scorer = self._make_scorer()
        result = scorer.score_source("https://example.com/page", "mit.edu")
        assert result == 0.3

    def test_score_source_none(self):
        scorer = self._make_scorer()
        result = scorer.score_source(None, "mit.edu")
        assert result == 0.0

    # ── score_extraction() ─────────────────────────────────────────────

    def test_score_extraction_all_fields(self):
        scorer = self._make_scorer()
        extracted = {
            "description": "Desc",
            "acceptance_rate": 0.15,
            "enrollment_total": 11000,
            "grad_enrollment": 6000,
            "campus_setting": "City",
            "academic_calendar": "Semester",
        }
        result = scorer.score_extraction(extracted, "school")
        assert result == 1.0

    def test_score_extraction_half_fields(self):
        scorer = self._make_scorer()
        extracted = {
            "description": "Desc",
            "acceptance_rate": 0.15,
            "enrollment_total": 11000,
        }
        result = scorer.score_extraction(extracted, "school")
        assert result == 0.5

    def test_score_extraction_empty(self):
        scorer = self._make_scorer()
        result = scorer.score_extraction({}, "school")
        assert result == 0.0

    # ── score_validation() ─────────────────────────────────────────────

    def test_score_validation_passed_clean(self):
        scorer = self._make_scorer()
        vr = self._make_validation_result(passed=True)
        result = scorer.score_validation(vr)
        assert result == 1.0

    def test_score_validation_passed_with_warnings(self):
        scorer = self._make_scorer()
        vr = self._make_validation_result(passed=True, warnings=["minor issue"])
        result = scorer.score_validation(vr)
        assert result == 0.8

    def test_score_validation_failed(self):
        scorer = self._make_scorer()
        vr = self._make_validation_result(passed=False, errors=["bad field"])
        result = scorer.score_validation(vr)
        assert result == 0.3

    def test_score_validation_failed_multiple_errors(self):
        scorer = self._make_scorer()
        vr = self._make_validation_result(
            passed=False, errors=["bad field", "missing field"]
        )
        result = scorer.score_validation(vr)
        assert result == 0.1

    # ── score_staleness() ──────────────────────────────────────────────

    @patch("src.pipeline.processors.confidence_scorer.datetime")
    def test_score_staleness_fresh(self, mock_dt):
        scorer = self._make_scorer()
        now = datetime(2026, 3, 4, 12, 0, 0)
        mock_dt.utcnow.return_value = now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        fetched_at = now - timedelta(hours=1)
        result = scorer.score_staleness(fetched_at)
        assert result == 1.0

    @patch("src.pipeline.processors.confidence_scorer.datetime")
    def test_score_staleness_week(self, mock_dt):
        scorer = self._make_scorer()
        now = datetime(2026, 3, 4, 12, 0, 0)
        mock_dt.utcnow.return_value = now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        fetched_at = now - timedelta(days=3)
        result = scorer.score_staleness(fetched_at)
        assert result == 0.8

    # ── should_promote / should_stage / should_warn ────────────────────

    def test_should_promote_boundary(self):
        scorer = self._make_scorer()
        # New threshold: 0.78 (was 0.85)
        assert scorer.should_promote(0.78) is True
        assert scorer.should_promote(0.779) is False

    def test_should_stage_boundary(self):
        scorer = self._make_scorer()
        # Stage range: 0.55–0.77; below 0.55 is stage-with-warning
        assert scorer.should_promote(0.77) is False
        assert scorer.should_warn(0.54) is True
        assert scorer.should_warn(0.55) is False

    def test_should_warn_replaces_repair(self):
        scorer = self._make_scorer()
        # should_warn fires below 0.55 — no auto-repair
        assert scorer.should_warn(0.40) is True
        assert scorer.should_warn(0.55) is False
        # should_repair should no longer exist or always return False
        assert not hasattr(scorer, 'should_repair') or scorer.should_repair(0.40) is False

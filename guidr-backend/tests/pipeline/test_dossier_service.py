"""Unit tests for DossierService: cache hit, quota, dedup, dispatch paths."""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta
from decimal import Decimal
import uuid


class TestDossierService:
    """Tests for DossierService."""

    def _make_service(self, mock_db=None):
        if mock_db is None:
            mock_db = MagicMock()
        with patch("src.services.dossier_service.JobRepository"):
            from src.services.dossier_service import DossierService
            return DossierService(mock_db)

    @patch("src.services.dossier_service.check_and_increment_quota")
    def test_cache_hit_returns_cached(self, mock_quota):
        mock_db = MagicMock()
        service = self._make_service(mock_db)

        # Mock cache entry
        mock_cache = MagicMock()
        mock_cache.expires_at = datetime.utcnow() + timedelta(days=10)
        mock_cache.confidence = Decimal("0.85")
        mock_cache.value_json = {"name": "MIT"}
        mock_cache.hit_count = 5
        mock_cache.last_hit_at = None
        mock_cache.citations_json = []
        mock_cache.evidence_map_json = {}

        mock_db.query.return_value.filter.return_value.first.return_value = mock_cache

        result = service.request_school_dossier(
            school_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
        )

        assert result.status == "cache_hit"
        assert result.cache_entry is mock_cache
        assert mock_cache.hit_count == 6  # Bumped

    @patch("src.services.dossier_service.check_and_increment_quota")
    def test_quota_exceeded(self, mock_quota):
        mock_db = MagicMock()
        service = self._make_service(mock_db)

        # No cache
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Quota exceeded
        mock_quota.return_value = MagicMock(allowed=False, limit=10)

        result = service.request_school_dossier(
            school_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
        )

        assert result.status == "quota_exceeded"
        assert "limit reached" in result.message

    @patch("src.services.dossier_service.check_and_increment_quota")
    def test_dedup_in_progress(self, mock_quota):
        mock_db = MagicMock()
        service = self._make_service(mock_db)

        # No cache
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Quota OK
        mock_quota.return_value = MagicMock(allowed=True)

        # Existing in-progress job
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.find_in_progress.return_value = mock_job

        result = service.request_school_dossier(
            school_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
        )

        assert result.status == "dedup_in_progress"
        assert result.job is mock_job

    @patch("src.services.dossier_service.check_and_increment_quota")
    def test_enqueues_new_job(self, mock_quota):
        mock_db = MagicMock()
        service = self._make_service(mock_db)

        # No cache
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Quota OK
        mock_quota.return_value = MagicMock(allowed=True)

        # No existing job
        service.repo.find_in_progress.return_value = None

        # Create job
        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.create_job.return_value = mock_job

        with patch.object(service, "_dispatch"):
            result = service.request_school_dossier(
                school_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
            )

        assert result.status == "enqueued"
        assert result.job is mock_job

    @patch("src.services.dossier_service.check_and_increment_quota")
    def test_force_refresh_skips_cache(self, mock_quota):
        mock_db = MagicMock()
        service = self._make_service(mock_db)

        # Cache exists but should be skipped
        mock_cache = MagicMock()
        mock_cache.expires_at = datetime.utcnow() + timedelta(days=10)

        mock_quota.return_value = MagicMock(allowed=True)
        service.repo.find_in_progress.return_value = None

        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.create_job.return_value = mock_job

        with patch.object(service, "_dispatch"):
            result = service.request_school_dossier(
                school_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                force=True,
            )

        assert result.status == "enqueued"

    @patch("src.services.dossier_service.check_and_increment_quota")
    def test_professor_match_dispatches_correctly(self, mock_quota):
        mock_db = MagicMock()
        service = self._make_service(mock_db)

        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_quota.return_value = MagicMock(allowed=True)
        service.repo.find_in_progress.return_value = None

        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.create_job.return_value = mock_job

        with patch.object(service, "_dispatch") as mock_dispatch:
            result = service.request_professor_matches(
                school_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                research_interests=["ML", "NLP"],
            )

        assert result.status == "enqueued"
        mock_dispatch.assert_called_once_with(mock_job, "professor_match")

    @patch("src.services.dossier_service.check_and_increment_quota")
    def test_recommendation_request(self, mock_quota):
        mock_db = MagicMock()
        service = self._make_service(mock_db)

        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_quota.return_value = MagicMock(allowed=True)
        service.repo.find_in_progress.return_value = None

        mock_job = MagicMock()
        mock_job.id = uuid.uuid4()
        service.repo.create_job.return_value = mock_job

        with patch.object(service, "_dispatch"):
            result = service.request_recommendations(
                user_id=str(uuid.uuid4()),
                trigger_source="dashboard_button",
            )

        assert result.status == "enqueued"

"""Unit tests for JobRepository: create, find, claim, complete, cancel, requeue."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid


class TestJobRepository:
    """Tests for JobRepository with mocked DB session and fingerprint."""

    def _make_repo(self, mock_db=None):
        if mock_db is None:
            mock_db = MagicMock()
        from src.pipeline.repositories.job_repository import JobRepository
        return JobRepository(mock_db)

    # ── create_job ─────────────────────────────────────────────────────

    def test_create_job_computes_fingerprint_and_flushes(self):
        from src.pipeline.repositories import job_repository as mod

        with patch.object(mod, "compute_job_fingerprint", return_value=("abc123", "input")) as mock_fp:
            mock_db = MagicMock()
            repo = self._make_repo(mock_db)

            job = repo.create_job(
                job_type="enrichment",
                entity_kind="school",
                entity_id=str(uuid.uuid4()),
            )

            mock_fp.assert_called_once()
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()

    def test_create_job_sets_correct_fields(self):
        from src.pipeline.repositories import job_repository as mod

        with patch.object(mod, "compute_job_fingerprint", return_value=("abc123", "input")) as mock_fp:
            mock_db = MagicMock()
            repo = self._make_repo(mock_db)

            entity_id = str(uuid.uuid4())
            job = repo.create_job(
                job_type="enrichment",
                entity_kind="school",
                entity_id=entity_id,
                priority="low",
                schema_version="v2",
                freshness_bucket="14d",
                max_attempts=3,
                input_json={"key": "val"},
            )

            assert job.job_type == "enrichment"
            assert job.entity_kind == "school"
            assert job.priority == "low"
            assert job.schema_version == "v2"
            assert job.freshness_bucket == "14d"
            assert job.fingerprint == "abc123"
            assert job.max_attempts == 3
            assert job.input_json == {"key": "val"}
            assert job.status == "queued"

    # ── find_recent_success ────────────────────────────────────────────

    def test_find_recent_success_matches_fingerprint(self):
        from src.pipeline.repositories import job_repository as mod

        with patch.object(mod, "compute_job_fingerprint", return_value=("abc123", "input")) as mock_fp:
            mock_db = MagicMock()
            repo = self._make_repo(mock_db)

            mock_job = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_job

            result = repo.find_recent_success(
                job_type="enrichment",
                entity_kind="school",
                entity_id=str(uuid.uuid4()),
            )

            assert result is mock_job
            mock_fp.assert_called()

    def test_find_recent_success_respects_window(self):
        from src.pipeline.repositories import job_repository as mod

        with patch.object(mod, "compute_job_fingerprint", return_value=("abc123", "input")) as mock_fp:
            mock_db = MagicMock()
            repo = self._make_repo(mock_db)

            mock_db.query.return_value.filter.return_value.first.return_value = None

            result = repo.find_recent_success(
                job_type="enrichment",
                entity_kind="school",
                window_hours=1,
            )

            assert result is None

    # ── find_in_progress ───────────────────────────────────────────────

    def test_find_in_progress_filters_queued_running(self):
        from src.pipeline.repositories import job_repository as mod

        with patch.object(mod, "compute_job_fingerprint", return_value=("abc123", "input")) as mock_fp:
            mock_db = MagicMock()
            repo = self._make_repo(mock_db)

            mock_job = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_job

            result = repo.find_in_progress(
                job_type="enrichment",
                entity_kind="school",
                entity_id=str(uuid.uuid4()),
            )

            assert result is mock_job

    def test_find_in_progress_uses_default_bucket(self):
        from src.pipeline.repositories import job_repository as mod

        with patch.object(mod, "compute_job_fingerprint", return_value=("abc123", "input")) as mock_fp:
            mock_db = MagicMock()
            repo = self._make_repo(mock_db)

            repo.find_in_progress(
                job_type="enrichment",
                entity_kind="school",
            )

            # Verify fingerprint called with default bucket
            call_kwargs = mock_fp.call_args[1]
            assert call_kwargs["freshness_bucket"] == "default"

    # ── claim_job ──────────────────────────────────────────────────────

    def test_claim_job_updates_status(self):
        mock_db = MagicMock()
        repo = self._make_repo(mock_db)

        job_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_db.query.return_value.filter.return_value.update.return_value = 1
        mock_db.query.return_value.get.return_value = mock_job

        result = repo.claim_job(job_id, run_by="worker-1")

        assert result is mock_job
        mock_db.flush.assert_called()

    def test_claim_job_already_claimed_returns_none(self):
        mock_db = MagicMock()
        repo = self._make_repo(mock_db)

        job_id = str(uuid.uuid4())
        mock_db.query.return_value.filter.return_value.update.return_value = 0

        result = repo.claim_job(job_id, run_by="worker-1")

        assert result is None

    # ── complete_job ───────────────────────────────────────────────────

    def test_complete_job_sets_finished_at(self):
        mock_db = MagicMock()
        repo = self._make_repo(mock_db)

        job_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_db.query.return_value.get.return_value = mock_job

        result = repo.complete_job(
            job_id,
            status="succeeded",
            output_json={"result": "ok"},
            metrics_json={"duration_ms": 150},
        )

        assert result is mock_job
        assert mock_job.status == "succeeded"
        assert mock_job.finished_at is not None
        assert mock_job.output_json == {"result": "ok"}
        assert mock_job.metrics_json == {"duration_ms": 150}
        mock_db.flush.assert_called()

    def test_complete_job_missing_raises_value_error(self):
        mock_db = MagicMock()
        repo = self._make_repo(mock_db)

        mock_db.query.return_value.get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            repo.complete_job(str(uuid.uuid4()))

    # ── cancel_job ─────────────────────────────────────────────────────

    def test_cancel_job_only_queued(self):
        mock_db = MagicMock()
        repo = self._make_repo(mock_db)

        # 1 row updated = success (was queued)
        mock_db.query.return_value.filter.return_value.update.return_value = 1

        result = repo.cancel_job(str(uuid.uuid4()))
        assert result is True

        # 0 rows = not queued, can't cancel
        mock_db.query.return_value.filter.return_value.update.return_value = 0
        result = repo.cancel_job(str(uuid.uuid4()))
        assert result is False

    # ── requeue_job ────────────────────────────────────────────────────

    def test_requeue_job_respects_max_attempts(self):
        mock_db = MagicMock()
        repo = self._make_repo(mock_db)

        # Job at max attempts
        mock_job = MagicMock()
        mock_job.status = "failed"
        mock_job.attempt = 5
        mock_job.max_attempts = 5
        mock_db.query.return_value.get.return_value = mock_job

        result = repo.requeue_job(str(uuid.uuid4()))
        assert result is None

        # Job under max attempts
        mock_job.attempt = 2
        mock_job.max_attempts = 5
        result = repo.requeue_job(str(uuid.uuid4()))
        assert result is mock_job
        assert mock_job.status == "queued"

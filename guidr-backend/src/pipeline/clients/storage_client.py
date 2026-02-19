"""MinIO / S3 storage client for the pipeline raw data lake.

Separate from the existing R2 storage service (src/services/storage.py)
which handles user document uploads. This client stores raw scraped HTML,
markdown, and intermediate pipeline artifacts.
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.config import settings

logger = logging.getLogger(__name__)


class DataLakeStorageClient:
    """Store and retrieve raw pipeline data in MinIO or S3."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        """Lazy-init the minio client."""
        if self._client is not None:
            return self._client

        try:
            from minio import Minio

            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            # Ensure bucket exists
            if not self._client.bucket_exists(settings.minio_bucket):
                self._client.make_bucket(settings.minio_bucket)
                logger.info("Created MinIO bucket: %s", settings.minio_bucket)
        except Exception as exc:
            logger.warning("MinIO unavailable, storage disabled: %s", exc)
            self._client = None

        return self._client

    def _build_key(self, institution_id: str, job_type: str, suffix: str) -> str:
        """Build an object key for the data lake.

        Format: raw/{YYYY}/{MM}/{DD}/{institution_id}/{job_type}/{suffix}
        """
        now = datetime.utcnow()
        return (
            f"raw/{now.year}/{now.month:02d}/{now.day:02d}"
            f"/{institution_id}/{job_type}/{suffix}"
        )

    def store_json(
        self,
        institution_id: str,
        job_type: str,
        filename: str,
        data: Any,
    ) -> Optional[str]:
        """Store a JSON-serializable object in the data lake.

        Args:
            institution_id: UUID string of the institution.
            job_type: Scrape job type (e.g. 'funding', 'faculty').
            filename: File name including extension.
            data: JSON-serializable data.

        Returns:
            Object key on success, None on failure.
        """
        client = self._get_client()
        if client is None:
            return None

        key = self._build_key(institution_id, job_type, filename)
        payload = json.dumps(data, default=str).encode("utf-8")

        try:
            client.put_object(
                settings.minio_bucket,
                key,
                io.BytesIO(payload),
                length=len(payload),
                content_type="application/json",
            )
            logger.debug("Stored %s (%d bytes)", key, len(payload))
            return key
        except Exception as exc:
            logger.error("Failed to store %s: %s", key, exc)
            return None

    def store_text(
        self,
        institution_id: str,
        job_type: str,
        filename: str,
        text: str,
    ) -> Optional[str]:
        """Store plain text (e.g. scraped markdown) in the data lake.

        Args:
            institution_id: UUID string of the institution.
            job_type: Scrape job type.
            filename: File name including extension.
            text: Text content.

        Returns:
            Object key on success, None on failure.
        """
        client = self._get_client()
        if client is None:
            return None

        key = self._build_key(institution_id, job_type, filename)
        payload = text.encode("utf-8")

        try:
            client.put_object(
                settings.minio_bucket,
                key,
                io.BytesIO(payload),
                length=len(payload),
                content_type="text/plain",
            )
            return key
        except Exception as exc:
            logger.error("Failed to store %s: %s", key, exc)
            return None

    def get_json(self, key: str) -> Optional[Dict]:
        """Retrieve a JSON object from the data lake.

        Args:
            key: Object key.

        Returns:
            Parsed JSON dict or None.
        """
        client = self._get_client()
        if client is None:
            return None

        try:
            resp = client.get_object(settings.minio_bucket, key)
            data = json.loads(resp.read().decode("utf-8"))
            resp.close()
            resp.release_conn()
            return data
        except Exception as exc:
            logger.error("Failed to read %s: %s", key, exc)
            return None

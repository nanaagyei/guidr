"""Unit tests for DataLakeStorageClient (mocked MinIO)."""
import pytest
from unittest.mock import MagicMock, patch

from src.pipeline.clients.storage_client import DataLakeStorageClient


class TestDataLakeStorageClient:
    def test_store_json_returns_none_when_minio_unavailable(self):
        with patch.object(DataLakeStorageClient, "_get_client", return_value=None):
            client = DataLakeStorageClient()
            result = client.store_json(
                "test-inst-id", "funding", "data.json", {"key": "value"}
            )
            assert result is None

    def test_store_text_returns_none_when_minio_unavailable(self):
        with patch.object(DataLakeStorageClient, "_get_client", return_value=None):
            client = DataLakeStorageClient()
            result = client.store_text(
                "test-inst-id", "overview", "overview.md", "Hello world"
            )
            assert result is None

    def test_get_json_returns_none_when_minio_unavailable(self):
        with patch.object(DataLakeStorageClient, "_get_client", return_value=None):
            client = DataLakeStorageClient()
            result = client.get_json("raw/2025/01/01/abc/funding/data.json")
            assert result is None

    def test_store_json_stores_when_client_available(self):
        mock_minio = MagicMock()
        with patch.object(DataLakeStorageClient, "_get_client", return_value=mock_minio):
            with patch("src.pipeline.clients.storage_client.settings") as mock_settings:
                mock_settings.minio_bucket = "test-bucket"
                client = DataLakeStorageClient()
                result = client.store_json(
                    "inst-123", "funding", "data.json", {"key": "value"}
                )
                assert result is not None
                assert "inst-123" in result
                assert "funding" in result
                assert "data.json" in result
                mock_minio.put_object.assert_called_once()

"""Storage service for R2/S3-compatible object storage."""
from typing import Optional
from datetime import timedelta
from src.config import settings
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class StorageService:
    """Service for interacting with R2/S3 storage."""

    def __init__(self):
        """Initialize storage client."""
        if not all([
            settings.r2_account_id,
            settings.r2_access_key_id,
            settings.r2_secret_access_key,
            settings.r2_bucket_name
        ]):
            self.client = None
            return

        # Configure boto3 for R2
        self.client = boto3.client(
            's3',
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=Config(signature_version='s3v4')
        )
        self.bucket_name = settings.r2_bucket_name

    def generate_upload_url(
        self,
        storage_key: str,
        expiration_minutes: int = 15
    ) -> Optional[str]:
        """Generate a presigned URL for uploading a file.

        Args:
            storage_key: The key/path where the file will be stored
            expiration_minutes: URL expiration time in minutes

        Returns:
            Presigned upload URL or None if storage not configured
        """
        if not self.client:
            return None

        try:
            url = self.client.generate_presigned_url(
                'put_object',
                Params={'Bucket': self.bucket_name, 'Key': storage_key},
                ExpiresIn=expiration_minutes * 60
            )
            return url
        except ClientError as e:
            print(f"Error generating upload URL: {e}")
            return None

    def download_file(self, storage_key: str) -> Optional[bytes]:
        """Download a file from storage.

        Args:
            storage_key: The key/path of the file to download

        Returns:
            File contents as bytes or None if error
        """
        if not self.client:
            return None

        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=storage_key
            )
            return response['Body'].read()
        except ClientError as e:
            print(f"Error downloading file: {e}")
            return None

    def delete_file(self, storage_key: str) -> bool:
        """Delete a file from storage.

        Args:
            storage_key: The key/path of the file to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_key
            )
            return True
        except ClientError as e:
            print(f"Error deleting file: {e}")
            return False


storage_service = StorageService()

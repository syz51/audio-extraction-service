"""
S3 file management utilities.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("utils.s3_utils")


class S3FileManager:
    """Secure S3 file operations manager."""

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
        self.temp_dir = settings.temp_dir_path
        self.temp_dir.mkdir(exist_ok=True, parents=True)

    async def download_file(
        self, bucket_name: str, object_key: str, local_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Download a file from S3 to local storage.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            local_filename: Optional local filename, will generate if not provided

        Returns:
            str: Local file path if successful, None if failed
        """
        try:
            if local_filename is None:
                # Generate safe local filename
                safe_filename = self._generate_safe_filename(object_key)
                local_path = self.temp_dir / safe_filename
            else:
                local_path = Path(local_filename)

            logger.info(f"Downloading s3://{bucket_name}/{object_key} to {local_path}")

            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download the file
            self.s3_client.download_file(bucket_name, object_key, str(local_path))

            # Verify file was downloaded
            if not local_path.exists() or local_path.stat().st_size == 0:
                logger.error(f"Downloaded file is empty or missing: {local_path}")
                return None

            logger.info(
                f"Successfully downloaded {object_key} ({local_path.stat().st_size:,} bytes)"
            )
            return str(local_path)

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                logger.error(f"File not found in S3: s3://{bucket_name}/{object_key}")
            elif error_code == "AccessDenied":
                logger.error(
                    f"Access denied downloading s3://{bucket_name}/{object_key}"
                )
            else:
                logger.error(f"S3 error downloading {object_key}: {e}")
            return None

        except BotoCoreError as e:
            logger.error(f"AWS SDK error downloading {object_key}: {e}")
            return None

        except Exception as e:
            logger.exception(f"Unexpected error downloading {object_key}: {e}")
            return None

    async def upload_file(
        self,
        local_path: str,
        bucket_name: str,
        object_key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> bool:
        """
        Upload a local file to S3.

        Args:
            local_path: Local file path
            bucket_name: S3 bucket name
            object_key: S3 object key
            metadata: Optional metadata to attach to the object
            content_type: Optional content type

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            local_file = Path(local_path)

            if not local_file.exists():
                logger.error(f"Local file not found: {local_path}")
                return False

            logger.info(f"Uploading {local_path} to s3://{bucket_name}/{object_key}")

            # Prepare upload arguments
            extra_args = {}

            if metadata:
                extra_args["Metadata"] = metadata

            if content_type:
                extra_args["ContentType"] = content_type
            else:
                # Try to determine content type from file extension
                content_type = self._guess_content_type(local_path)
                if content_type:
                    extra_args["ContentType"] = content_type

            # Upload the file
            self.s3_client.upload_file(
                local_path, bucket_name, object_key, ExtraArgs=extra_args
            )

            logger.info(
                f"Successfully uploaded {object_key} ({local_file.stat().st_size:,} bytes)"
            )
            return True

        except ClientError as e:
            logger.error(f"S3 error uploading {local_path}: {e}")
            return False

        except BotoCoreError as e:
            logger.error(f"AWS SDK error uploading {local_path}: {e}")
            return False

        except Exception as e:
            logger.exception(f"Unexpected error uploading {local_path}: {e}")
            return False

    async def get_object_metadata(
        self, bucket_name: str, object_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get S3 object metadata.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key

        Returns:
            Dict containing metadata if successful, None if failed
        """
        try:
            response = self.s3_client.head_object(Bucket=bucket_name, Key=object_key)

            metadata = {
                "content_length": response["ContentLength"],
                "content_type": response.get("ContentType"),
                "last_modified": response["LastModified"],
                "etag": response["ETag"].strip('"'),
                "metadata": response.get("Metadata", {}),
            }

            return metadata

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                logger.error(f"Object not found: s3://{bucket_name}/{object_key}")
            else:
                logger.error(f"Error getting metadata for {object_key}: {e}")
            return None

        except Exception as e:
            logger.exception(f"Unexpected error getting metadata for {object_key}: {e}")
            return None

    async def delete_object(self, bucket_name: str, object_key: str) -> bool:
        """
        Delete an object from S3.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting s3://{bucket_name}/{object_key}")

            self.s3_client.delete_object(Bucket=bucket_name, Key=object_key)

            logger.info(f"Successfully deleted {object_key}")
            return True

        except ClientError as e:
            logger.error(f"S3 error deleting {object_key}: {e}")
            return False

        except Exception as e:
            logger.exception(f"Unexpected error deleting {object_key}: {e}")
            return False

    def generate_presigned_url(
        self,
        bucket_name: str,
        object_key: str,
        operation: str = "get_object",
        expires_in: Optional[int] = None,
    ) -> Optional[str]:
        """
        Generate a presigned URL for S3 operations.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            operation: S3 operation (get_object, put_object, etc.)
            expires_in: URL expiration time in seconds

        Returns:
            str: Presigned URL if successful, None if failed
        """
        try:
            if expires_in is None:
                expires_in = settings.S3_PRESIGNED_URL_EXPIRY

            url = self.s3_client.generate_presigned_url(
                operation,
                Params={"Bucket": bucket_name, "Key": object_key},
                ExpiresIn=expires_in,
            )

            logger.debug(f"Generated presigned URL for {operation}: {object_key}")
            return url

        except Exception as e:
            logger.error(f"Error generating presigned URL for {object_key}: {e}")
            return None

    def _generate_safe_filename(self, object_key: str) -> str:
        """Generate a safe local filename from S3 object key."""
        # Extract filename from object key
        filename = Path(object_key).name

        # Sanitize filename to prevent path traversal
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)

        # Ensure filename is not empty and has reasonable length
        if not sanitized or len(sanitized) > 200:
            sanitized = f"file_{hash(object_key) % 1000000}"

        # Add timestamp to prevent collisions
        import time

        timestamp = int(time.time() * 1000)

        name, ext = os.path.splitext(sanitized)
        return f"{name}_{timestamp}{ext}"

    def _guess_content_type(self, file_path: str) -> Optional[str]:
        """Guess content type from file extension."""
        content_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
            ".ogg": "audio/ogg",
            ".opus": "audio/opus",
            ".wma": "audio/x-ms-wma",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
        }

        ext = Path(file_path).suffix.lower()
        return content_types.get(ext)

    async def cleanup_local_file(self, file_path: str) -> None:
        """Safely clean up a local file."""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up local file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup local file {file_path}: {e}")

"""
Audio file validation utilities.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError


from magika import Magika


from app.core.config import settings
from app.core.media_types import MediaTypes
from app.utils.logging import get_logger

logger = get_logger("utils.file_validation")


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.is_valid: bool = False
        self.file_type: Optional[str] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        logger.error(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "file_type": self.file_type,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class AudioFileValidator:
    """Comprehensive audio file validator."""

    def __init__(self):
        """Initialize the validator."""
        self.s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
        self.magika = Magika()

    async def validate_audio_file(
        self, bucket_name: str, object_key: str, object_size: Optional[int] = None
    ) -> ValidationResult:
        """
        Comprehensive audio file validation.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            object_size: File size in bytes (optional)

        Returns:
            ValidationResult: Validation result with details
        """
        result = ValidationResult()

        try:
            # Get object metadata if size not provided
            if object_size is None:
                object_size = await self._get_object_size(
                    bucket_name, object_key, result
                )
                if object_size is None:
                    return result

            # Layer 1: Basic file validation
            if not await self._validate_basic_properties(
                object_key, object_size, result
            ):
                return result

            # Layer 2: Magic byte validation
            if not await self._validate_magic_bytes(bucket_name, object_key, result):
                return result

            # Layer 3: FFprobe validation
            if not await self._validate_with_ffprobe(bucket_name, object_key, result):
                return result

            result.is_valid = True
            logger.info(f"Validation successful for {object_key}")

        except Exception as e:
            result.add_error(f"Unexpected validation error: {str(e)}")
            logger.exception(f"Validation failed for {object_key}")

        return result

    async def _get_object_size(
        self, bucket_name: str, object_key: str, result: ValidationResult
    ) -> Optional[int]:
        """Get S3 object size."""
        try:
            response = self.s3_client.head_object(Bucket=bucket_name, Key=object_key)
            return response["ContentLength"]
        except ClientError as e:
            result.add_error(f"Failed to get object metadata: {e}")
            return None
        except Exception as e:
            result.add_error(f"Unexpected error getting object size: {e}")
            return None

    async def _validate_basic_properties(
        self, object_key: str, object_size: int, result: ValidationResult
    ) -> bool:
        """Validate basic file properties."""

        # File size validation
        if object_size == 0:
            result.add_error("File is empty (0 bytes)")
            return False

        if object_size > settings.MAX_VIDEO_FILE_SIZE:
            result.add_error(
                f"File too large: {object_size:,} bytes "
                f"(max: {settings.MAX_VIDEO_FILE_SIZE:,} bytes)"
            )
            return False

        result.metadata["file_size"] = object_size
        logger.debug(f"Basic validation passed for {object_key}")
        return True

    async def _validate_magic_bytes(
        self, bucket_name: str, object_key: str, result: ValidationResult
    ) -> bool:
        """Validate file content using Magika AI-powered detection."""

        try:
            # Download first 8kb for magic byte detection
            response = self.s3_client.get_object(
                Bucket=bucket_name, Key=object_key, Range="bytes=0-8192"
            )
            header_bytes = response["Body"].read()

            # Use Magika's identify_bytes method - it will seek() around as needed
            magika_result = self.magika.identify_bytes(header_bytes)  # type: ignore

            if not magika_result.ok:
                result.add_error(f"Magika analysis failed: {magika_result.status}")
                return False

            detected_label = magika_result.output.label
            detected_description = magika_result.output.description
            detected_mime_type = magika_result.output.mime_type
            confidence_score = magika_result.score

            # Store detailed Magika results in metadata
            result.metadata["magika"] = {
                "label": detected_label,
                "description": detected_description,
                "mime_type": detected_mime_type,
                "score": confidence_score,
                "group": magika_result.output.group,
                "is_text": magika_result.output.is_text,
            }

            # Check if detected type is in our valid audio/video types
            if not MediaTypes.is_supported_format(detected_label):
                result.add_error(
                    f"File content detected as '{detected_description}' ({detected_label}) "
                    f"which is not a supported audio/video format. "
                    f"Confidence: {confidence_score:.3f}"
                )
                return False

            result.file_type = detected_label
            result.metadata["detected_type"] = detected_label
            result.metadata["mime_type"] = detected_mime_type
            return True

        except ClientError as e:
            result.add_error(f"Failed to read file content from S3: {e}")
            return False
        except Exception as e:
            result.add_error(f"Magika content validation error: {e}")
            return False
        finally:
            # Ensure the stream is properly closed
            if "response" in locals() and "Body" in response:
                response["Body"].close()

    async def _validate_with_ffprobe(
        self, bucket_name: str, object_key: str, result: ValidationResult
    ) -> bool:
        """Use ffprobe for lightweight metadata extraction and validation."""

        try:
            # Generate pre-signed URL for ffprobe
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_key},
                ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRY,
            )

            # Run ffprobe command
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,bit_rate,size,format_name:stream=codec_type,codec_name,duration",
                "-of",
                "json",
                url,
            ]

            process = await self._create_subprocess(cmd)

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=settings.FFPROBE_TIMEOUT
                )
            except asyncio.TimeoutError:
                process.kill()
                result.add_error(
                    f"FFprobe validation timed out after {settings.FFPROBE_TIMEOUT}s"
                )
                return False

            if process.returncode != 0:
                error_msg = self._extract_ffmpeg_error(stderr.decode())
                result.add_error(f"FFprobe validation failed: {error_msg}")
                return False

            # Parse and validate metadata
            try:
                metadata = json.loads(stdout.decode())
                result.metadata["ffprobe"] = metadata

                if not self._validate_audio_metadata(metadata, result):
                    return False

                return True

            except json.JSONDecodeError as e:
                result.add_error(f"Failed to parse ffprobe output: {e}")
                return False

        except Exception as e:
            logger.exception(f"FFprobe validation error: {e}")
            result.add_error(f"FFprobe validation error: {e}")
            return False

    def _validate_audio_metadata(
        self, metadata: Dict[str, Any], result: ValidationResult
    ) -> bool:
        """Validate audio metadata from ffprobe."""
        format_info = metadata.get("format", {})
        streams = metadata.get("streams", [])

        # Check if file has audio streams
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        video_streams = [s for s in streams if s.get("codec_type") == "video"]

        if not audio_streams and not video_streams:
            result.add_error("No audio or video streams found in file")
            return False

        if not audio_streams and video_streams:
            result.add_error("File contains video but no audio streams")
            return False

        # Validate duration
        duration_str = format_info.get("duration")
        if duration_str:
            try:
                duration = float(duration_str)
                result.metadata["duration"] = duration

                if duration <= 0:
                    result.add_error("Invalid duration (≤ 0 seconds)")
                    return False
                elif duration > settings.MAX_AUDIO_DURATION:
                    result.add_warning(
                        f"Very long audio file: {duration:.1f}s "
                        f"(max recommended: {settings.MAX_AUDIO_DURATION}s)"
                    )
            except (ValueError, TypeError):
                result.add_warning("Unable to parse audio duration")
        else:
            result.add_warning("Duration information not available")

        # Store additional metadata
        result.metadata["format_name"] = format_info.get("format_name")
        result.metadata["bit_rate"] = format_info.get("bit_rate")
        result.metadata["audio_stream_count"] = len(audio_streams)
        result.metadata["video_stream_count"] = len(video_streams)

        return True

    def _extract_ffmpeg_error(self, stderr_text: str) -> str:
        """Extract concise error information from FFmpeg stderr."""
        if not stderr_text:
            return "Unknown FFmpeg error (stderr is empty)"

        lines = stderr_text.strip().splitlines()
        if not lines:
            return "Unknown FFmpeg error (no stderr content)"

        # Look for key error indicators
        error_keywords = [
            "error",
            "invalid",
            "fail",
            "could not",
            "no such",
            "denied",
            "unsupported",
            "unable",
            "can't open",
            "conversion failed",
            "not found",
            "permission denied",
        ]

        # Check last few lines for errors
        for line in reversed(lines[-5:]):
            line = line.strip()
            if any(keyword in line.lower() for keyword in error_keywords):
                return line[:300]  # Limit length

        # Fallback to last non-empty line
        for line in reversed(lines):
            if line.strip():
                return line[:300]

        return "Unknown FFmpeg error"

"""
Tests for audio file validation utilities.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import json

from app.utils.file_validation import AudioFileValidator, ValidationResult
from app.core.config import settings


class TestValidationResult:
    """Test ValidationResult container."""

    def test_validation_result_initialization(self):
        """Test ValidationResult initial state."""
        result = ValidationResult()

        assert result.is_valid is False
        assert result.file_type is None
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}

    def test_add_error(self):
        """Test adding error messages."""
        result = ValidationResult()

        result.add_error("Test error")

        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"

    def test_add_warning(self):
        """Test adding warning messages."""
        result = ValidationResult()

        result.add_warning("Test warning")

        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"

    def test_to_dict(self):
        """Test converting ValidationResult to dictionary."""
        result = ValidationResult()
        result.is_valid = True
        result.file_type = "mp3"
        result.add_error("Test error")
        result.add_warning("Test warning")
        result.metadata = {"duration": 120.5}

        result_dict = result.to_dict()

        expected = {
            "is_valid": True,
            "file_type": "mp3",
            "errors": ["Test error"],
            "warnings": ["Test warning"],
            "metadata": {"duration": 120.5},
        }
        assert result_dict == expected


class TestAudioFileValidator:
    """Test AudioFileValidator class."""

    @pytest.fixture
    def validator(self):
        """Create AudioFileValidator instance."""
        with patch("boto3.client"):
            return AudioFileValidator()

    @pytest.fixture
    def mock_s3_client(self, validator):
        """Mock S3 client."""
        mock_client = Mock()
        validator.s3_client = mock_client
        return mock_client

    def test_validator_initialization(self):
        """Test validator initialization."""
        with patch("boto3.client") as mock_boto3:
            mock_boto3.assert_called_once_with("s3", region_name=settings.AWS_REGION)

    def test_detect_file_type_mp3(self, validator):
        """Test MP3 magic byte detection."""
        # Test ID3 tag
        mp3_data_id3 = b"ID3\x03\x00\x00\x00"
        assert validator._detect_file_type_from_magic_bytes(mp3_data_id3) == "mp3"

        # Test MP3 frame header
        mp3_data_frame = b"\xff\xfb\x90\x00"
        assert validator._detect_file_type_from_magic_bytes(mp3_data_frame) == "mp3"

    def test_detect_file_type_wav(self, validator):
        """Test WAV magic byte detection."""
        wav_data = b"RIFF\x24\x08\x00\x00WAVE"
        assert validator._detect_file_type_from_magic_bytes(wav_data) == "wav"

        # Test non-WAV RIFF file
        riff_data = b"RIFF\x24\x08\x00\x00AVI "
        assert validator._detect_file_type_from_magic_bytes(riff_data) is None

    def test_detect_file_type_flac(self, validator):
        """Test FLAC magic byte detection."""
        flac_data = b"fLaC\x00\x00\x00\x22"
        assert validator._detect_file_type_from_magic_bytes(flac_data) == "flac"

    def test_detect_file_type_mp4(self, validator):
        """Test MP4/M4A magic byte detection."""
        # Test ftyp box
        mp4_data = b"\x00\x00\x00\x20ftypmp41"
        assert validator._detect_file_type_from_magic_bytes(mp4_data) == "mp4"

        # Test M4A
        m4a_data = b"\x00\x00\x00\x20ftypM4A "
        assert validator._detect_file_type_from_magic_bytes(m4a_data) == "mp4"

    def test_detect_file_type_ogg(self, validator):
        """Test OGG magic byte detection."""
        ogg_data = b"OggS\x00\x02\x00\x00"
        assert validator._detect_file_type_from_magic_bytes(ogg_data) == "ogg"

    def test_detect_file_type_unknown(self, validator):
        """Test unknown file type detection."""
        unknown_data = b"\x89PNG\r\n\x1a\n"
        assert validator._detect_file_type_from_magic_bytes(unknown_data) is None

    def test_detect_file_type_insufficient_data(self, validator):
        """Test detection with insufficient data."""
        short_data = b"\xff"
        assert validator._detect_file_type_from_magic_bytes(short_data) is None

    @pytest.mark.asyncio
    async def test_get_object_size_success(self, validator, mock_s3_client):
        """Test successful object size retrieval."""
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}

        result = ValidationResult()
        size = await validator._get_object_size("test-bucket", "test.mp3", result)

        assert size == 1024
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.mp3"
        )

    @pytest.mark.asyncio
    async def test_get_object_size_client_error(self, validator, mock_s3_client):
        """Test object size retrieval with client error."""
        from botocore.exceptions import ClientError

        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "HeadObject"
        )

        result = ValidationResult()
        size = await validator._get_object_size("test-bucket", "test.mp3", result)

        assert size is None
        assert len(result.errors) == 1
        assert "Failed to get object metadata" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_basic_properties_success(self, validator):
        """Test successful basic properties validation."""
        result = ValidationResult()

        success = await validator._validate_basic_properties("test.mp3", 1024, result)

        assert success is True
        assert result.metadata["file_size"] == 1024
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_basic_properties_empty_file(self, validator):
        """Test validation of empty file."""
        result = ValidationResult()

        success = await validator._validate_basic_properties("test.mp3", 0, result)

        assert success is False
        assert len(result.errors) == 1
        assert "File is empty" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_basic_properties_too_large(self, validator):
        """Test validation of oversized file."""
        result = ValidationResult()
        large_size = settings.MAX_VIDEO_FILE_SIZE + 1

        success = await validator._validate_basic_properties(
            "test.mp3", large_size, result
        )

        assert success is False
        assert len(result.errors) == 1
        assert "File too large" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_basic_properties_various_files(self, validator):
        """Test basic properties validation with various file types."""
        result = ValidationResult()

        # Basic validation doesn't check file extensions, only size
        success = await validator._validate_basic_properties("test.txt", 1024, result)

        assert success is True  # Basic validation passes for any file with valid size
        assert result.metadata["file_size"] == 1024
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_success(self, validator, mock_s3_client):
        """Test successful magic bytes validation."""
        # Mock S3 response with MP3 data
        mock_response = Mock()
        mock_response.read.return_value = b"ID3\x03\x00\x00\x00"
        mock_s3_client.get_object.return_value = {"Body": mock_response}

        result = ValidationResult()
        success = await validator._validate_magic_bytes(
            "test-bucket", "test.mp3", result
        )

        assert success is True
        assert result.file_type == "mp3"
        assert result.metadata["detected_type"] == "mp3"

    @pytest.mark.asyncio
    async def test_validate_magic_bytes_invalid_content(
        self, validator, mock_s3_client
    ):
        """Test magic bytes validation with invalid content."""
        # Mock S3 response with non-audio data
        mock_response = Mock()
        mock_response.read.return_value = b"\x89PNG\r\n\x1a\n"
        mock_s3_client.get_object.return_value = {"Body": mock_response}

        result = ValidationResult()
        success = await validator._validate_magic_bytes(
            "test-bucket", "test.png", result
        )

        assert success is False
        assert len(result.errors) == 1
        assert "Unable to detect valid audio/video file type" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_with_ffprobe_success(self, validator, mock_s3_client):
        """Test successful ffprobe validation."""
        # Mock presigned URL generation
        mock_s3_client.generate_presigned_url.return_value = "https://presigned-url"

        # Mock ffprobe output
        ffprobe_output = {
            "format": {"duration": "180.5", "bit_rate": "192000", "format_name": "mp3"},
            "streams": [
                {"codec_type": "audio", "codec_name": "mp3", "duration": "180.5"}
            ],
        }

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock process
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                json.dumps(ffprobe_output).encode(),
                b"",
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = ValidationResult()
            success = await validator._validate_with_ffprobe(
                "test-bucket", "test.mp3", result
            )

        assert success is True
        assert result.metadata["ffprobe"] == ffprobe_output
        assert result.metadata["duration"] == 180.5
        assert result.metadata["format_name"] == "mp3"

    @pytest.mark.asyncio
    async def test_validate_with_ffprobe_failure(self, validator, mock_s3_client):
        """Test ffprobe validation failure."""
        mock_s3_client.generate_presigned_url.return_value = "https://presigned-url"

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"Error: Invalid file")
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            result = ValidationResult()
            success = await validator._validate_with_ffprobe(
                "test-bucket", "test.mp3", result
            )

        assert success is False
        assert len(result.errors) == 1
        assert "FFprobe validation failed" in result.errors[0]

    def test_validate_audio_metadata_success(self, validator):
        """Test successful audio metadata validation."""
        metadata = {
            "format": {"duration": "120.5", "bit_rate": "192000", "format_name": "mp3"},
            "streams": [{"codec_type": "audio", "codec_name": "mp3"}],
        }

        result = ValidationResult()
        success = validator._validate_audio_metadata(metadata, result)

        assert success is True
        assert result.metadata["duration"] == 120.5
        assert result.metadata["format_name"] == "mp3"
        assert result.metadata["audio_stream_count"] == 1
        assert result.metadata["video_stream_count"] == 0

    def test_validate_audio_metadata_no_streams(self, validator):
        """Test metadata validation with no audio/video streams."""
        metadata = {"format": {"duration": "120.5"}, "streams": []}

        result = ValidationResult()
        success = validator._validate_audio_metadata(metadata, result)

        assert success is False
        assert len(result.errors) == 1
        assert "No audio or video streams found" in result.errors[0]

    def test_validate_audio_metadata_video_only(self, validator):
        """Test metadata validation with video but no audio."""
        metadata = {
            "format": {"duration": "120.5"},
            "streams": [{"codec_type": "video", "codec_name": "h264"}],
        }

        result = ValidationResult()
        success = validator._validate_audio_metadata(metadata, result)

        assert success is True
        assert len(result.warnings) == 1
        assert "contains video but no audio streams" in result.warnings[0]

    def test_validate_audio_metadata_invalid_duration(self, validator):
        """Test metadata validation with invalid duration."""
        metadata = {
            "format": {"duration": "0"},
            "streams": [{"codec_type": "audio", "codec_name": "mp3"}],
        }

        result = ValidationResult()
        success = validator._validate_audio_metadata(metadata, result)

        assert success is False
        assert len(result.errors) == 1
        assert "Invalid duration" in result.errors[0]

    def test_extract_ffmpeg_error(self, validator):
        """Test FFmpeg error extraction."""
        stderr_with_error = """
        ffmpeg version 4.4.0
        Built with gcc 9
        Error: Input file not found
        """

        error = validator._extract_ffmpeg_error(stderr_with_error)
        assert "Input file not found" in error

    def test_extract_ffmpeg_error_empty(self, validator):
        """Test FFmpeg error extraction with empty stderr."""
        error = validator._extract_ffmpeg_error("")
        assert "Unknown FFmpeg error (stderr is empty)" in error

    @pytest.mark.asyncio
    async def test_validate_audio_file_full_success(self, validator, mock_s3_client):
        """Test complete successful audio file validation."""
        # Mock S3 head_object for size
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}

        # Mock S3 get_object for magic bytes
        mock_response = Mock()
        mock_response.read.return_value = b"ID3\x03\x00\x00\x00"
        mock_s3_client.get_object.return_value = {"Body": mock_response}

        # Mock presigned URL
        mock_s3_client.generate_presigned_url.return_value = "https://presigned-url"

        # Mock ffprobe
        ffprobe_output = {
            "format": {"duration": "180.5", "format_name": "mp3"},
            "streams": [{"codec_type": "audio", "codec_name": "mp3"}],
        }

        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                json.dumps(ffprobe_output).encode(),
                b"",
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            with patch("app.schemas.s3_events.is_audio_file", return_value=True):
                result = await validator.validate_audio_file("test-bucket", "test.mp3")

        assert result.is_valid is True
        assert result.file_type == "mp3"
        assert len(result.errors) == 0
        assert result.metadata["file_size"] == 1024
        assert result.metadata["duration"] == 180.5

    @pytest.mark.asyncio
    async def test_validate_audio_file_validation_disabled(self, validator):
        """Test validation with some validation layers disabled."""
        # Temporarily disable magic byte and ffprobe validation
        original_magic = settings.ENABLE_MAGIC_BYTE_VALIDATION
        original_ffprobe = settings.ENABLE_FFPROBE_VALIDATION

        try:
            settings.ENABLE_MAGIC_BYTE_VALIDATION = False
            settings.ENABLE_FFPROBE_VALIDATION = False

            with patch("app.schemas.s3_events.is_audio_file", return_value=True):
                result = await validator.validate_audio_file(
                    "test-bucket", "test.mp3", 1024
                )

            assert result.is_valid is True
            assert result.file_type is None  # No magic byte detection
            assert "ffprobe" not in result.metadata  # No ffprobe validation

        finally:
            # Restore original settings
            settings.ENABLE_MAGIC_BYTE_VALIDATION = original_magic
            settings.ENABLE_FFPROBE_VALIDATION = original_ffprobe

    @pytest.fixture
    def mock_s3_response(self):
        """Mock S3 response with sample audio bytes."""
        mock_response = Mock()
        # Sample MP3 header bytes (ID3 tag + MP3 frame header)
        mock_response.read.return_value = (
            b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb" + b"\x00" * 100
        )
        return {"Body": mock_response}

    @pytest.mark.asyncio
    async def test_magika_validation_success(self, validator, mock_s3_response):
        """Test successful Magika validation."""
        if not validator.magika:
            pytest.skip("Magika not available in test environment")

        with patch.object(
            validator.s3_client, "get_object", return_value=mock_s3_response
        ):
            # Mock Magika result
            mock_magika_result = Mock()
            mock_magika_result.ok = True
            mock_magika_result.output.label = "mp3"
            mock_magika_result.output.description = "MP3 audio"
            mock_magika_result.output.mime_type = "audio/mpeg"
            mock_magika_result.output.group = "audio"
            mock_magika_result.output.is_text = False
            mock_magika_result.score = 0.98

            with patch.object(
                validator.magika, "identify_bytes", return_value=mock_magika_result
            ):
                result = ValidationResult()
                success = await validator._validate_magic_bytes(
                    "test-bucket", "test.mp3", result
                )

                assert success is True
                assert result.file_type == "mp3"
                assert result.metadata["detected_type"] == "mp3"
                assert result.metadata["mime_type"] == "audio/mpeg"
                assert "magika" in result.metadata
                assert result.metadata["magika"]["score"] == 0.98

    @pytest.mark.asyncio
    async def test_magika_validation_invalid_type(self, validator, mock_s3_response):
        """Test Magika validation with invalid file type."""
        if not validator.magika:
            pytest.skip("Magika not available in test environment")

        with patch.object(
            validator.s3_client, "get_object", return_value=mock_s3_response
        ):
            # Mock Magika result for a text file
            mock_magika_result = Mock()
            mock_magika_result.ok = True
            mock_magika_result.output.label = "txt"
            mock_magika_result.output.description = "Text document"
            mock_magika_result.output.mime_type = "text/plain"
            mock_magika_result.output.group = "text"
            mock_magika_result.output.is_text = True
            mock_magika_result.score = 0.95

            with patch.object(
                validator.magika, "identify_bytes", return_value=mock_magika_result
            ):
                result = ValidationResult()
                success = await validator._validate_magic_bytes(
                    "test-bucket", "test.txt", result
                )

                assert success is False
                assert len(result.errors) > 0
                assert "not a supported audio/video format" in result.errors[0]

    @pytest.mark.asyncio
    async def test_magika_validation_without_magika(self, validator, mock_s3_response):
        """Test validation when Magika is not available."""
        # Temporarily disable Magika
        original_magika = validator.magika
        validator.magika = None

        try:
            result = ValidationResult()
            success = await validator._validate_magic_bytes(
                "test-bucket", "test.mp3", result
            )

            assert success is True  # Should pass without Magika
            assert len(result.warnings) > 0
            assert "Magika not available" in result.warnings[0]
        finally:
            validator.magika = original_magika

    @pytest.mark.asyncio
    async def test_magika_validation_likely_audio_type(
        self, validator, mock_s3_response
    ):
        """Test validation with a file type that's likely audio but not in explicit list."""
        if not validator.magika:
            pytest.skip("Magika not available in test environment")

        with patch.object(
            validator.s3_client, "get_object", return_value=mock_s3_response
        ):
            # Mock Magika result for an unknown audio type
            mock_magika_result = Mock()
            mock_magika_result.ok = True
            mock_magika_result.output.label = "unknown_audio"
            mock_magika_result.output.description = "Unknown audio format"
            mock_magika_result.output.mime_type = "audio/x-unknown"
            mock_magika_result.output.group = "audio"
            mock_magika_result.output.is_text = False
            mock_magika_result.score = 0.85

            with patch.object(
                validator.magika, "identify_bytes", return_value=mock_magika_result
            ):
                result = ValidationResult()
                success = await validator._validate_magic_bytes(
                    "test-bucket", "test.unk", result
                )

                assert (
                    success is True
                )  # Should pass because MIME type starts with "audio/"
                assert len(result.warnings) > 0
                assert "may not be optimal for audio processing" in result.warnings[0]

    def test_is_likely_audio_video_type(self, validator):
        """Test the helper method for detecting likely audio/video types."""
        # Test MIME type patterns
        assert validator._is_likely_audio_video_type("unknown", "audio/mpeg") is True
        assert validator._is_likely_audio_video_type("unknown", "video/mp4") is True
        assert (
            validator._is_likely_audio_video_type("unknown", "application/x-audio")
            is True
        )

        # Test label patterns
        assert validator._is_likely_audio_video_type("audio_file", "unknown") is True
        assert validator._is_likely_audio_video_type("video_stream", "unknown") is True
        assert (
            validator._is_likely_audio_video_type("media_container", "unknown") is True
        )
        assert validator._is_likely_audio_video_type("sound_file", "unknown") is True

        # Test negative cases
        assert validator._is_likely_audio_video_type("txt", "text/plain") is False
        assert validator._is_likely_audio_video_type("pdf", "application/pdf") is False

    @pytest.mark.asyncio
    async def test_validation_with_too_small_file(self, validator):
        """Test validation with a file that's too small."""
        if not validator.magika:
            pytest.skip("Magika not available in test environment")

        mock_response = Mock()
        mock_response.read.return_value = b"ab"  # Only 2 bytes
        small_file_response = {"Body": mock_response}

        with patch.object(
            validator.s3_client, "get_object", return_value=small_file_response
        ):
            result = ValidationResult()
            success = await validator._validate_magic_bytes(
                "test-bucket", "small.mp3", result
            )

            assert success is False
            assert "File too small for content analysis" in result.errors

    @pytest.mark.asyncio
    async def test_magika_analysis_failure(self, validator, mock_s3_response):
        """Test handling of Magika analysis failure."""
        if not validator.magika:
            pytest.skip("Magika not available in test environment")

        with patch.object(
            validator.s3_client, "get_object", return_value=mock_s3_response
        ):
            # Mock Magika result with failure
            mock_magika_result = Mock()
            mock_magika_result.ok = False
            mock_magika_result.status = "analysis_failed"

            with patch.object(
                validator.magika, "identify_bytes", return_value=mock_magika_result
            ):
                result = ValidationResult()
                success = await validator._validate_magic_bytes(
                    "test-bucket", "bad.file", result
                )

                assert success is False
                assert "Magika analysis failed: analysis_failed" in result.errors

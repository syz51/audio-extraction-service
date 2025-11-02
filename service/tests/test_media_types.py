"""
Tests for the centralized MediaTypes configuration.
"""

from app.core.media_types import (
    MediaTypes,
    is_audio_file,
    SUPPORTED_AUDIO_VIDEO_FORMATS,
    SUPPORTED_AUDIO_VIDEO_EXTENSIONS,
)


class TestMediaTypes:
    """Test the MediaTypes class functionality."""

    def test_get_supported_format_names(self):
        """Test getting supported format names."""
        formats = MediaTypes.get_supported_format_names()

        # Should be a frozenset
        assert isinstance(formats, frozenset)

        # Should contain expected audio formats
        expected_audio = {
            "mp3",
            "wav",
            "flac",
            "aac",
            "ogg",
            "m4a",
            "wma",
            "opus",
            "aiff",
            "au",
            "amr",
        }
        assert expected_audio.issubset(formats)

        # Should contain expected video formats
        expected_video = {"mp4", "m4v", "avi", "mov", "mkv", "webm", "wmv", "3gp"}
        assert expected_video.issubset(formats)

        # Should not be empty
        assert len(formats) > 0

    def test_get_supported_extensions(self):
        """Test getting supported file extensions."""
        extensions = MediaTypes.get_supported_extensions()

        # Should be a frozenset
        assert isinstance(extensions, frozenset)

        # Should contain expected audio extensions
        expected_audio = {
            ".mp3",
            ".wav",
            ".flac",
            ".aac",
            ".ogg",
            ".m4a",
            ".wma",
            ".opus",
            ".aiff",
            ".au",
            ".amr",
        }
        assert expected_audio.issubset(extensions)

        # Should contain expected video extensions
        expected_video = {
            ".mp4",
            ".m4v",
            ".avi",
            ".mov",
            ".mkv",
            ".webm",
            ".wmv",
            ".3gp",
        }
        assert expected_video.issubset(extensions)

        # All extensions should start with a dot
        assert all(ext.startswith(".") for ext in extensions)

        # Should not be empty
        assert len(extensions) > 0

    def test_is_supported_format(self):
        """Test format name validation."""
        # Valid formats
        assert MediaTypes.is_supported_format("mp3") is True
        assert MediaTypes.is_supported_format("MP3") is True  # Case insensitive
        assert MediaTypes.is_supported_format("wav") is True
        assert MediaTypes.is_supported_format("mp4") is True
        assert MediaTypes.is_supported_format("mkv") is True

        # Invalid formats
        assert MediaTypes.is_supported_format("pdf") is False
        assert MediaTypes.is_supported_format("txt") is False
        assert MediaTypes.is_supported_format("") is False
        assert MediaTypes.is_supported_format("unknown") is False

    def test_is_supported_extension(self):
        """Test file extension validation."""
        # Valid extensions
        assert MediaTypes.is_supported_extension(".mp3") is True
        assert MediaTypes.is_supported_extension(".MP3") is True  # Case insensitive
        assert MediaTypes.is_supported_extension(".wav") is True
        assert MediaTypes.is_supported_extension(".mp4") is True
        assert MediaTypes.is_supported_extension(".mkv") is True

        # Invalid extensions
        assert MediaTypes.is_supported_extension(".pdf") is False
        assert MediaTypes.is_supported_extension(".txt") is False
        assert MediaTypes.is_supported_extension("") is False
        assert MediaTypes.is_supported_extension("mp3") is False  # Missing dot
        assert MediaTypes.is_supported_extension(".unknown") is False

    def test_is_audio_file_method(self):
        """Test the is_audio_file class method."""
        # Valid audio files
        audio_files = [
            "sample.mp3",
            "music.wav",
            "audio.flac",
            "podcast.m4a",
            "song.aac",
            "recording.ogg",
            "track.wma",
            "voice.opus",
            "folder/subfolder/music.mp3",
            "UPPERCASE.MP3",
            "Mixed_Case.WaV",
            "audio.aiff",
            "old.au",
            "voice.amr",
        ]

        for file_key in audio_files:
            assert MediaTypes.is_audio_file(file_key), (
                f"Should detect {file_key} as audio file"
            )

        # Valid video files (that may contain audio)
        video_files = [
            "video.mp4",
            "movie.m4v",
            "clip.avi",
            "presentation.mov",
            "recording.mkv",
            "stream.webm",
            "movie.wmv",
            "mobile.3gp",
        ]

        for file_key in video_files:
            assert MediaTypes.is_audio_file(file_key), (
                f"Should detect {file_key} as containing audio"
            )

        # Non-audio files
        non_audio_files = [
            "document.pdf",
            "image.jpg",
            "photo.png",
            "data.json",
            "config.yaml",
            "script.py",
            "readme.txt",
            "archive.zip",
            "spreadsheet.xlsx",
            "presentation.pptx",
        ]

        for file_key in non_audio_files:
            assert not MediaTypes.is_audio_file(file_key), (
                f"Should NOT detect {file_key} as audio file"
            )

    def test_is_audio_file_edge_cases(self):
        """Test edge cases for audio file detection."""
        edge_cases = [
            ("", False),  # Empty string
            ("no_extension", False),  # No extension
            (".mp3", True),  # Just extension
            ("file.", False),  # Dot but no extension
            ("file.mp3.backup", False),  # Extension not at end
            ("audio.mp3/folder", False),  # Extension in middle of path
        ]

        for file_key, expected in edge_cases:
            result = MediaTypes.is_audio_file(file_key)
            assert result == expected, (
                f"Expected {expected} for '{file_key}', got {result}"
            )

    def test_backward_compatibility_constants(self):
        """Test that backward compatibility constants work."""
        # Test that constants are populated
        assert len(SUPPORTED_AUDIO_VIDEO_FORMATS) > 0
        assert len(SUPPORTED_AUDIO_VIDEO_EXTENSIONS) > 0

        # Test they match the class methods
        assert SUPPORTED_AUDIO_VIDEO_FORMATS == MediaTypes.get_supported_format_names()
        assert SUPPORTED_AUDIO_VIDEO_EXTENSIONS == MediaTypes.get_supported_extensions()

    def test_backward_compatibility_function(self):
        """Test that the backward compatibility function works."""
        # Test some examples
        assert is_audio_file("test.mp3") is True
        assert is_audio_file("test.pdf") is False

        # Should match the class method
        test_files = ["audio.mp3", "video.mp4", "document.pdf", "image.jpg"]
        for file_key in test_files:
            assert is_audio_file(file_key) == MediaTypes.is_audio_file(file_key)

    def test_format_extension_consistency(self):
        """Test that format names and extensions are consistent."""
        formats = MediaTypes.get_supported_format_names()
        extensions = MediaTypes.get_supported_extensions()

        # Should have the same number of formats and extensions
        assert len(formats) == len(extensions)

        # Each format should have a corresponding extension
        for format_name in formats:
            expected_extension = f".{format_name}"
            assert expected_extension in extensions, (
                f"Missing extension for format: {format_name}"
            )

    def test_no_duplicates(self):
        """Test that there are no duplicate formats or extensions."""
        formats = MediaTypes.get_supported_format_names()
        extensions = MediaTypes.get_supported_extensions()

        # Frozensets shouldn't have duplicates anyway, but let's be explicit
        formats_list = list(formats)
        extensions_list = list(extensions)

        assert len(formats_list) == len(set(formats_list))
        assert len(extensions_list) == len(set(extensions_list))

    def test_comprehensive_format_coverage(self):
        """Test that we have comprehensive coverage of common audio/video formats."""
        formats = MediaTypes.get_supported_format_names()

        # Common audio formats should be supported
        common_audio = {"mp3", "wav", "flac", "aac", "ogg", "m4a"}
        assert common_audio.issubset(formats), (
            f"Missing common audio formats: {common_audio - formats}"
        )

        # Common video formats should be supported
        common_video = {"mp4", "avi", "mov", "mkv", "webm"}
        assert common_video.issubset(formats), (
            f"Missing common video formats: {common_video - formats}"
        )

        # Should have at least 15 total formats
        assert len(formats) >= 15

"""
Centralized media type definitions for audio/video file processing.

This module provides a single source of truth for supported audio and video
file types, eliminating duplication across the codebase.
"""

from typing import FrozenSet


class MediaTypes:
    """Centralized media type definitions for audio/video processing."""

    # Core supported formats with both format names and extensions
    _SUPPORTED_FORMATS = {
        # Video formats
        "mp4": ".mp4",
        "m4v": ".m4v",
        "avi": ".avi",
        "mov": ".mov",
        "mkv": ".mkv",
        "webm": ".webm",
        "wmv": ".wmv",
        "3gp": ".3gp",
    }

    @classmethod
    def get_supported_format_names(cls) -> FrozenSet[str]:
        """
        Get supported format names (for Magika validation).

        Returns:
            Frozen set of format names like {'mp3', 'wav', 'mp4', ...}
        """
        return frozenset(cls._SUPPORTED_FORMATS.keys())

    @classmethod
    def get_supported_extensions(cls) -> FrozenSet[str]:
        """
        Get supported file extensions (for filename validation).

        Returns:
            Frozen set of extensions like {'.mp3', '.wav', '.mp4', ...}
        """
        return frozenset(cls._SUPPORTED_FORMATS.values())

    @classmethod
    def is_supported_format(cls, format_name: str) -> bool:
        """
        Check if a format name is supported.

        Args:
            format_name: Format name to check (e.g., 'mp3', 'wav')

        Returns:
            True if format is supported
        """
        return format_name.lower() in cls._SUPPORTED_FORMATS

    @classmethod
    def is_supported_extension(cls, extension: str) -> bool:
        """
        Check if a file extension is supported.

        Args:
            extension: File extension to check (e.g., '.mp3', '.wav')

        Returns:
            True if extension is supported
        """
        return extension.lower() in cls._SUPPORTED_FORMATS.values()

    @classmethod
    def is_audio_file(cls, object_key: str) -> bool:
        """
        Check if the S3 object is likely an audio/video file based on its extension.

        This replaces the function previously in s3_events.py.

        Args:
            object_key: S3 object key or filename

        Returns:
            True if the file appears to be an audio/video file
        """
        return any(
            object_key.lower().endswith(ext) for ext in cls.get_supported_extensions()
        )


# Backward compatibility constants
SUPPORTED_AUDIO_VIDEO_FORMATS = MediaTypes.get_supported_format_names()
SUPPORTED_AUDIO_VIDEO_EXTENSIONS = MediaTypes.get_supported_extensions()


# Convenience function for backward compatibility
def is_audio_file(object_key: str) -> bool:
    """Backward compatibility wrapper for MediaTypes.is_audio_file()."""
    return MediaTypes.is_audio_file(object_key)

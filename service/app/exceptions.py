"""
Custom exception classes for the audio extraction service.
"""

from typing import Any, Dict, Optional


class AudioExtractionError(Exception):
    """Base exception for audio extraction service."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class EventProcessingError(AudioExtractionError):
    """Exception raised when event processing fails."""

    pass


class InvalidEventFormat(AudioExtractionError):
    """Exception raised when event format is invalid."""

    pass


class AudioProcessingError(AudioExtractionError):
    """Exception raised when audio processing fails."""

    pass

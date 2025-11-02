"""
Utility modules for the application.
"""

from .logging import get_logger, setup_logging

# Import new utilities conditionally to handle potential import errors
try:
    from .file_validation import AudioFileValidator

    AUDIO_VALIDATOR_AVAILABLE = True
except ImportError:
    AudioFileValidator = None
    AUDIO_VALIDATOR_AVAILABLE = False

try:
    from .ffmpeg_utils import FFmpegProcessor

    FFMPEG_PROCESSOR_AVAILABLE = True
except ImportError:
    FFmpegProcessor = None
    FFMPEG_PROCESSOR_AVAILABLE = False

try:
    from .s3_utils import S3FileManager

    S3_MANAGER_AVAILABLE = True
except ImportError:
    S3FileManager = None
    S3_MANAGER_AVAILABLE = False

__all__ = [
    "get_logger",
    "setup_logging",
]

# Add to __all__ only if imports are successful
if AUDIO_VALIDATOR_AVAILABLE:
    __all__.append("AudioFileValidator")

if FFMPEG_PROCESSOR_AVAILABLE:
    __all__.append("FFmpegProcessor")

if S3_MANAGER_AVAILABLE:
    __all__.append("S3FileManager")

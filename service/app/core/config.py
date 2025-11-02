"""
Application configuration settings.
"""

import os
import sys
from pathlib import Path
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Logging configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Audio Processing Configuration
    MAX_VIDEO_FILE_SIZE: int = 1000 * 1024 * 1024  # 1GB
    MAX_AUDIO_DURATION: int = 24 * 60 * 60  # 24 hours in seconds
    TEMP_DIR: str = Field(default="", description="Temporary directory for processing")

    # AWS Configuration
    AWS_REGION: str = "eu-west-2"
    S3_PRESIGNED_URL_EXPIRY: int = 300  # 5 minutes

    # FFmpeg Configuration
    FFMPEG_TIMEOUT: int = 300  # 5 minutes
    FFPROBE_TIMEOUT: int = 30  # 30 seconds

    # Validation Configuration
    ENABLE_MAGIC_BYTE_VALIDATION: bool = True
    ENABLE_FFPROBE_VALIDATION: bool = True

    @computed_field
    @property
    def temp_dir_path(self) -> Path:
        """Get the appropriate temporary directory for the current platform."""
        if self.TEMP_DIR:
            return Path(self.TEMP_DIR)

        if sys.platform == "win32":
            # On Windows, use the user's temp directory or a writable location
            temp_base = os.environ.get("TEMP") or os.environ.get("TMP") or "C:\\temp"
            return Path(temp_base) / "audio_extraction_service"
        else:
            # Unix-like systems
            return Path("/tmp") / "audio_extraction_service"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()

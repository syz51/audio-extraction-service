"""
FFmpeg processing utilities for audio extraction.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List


from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("utils.ffmpeg_utils")


class FFmpegResult:
    """Container for FFmpeg processing results."""

    def __init__(self):
        self.success: bool = False
        self.output_path: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.error_message: Optional[str] = None
        self.processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output_path": self.output_path,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
        }


class SyncFFmpegProcessor:
    """Synchronous FFmpeg processor for audio extraction."""

    def __init__(self):
        """Initialize the synchronous FFmpeg processor."""
        self.temp_dir = settings.temp_dir_path
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Sync FFmpeg processor initialized with temp dir: {self.temp_dir}")

    def _run_subprocess(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run subprocess synchronously with Windows compatibility."""
        if os.name == "nt":  # Windows
            # Use shell=True for Windows compatibility with FFmpeg
            cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
            return subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=settings.FFMPEG_TIMEOUT,
            )
        else:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=settings.FFMPEG_TIMEOUT
            )

    def extract_audio(
        self,
        input_path: str,
        output_format: str = "wav",
        audio_codec: str = "pcm_s16le",
        sample_rate: int = 44100,
        channels: int = 2,
    ) -> FFmpegResult:
        """
        Extract audio from input file synchronously.

        Args:
            input_path: Path to input file
            output_format: Output format (wav, mp3, flac, etc.)
            audio_codec: Audio codec to use
            sample_rate: Sample rate in Hz
            channels: Number of audio channels

        Returns:
            FFmpegResult: Processing result
        """
        result = FFmpegResult()
        start_time = time.time()

        try:
            # Generate output path
            output_path = self._generate_output_path(input_path, output_format)

            # Build FFmpeg command
            cmd = self._build_extraction_command(
                input_path,
                output_path,
                output_format,
                audio_codec,
                sample_rate,
                channels,
            )

            logger.info(
                f"Starting sync audio extraction: {input_path} -> {output_path}"
            )
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            # Execute FFmpeg synchronously
            try:
                process_result = self._run_subprocess(cmd)
            except subprocess.TimeoutExpired:
                result.error_message = (
                    f"FFmpeg processing timed out after {settings.FFMPEG_TIMEOUT}s"
                )
                return result

            result.processing_time = time.time() - start_time

            if process_result.returncode == 0:
                result.success = True
                result.output_path = output_path

                # Extract metadata from output
                self._extract_output_metadata(output_path, result)

                logger.info(f"Sync audio extraction successful: {output_path}")
            else:
                result.error_message = self._extract_ffmpeg_error(process_result.stderr)
                logger.error(f"Sync audio extraction failed: {result.error_message}")

                # Clean up failed output file
                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            result.error_message = (
                f"Unexpected error during sync audio extraction: {str(e)}"
            )
            logger.exception(f"Sync audio extraction error for {input_path}")

        return result

    def convert_audio_format(
        self, input_path: str, target_format: str, quality_preset: str = "medium"
    ) -> FFmpegResult:
        """
        Convert audio to different format synchronously.

        Args:
            input_path: Path to input audio file
            target_format: Target format (mp3, flac, ogg, etc.)
            quality_preset: Quality preset (low, medium, high)

        Returns:
            FFmpegResult: Processing result
        """
        result = FFmpegResult()
        start_time = time.time()

        try:
            output_path = self._generate_output_path(input_path, target_format)

            # Build conversion command based on format and quality
            cmd = self._build_conversion_command(
                input_path, output_path, target_format, quality_preset
            )

            logger.info(
                f"Starting sync audio conversion: {input_path} -> {target_format}"
            )

            try:
                process_result = self._run_subprocess(cmd)
            except subprocess.TimeoutExpired:
                result.error_message = (
                    f"Audio conversion timed out after {settings.FFMPEG_TIMEOUT}s"
                )
                return result

            result.processing_time = time.time() - start_time

            if process_result.returncode == 0:
                result.success = True
                result.output_path = output_path
                self._extract_output_metadata(output_path, result)
                logger.info(f"Sync audio conversion successful: {output_path}")
            else:
                result.error_message = self._extract_ffmpeg_error(process_result.stderr)
                logger.error(f"Sync audio conversion failed: {result.error_message}")

                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            result.error_message = (
                f"Unexpected error during sync audio conversion: {str(e)}"
            )
            logger.exception(f"Sync audio conversion error for {input_path}")

        return result

    def _generate_output_path(self, input_path: str, output_format: str) -> str:
        """Generate output file path."""
        input_file = Path(input_path)
        timestamp = int(time.time() * 1000)

        output_filename = f"{input_file.stem}_{timestamp}.{output_format}"
        return str(self.temp_dir / output_filename)

    def _build_extraction_command(
        self,
        input_path: str,
        output_path: str,
        output_format: str,
        audio_codec: str,
        sample_rate: int,
        channels: int,
    ) -> List[str]:
        """Build FFmpeg command for audio extraction."""
        cmd = [
            "ffmpeg",
            "-i",
            input_path,
            "-vn",  # No video
            "-acodec",
            audio_codec,
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-y",  # Overwrite output file
            output_path,
        ]

        # Add format-specific options
        if output_format.lower() == "mp3":
            cmd.extend(["-q:a", "2"])  # High quality MP3
        elif output_format.lower() == "flac":
            cmd.extend(["-compression_level", "8"])  # High compression FLAC

        return cmd

    def _build_conversion_command(
        self, input_path: str, output_path: str, target_format: str, quality_preset: str
    ) -> List[str]:
        """Build FFmpeg command for audio conversion."""
        cmd = ["ffmpeg", "-i", input_path]

        # Quality settings based on format and preset
        quality_settings = {
            "mp3": {
                "low": ["-q:a", "6"],
                "medium": ["-q:a", "2"],
                "high": ["-q:a", "0"],
            },
            "flac": {
                "low": ["-compression_level", "0"],
                "medium": ["-compression_level", "5"],
                "high": ["-compression_level", "8"],
            },
            "ogg": {
                "low": ["-q:a", "3"],
                "medium": ["-q:a", "6"],
                "high": ["-q:a", "9"],
            },
        }

        if (
            target_format in quality_settings
            and quality_preset in quality_settings[target_format]
        ):
            cmd.extend(quality_settings[target_format][quality_preset])

        cmd.extend(["-y", output_path])
        return cmd

    def _extract_output_metadata(self, output_path: str, result: FFmpegResult) -> None:
        """Extract metadata from output file synchronously."""
        try:
            # Use ffprobe to extract metadata
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                output_path,
            ]

            process_result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )

            if process_result.returncode == 0:
                metadata = json.loads(process_result.stdout)
                result.metadata = {
                    "duration": metadata.get("format", {}).get("duration"),
                    "size": metadata.get("format", {}).get("size"),
                    "bit_rate": metadata.get("format", {}).get("bit_rate"),
                    "streams": metadata.get("streams", []),
                }
            else:
                logger.warning(f"Failed to extract metadata: {process_result.stderr}")

        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")

    def _extract_ffmpeg_error(self, stderr_text: str) -> str:
        """Extract meaningful error message from FFmpeg stderr."""
        if not stderr_text:
            return "Unknown FFmpeg error"

        # Look for common error patterns
        error_patterns = [
            "No such file or directory",
            "Invalid data found",
            "Permission denied",
            "Disk full",
            "Unknown encoder",
            "Invalid argument",
        ]

        lines = stderr_text.strip().split("\n")
        for line in reversed(lines):  # Check from bottom up
            line = line.strip()
            if any(pattern in line for pattern in error_patterns):
                return line
            # Return lines that start with error indicators
            if line.startswith(("[error]", "Error", "ERROR")):
                return line

        # If no specific error found, return last non-empty line
        for line in reversed(lines):
            if line.strip():
                return line.strip()

        return "Unknown FFmpeg error"

    def cleanup_file(self, file_path: str) -> None:
        """Clean up a single file synchronously."""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {str(e)}")

    def cleanup_files(self, file_paths: List[str]) -> None:
        """Clean up multiple files synchronously."""
        for file_path in file_paths:
            self.cleanup_file(file_path)


class FFmpegProcessor:
    """High-level FFmpeg processor for audio extraction."""

    def __init__(self):
        """Initialize the FFmpeg processor."""
        self.temp_dir = settings.temp_dir_path
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"FFmpeg processor initialized with temp dir: {self.temp_dir}")

    async def _create_subprocess(self, cmd: List[str]) -> asyncio.subprocess.Process:  # type: ignore
        """Create subprocess with Windows compatibility."""
        pass

    async def extract_audio(
        self,
        input_path: str,
        output_format: str = "wav",
        audio_codec: str = "pcm_s16le",
        sample_rate: int = 44100,
        channels: int = 2,
    ) -> FFmpegResult:
        """
        Extract audio from input file.

        Args:
            input_path: Path to input file
            output_format: Output format (wav, mp3, flac, etc.)
            audio_codec: Audio codec to use
            sample_rate: Sample rate in Hz
            channels: Number of audio channels

        Returns:
            FFmpegResult: Processing result
        """
        result = FFmpegResult()
        start_time = asyncio.get_event_loop().time()

        try:
            # Generate output path
            output_path = self._generate_output_path(input_path, output_format)

            # Build FFmpeg command
            cmd = self._build_extraction_command(
                input_path,
                output_path,
                output_format,
                audio_codec,
                sample_rate,
                channels,
            )

            logger.info(f"Starting audio extraction: {input_path} -> {output_path}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            # Execute FFmpeg with Windows compatibility
            process = await self._create_subprocess(cmd)

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=settings.FFMPEG_TIMEOUT
                )
            except asyncio.TimeoutError:
                process.kill()
                result.error_message = (
                    f"FFmpeg processing timed out after {settings.FFMPEG_TIMEOUT}s"
                )
                return result

            result.processing_time = asyncio.get_event_loop().time() - start_time

            if process.returncode == 0:
                result.success = True
                result.output_path = output_path

                # Extract metadata from output
                await self._extract_output_metadata(output_path, result)

                logger.info(f"Audio extraction successful: {output_path}")
            else:
                result.error_message = self._extract_ffmpeg_error(stderr.decode())
                logger.error(f"Audio extraction failed: {result.error_message}")

                # Clean up failed output file
                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            result.error_message = f"Unexpected error during audio extraction: {str(e)}"
            logger.exception(f"Audio extraction error for {input_path}")

        return result

    async def convert_audio_format(
        self, input_path: str, target_format: str, quality_preset: str = "medium"
    ) -> FFmpegResult:
        """
        Convert audio to different format.

        Args:
            input_path: Path to input audio file
            target_format: Target format (mp3, flac, ogg, etc.)
            quality_preset: Quality preset (low, medium, high)

        Returns:
            FFmpegResult: Processing result
        """
        result = FFmpegResult()
        start_time = asyncio.get_event_loop().time()

        try:
            output_path = self._generate_output_path(input_path, target_format)

            # Build conversion command based on format and quality
            cmd = self._build_conversion_command(
                input_path, output_path, target_format, quality_preset
            )

            logger.info(f"Starting audio conversion: {input_path} -> {target_format}")

            process = await self._create_subprocess(cmd)

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=settings.FFMPEG_TIMEOUT
                )
            except asyncio.TimeoutError:
                process.kill()
                result.error_message = (
                    f"Audio conversion timed out after {settings.FFMPEG_TIMEOUT}s"
                )
                return result

            result.processing_time = asyncio.get_event_loop().time() - start_time

            if process.returncode == 0:
                result.success = True
                result.output_path = output_path
                await self._extract_output_metadata(output_path, result)
                logger.info(f"Audio conversion successful: {output_path}")
            else:
                result.error_message = self._extract_ffmpeg_error(stderr.decode())
                logger.error(f"Audio conversion failed: {result.error_message}")

                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            result.error_message = f"Unexpected error during audio conversion: {str(e)}"
            logger.exception(f"Audio conversion error for {input_path}")

        return result

    def _generate_output_path(self, input_path: str, output_format: str) -> str:
        """Generate output file path."""
        input_file = Path(input_path)
        timestamp = int(asyncio.get_event_loop().time() * 1000)

        output_filename = f"{input_file.stem}_{timestamp}.{output_format}"
        return str(self.temp_dir / output_filename)

    def _build_extraction_command(
        self,
        input_path: str,
        output_path: str,
        output_format: str,
        audio_codec: str,
        sample_rate: int,
        channels: int,
    ) -> List[str]:
        """Build FFmpeg command for audio extraction."""
        cmd = [
            "ffmpeg",
            "-i",
            input_path,
            "-vn",  # Disable video
            "-acodec",
            audio_codec,
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-y",  # Overwrite output file
        ]

        # Add format-specific options
        if output_format == "mp3":
            cmd.extend(["-b:a", "192k"])  # 192 kbps for MP3
        elif output_format == "flac":
            cmd.extend(["-compression_level", "5"])  # FLAC compression

        cmd.append(output_path)
        return cmd

    def _build_conversion_command(
        self, input_path: str, output_path: str, target_format: str, quality_preset: str
    ) -> List[str]:
        """Build FFmpeg command for audio format conversion."""
        cmd = ["ffmpeg", "-i", input_path, "-y"]

        # Format-specific settings based on quality preset
        if target_format == "mp3":
            if quality_preset == "low":
                cmd.extend(["-b:a", "128k"])
            elif quality_preset == "high":
                cmd.extend(["-b:a", "320k"])
            else:  # medium
                cmd.extend(["-b:a", "192k"])

        elif target_format == "flac":
            if quality_preset == "low":
                cmd.extend(["-compression_level", "0"])
            elif quality_preset == "high":
                cmd.extend(["-compression_level", "8"])
            else:  # medium
                cmd.extend(["-compression_level", "5"])

        elif target_format == "ogg":
            if quality_preset == "low":
                cmd.extend(["-q:a", "3"])
            elif quality_preset == "high":
                cmd.extend(["-q:a", "9"])
            else:  # medium
                cmd.extend(["-q:a", "6"])

        cmd.append(output_path)
        return cmd

    async def _extract_output_metadata(
        self, output_path: str, result: FFmpegResult
    ) -> None:
        """Extract metadata from processed output file."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,bit_rate,size:stream=codec_name,sample_rate,channels",
                "-of",
                "json",
                output_path,
            ]

            process = await self._create_subprocess(cmd)

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                metadata = json.loads(stdout.decode())
                result.metadata.update(metadata)

                # Add file size
                file_stats = os.stat(output_path)
                result.metadata["output_file_size"] = file_stats.st_size

        except Exception as e:
            logger.warning(f"Failed to extract output metadata: {e}")

    def _extract_ffmpeg_error(self, stderr_text: str) -> str:
        """Extract meaningful error from FFmpeg stderr."""
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
            "can't",
            "conversion failed",
            "not found",
            "permission denied",
            "codec not found",
        ]

        # Check last few lines for errors
        for line in reversed(lines[-5:]):
            line = line.strip()
            if any(keyword in line.lower() for keyword in error_keywords):
                return line[:300]

        # Fallback to last meaningful line
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("[") and len(line) > 10:
                return line[:300]

        return "Unknown FFmpeg error"

    async def cleanup_file(self, file_path: str) -> None:
        """Safely clean up a file."""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")

    async def cleanup_files(self, file_paths: List[str]) -> None:
        """Clean up multiple files."""
        for file_path in file_paths:
            await self.cleanup_file(file_path)

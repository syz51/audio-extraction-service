"""
Event processing service containing business logic for SQS event handling.
"""

import json
from typing import List

from app.schemas.events import EventProcessingResponse, ProcessedRecord
from app.schemas.s3_events import S3Event, S3EventRecord, S3EventTypes
from app.schemas.sqs import SQSEvent, SQSRecord
from app.utils.logging import get_logger
from app.utils.file_validation import AudioFileValidator
from app.utils.ffmpeg_utils import FFmpegProcessor
from app.utils.s3_utils import S3FileManager
from app.core.media_types import is_audio_file

logger = get_logger("services.event_processor")


class EventProcessorService:
    """Service for processing SQS events containing S3 event notifications."""

    def __init__(self):
        """Initialize the event processor with validation and processing utilities."""
        self.validator = AudioFileValidator()
        self.ffmpeg_processor = FFmpegProcessor()
        self.s3_manager = S3FileManager()

    async def process_events(self, event: SQSEvent) -> EventProcessingResponse:
        """
        Process a batch of SQS events containing S3 notifications.

        Args:
            event: The SQS event containing multiple records

        Returns:
            EventProcessingResponse: Summary of processing results
        """

        processed_records: List[ProcessedRecord] = []

        for record in event.Records:
            try:
                processed_record = await self._process_single_record(record)
                processed_records.append(processed_record)
            except Exception as e:
                logger.error(f"Failed to process record {record.messageId}: {e}")
                # Create a failed record entry
                failed_record = ProcessedRecord(
                    messageId=record.messageId,
                    processed=False,
                    body_length=len(record.body),
                    source=record.eventSourceARN,
                )
                processed_records.append(failed_record)

        return EventProcessingResponse(
            status="success",
            processed_count=len(processed_records),
            records=processed_records,
        )

    async def _process_single_record(self, record: SQSRecord) -> ProcessedRecord:
        """
        Process a single SQS record containing an S3 event.

        Args:
            record: Individual SQS record to process

        Returns:
            ProcessedRecord: Processing result for the record
        """

        try:
            # Parse the SQS message body as an S3 event
            s3_event = S3Event.model_validate_json(record.body)

            # Process each S3 record in the event
            for s3_record in s3_event.Records:
                await self._process_s3_record(s3_record)

        except Exception as e:
            logger.error(f"Failed to parse SQS message body as S3 event: {e}")
            raise

        return ProcessedRecord(
            messageId=record.messageId,
            processed=True,
            body_length=len(record.body),
            source=record.eventSourceARN,
        )

    async def _process_s3_record(self, s3_record: S3EventRecord) -> None:
        """
        Process a single S3 event record.

        Args:
            s3_record: Individual S3 event record to process
        """
        bucket_name = s3_record.s3.bucket.name
        object_key = s3_record.s3.object.key
        event_name = s3_record.eventName

        # Check if this is an audio file
        if is_audio_file(object_key):
            # Handle different S3 event types
            if event_name in [
                S3EventTypes.OBJECT_CREATED_PUT,
                S3EventTypes.OBJECT_CREATED_POST,
                S3EventTypes.OBJECT_CREATED_COPY,
                S3EventTypes.OBJECT_CREATED_COMPLETE_MULTIPART_UPLOAD,
            ]:
                await self._handle_audio_file_created(
                    bucket_name, object_key, s3_record
                )
            elif event_name in [
                S3EventTypes.OBJECT_REMOVED_DELETE,
                S3EventTypes.OBJECT_REMOVED_DELETE_MARKER_CREATED,
            ]:
                await self._handle_audio_file_deleted(
                    bucket_name, object_key, s3_record
                )
            else:
                logger.info(f"Unhandled S3 event type for audio file: {event_name}")
        else:
            logger.info(f"Non-audio file, skipping: {object_key}")

    async def _handle_audio_file_created(
        self, bucket_name: str, object_key: str, s3_record: S3EventRecord
    ) -> None:
        """
        Handle audio file creation events with comprehensive validation and processing.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            s3_record: S3 event record
        """

        object_size = s3_record.s3.object.size
        local_file_path = None
        output_files = []

        try:
            # Step 1: Comprehensive validation
            validation_result = await self.validator.validate_audio_file(
                bucket_name, object_key, object_size
            )

            if not validation_result.is_valid:
                logger.error(
                    f"Audio file validation failed for {object_key}. "
                    f"Errors: {validation_result.errors}"
                )
                # Optionally send to dead letter queue or error handling service
                return

            # Log warnings if any
            if validation_result.warnings:
                logger.warning(
                    f"Audio file validation warnings for {object_key}: "
                    f"{validation_result.warnings}"
                )

            # # Step 2: Download file for processing
            # local_file_path = await self.s3_manager.download_file(
            #     bucket_name, object_key
            # )

            # if not local_file_path:
            #     logger.error(
            #         f"Failed to download file: s3://{bucket_name}/{object_key}"
            #     )
            #     return

            # # Step 3: Process audio with FFmpeg
            # processing_results = await self._process_audio_with_ffmpeg(
            #     local_file_path, object_key, validation_result.metadata
            # )

            # if processing_results:
            #     # Step 4: Upload processed files back to S3
            #     await self._upload_processed_files(
            #         processing_results, bucket_name, object_key
            #     )

            #     # Step 5: Store metadata (you could add database integration here)
            #     await self._store_processing_metadata(
            #         bucket_name, object_key, validation_result, processing_results
            #     )

            #     logger.info(f"Successfully processed audio file: {object_key}")
            # else:
            #     logger.error(f"Audio processing failed for: {object_key}")

        except Exception as e:
            logger.exception(f"Unexpected error processing {object_key}: {str(e)}")

        finally:
            # Cleanup local files
            if local_file_path:
                await self.s3_manager.cleanup_local_file(local_file_path)

            # Cleanup any output files
            if output_files:
                await self.ffmpeg_processor.cleanup_files(output_files)

    async def _handle_audio_file_deleted(
        self, bucket_name: str, object_key: str, s3_record: S3EventRecord
    ) -> None:
        """
        Handle audio file deletion events.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            s3_record: S3 event record
        """
        logger.info(f"Processing audio file deletion: s3://{bucket_name}/{object_key}")

        try:
            # Clean up related processed files
            await self._cleanup_processed_files(bucket_name, object_key)

            # Clean up metadata (database records, etc.)
            await self._cleanup_processing_metadata(bucket_name, object_key)

            logger.info(f"Cleaned up resources for deleted file: {object_key}")

        except Exception as e:
            logger.exception(f"Error cleaning up resources for {object_key}: {str(e)}")

    async def _process_audio_with_ffmpeg(
        self, local_file_path: str, object_key: str, metadata: dict
    ) -> List[dict]:
        """
        Process audio file with FFmpeg.

        Args:
            local_file_path: Path to local audio file
            object_key: Original S3 object key
            metadata: Validation metadata

        Returns:
            List of processing results
        """
        logger.info(f"Starting FFmpeg processing for: {object_key}")
        processing_results = []

        try:
            # Example: Extract audio in different formats
            # You can customize this based on your specific requirements

            # 1. Extract high-quality WAV
            wav_result = await self.ffmpeg_processor.extract_audio(
                local_file_path,
                output_format="wav",
                audio_codec="pcm_s16le",
                sample_rate=44100,
                channels=2,
            )

            if wav_result.success:
                processing_results.append(
                    {
                        "format": "wav",
                        "result": wav_result,
                        "description": "High-quality WAV extraction",
                    }
                )
                logger.info(f"WAV extraction successful for {object_key}")
            else:
                logger.error(
                    f"WAV extraction failed for {object_key}: {wav_result.error_message}"
                )

            # 2. Convert to compressed MP3
            mp3_result = await self.ffmpeg_processor.convert_audio_format(
                local_file_path, target_format="mp3", quality_preset="medium"
            )

            if mp3_result.success:
                processing_results.append(
                    {
                        "format": "mp3",
                        "result": mp3_result,
                        "description": "Compressed MP3 conversion",
                    }
                )
                logger.info(f"MP3 conversion successful for {object_key}")
            else:
                logger.error(
                    f"MP3 conversion failed for {object_key}: {mp3_result.error_message}"
                )

            # 3. Extract metadata-rich FLAC (if original isn't FLAC)
            if not object_key.lower().endswith(".flac"):
                flac_result = await self.ffmpeg_processor.convert_audio_format(
                    local_file_path, target_format="flac", quality_preset="high"
                )

                if flac_result.success:
                    processing_results.append(
                        {
                            "format": "flac",
                            "result": flac_result,
                            "description": "Lossless FLAC conversion",
                        }
                    )
                    logger.info(f"FLAC conversion successful for {object_key}")
                else:
                    logger.error(
                        f"FLAC conversion failed for {object_key}: {flac_result.error_message}"
                    )

            return processing_results

        except Exception as e:
            logger.exception(f"FFmpeg processing error for {object_key}: {str(e)}")
            return []

    async def _upload_processed_files(
        self, processing_results: List[dict], bucket_name: str, original_key: str
    ) -> None:
        """
        Upload processed audio files back to S3.

        Args:
            processing_results: List of processing results
            bucket_name: S3 bucket name
            original_key: Original file key
        """
        # Define processed files bucket/prefix
        processed_bucket = bucket_name  # You might want to use a different bucket
        base_key = f"processed/{original_key}"

        for result_data in processing_results:
            if not result_data["result"].success:
                continue

            result = result_data["result"]
            format_name = result_data["format"]

            # Generate S3 key for processed file
            processed_key = f"{base_key}.{format_name}"

            # Upload with metadata
            metadata = {
                "original_file": original_key,
                "processing_format": format_name,
                "processing_time": str(result.processing_time),
                "description": result_data["description"],
            }

            success = await self.s3_manager.upload_file(
                local_path=result.output_path,
                bucket_name=processed_bucket,
                object_key=processed_key,
                metadata=metadata,
            )

            if success:
                logger.info(
                    f"Uploaded processed file: s3://{processed_bucket}/{processed_key}"
                )
            else:
                logger.error(f"Failed to upload processed file: {processed_key}")

    async def _store_processing_metadata(
        self,
        bucket_name: str,
        object_key: str,
        validation_result,
        processing_results: List[dict],
    ) -> None:
        """
        Store processing metadata.

        This is where you would integrate with a database to store metadata
        about the processed files for future reference.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            validation_result: Validation result
            processing_results: Processing results
        """
        try:
            # Example metadata structure
            metadata = {
                "original_file": {
                    "bucket": bucket_name,
                    "key": object_key,
                    "size": validation_result.metadata.get("file_size"),
                    "detected_type": validation_result.file_type,
                    "duration": validation_result.metadata.get("duration"),
                    "format_name": validation_result.metadata.get("format_name"),
                },
                "validation": validation_result.to_dict(),
                "processing": [
                    {
                        "format": r["format"],
                        "success": r["result"].success,
                        "processing_time": r["result"].processing_time,
                        "output_size": r["result"].metadata.get("output_file_size"),
                        "description": r["description"],
                    }
                    for r in processing_results
                ],
                "timestamp": "2024-01-01T00:00:00Z",  # You would use actual timestamp
            }

            # Here you would store this in your database
            # For example: await database.store_processing_metadata(metadata)

            logger.info(f"Processing metadata stored for {object_key}")
            logger.debug(f"Metadata: {json.dumps(metadata, indent=2)}")

        except Exception as e:
            logger.exception(
                f"Failed to store processing metadata for {object_key}: {str(e)}"
            )

    async def _cleanup_processed_files(self, bucket_name: str, object_key: str) -> None:
        """
        Clean up processed files when original is deleted.

        Args:
            bucket_name: S3 bucket name
            object_key: Original S3 object key
        """
        try:
            # List and delete processed files
            # This is a simplified example - you might want to use S3 list operations
            processed_formats = ["wav", "mp3", "flac"]

            for format_name in processed_formats:
                processed_key = f"processed/{object_key}.{format_name}"
                await self.s3_manager.delete_object(bucket_name, processed_key)

            logger.info(f"Cleaned up processed files for {object_key}")

        except Exception as e:
            logger.exception(
                f"Failed to cleanup processed files for {object_key}: {str(e)}"
            )

    async def _cleanup_processing_metadata(
        self, bucket_name: str, object_key: str
    ) -> None:
        """
        Clean up processing metadata when original is deleted.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
        """
        try:
            # Here you would remove database records
            # For example: await database.delete_processing_metadata(bucket_name, object_key)

            logger.info(f"Cleaned up processing metadata for {object_key}")

        except Exception as e:
            logger.exception(
                f"Failed to cleanup processing metadata for {object_key}: {str(e)}"
            )

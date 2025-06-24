"""
Event processing service containing business logic for SQS event handling.
"""

import json
from typing import List

from app.schemas.events import EventProcessingResponse, ProcessedRecord
from app.schemas.s3_events import S3Event, S3EventRecord, S3EventTypes, is_audio_file
from app.schemas.sqs import SQSEvent, SQSRecord
from app.utils.logging import get_logger

logger = get_logger("services.event_processor")


class EventProcessorService:
    """Service for processing SQS events containing S3 event notifications."""

    async def process_events(self, event: SQSEvent) -> EventProcessingResponse:
        """
        Process a batch of SQS events containing S3 notifications.

        Args:
            event: The SQS event containing multiple records

        Returns:
            EventProcessingResponse: Summary of processing results
        """

        logger.info(f"Received {len(event.Records)} SQS records for processing")

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

        logger.info(f"Processing message ID: {record.messageId}")

        try:
            # Parse the SQS message body as an S3 event
            s3_event_data = json.loads(record.body)
            s3_event = S3Event(**s3_event_data)

            logger.info(f"Parsed S3 event with {len(s3_event.Records)} S3 records")

            # Process each S3 record in the event
            for s3_record in s3_event.Records:
                await self._process_s3_record(s3_record)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SQS message body as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse S3 event: {e}")
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
        object_size = s3_record.s3.object.size

        logger.info(f"Processing S3 event: {event_name}")
        logger.info(f"Bucket: {bucket_name}, Object: {object_key}, Size: {object_size}")

        # Check if this is an audio file
        if is_audio_file(object_key):
            logger.info(f"Detected audio file: {object_key}")

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
        self, bucket_name: str, object_key: str, s3_record
    ) -> None:
        """
        Handle audio file creation events.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            s3_record: S3 event record
        """
        logger.info(f"Processing audio file creation: s3://{bucket_name}/{object_key}")

        # TODO: Implement your audio processing logic here
        # This could include:
        # 1. Download the audio file from S3
        # 2. Extract audio if it's a video file
        # 3. Convert audio formats
        # 4. Extract metadata (duration, bitrate, etc.)
        # 5. Generate transcripts
        # 6. Upload processed files back to S3
        # 7. Store metadata in a database

        # Example S3 URL construction
        s3_url = f"s3://{bucket_name}/{object_key}"
        https_url = (
            f"https://{bucket_name}.s3.{s3_record.awsRegion}.amazonaws.com/{object_key}"
        )

        logger.info(f"S3 URL: {s3_url}")
        logger.info(f"HTTPS URL: {https_url}")

        # Simulate processing
        await self._simulate_audio_processing(object_key)

    async def _handle_audio_file_deleted(
        self, bucket_name: str, object_key: str, s3_record
    ) -> None:
        """
        Handle audio file deletion events.

        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key
            s3_record: S3 event record
        """
        logger.info(f"Processing audio file deletion: s3://{bucket_name}/{object_key}")

        # TODO: Implement cleanup logic here
        # This could include:
        # 1. Remove processed files from S3
        # 2. Clean up database records
        # 3. Remove cached data

        logger.info(f"Cleaned up resources for deleted file: {object_key}")

    async def _simulate_audio_processing(self, object_key: str) -> None:
        """
        Simulate audio processing logic.

        Args:
            object_key: The S3 object key to process
        """
        # TODO: Replace with actual audio extraction logic
        # This could include:
        # - Downloading audio files from URLs using boto3
        # - Converting audio formats using ffmpeg
        # - Extracting audio from video files
        # - Uploading processed files to S3
        logger.info(f"Simulating audio processing for: {object_key}")

        # You can add more sophisticated audio processing here
        # For example:
        # - Use boto3 to download the file
        # - Use ffmpeg to extract/convert audio
        # - Use speech-to-text services for transcription
        # - Store results in a database or another S3 bucket

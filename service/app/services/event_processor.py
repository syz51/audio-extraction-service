"""
Event processing service containing business logic for SQS event handling.
"""

import json
from typing import List

from fastapi.encoders import jsonable_encoder

from app.schemas.events import EventProcessingResponse, ProcessedRecord
from app.schemas.sqs import SQSEvent, SQSRecord
from app.utils.logging import get_logger

logger = get_logger("services.event_processor")


class EventProcessorService:
    """Service for processing SQS events."""

    async def process_events(self, event: SQSEvent) -> EventProcessingResponse:
        """
        Process a batch of SQS events.

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
        Process a single SQS record.

        Args:
            record: Individual SQS record to process

        Returns:
            ProcessedRecord: Processing result for the record
        """
        logger.info(f"Processing message ID: {record.messageId}")

        # TODO: Add your actual audio processing logic here
        # For now, we'll just simulate processing
        logger.info(json.dumps(jsonable_encoder(record), indent=4))
        await self._simulate_audio_processing(record.body)

        return ProcessedRecord(
            messageId=record.messageId,
            processed=True,
            body_length=len(record.body),
            source=record.eventSourceARN,
        )

    async def _simulate_audio_processing(self, message_body: str) -> None:
        """
        Simulate audio processing logic.

        Args:
            message_body: The message body to process
        """
        # TODO: Replace with actual audio extraction logic
        # This could include:
        # - Downloading audio files from URLs
        # - Converting audio formats using ffmpeg
        # - Extracting audio from video files
        # - Uploading processed files to S3
        logger.info(f"Simulating audio processing for message: {message_body[:100]}...")

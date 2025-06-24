"""
Tests for service layer components.
"""

import pytest
from unittest.mock import patch

from app.schemas.sqs import SQSEvent, SQSRecord, SQSAttributes
from app.services.event_processor import EventProcessorService


@pytest.fixture
def event_processor():
    """Create an EventProcessorService instance."""
    return EventProcessorService()


@pytest.fixture
def sample_sqs_record():
    """Create a sample SQS record."""
    return SQSRecord(
        messageId="test-message-id",
        receiptHandle="test-receipt-handle",
        body="Test message body",
        attributes=SQSAttributes(
            ApproximateReceiveCount="1",
            SentTimestamp="1609459200000",
            SenderId="test-sender-id",
            ApproximateFirstReceiveTimestamp="1609459200000",
        ),
        messageAttributes={},
        md5OfBody="test-md5-hash",
        eventSource="aws:sqs",
        eventSourceARN="arn:aws:sqs:us-east-1:123456789012:test-queue",
        awsRegion="us-east-1",
    )


@pytest.mark.asyncio
async def test_process_single_record(event_processor, sample_sqs_record):
    """Test processing a single SQS record."""
    result = await event_processor._process_single_record(sample_sqs_record)

    assert result.messageId == "test-message-id"
    assert result.processed is True
    assert result.body_length == len(sample_sqs_record.body)
    assert result.source == sample_sqs_record.eventSourceARN


@pytest.mark.asyncio
async def test_process_events(event_processor, sample_sqs_record):
    """Test processing an SQS event with multiple records."""
    event = SQSEvent(Records=[sample_sqs_record])

    result = await event_processor.process_events(event)

    assert result.status == "success"
    assert result.processed_count == 1
    assert len(result.records) == 1
    assert result.records[0].messageId == "test-message-id"


@pytest.mark.asyncio
async def test_process_events_with_failure(event_processor, sample_sqs_record):
    """Test event processing when a record fails."""
    event = SQSEvent(Records=[sample_sqs_record])

    # Mock the _process_single_record method to raise an exception
    with patch.object(
        event_processor,
        "_process_single_record",
        side_effect=Exception("Processing failed"),
    ):
        result = await event_processor.process_events(event)

    assert result.status == "success"  # Overall status is still success
    assert result.processed_count == 1
    assert len(result.records) == 1
    assert result.records[0].processed is False  # But this record failed

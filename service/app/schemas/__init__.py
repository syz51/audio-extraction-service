"""
Pydantic schemas for request/response validation.
"""

from .events import EventProcessingResponse, ProcessedRecord
from .health import HealthCheckResponse
from .s3_events import (
    S3Event,
    S3EventRecord,
    S3EventData,
    S3Object,
    S3Bucket,
    S3TestEvent,
    S3EventTypes,
    is_audio_file,
)
from .sqs import SQSEvent, SQSRecord, SQSAttributes

__all__ = [
    # Event processing schemas
    "EventProcessingResponse",
    "ProcessedRecord",
    # Health schemas
    "HealthCheckResponse",
    # S3 event schemas
    "S3Event",
    "S3EventRecord",
    "S3EventData",
    "S3Object",
    "S3Bucket",
    "S3TestEvent",
    "S3EventTypes",
    "is_audio_file",
    # SQS schemas
    "SQSEvent",
    "SQSRecord",
    "SQSAttributes",
]

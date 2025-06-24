"""
Event processing response schemas.
"""

from typing import List

from pydantic import BaseModel


class ProcessedRecord(BaseModel):
    """Model for a processed SQS record."""

    messageId: str
    processed: bool
    body_length: int
    source: str


class EventProcessingResponse(BaseModel):
    """Response model for event processing."""

    status: str
    processed_count: int
    records: List[ProcessedRecord]

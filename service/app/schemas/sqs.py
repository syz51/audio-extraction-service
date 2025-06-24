"""
SQS-related Pydantic schemas for request/response validation.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, RootModel


class MessageAttributes(BaseModel):
    """Model for SQS message attributes."""

    stringValue: Optional[str] = None
    stringListValues: Optional[List[str]] = Field(default_factory=list)
    binaryListValues: Optional[List[str]] = Field(default_factory=list)
    dataType: str


class SQSMessageAttributes(RootModel[Dict[str, MessageAttributes]]):
    """Model for SQS message attributes with dynamic keys."""

    root: Dict[str, MessageAttributes] = Field(default_factory=dict)


class SQSAttributes(BaseModel):
    """Model for SQS message attributes."""

    ApproximateReceiveCount: str
    SentTimestamp: str
    SenderId: str
    ApproximateFirstReceiveTimestamp: str
    # Additional attributes for FIFO queues
    SequenceNumber: Optional[str] = None
    MessageGroupId: Optional[str] = None
    MessageDeduplicationId: Optional[str] = None


class SQSRecord(BaseModel):
    """Model for individual SQS record within the event."""

    messageId: str
    receiptHandle: str
    body: str
    attributes: SQSAttributes
    messageAttributes: Dict[str, MessageAttributes] = Field(default_factory=dict)
    md5OfBody: str
    eventSource: str = Field(default="aws:sqs")
    eventSourceARN: str
    awsRegion: str


class SQSEvent(BaseModel):
    """Model for the complete SQS event structure."""

    Records: List[SQSRecord]

"""
Pytest configuration and shared fixtures.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_sqs_event():
    """Create a sample SQS event for testing."""
    return {
        "Records": [
            {
                "messageId": "test-message-id-1",
                "receiptHandle": "test-receipt-handle",
                "body": "Test message body",
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": "1609459200000",
                    "SenderId": "test-sender-id",
                    "ApproximateFirstReceiveTimestamp": "1609459200000",
                },
                "messageAttributes": {},
                "md5OfBody": "test-md5-hash",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:test-queue",
                "awsRegion": "us-east-1",
            }
        ]
    }

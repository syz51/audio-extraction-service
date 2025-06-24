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
    """Create a sample SQS event containing S3 ObjectCreated:Put event for testing."""
    import json

    # S3 event that becomes the SQS message body
    s3_event = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-west-2",
                "eventTime": "1970-01-01T00:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {"principalId": "AIDAJDPLRKLG7UEXAMPLE"},
                "requestParameters": {"sourceIPAddress": "127.0.0.1"},
                "responseElements": {
                    "x-amz-request-id": "C3D13FE58DE4C810",
                    "x-amz-id-2": "FMyUVURIY8/IgAtTv8xRjskZQpcIZ9KG4V5Wp6S7S/JRWeUWerMUE5JgHvANOjpD",
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigRule",
                    "bucket": {
                        "name": "audio-extraction-test-bucket",
                        "ownerIdentity": {"principalId": "A3NL1KOZZKExample"},
                        "arn": "arn:aws:s3:::audio-extraction-test-bucket",
                    },
                    "object": {
                        "key": "audio/test-recording.mp3",
                        "size": 1024,
                        "eTag": "d41d8cd98f00b204e9800998ecf8427e",
                        "versionId": "096fKKXTRTtl3on89fVO.nfljtsv6qko",
                        "sequencer": "0055AED6DCD90281E5",
                    },
                },
            }
        ]
    }

    return {
        "Records": [
            {
                "messageId": "test-message-id-1",
                "receiptHandle": "test-receipt-handle",
                "body": json.dumps(s3_event),  # S3 event JSON becomes the SQS body
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


@pytest.fixture
def sample_sqs_record(sample_sqs_event):
    """Create a sample SQS record (single record from SQS event)."""
    from app.schemas.sqs import SQSRecord, SQSAttributes

    # Extract the first record from the SQS event
    sqs_record_data = sample_sqs_event["Records"][0]

    return SQSRecord(
        messageId=sqs_record_data["messageId"],
        receiptHandle=sqs_record_data["receiptHandle"],
        body=sqs_record_data["body"],
        attributes=SQSAttributes(
            ApproximateReceiveCount=sqs_record_data["attributes"][
                "ApproximateReceiveCount"
            ],
            SentTimestamp=sqs_record_data["attributes"]["SentTimestamp"],
            SenderId=sqs_record_data["attributes"]["SenderId"],
            ApproximateFirstReceiveTimestamp=sqs_record_data["attributes"][
                "ApproximateFirstReceiveTimestamp"
            ],
        ),
        messageAttributes=sqs_record_data["messageAttributes"],
        md5OfBody=sqs_record_data["md5OfBody"],
        eventSource=sqs_record_data["eventSource"],
        eventSourceARN=sqs_record_data["eventSourceARN"],
        awsRegion=sqs_record_data["awsRegion"],
    )

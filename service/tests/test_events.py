"""
Tests for event processing endpoints.
"""


def test_process_sqs_events(client, sample_sqs_event):
    """Test SQS event processing endpoint."""
    response = client.post("/events", json=sample_sqs_event)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["processed_count"] == 1
    assert len(data["records"]) == 1

    record = data["records"][0]
    assert record["messageId"] == "test-message-id-1"
    assert record["processed"] is True
    assert record["body_length"] > 0


def test_process_empty_sqs_event(client):
    """Test processing an empty SQS event."""
    empty_event = {"Records": []}

    response = client.post("/events", json=empty_event)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["processed_count"] == 0
    assert len(data["records"]) == 0


def test_process_invalid_sqs_event(client):
    """Test processing an invalid SQS event."""
    invalid_event = {"invalid": "data"}

    response = client.post("/events", json=invalid_event)

    assert response.status_code == 422  # Validation error

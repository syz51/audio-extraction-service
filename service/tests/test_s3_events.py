"""
Tests for S3 event schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.s3_events import (
    S3Event,
    S3TestEvent,
    S3EventTypes,
    is_audio_file,
)


class TestS3EventSchemas:
    """Test S3 event schema validation."""

    def test_s3_event_with_object_created_put(self):
        """Test S3 event parsing for ObjectCreated:Put event."""
        s3_event_data = {
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
                            "name": "amzn-s3-demo-bucket",
                            "ownerIdentity": {"principalId": "A3NL1KOZZKExample"},
                            "arn": "arn:aws:s3:::amzn-s3-demo-bucket",
                        },
                        "object": {
                            "key": "audio/sample.mp3",
                            "size": 1024,
                            "eTag": "d41d8cd98f00b204e9800998ecf8427e",
                            "versionId": "096fKKXTRTtl3on89fVO.nfljtsv6qko",
                            "sequencer": "0055AED6DCD90281E5",
                        },
                    },
                }
            ]
        }

        # Parse the event
        s3_event = S3Event.model_validate(s3_event_data)

        # Validate the parsed event
        assert len(s3_event.Records) == 1
        record = s3_event.Records[0]

        assert record.eventVersion == "2.1"
        assert record.eventSource == "aws:s3"
        assert record.awsRegion == "us-west-2"
        assert record.eventName == "ObjectCreated:Put"
        assert record.userIdentity.principalId == "AIDAJDPLRKLG7UEXAMPLE"
        assert record.requestParameters.sourceIPAddress == "127.0.0.1"
        assert record.responseElements.x_amz_request_id == "C3D13FE58DE4C810"

        # Validate S3 data
        s3_data = record.s3
        assert s3_data.s3SchemaVersion == "1.0"
        assert s3_data.configurationId == "testConfigRule"
        assert s3_data.bucket.name == "amzn-s3-demo-bucket"
        assert s3_data.bucket.arn == "arn:aws:s3:::amzn-s3-demo-bucket"
        assert s3_data.object.key == "audio/sample.mp3"
        assert s3_data.object.size == 1024
        assert s3_data.object.eTag == "d41d8cd98f00b204e9800998ecf8427e"

    def test_s3_test_event(self):
        """Test S3 test event parsing."""
        test_event_data = {
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Time": "2014-10-13T15:57:02.089Z",
            "Bucket": "amzn-s3-demo-bucket",
            "RequestId": "5582815E1AEA5ADF",
            "HostId": "8cLeGAmw098X5cv4Zkwcmo8vvZa3eH3eKxsPzbB9wrR+YstdA6Knx4Ip8EXAMPLE",
        }

        test_event = S3TestEvent.model_validate(test_event_data)

        assert test_event.Service == "Amazon S3"
        assert test_event.Event == "s3:TestEvent"
        assert test_event.Bucket == "amzn-s3-demo-bucket"
        assert test_event.RequestId == "5582815E1AEA5ADF"

    def test_s3_event_with_multiple_records(self):
        """Test S3 event with multiple records."""
        s3_event_data = {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "us-west-2",
                    "eventTime": "1970-01-01T00:00:00.000Z",
                    "eventName": "ObjectCreated:Put",
                    "userIdentity": {"principalId": "EXAMPLE1"},
                    "requestParameters": {"sourceIPAddress": "127.0.0.1"},
                    "responseElements": {
                        "x-amz-request-id": "REQ1",
                        "x-amz-id-2": "ID1",
                    },
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "configurationId": "config1",
                        "bucket": {
                            "name": "bucket1",
                            "ownerIdentity": {"principalId": "OWNER1"},
                            "arn": "arn:aws:s3:::bucket1",
                        },
                        "object": {"key": "file1.mp3", "size": 1024},
                    },
                },
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "us-west-2",
                    "eventTime": "1970-01-01T00:01:00.000Z",
                    "eventName": "ObjectRemoved:Delete",
                    "userIdentity": {"principalId": "EXAMPLE2"},
                    "requestParameters": {"sourceIPAddress": "127.0.0.2"},
                    "responseElements": {
                        "x-amz-request-id": "REQ2",
                        "x-amz-id-2": "ID2",
                    },
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "configurationId": "config2",
                        "bucket": {
                            "name": "bucket2",
                            "ownerIdentity": {"principalId": "OWNER2"},
                            "arn": "arn:aws:s3:::bucket2",
                        },
                        "object": {"key": "file2.wav"},
                    },
                },
            ]
        }

        s3_event = S3Event.model_validate(s3_event_data)

        assert len(s3_event.Records) == 2

        # First record
        record1 = s3_event.Records[0]
        assert record1.eventName == "ObjectCreated:Put"
        assert record1.s3.object.key == "file1.mp3"
        assert record1.s3.object.size == 1024

        # Second record
        record2 = s3_event.Records[1]
        assert record2.eventName == "ObjectRemoved:Delete"
        assert record2.s3.object.key == "file2.wav"
        assert record2.s3.object.size is None  # Delete events may not have size

    def test_invalid_s3_event_missing_required_fields(self):
        """Test validation error for missing required fields."""
        invalid_event_data = {
            "Records": [
                {
                    "eventVersion": "2.1",
                    # Missing required fields
                }
            ]
        }

        with pytest.raises(ValidationError):
            S3Event.model_validate(invalid_event_data)

    def test_s3_event_with_glacier_restore_data(self):
        """Test S3 event with glacier restore event data."""
        s3_event_data = {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "us-west-2",
                    "eventTime": "1970-01-01T00:00:00.000Z",
                    "eventName": "ObjectRestore:Completed",
                    "userIdentity": {"principalId": "EXAMPLE"},
                    "requestParameters": {"sourceIPAddress": "127.0.0.1"},
                    "responseElements": {"x-amz-request-id": "REQ", "x-amz-id-2": "ID"},
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "configurationId": "config",
                        "bucket": {
                            "name": "glacier-bucket",
                            "ownerIdentity": {"principalId": "OWNER"},
                            "arn": "arn:aws:s3:::glacier-bucket",
                        },
                        "object": {"key": "archived-file.mp3"},
                    },
                    "glacierEventData": {
                        "restoreEventData": {
                            "lifecycleRestorationExpiryTime": "2023-01-01T00:00:00.000Z",
                            "lifecycleRestoreStorageClass": "GLACIER",
                        }
                    },
                }
            ]
        }

        s3_event = S3Event.model_validate(s3_event_data)
        record = s3_event.Records[0]

        assert record.eventName == "ObjectRestore:Completed"
        assert record.glacierEventData is not None
        assert record.glacierEventData.restoreEventData is not None
        assert (
            record.glacierEventData.restoreEventData.lifecycleRestoreStorageClass
            == "GLACIER"
        )


class TestAudioFileDetection:
    """Test audio file detection utility."""

    def test_is_audio_file_audio_extensions(self):
        """Test audio file detection for common audio extensions."""
        audio_files = [
            "sample.mp3",
            "music.wav",
            "audio.flac",
            "podcast.m4a",
            "song.aac",
            "recording.ogg",
            "track.wma",
            "voice.opus",
            "folder/subfolder/music.mp3",
            "UPPERCASE.MP3",
            "Mixed_Case.WaV",
        ]

        for file_key in audio_files:
            assert is_audio_file(file_key), f"Should detect {file_key} as audio file"

    def test_is_audio_file_video_extensions(self):
        """Test audio file detection for video files (which may contain audio)."""
        video_files = [
            "video.mp4",
            "movie.m4v",
            "clip.avi",
            "presentation.mov",
            "recording.mkv",
            "stream.webm",
        ]

        for file_key in video_files:
            assert is_audio_file(file_key), (
                f"Should detect {file_key} as containing audio"
            )

    def test_is_audio_file_non_audio_extensions(self):
        """Test that non-audio files are not detected as audio."""
        non_audio_files = [
            "document.pdf",
            "image.jpg",
            "photo.png",
            "data.json",
            "config.yaml",
            "script.py",
            "readme.txt",
            "archive.zip",
            "spreadsheet.xlsx",
            "presentation.pptx",
        ]

        for file_key in non_audio_files:
            assert not is_audio_file(file_key), (
                f"Should NOT detect {file_key} as audio file"
            )

    def test_is_audio_file_edge_cases(self):
        """Test edge cases for audio file detection."""
        edge_cases = [
            ("", False),  # Empty string
            ("no_extension", False),  # No extension
            (".mp3", True),  # Just extension
            ("file.", False),  # Dot but no extension
            ("file.mp3.backup", False),  # Extension not at end
            ("audio.mp3/folder", False),  # Extension in middle of path
        ]

        for file_key, expected in edge_cases:
            result = is_audio_file(file_key)
            assert result == expected, (
                f"Expected {expected} for '{file_key}', got {result}"
            )


class TestS3EventTypes:
    """Test S3 event type constants."""

    def test_event_type_constants(self):
        """Test that S3 event type constants are correct."""
        assert S3EventTypes.OBJECT_CREATED_PUT == "ObjectCreated:Put"
        assert S3EventTypes.OBJECT_CREATED_POST == "ObjectCreated:Post"
        assert S3EventTypes.OBJECT_CREATED_COPY == "ObjectCreated:Copy"
        assert S3EventTypes.OBJECT_REMOVED_DELETE == "ObjectRemoved:Delete"
        assert S3EventTypes.OBJECT_RESTORE_COMPLETED == "ObjectRestore:Completed"
        assert S3EventTypes.TEST_EVENT == "s3:TestEvent"

    def test_creation_event_types(self):
        """Test grouping of creation event types."""
        creation_events = [
            S3EventTypes.OBJECT_CREATED_PUT,
            S3EventTypes.OBJECT_CREATED_POST,
            S3EventTypes.OBJECT_CREATED_COPY,
            S3EventTypes.OBJECT_CREATED_COMPLETE_MULTIPART_UPLOAD,
        ]

        for event_type in creation_events:
            assert "ObjectCreated:" in event_type

    def test_deletion_event_types(self):
        """Test grouping of deletion event types."""
        deletion_events = [
            S3EventTypes.OBJECT_REMOVED_DELETE,
            S3EventTypes.OBJECT_REMOVED_DELETE_MARKER_CREATED,
        ]

        for event_type in deletion_events:
            assert "ObjectRemoved:" in event_type

"""
AWS S3 Event notification schemas based on official AWS S3 event structure.

These models represent the structure of S3 events that are sent to SQS and then
processed by this service. The S3 event becomes the 'body' of the SQS message.

References:
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-content-structure.html
- Event versions supported: 2.1, 2.2, 2.3
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class S3UserIdentity(BaseModel):
    """User identity information for S3 events."""

    principalId: str = Field(
        ..., description="Amazon customer ID of the user who caused the event"
    )


class S3RequestParameters(BaseModel):
    """Request parameters from the S3 event."""

    sourceIPAddress: str = Field(
        ..., description="IP address where the request came from"
    )


class S3ResponseElements(BaseModel):
    """Response elements from the S3 event."""

    x_amz_request_id: str = Field(
        ..., alias="x-amz-request-id", description="Amazon S3 generated request ID"
    )
    x_amz_id_2: str = Field(
        ..., alias="x-amz-id-2", description="Amazon S3 host that processed the request"
    )


class S3BucketOwnerIdentity(BaseModel):
    """S3 bucket owner identity information."""

    principalId: str = Field(..., description="Amazon customer ID of the bucket owner")


class S3Bucket(BaseModel):
    """S3 bucket information in the event."""

    name: str = Field(..., description="S3 bucket name")
    ownerIdentity: S3BucketOwnerIdentity = Field(
        ..., description="Bucket owner information"
    )
    arn: str = Field(..., description="S3 bucket ARN")


class S3Object(BaseModel):
    """S3 object information in the event."""

    key: str = Field(..., description="S3 object key (URL encoded)")
    size: Optional[int] = Field(None, description="Object size in bytes")
    eTag: Optional[str] = Field(None, description="Object ETag")
    versionId: Optional[str] = Field(
        None, description="Object version ID if versioning enabled"
    )
    sequencer: Optional[str] = Field(
        None, description="Hexadecimal value to determine event sequence"
    )


class S3RestoreEventData(BaseModel):
    """Restore event data for S3 Glacier events."""

    lifecycleRestorationExpiryTime: Optional[datetime] = Field(
        None, description="The time of Restore Expiry in ISO-8601 format"
    )
    lifecycleRestoreStorageClass: Optional[str] = Field(
        None, description="Source storage class for restore"
    )


class S3GlacierEventData(BaseModel):
    """Glacier event data (only present for ObjectRestore:Completed events)."""

    restoreEventData: Optional[S3RestoreEventData] = Field(
        None, description="Restore event data"
    )


class S3ReplicationEventData(BaseModel):
    """Replication event data (only present for replication events)."""

    # Additional fields can be added based on replication event requirements
    pass


class S3IntelligentTieringEventData(BaseModel):
    """Intelligent Tiering event data (only present for S3 Intelligent-Tiering events)."""

    # Additional fields can be added based on intelligent tiering event requirements
    pass


class S3LifecycleEventData(BaseModel):
    """Lifecycle event data (only present for S3 Lifecycle transition events)."""

    # Additional fields can be added based on lifecycle event requirements
    pass


class S3EventData(BaseModel):
    """S3-specific event data."""

    s3SchemaVersion: str = Field(..., description="S3 schema version (typically '1.0')")
    configurationId: str = Field(
        ..., description="ID from bucket notification configuration"
    )
    bucket: S3Bucket = Field(..., description="S3 bucket information")
    object: S3Object = Field(..., description="S3 object information")


class S3EventRecord(BaseModel):
    """Individual S3 event record."""

    eventVersion: str = Field(
        ..., description="Event version (e.g., '2.1', '2.2', '2.3')"
    )
    eventSource: str = Field(
        default="aws:s3", description="Event source (always 'aws:s3')"
    )
    awsRegion: str = Field(..., description="AWS region where the event occurred")
    eventTime: datetime = Field(..., description="Event timestamp in ISO-8601 format")
    eventName: str = Field(..., description="S3 event type (e.g., 'ObjectCreated:Put')")
    userIdentity: S3UserIdentity = Field(..., description="User identity information")
    requestParameters: S3RequestParameters = Field(
        ..., description="Request parameters"
    )
    responseElements: S3ResponseElements = Field(..., description="Response elements")
    s3: S3EventData = Field(..., description="S3-specific event data")

    # Optional event-specific data (only present for certain event types)
    glacierEventData: Optional[S3GlacierEventData] = Field(
        None, description="Glacier event data (only for ObjectRestore:Completed events)"
    )
    replicationEventData: Optional[S3ReplicationEventData] = Field(
        None, description="Replication event data (only for replication events)"
    )
    intelligentTieringEventData: Optional[S3IntelligentTieringEventData] = Field(
        None,
        description="Intelligent Tiering event data (only for S3 Intelligent-Tiering events)",
    )
    lifecycleEventData: Optional[S3LifecycleEventData] = Field(
        None,
        description="Lifecycle event data (only for S3 Lifecycle transition events)",
    )


class S3Event(BaseModel):
    """Complete S3 event notification structure.

    This represents the structure that S3 sends to SQS. When your service receives
    an SQS message, the S3 event will be in the SQS message body as JSON.
    """

    Records: List[S3EventRecord] = Field(..., description="List of S3 event records")


class S3TestEvent(BaseModel):
    """S3 test event structure.

    This is the test message that S3 sends when you first configure event notifications.
    """

    Service: str = Field(default="Amazon S3", description="Service name")
    Event: str = Field(default="s3:TestEvent", description="Event type")
    Time: datetime = Field(..., description="Event timestamp")
    Bucket: str = Field(..., description="S3 bucket name")
    RequestId: str = Field(..., description="Request ID")
    HostId: str = Field(..., description="Host ID")


# Common S3 Event Types (for reference and validation)
class S3EventTypes:
    """Common S3 event types for reference."""

    # Object creation events
    OBJECT_CREATED_PUT = "ObjectCreated:Put"
    OBJECT_CREATED_POST = "ObjectCreated:Post"
    OBJECT_CREATED_COPY = "ObjectCreated:Copy"
    OBJECT_CREATED_COMPLETE_MULTIPART_UPLOAD = "ObjectCreated:CompleteMultipartUpload"

    # Object deletion events
    OBJECT_REMOVED_DELETE = "ObjectRemoved:Delete"
    OBJECT_REMOVED_DELETE_MARKER_CREATED = "ObjectRemoved:DeleteMarkerCreated"

    # Object restore events
    OBJECT_RESTORE_POST = "ObjectRestore:Post"
    OBJECT_RESTORE_COMPLETED = "ObjectRestore:Completed"
    OBJECT_RESTORE_DELETE = "ObjectRestore:Delete"

    # Reduced Redundancy Storage events
    REDUCED_REDUNDANCY_LOST_OBJECT = "ReducedRedundancyLostObject"

    # Replication events
    REPLICATION_OPERATION_FAILED_REPLICATION = "Replication:OperationFailedReplication"
    REPLICATION_OPERATION_MISSED_THRESHOLD = "Replication:OperationMissedThreshold"
    REPLICATION_OPERATION_REPLICATED_AFTER_THRESHOLD = (
        "Replication:OperationReplicatedAfterThreshold"
    )
    REPLICATION_OPERATION_NOT_TRACKED = "Replication:OperationNotTracked"

    # Test event
    TEST_EVENT = "s3:TestEvent"

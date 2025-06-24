"""
Event processing API endpoints.
"""

from fastapi import APIRouter

from app.schemas.events import EventProcessingResponse
from app.schemas.sqs import SQSEvent
from app.services.event_processor import EventProcessorService

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventProcessingResponse)
async def process_sqs_events(event: SQSEvent) -> EventProcessingResponse:
    """
    Process SQS events received from AWS.

    This endpoint accepts SQS event payloads and processes each record
    in the batch. The event structure follows AWS SQS Lambda integration format.
    """
    event_processor = EventProcessorService()
    return await event_processor.process_events(event)

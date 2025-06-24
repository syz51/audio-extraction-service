"""
Health check API endpoints.
"""

from fastapi import APIRouter

from app.schemas.health import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
    )

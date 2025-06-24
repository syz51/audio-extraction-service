"""
Health check schemas.
"""

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str

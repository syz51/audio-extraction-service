"""
Main API v1 router that combines all route handlers.
"""

from fastapi import APIRouter

from app.api.v1.routes import events, health

# Create the main v1 router
api_v1_router = APIRouter()

# Include individual route handlers
api_v1_router.include_router(events.router)
api_v1_router.include_router(health.router)

"""
Main API router that combines all route handlers.
"""

from fastapi import APIRouter

from app.api.routes import events

# Create the main router
api_router = APIRouter()

# Include individual route handlers
api_router.include_router(events.router)

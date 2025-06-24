"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    setup_logging()
    yield
    # Shutdown
    pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Initialize FastAPI app
    app = FastAPI(
        lifespan=lifespan,
    )

    # Include API routers
    app.include_router(api_router)

    return app


# Create the app instance
app = create_app()

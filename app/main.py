"""
FastAPI application entry point.

This module creates and configures the FastAPI app instance, registers all
routers, and sets up startup / shutdown lifecycle events.

The app is structured to be production-ready:
- Descriptive OpenAPI metadata so the /docs page is useful
- CORS enabled (wide open for development, should be locked down in production)
- Structured logging configured at startup
- Mock data seeded on first run if data files are missing
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, data, llm
from app.utils.logging import configure_logging
from app.utils.mock_data import seed_data_files

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks when the server starts, teardown tasks on shutdown."""

    # Ensure data files exist so the connectors don't crash immediately
    data_dir = Path(settings.DATA_DIR)
    if not (data_dir / "customers.json").exists():
        logger.warning("Data files not found – seeding mock data now")
        seed_data_files(settings.DATA_DIR)
    else:
        logger.info("Data files found at %s", data_dir.resolve())

    logger.info(
        "Starting %s v%s | debug=%s | max_results=%d",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.DEBUG,
        settings.MAX_RESULTS,
    )

    yield  # Server is running

    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    """Factory function that assembles and returns the FastAPI application."""

    configure_logging(debug=settings.DEBUG)

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "A Universal Data Connector that provides a unified REST interface for "
            "an LLM to query CRM, support ticket, and analytics data sources through "
            "function calling.  Responses are optimized for voice conversations – "
            "concise, prioritized, and annotated with freshness metadata."
        ),
        contact={
            "name": "Universal Data Connector",
            "url": "https://github.com/your-org/universal-data-connector",
        },
        license_info={"name": "MIT"},
        lifespan=lifespan,
    )

    # Allow all origins during development – restrict this in production
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    application.include_router(health.router)
    application.include_router(data.router)
    application.include_router(llm.router)

    return application


app = create_app()

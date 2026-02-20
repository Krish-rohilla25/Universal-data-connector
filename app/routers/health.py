"""
Health check router.

Provides a simple /health endpoint for load balancers and readiness probes,
plus a /health/info endpoint with the application version and configuration
summary.  For Docker health checks the /health endpoint is all you need.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", summary="Basic health check")
def health_check():
    """Returns ok when the service is up and running."""
    logger.debug("Health check called")
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/info", summary="Application info")
def app_info():
    """Returns the application name, version, and current configuration limits."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "max_results": settings.MAX_RESULTS,
        "max_voice_results": settings.MAX_VOICE_RESULTS,
        "debug": settings.DEBUG,
    }

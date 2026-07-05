from fastapi import APIRouter, status, HTTPException
import logging

from app.services.analytics.system_health import SystemHealth

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Return production-grade health status of the system."""
    try:
        report = await SystemHealth.get_report()
        return report
    except Exception as e:
        logger.exception("Failed to compute system health report.")
        raise HTTPException(status_code=500, detail=str(e))

"""Health and status routes."""

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    provider = "none"
    try:
        provider = settings.resolve_provider()
    except ValueError:
        pass

    return HealthResponse(
        status="DICOM AI Report API is running",
        version=settings.app_version,
        ai_provider=provider,
        dr7_configured=settings.dr7_enabled,
        gemini_configured=settings.gemini_enabled,
    )

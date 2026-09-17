from fastapi import APIRouter

from app.core.config import settings
from app.schemas.chat import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_provider=settings.llm_provider,
        model=settings.active_model,
        crm=settings.leadrat_base_url,
    )

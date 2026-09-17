from fastapi import APIRouter

from app.api.deps import JWTToken
from app.core.context import use_jwt
from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import Lead, LeadFilters

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/search", response_model=list[Lead])
def search_leads(
    jwt: JWTToken,
    source: str | None = None,
    location: str | None = None,
    status: str | None = None,
) -> list[Lead]:
    with use_jwt(jwt):
        filters = LeadFilters(source=source, location=location, status=status)
        return get_crm_client().search_leads(filters)


@router.get("/{lead_id}", response_model=Lead)
def get_lead(lead_id: str, jwt: JWTToken) -> Lead:
    with use_jwt(jwt):
        return get_crm_client().get_lead(lead_id)

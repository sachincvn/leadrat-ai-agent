"""File-backed CRM for local development. Synthetic data only."""

import json
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import LeadNotFoundError
from app.integrations.crm.base import CRMClient
from app.schemas.lead import Lead, LeadFilters


@lru_cache
def _load_leads() -> list[Lead]:
    rows = json.loads(settings.mock_data_file.read_text(encoding="utf-8"))
    return [Lead(**row) for row in rows]


class MockCRMClient(CRMClient):
    def get_lead(self, lead_id: str) -> Lead:
        for lead in _load_leads():
            if lead.id.lower() == lead_id.lower():
                return lead
        raise LeadNotFoundError(f"Lead '{lead_id}' not found")

    def search_leads(self, filters: LeadFilters) -> list[Lead]:
        def matches(lead: Lead) -> bool:
            if filters.lead_ids and lead.id not in filters.lead_ids:
                return False
            for field in ("source", "status", "location"):
                wanted = getattr(filters, field)
                if wanted and (getattr(lead, field) or "").lower() != wanted.lower():
                    return False
            if filters.keyword and filters.keyword.lower() not in lead.name.lower():
                return False
            return True

        return [lead for lead in _load_leads() if matches(lead)][: filters.limit]

"""CRM contract. Every client — mock or live — implements this."""

from abc import ABC, abstractmethod

from app.schemas.lead import Lead, LeadFilters


class CRMClient(ABC):
    @abstractmethod
    def get_lead(self, lead_id: str) -> Lead: ...

    @abstractmethod
    def search_leads(self, filters: LeadFilters) -> list[Lead]: ...

"""One file per Leadrat API.

Adding an endpoint: new file here holding its path, body builder and row
mapper, then call it from LeadratClient.
"""

from app.integrations.crm.leadrat.endpoints.get_all_leads import get_all_leads
from app.integrations.crm.leadrat.endpoints.get_all_users import get_all_users
from app.integrations.crm.leadrat.endpoints.get_amenity_categories import get_amenity_categories
from app.integrations.crm.leadrat.endpoints.get_area_units import get_area_units
from app.integrations.crm.leadrat.endpoints.get_lead_history import get_lead_history
from app.integrations.crm.leadrat.endpoints.get_project_types import get_project_types
from app.integrations.crm.leadrat.endpoints.get_property_types import get_property_types
from app.integrations.crm.leadrat.endpoints.get_statuses import get_statuses
from app.integrations.crm.leadrat.endpoints.get_user_profile import get_user_profile

__all__ = [
    "get_all_leads",
    "get_all_users",
    "get_amenity_categories",
    "get_area_units",
    "get_lead_history",
    "get_project_types",
    "get_property_types",
    "get_statuses",
    "get_user_profile",
]

"""One file per Leadrat API.

Adding an endpoint: new file here holding its path, body builder and row
mapper, then call it from LeadratClient.
"""

from app.integrations.crm.leadrat.endpoints.get_all_leads import get_all_leads
from app.integrations.crm.leadrat.endpoints.get_all_users import get_all_users
from app.integrations.crm.leadrat.endpoints.get_lead_history import get_lead_history
from app.integrations.crm.leadrat.endpoints.get_user_profile import get_user_profile

__all__ = ["get_all_leads", "get_all_users", "get_lead_history", "get_user_profile"]

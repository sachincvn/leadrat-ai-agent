"""One file per Leadrat API.

Adding an endpoint: new file here holding its path, body builder and row
mapper, then call it from LeadratClient.
"""

from app.integrations.crm.leadrat.endpoints.get_all_leads import get_all_leads

__all__ = ["get_all_leads"]

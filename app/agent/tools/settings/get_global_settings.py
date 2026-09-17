"""Tool: tenant configuration - which features are enabled, supported countries.

Backed by GET /globalsettings/anonymous.
"""

import json

from langchain_core.tools import tool

from app.integrations.crm.factory import get_crm_client


@tool
def get_global_settings() -> str:
    """Get this tenant's configuration - which features are switched on
    (WhatsApp integration, lead rotation, microsite, export, duplicate
    detection, custom statuses) and which countries the tenant supports.

    Use this for "is WhatsApp enabled for us", "do we support international
    leads", "which countries are we set up for".
    """
    settings = get_crm_client().get_global_settings()
    if settings is None:
        return json.dumps({"error": "No settings data returned"})
    return settings.model_dump_json(exclude_none=True)

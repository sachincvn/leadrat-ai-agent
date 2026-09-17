"""Tenant global-settings models, from GET /globalsettings/anonymous.

Leadrat's own response carries ~70 internal feature-flag fields; only the
ones a chat question could plausibly be about are modeled here.
"""

from pydantic import BaseModel


class CountryInfo(BaseModel):
    name: str | None = None
    code: str | None = None
    currency: str | None = None
    phone_code: str | None = None


class GlobalSettings(BaseModel):
    has_international_support: bool | None = None
    is_leads_export_enabled: bool | None = None
    is_properties_export_enabled: bool | None = None
    is_whatsapp_enabled: bool | None = None
    is_microsite_feature_enabled: bool | None = None
    is_lead_rotation_enabled: bool | None = None
    is_duplicate_feature_enabled: bool | None = None
    is_custom_status_enabled: bool | None = None
    countries: list[CountryInfo] = []

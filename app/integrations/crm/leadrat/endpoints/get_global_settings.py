"""GET /globalsettings/anonymous - tenant configuration and supported countries.

Confirmed against the live Swagger spec (operation MCP_GetWithoutPermission,
no request body, checked 2026-09-17).
"""

from typing import Any

from app.core.logging import get_logger
from app.integrations.crm.leadrat.http import LeadratHttp
from app.schemas.global_settings import CountryInfo, GlobalSettings

log = get_logger(__name__)

PATH = "/globalsettings/anonymous"


def to_country(row: dict) -> CountryInfo:
    return CountryInfo(
        name=row.get("name") or row.get("countryName"),
        code=row.get("code") or row.get("countryCode"),
        currency=row.get("currency") or row.get("currencyCode"),
        phone_code=row.get("phoneCode") or row.get("dialCode"),
    )


def get_global_settings(http: LeadratHttp) -> GlobalSettings | None:
    payload = http.get(PATH)
    data: Any = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None

    countries = data.get("countries") or []
    return GlobalSettings(
        has_international_support=data.get("hasInternationalSupport"),
        is_leads_export_enabled=data.get("isLeadsExportEnabled"),
        is_properties_export_enabled=data.get("isPropertiesExportEnabled"),
        is_whatsapp_enabled=data.get("isWhatsAppEnabled"),
        is_microsite_feature_enabled=data.get("isMicrositeFeatureEnabled"),
        is_lead_rotation_enabled=data.get("isLeadRotationEnabled"),
        is_duplicate_feature_enabled=data.get("isDuplicateFeatureAdded"),
        is_custom_status_enabled=data.get("isCustomStatusEnabled"),
        countries=[to_country(c) for c in countries if isinstance(c, dict)],
    )

"""Leadrat serialises enquiry.leadSource as a numeric code. This maps it back.

Mirrors LeadSourceCatalog in the Leadrat MCP server - keep in sync when the
backend adds sources.
"""

CODE_TO_NAME: dict[int, str] = {
    0: "Direct", 1: "IVR", 2: "Facebook", 3: "LinkedIn", 4: "Google Ads",
    5: "Magic Bricks", 6: "99 Acres", 7: "Housing.com", 8: "GharOffice",
    9: "Referral", 10: "Walk In", 11: "Website", 12: "Gmail", 13: "Microsite",
    14: "Portfolio", 15: "Phonebook", 16: "Call Logs", 17: "Lead Pool",
    18: "Square Yards", 19: "Quikr Homes", 20: "Just Lead", 21: "WhatsApp",
    22: "YouTube", 23: "QR Code", 24: "Instagram", 25: "OLX", 26: "Estate Dekho",
    27: "Google Sheets", 28: "Channel Partner", 29: "Real Estate India",
    30: "Common Floor", 31: "Data", 32: "Roof & Floor", 33: "Microsoft Ads",
    34: "PropertyWala", 35: "Project Microsite", 36: "MyGate", 37: "Flipkart",
    38: "Property Finder", 39: "Bayut", 40: "Dubizzle", 41: "Webhook",
    42: "TikTok", 43: "Snapchat", 44: "GoogleAdsCampaign", 45: "ViaSocket",
    46: "Pabbly", 47: "RCS", 48: "BoardsAndHoardings", 49: "ExcelData",
    50: "OrganizationAssociation", 51: "BrochuresDistribution", 52: "PaperAds",
    53: "FM", 54: "ListingMicrosite", 55: "Skyloov",
}


def _normalize(value: str) -> str:
    return "".join(value.strip().lower().split()).replace("-", "")


_NAME_TO_CODE = {_normalize(name): code for code, name in sorted(CODE_TO_NAME.items())}


def display_name(code: int | None) -> str | None:
    return CODE_TO_NAME.get(code) if code is not None else None


def code_for(name: str) -> int | None:
    """Resolve a source the user typed, e.g. 'facebook' -> 2."""
    return _NAME_TO_CODE.get(_normalize(name))


# "Microsite" is a virtual alias covering both the property and project
# microsite sources at once, matching old mcp's behaviour: a caller who
# does not say which kind ("leads from microsite") means both.
_MICROSITE_ALIASES: dict[str, list[int]] = {
    "microsite": [13, 35],
    "propertymicrosite": [13],
    "projectmicrosite": [35],
}


def codes_for(name: str) -> list[int]:
    """Resolve one source name to one or more codes.

    Most names map to a single code via `code_for`; "Microsite" (and the
    explicit "PropertyMicrosite"/"ProjectMicrosite") expand to the codes
    above. Returns an empty list for a name that doesn't match anything.
    """
    alias = _MICROSITE_ALIASES.get(_normalize(name))
    if alias is not None:
        return alias
    code = code_for(name)
    return [code] if code is not None else []

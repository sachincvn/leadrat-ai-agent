"""Shared name/label -> id/code resolution for the lead tools.

Leadrat's lead search takes GUIDs and integer enum codes on the wire, but the
model only ever has the words the user typed ("Hot", "New", "Priya",
"Apartment"). This module is the single place that turns those words into
what the API expects, so search_leads and get_lead_counts (which must send
identical filters to compare like-for-like) resolve names exactly the same
way - mirroring old mcp's shared buildLeadSearchFilter/resolve* helpers.

Every enum table below was confirmed against the live Swagger schema at
https://connect.leadrat.info/swagger/v1/swagger.json (the x-enumNames on
LeadFilterTypeWeb, BaseLeadVisibility, LeadTagEnum, OwnerSelectionType,
BHKType, Purpose, OfferType, FurnishStatus, Profession,
MeetingOrVisitCompletionStatus and LeadDateType), so the integer codes here
are exact, not guessed.
"""

from app.core.clock import resolve_range, resolve_relative_date
from uuid import UUID

from app.core.context import get_jwt
from app.core.jwt_claims import user_id as jwt_user_id
from app.core.jwt_claims import user_name as jwt_user_name
from app.core.logging import get_logger
from app.integrations.crm.factory import get_crm_client
from app.integrations.crm.leadrat.lead_sources import codes_for as source_codes_for
from app.schemas.lead import LeadDateFilter

log = get_logger(__name__)


def _normalize(value: str) -> str:
    return "".join(value.strip().lower().split())


def _matches(display_name: str | None, internal_name: str | None, query: str) -> bool:
    q = query.strip().lower()
    return bool(
        (display_name and q in display_name.lower())
        or (internal_name and q in internal_name.lower())
    )


# --- enum tables (name -> Leadrat's wire integer code) ---

FILTER_TYPE: dict[str, int] = {
    "all": 0, "new": 1, "today": 2, "overdue": 3, "notinterested": 4,
    "dropped": 5, "escalated": 6, "pending": 7, "booked": 8, "upcoming": 9,
    "allwithnid": 10, "bookingcancel": 11,
}

LEAD_VISIBILITY: dict[str, int] = {
    "selfwithreportee": 0, "self": 1, "reportee": 2, "unassignlead": 3,
    "deletedleads": 4, "duplicateleads": 5, "reenquired": 6,
    "pendingassignment": 7, "leadpool": 8,
}

OWNER_SELECTION: dict[str, int] = {
    "both": 0, "primaryowner": 1, "primary": 1, "secondaryowner": 2, "secondary": 2,
}

LEAD_TAGS: dict[str, int] = {
    "hot": 0, "abouttoconvert": 1, "escalated": 2, "integrationlead": 3,
    "highlighted": 4, "warm": 5, "cold": 6,
}

BHK_TYPES: dict[str, int] = {"simplex": 1, "duplex": 2, "penthouse": 3, "others": 4}

PURPOSES: dict[str, int] = {"investment": 1, "selfuse": 2}

OFFER_TYPES: dict[str, int] = {"ready": 1, "offplan": 2, "secondary": 3}

FURNISHED: dict[str, int] = {"unfurnished": 1, "semifurnished": 2, "furnished": 3}

PROFESSIONS: dict[str, int] = {
    "salaried": 1, "business": 2, "selfemployed": 3, "doctor": 4, "retired": 5,
    "housewife": 6, "student": 7, "unemployed": 8, "others": 9,
}

MEETING_OR_VISIT_STATUSES: dict[str, int] = {
    "ismeetingdone": 1, "ismeetingnotdone": 2, "issitevisitdone": 3, "issitevisitnotdone": 4,
}

# LeadDateType: 0=All, 1=ReceivedDate ... 9=ReEnquiredDate. "created"/"received"
# and "modified"/"updated" are the two aliases old mcp calls out explicitly.
LEAD_DATE_TYPE: dict[str, int] = {
    "all": 0, "receiveddate": 1, "received": 1, "created": 1, "createddate": 1,
    "scheduleddate": 2, "scheduled": 2, "modifieddate": 3, "modified": 3, "updated": 3,
    "deleteddate": 4, "deleted": 4, "possessiondate": 5, "possession": 5,
    "pickeddate": 6, "picked": 6, "bookeddate": 7, "booked": 7,
    "assigneddate": 8, "assigned": 8, "reenquireddate": 9, "reenquired": 9,
}


def _parse_one(table: dict[str, int], value: str) -> int | None:
    return table.get(_normalize(value))


def parse_codes(table: dict[str, int], values: list[str] | None) -> list[int] | None:
    """Resolve a list of labels against an enum table. Unknown labels are
    dropped (and logged) rather than failing the whole call."""
    if not values:
        return None
    codes: list[int] = []
    for value in values:
        code = _parse_one(table, value)
        if code is None:
            log.warning("Unrecognised filter value '%s' - ignored", value)
        else:
            codes.append(code)
    codes = sorted(set(codes))
    return codes or None


def parse_code(table: dict[str, int], value: str | None) -> int | None:
    if not value:
        return None
    code = _parse_one(table, value)
    if code is None:
        log.warning("Unrecognised filter value '%s' - ignored", value)
    return code


def resolve_source_codes(names: list[str] | None) -> list[int] | None:
    if not names:
        return None
    codes: list[int] = []
    for name in names:
        found = source_codes_for(name)
        if not found:
            log.warning("Unrecognised lead source '%s' - ignored", name)
        codes.extend(found)
    codes = sorted(set(codes))
    return codes or None


def _resolve_dates(from_date: str, to_date: str) -> tuple[str, str]:
    """Replace any relative word with a real date off the server's clock.

    The prompt tells the model today's date, but a model that writes "today" or
    "this month" into a filter anyway must not reach the CRM with it. An ISO
    date the model worked out itself is passed through untouched - it is the
    one form we cannot second-guess.
    """
    if from_date.strip().lower() == to_date.strip().lower():
        span = resolve_range(from_date)
        if span:
            return span

    start = resolve_relative_date(from_date)
    if start is None:
        span = resolve_range(from_date)
        start = span[0] if span else from_date

    end = resolve_relative_date(to_date)
    if end is None:
        span = resolve_range(to_date)
        end = span[1] if span else to_date

    return start, end


def parse_date_filters(entries: list[dict] | None) -> list[LeadDateFilter] | None:
    """entries: [{"date_type": "ReceivedDate", "from_date": "2026-06-23", "to_date": "2026-06-23"}, ...]

    from_date/to_date are ISO dates, or a relative word ("today", "this month")
    resolved here against the server clock - never against the model's idea of
    what day it is.
    """
    if not entries:
        return None
    parsed: list[LeadDateFilter] = []
    for entry in entries:
        date_type = entry.get("date_type") or entry.get("dateType")
        from_date = entry.get("from_date") or entry.get("fromDate")
        to_date = entry.get("to_date") or entry.get("toDate")
        if date_type and from_date and not to_date:
            to_date = from_date  # a single day sent with only one end
        if not (date_type and from_date and to_date):
            log.warning("Incomplete date filter %s - ignored", entry)
            continue
        code = LEAD_DATE_TYPE.get(_normalize(str(date_type)))
        if code is None:
            log.warning("Unrecognised date field '%s' - ignored", date_type)
            continue
        start, end = _resolve_dates(str(from_date), str(to_date))
        if (start, end) != (from_date, to_date):
            log.info("Date filter %s..%s resolved to %s..%s", from_date, to_date, start, end)
        parsed.append(LeadDateFilter(date_type=code, from_date=start, to_date=end))
    return parsed or None


def _is_guid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _my_user_id() -> str | None:
    """The caller's own user GUID.

    Tokens differ by tenant: some carry the GUID in a claim, others carry only
    a login name like "surya_sachin". A name cannot go into assignTo - the
    field is typed System.Guid and the whole request fails with a 400, not just
    that filter - so a name is looked up in the tenant's user directory and
    turned into the GUID it stands for.
    """
    jwt = get_jwt()
    if not jwt:
        log.warning("Could not resolve 'me' - no caller JWT on this request")
        return None

    my_id = jwt_user_id(jwt)
    if my_id:
        return my_id

    login = jwt_user_name(jwt)
    if not login:
        log.warning("Could not resolve 'me' - the caller's JWT carries neither a user id nor a name")
        return None

    handle = login.split("@")[0].strip().lower()
    for user in get_crm_client().list_users():
        candidates = [
            (user.user_name or "").strip().lower(),
            f"{user.first_name or ''} {user.last_name or ''}".strip().lower(),
        ]
        if handle in candidates and _is_guid(user.id):
            log.info("Resolved 'me' to %s via the user directory", user.user_name)
            return user.id

    log.warning("Could not resolve 'me' - no user in the directory matches '%s'", login)
    return None


def resolve_user_ids(names: list[str] | None) -> list[str] | None:
    """Name -> user GUID, with "me" resolved from the caller's own JWT."""
    if not names:
        return None
    ids: list[str] = []
    remaining: list[str] = []
    for name in names:
        if name.strip().lower() == "me":
            my_id = _my_user_id()
            if my_id:
                ids.append(my_id)
        else:
            remaining.append(name)

    if remaining:
        users = get_crm_client().list_users()
        for name in remaining:
            matched = [
                u.id
                for u in users
                if _matches(f"{u.first_name or ''} {u.last_name or ''}".strip(), u.user_name, name)
            ]
            if not matched:
                log.warning("No user matched '%s' - ignored", name)
            ids.extend(matched)

    ids = list(dict.fromkeys(ids))  # de-dupe, keep order
    # Last line of defence: Leadrat types these fields System.Guid, and one bad
    # value 400s the entire request rather than being ignored.
    valid = [i for i in ids if _is_guid(i)]
    for bad in set(ids) - set(valid):
        log.warning("Dropping user id '%s' - not a GUID", bad)
    return valid or None


def resolve_status_ids(names: list[str] | None, sub_status: bool = False) -> list[str] | None:
    """Name -> lead-status GUID, resolved against the tenant's real status tree."""
    if not names:
        return None
    tree = get_crm_client().list_statuses()
    ids: list[str] = []
    for name in names:
        matched: list[str] = []
        for parent in tree:
            if sub_status:
                for child in parent.children or []:
                    if _matches(child.display_name, child.status, name):
                        matched.append(child.id)
            elif _matches(parent.display_name, parent.status, name):
                matched.append(parent.id)
        if not matched:
            log.warning("No %sstatus matched '%s' - ignored", "sub-" if sub_status else "", name)
        ids.extend(matched)
    ids = list(dict.fromkeys(ids))
    return ids or None


def resolve_property_type_ids(names: list[str] | None, sub_type: bool = False) -> list[str] | None:
    """Name -> property-type GUID, resolved against the tenant's real type tree."""
    if not names:
        return None
    tree = get_crm_client().list_property_types()
    ids: list[str] = []
    for name in names:
        matched: list[str] = []
        for parent in tree:
            if sub_type:
                for child in parent.children or []:
                    if _matches(child.display_name, child.type, name):
                        matched.append(child.id)
            elif _matches(parent.display_name, parent.type, name):
                matched.append(parent.id)
        if not matched:
            log.warning("No property %stype matched '%s' - ignored", "sub-" if sub_type else "", name)
        ids.extend(matched)
    ids = list(dict.fromkeys(ids))
    return ids or None


def build_lead_filters(
    *,
    keyword: str = "",
    limit: int = 10,
    page: int = 1,
    filter_type: str = "",
    lead_visibility: str = "",
    lead_tags: list[str] | None = None,
    date_filters: list[dict] | None = None,
    min_budget: int | None = None,
    max_budget: int | None = None,
    assigned_to_names: list[str] | None = None,
    owner_selection: str = "",
    secondary_user_names: list[str] | None = None,
    status_names: list[str] | None = None,
    sub_status_names: list[str] | None = None,
    property_type_names: list[str] | None = None,
    property_sub_type_names: list[str] | None = None,
    cities: list[str] | None = None,
    states: list[str] | None = None,
    countries: list[str] | None = None,
    zones: list[str] | None = None,
    locations: list[str] | None = None,
    projects: list[str] | None = None,
    sources: list[str] | None = None,
    sub_sources: list[str] | None = None,
    beds: list[int] | None = None,
    baths: list[int] | None = None,
    no_of_bhks: list[float] | None = None,
    bhk_types: list[str] | None = None,
    purposes: list[str] | None = None,
    offer_types: list[str] | None = None,
    furnished: list[str] | None = None,
    professions: list[str] | None = None,
    meeting_or_visit_statuses: list[str] | None = None,
    company_name: str = "",
    referral_name: str = "",
    is_with_team: bool | None = None,
    campaign_names: list[str] | None = None,
    utm_sources: list[str] | None = None,
):
    """Build a resolved LeadFilters from the tool-facing (human-readable)
    arguments shared by search_leads and get_lead_counts. Kept in one place
    so the two tools always resolve identical filters the same way.
    """
    from app.schemas.lead import LeadFilters  # local import - avoids a cycle at module load

    assigned_ids = resolve_user_ids(assigned_to_names)
    secondary_ids = resolve_user_ids(secondary_user_names)
    owner = parse_code(OWNER_SELECTION, owner_selection)
    if owner is None and assigned_ids and not secondary_ids:
        # "my leads" / "Darshan's leads" is an ownership question, not a claim
        # about which slot the person sits in. Leaving this unset lets the
        # backend answer on the primary owner alone, which silently hides every
        # lead the person owns as secondary - the same ask against the Leadrat
        # MCP server returns them, because its tool contract makes the model
        # send Both. A small model does not reliably do that, so the default
        # lives here instead of in the prompt.
        owner = OWNER_SELECTION["both"]

    return LeadFilters(
        keyword=keyword or None,
        limit=max(1, min(limit, 500)),
        page=max(1, page),
        filter_type=parse_code(FILTER_TYPE, filter_type),
        lead_visibility=parse_code(LEAD_VISIBILITY, lead_visibility),
        lead_tags=parse_codes(LEAD_TAGS, lead_tags),
        date_filters=parse_date_filters(date_filters),
        min_budget=min_budget,
        max_budget=max_budget,
        assigned_to_ids=assigned_ids,
        owner_selection=owner,
        secondary_user_ids=secondary_ids,
        status_ids=resolve_status_ids(status_names, sub_status=False),
        sub_status_ids=resolve_status_ids(sub_status_names, sub_status=True),
        property_type_ids=resolve_property_type_ids(property_type_names, sub_type=False),
        property_sub_type_ids=resolve_property_type_ids(property_sub_type_names, sub_type=True),
        cities=cities or None,
        states=states or None,
        countries=countries or None,
        zones=zones or None,
        locations=locations or None,
        projects=projects or None,
        source_codes=resolve_source_codes(sources),
        sub_sources=sub_sources or None,
        beds=beds or None,
        baths=baths or None,
        no_of_bhks=no_of_bhks or None,
        bhk_type_codes=parse_codes(BHK_TYPES, bhk_types),
        purpose_codes=parse_codes(PURPOSES, purposes),
        offer_type_codes=parse_codes(OFFER_TYPES, offer_types),
        furnished_codes=parse_codes(FURNISHED, furnished),
        profession_codes=parse_codes(PROFESSIONS, professions),
        meeting_or_visit_status_codes=parse_codes(MEETING_OR_VISIT_STATUSES, meeting_or_visit_statuses),
        company_name=company_name or None,
        referral_name=referral_name or None,
        is_with_team=is_with_team,
        campaign_names=campaign_names or None,
        utm_sources=utm_sources or None,
    )

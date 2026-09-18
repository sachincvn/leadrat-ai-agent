"""Turning one tool's output into the blocks the client renders.

One renderer per tool, keyed by tool name. A tool with no renderer simply
produces no blocks - the answer is then text only, which is the correct
result for a tool whose output has no shape worth drawing.

Every list tool maps onto the same record_list block. A record becomes a
title, a subtitle, a badge and a list of labelled details; which CRM field
fills each slot is the only thing that differs between leads, projects,
properties and listings.

The details are what lets the answer stop repeating the records in prose - a
client that draws these cards says so on the request, and the model is then
told the fields are already on screen.

Renderers never raise: a block is a bonus on top of the answer, so anything
unexpected in a tool result costs the block, not the turn.
"""

import json
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.agent.genui.blocks import Block
from app.core.logging import get_logger

log = get_logger(__name__)

MAX_STATUS_TILES = 8

# Only counts a user actually asks about. The lead counts API returns far more
# buckets than anyone wants on screen, most of them null for a given tenant.
ACTIVE_COUNT_TILES = (
    ("new_leads_count", "New"),
    ("active_leads_count", "Active"),
    ("pending_leads_count", "Pending"),
    ("scheduled_leads_count", "Scheduled"),
    ("overdue_leads_count", "Overdue"),
    ("booked_leads_count", "Booked"),
)
BASE_COUNT_TILES = (
    ("all_leads_count", "All leads"),
    ("my_leads_count", "My leads"),
    ("team_leads_count", "Team leads"),
    ("unassign_leads_count", "Unassigned"),
)
# Projects and properties are both counted by category, and each spells the
# third one differently, so both spellings are listed and only one can match.
CATEGORY_TILES = (
    ("all", "All"),
    ("residential", "Residential"),
    ("commercial", "Commercial"),
    ("agriculture", "Agriculture"),
    ("agricultural", "Agricultural"),
)


# ------------------------------------------------------------------ helpers


def _join(*parts: Any) -> str:
    """The non-empty parts of a subtitle, in the order given."""
    return " · ".join(str(part) for part in parts if part not in (None, "", []))


def _record_list(kind: str, title: str, total: Any, records: list[dict]) -> list[Block]:
    rows = [record for record in records if record.get("id")]
    if not rows:
        return []
    return [
        Block(
            name="record_list",
            props={"title": title, "kind": kind, "total": total, "records": rows},
        )
    ]


def _details(*pairs: tuple[str, Any]) -> list[dict]:
    """Labelled fields for a card, minus the ones the CRM did not fill."""
    return [{"label": label, "value": str(value)} for label, value in pairs if value]


def _chips(*prompts: str) -> Block:
    return Block(name="action_chips", props={"prompts": list(prompts)})


def _more_chips(total: Any, shown: int, *prompts: str) -> list[Block]:
    """Follow-ups, offered only where there is more to see.

    On a complete result a "show the next ones" chip would return nothing,
    which is worse than no chip at all.
    """
    if not total or total <= shown:
        return []
    return [_chips(*prompts)]


def _tiles(source: dict | None, fields: tuple[tuple[str, str], ...]) -> list[dict]:
    if not source:
        return []
    return [
        {"label": label, "value": source[key]}
        for key, label in fields
        if source.get(key) is not None
    ]


def _stat_tiles(title: str, tiles: list[dict]) -> list[Block]:
    if not tiles:
        return []
    return [Block(name="stat_tiles", props={"title": title, "tiles": tiles})]


def _price_range(low: Any, high: Any) -> str:
    if isinstance(low, (int, float)) and isinstance(high, (int, float)):
        return f"{low:,.0f} - {high:,.0f}"
    value = low if low is not None else high
    return f"{value:,.0f}" if isinstance(value, (int, float)) else ""


def _count_of(value: Any, unit: str) -> str | None:
    return f"{value} {unit}" if value else None



# ------------------------------------------------- lead history formatting

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Audit values arrive as raw API payloads, so the keys are the wire's names.
# These are the ones worth showing, in the order they read best.
HISTORY_FIELD_LABELS = (
    ("Name", "Name"),
    ("ProjectName", "Project"),
    ("PropertyName", "Property"),
    ("ExecutiveName", "Executive"),
    ("ExecutiveContactNo", "Contact"),
    ("Location", "Location"),
    ("Status", "Status"),
    ("SubStatus", "Sub-status"),
    ("Remarks", "Remarks"),
    ("Note", "Note"),
    ("ScheduledOn", "Scheduled"),
    ("AppointmentDate", "Appointment"),
)
MAX_HISTORY_DETAILS = 4


def _readable_date(value: str) -> str:
    """An ISO timestamp as a person would write it, or the value untouched."""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return value
    return moment.strftime("%d %b %Y, %I:%M %p").lstrip("0").replace(" 0", " ")


def _readable_value(value: Any) -> str | None:
    """One audit value, or None when there is nothing worth showing."""
    if value in (None, "", [], {}):
        return None
    text = str(value).strip()
    if not text or text.lower() in ("null", "none"):
        return None
    # An id is what the audit trail stores instead of a name; it means nothing
    # to the person reading it.
    if _UUID_RE.match(text):
        return None
    if len(text) > 18 and text[:4].isdigit() and "-" in text:
        return _readable_date(text)
    return text


def _describe_change(raw: str | None) -> str:
    """A change as a sentence, out of whatever the audit trail stored.

    Leadrat records some changes as a label and a JSON snapshot of the whole
    record - mostly nulls, ids and timestamps. Rendered as-is it is a wall of
    `"ProjectName":null`. This keeps the handful of fields that were actually
    filled in, under names a person recognises.
    """
    if not raw:
        return ""

    text = str(raw).strip()
    start = text.find("{")
    if start == -1:
        return _readable_value(text) or ""

    label = text[:start].strip(" -:")
    try:
        payload = json.loads(text[start:])
    except ValueError:
        return label or ""

    if not isinstance(payload, dict):
        return label or ""

    parts = []
    for key, display in HISTORY_FIELD_LABELS:
        value = _readable_value(payload.get(key))
        if value:
            parts.append(f"{display}: {value}")
        if len(parts) == MAX_HISTORY_DETAILS:
            break

    if not parts:
        # Nothing in the snapshot was filled in - the label is the whole story.
        return label
    detail = ", ".join(parts)
    return f"{label} - {detail}" if label else detail


# ---------------------------------------------------------------- renderers


def _lead_row(lead: dict) -> dict:
    """One lead as a card.

    Status, source and owner - the three a list is actually scanned for. The
    sub-source, the project and what is scheduled are answers to a question
    about one lead, not things to carry on every row of ten.
    """
    return {
        "id": lead.get("id"),
        "title": lead.get("name"),
        "subtitle": _join(lead.get("phone"), lead.get("location")),
        "badge": lead.get("status"),
        "details": _details(
            ("Source", lead.get("source")),
            ("Owner", lead.get("assigned_to")),
        ),
    }


def _leads(data: dict) -> list[Block]:
    records = [_lead_row(lead) for lead in data.get("leads", [])]
    total = data.get("total_matching_leads")
    return _record_list("lead", "Matching leads", total, records) + _more_chips(
        total, len(records), "Show me the next ones", "Break these down by status"
    )


def _single_lead(data: dict) -> list[Block]:
    """One lead asked about by itself gets the whole record, not a row.

    A row is for choosing between leads; this is the screen someone works
    from, so it carries the contact details, where the lead came from, what
    they want and what is next.
    """
    if not data.get("id"):
        return []

    return [
        Block(
            name="lead_detail",
            props={
                "id": data.get("id"),
                "name": data.get("name"),
                "status": data.get("status"),
                "phone": data.get("phone"),
                "email": data.get("email"),
                "fields": _details(
                    ("Source", _join(data.get("source"), data.get("sub_source"))),
                    ("Owner", data.get("assigned_to")),
                    ("Location", data.get("location")),
                    ("Project", data.get("project")),
                    ("Requirement", data.get("requirement")),
                    ("Next scheduled", data.get("scheduled_at")),
                    ("Created", data.get("created_at")),
                    ("Last updated", data.get("last_modified_at")),
                ),
            },
        ),
        _chips(
            "Summarize this lead and what I should do next",
            "Show this lead's history",
        ),
    ]


def _brief(data: dict) -> list[Block]:
    """A lead as something to act on.

    The stats are the three numbers a salesperson opens a lead to find, and
    the signals are the facts that decide the next move - both worked out by
    the tool, not by the model. The prose beside this block is where the
    advice lives.
    """
    lead = data.get("lead") or {}
    if not lead.get("id"):
        return []

    stats = _details(
        ("In pipeline", _count_of(data.get("days_in_pipeline"), "days")),
        ("Last update", _count_of(data.get("days_since_update"), "days ago")),
        ("Owner", lead.get("assigned_to")),
    )

    return [
        Block(
            name="lead_brief",
            props={
                "id": lead.get("id"),
                "name": lead.get("name"),
                "status": lead.get("status"),
                "phone": lead.get("phone"),
                "email": lead.get("email"),
                "stats": stats,
                "signals": data.get("signals") or [],
                "fields": _details(
                    ("Wants", lead.get("requirement")),
                    ("Project", lead.get("project")),
                    ("Location", lead.get("location")),
                    ("Source", _join(lead.get("source"), lead.get("sub_source"))),
                    ("Next scheduled", lead.get("scheduled_at")),
                ),
            },
        ),
        _chips("Show this lead's history", "Find similar leads"),
    ]


def _history(data: dict) -> list[Block]:
    """A lead's audit trail as a timeline.

    Each entry is one field changing, so the change itself is the headline -
    "Status: New to Callback" - with who and when underneath.
    """
    entries = []
    for entry in data.get("history", []):
        old = _describe_change(entry.get("old_value"))
        new = _describe_change(entry.get("new_value"))

        # "Status" is a better headline than "Lead" when the API labels the
        # row by the record rather than the field that moved.
        field = entry.get("field_name") or ""
        category = entry.get("category") or ""
        title = category if field.lower() in ("", "lead") and category else field
        title = title or entry.get("action_type") or "Updated"

        if old and new and old != new:
            detail = f"{old} → {new}"
        else:
            detail = new or old

        # A snapshot with nothing filled in describes itself as its own label,
        # which the headline already says.
        if detail == title:
            detail = ""

        entries.append(
            {
                "title": title,
                "detail": detail,
                "by": entry.get("updated_by"),
                "at": _readable_date(entry.get("updated_at") or ""),
            }
        )

    if not entries:
        return []
    return [
        Block(
            name="timeline",
            props={
                "title": "Lead history",
                "total": data.get("total_entries"),
                "entries": entries,
            },
        ),
        # History says what happened; the obvious next question is what to do
        # about it.
        _chips("Summarize this lead and what I should do next"),
    ]


def _projects(data: dict) -> list[Block]:
    records = [
        {
            "id": project.get("id"),
            "title": project.get("name"),
            "subtitle": _price_range(project.get("min_price"), project.get("max_price")),
            "badge": project.get("status") or project.get("current_status"),
            "details": _details(("Possession", project.get("possession_date"))),
        }
        for project in data.get("projects", [])
    ]
    total = data.get("total_matching_projects")
    return _record_list("project", "Projects", total, records) + _more_chips(
        total,
        len(records),
        "Show me the next ones",
        "How many leads do these projects have?",
    )


def _properties(data: dict) -> list[Block]:
    records = [
        {
            "id": prop.get("id"),
            "title": prop.get("title"),
            "subtitle": _join(_count_of(prop.get("no_of_bhk"), "BHK"), prop.get("project")),
            "badge": prop.get("status"),
            "details": _details(
                ("Sale type", prop.get("sale_type")),
                ("Furnishing", prop.get("furnish_status")),
            ),
        }
        for prop in data.get("properties", [])
    ]
    total = data.get("total_matching_properties")
    return _record_list("property", "Properties", total, records) + _more_chips(
        total, len(records), "Show me the next ones", "Break these down by type"
    )


def _listings(data: dict) -> list[Block]:
    records = [
        {
            "id": listing.get("id"),
            "title": listing.get("title"),
            "subtitle": _join(
                _count_of(listing.get("no_of_bedroom"), "bed"),
                _count_of(listing.get("no_of_bathroom"), "bath"),
                listing.get("project"),
            ),
            "badge": listing.get("status"),
            "details": _details(("Leads", listing.get("lead_count"))),
        }
        for listing in data.get("listings", [])
    ]
    total = data.get("total_matching_listings")
    return _record_list("listing", "Listings", total, records) + _more_chips(
        total, len(records), "Show me the next ones"
    )


def _lead_counts(data: dict) -> list[Block]:
    tiles = _tiles(data.get("active_counts"), ACTIVE_COUNT_TILES)
    if not tiles:
        tiles = _tiles(data.get("base_filter_counts"), BASE_COUNT_TILES)
    if tiles:
        return _stat_tiles("Lead counts", tiles)

    # A custom-status tenant answers with per-status counts instead.
    status_tiles = [
        {"label": status["name"], "value": status.get("count", 0)}
        for status in data.get("status_counts", [])
        if status.get("name")
    ][:MAX_STATUS_TILES]
    return _stat_tiles("Leads by status", status_tiles)


def _project_counts(data: dict) -> list[Block]:
    return _stat_tiles("Projects", _tiles(data, CATEGORY_TILES))


def _property_counts(data: dict) -> list[Block]:
    return _stat_tiles("Properties", _tiles(data, CATEGORY_TILES))


# ------------------------------------------------------------- report tables

# A report row carries far more columns than fit on a screen, and which ones
# exist changes per tenant, so the table is capped at what can be read at a
# glance and the rest stays in the JSON the model already has.
MAX_TABLE_COLUMNS = 8
MAX_TABLE_ROWS = 25

# The column a report row is identified by, whichever of these it uses. It is
# pinned first so every report reads left-to-right from "who" or "what".
_LABEL_KEYS = (
    "userName", "name", "displayName", "fullName", "sourceName", "source",
    "subSource", "projectName", "campaignName", "channelPartnerName",
    "countryName", "country", "statusName",
)

# Columns that identify a row to the CRM but mean nothing on screen.
_HIDDEN_KEY_PARTS = ("id", "guid", "uuid")


def _is_hidden_column(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _HIDDEN_KEY_PARTS)


def _column_label(key: str) -> str:
    """"meetingDoneCount" -> "Meeting done"."""
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", key).replace("_", " ").strip()
    words = [word for word in spaced.split() if word.lower() != "count"]
    label = " ".join(words) or spaced
    return label[0].upper() + label[1:].lower() if label else key


def _table_columns(rows: list[dict]) -> list[dict]:
    """The columns worth drawing, label first and the emptiest dropped.

    Report responses are wide and sparse - a tenant that does not use a metric
    still gets its column, full of nulls - so columns are ranked by how often
    they are actually filled rather than by the order the backend listed them.
    """
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys and not _is_hidden_column(key):
                keys.append(key)

    label_key = next((key for key in _LABEL_KEYS if key in keys), None)
    if label_key is None:
        label_key = next((key for key in keys if isinstance(rows[0].get(key), str)), None)

    def filled(key: str) -> int:
        return sum(1 for row in rows if row.get(key) not in (None, "", []))

    others = sorted(
        (key for key in keys if key != label_key and filled(key)),
        key=lambda key: (-filled(key), keys.index(key)),
    )
    chosen = ([label_key] if label_key else []) + others[: MAX_TABLE_COLUMNS - bool(label_key)]
    return [
        {
            "key": key,
            "label": _column_label(key),
            "numeric": any(isinstance(row.get(key), (int, float)) for row in rows),
        }
        for key in chosen
    ]


def _report_table(title: str, data: dict) -> list[Block]:
    """One report as a table, or nothing when it came back empty."""
    rows = [row for row in data.get("rows", []) if isinstance(row, dict)]
    if not rows:
        return []

    columns = _table_columns(rows)
    if not columns:
        return []

    keys = [column["key"] for column in columns]
    return [
        Block(
            name="data_table",
            props={
                "title": title,
                "total": data.get("total"),
                "columns": columns,
                "rows": [
                    {key: row.get(key) for key in keys} for row in rows[:MAX_TABLE_ROWS]
                ],
            },
        )
    ]


def _report(title: str) -> Callable[[dict], list[Block]]:
    """A renderer for one named report."""
    return lambda data: _report_table(title, data)


RENDERERS: dict[str, Callable[[dict], list[Block]]] = {
    "search_leads": _leads,
    "get_lead": _single_lead,
    "get_lead_history": _history,
    "summarize_lead": _brief,
    "get_lead_counts": _lead_counts,
    "list_projects": _projects,
    "get_project_count": _project_counts,
    "list_properties": _properties,
    "get_property_count": _property_counts,
    "list_listings": _listings,
    "get_activity_report": _report("Activity by user"),
    "get_call_report": _report("Calls by user"),
    "get_user_status_report": _report("Leads by user and status"),
    "get_user_substatus_report": _report("Leads by user and sub-status"),
    "get_user_source_report": _report("Leads by user and source"),
    "get_user_subsource_report": _report("Leads by user and sub-source"),
    "get_source_status_report": _report("Leads by source and status"),
    "get_subsource_status_report": _report("Leads by sub-source and status"),
    "get_project_status_report": _report("Leads by project and status"),
    "get_country_status_report": _report("Leads by country and status"),
    "get_campaign_substatus_report": _report("Leads by campaign and sub-status"),
    "get_channel_partner_substatus_report": _report("Leads by channel partner and sub-status"),
    "get_revenue_source_report": _report("Revenue by source"),
    "get_revenue_subsource_report": _report("Revenue by sub-source"),
}


def render_blocks(tool_name: str, output: str) -> list[Block]:
    """Blocks for one tool result, or none at all."""
    renderer = RENDERERS.get(tool_name)
    if renderer is None:
        return []

    try:
        data = json.loads(output)
    except (TypeError, ValueError):
        # A failed tool call is fed back to the model as a sentence, not JSON.
        return []

    if not isinstance(data, dict) or data.get("error"):
        return []

    try:
        return renderer(data)
    except Exception:  # noqa: BLE001 - a block is never worth failing a turn over
        log.warning("genui renderer failed for %s", tool_name, exc_info=True)
        return []

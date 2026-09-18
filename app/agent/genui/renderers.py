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
from collections.abc import Callable
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


# ---------------------------------------------------------------- renderers


def _lead_row(lead: dict) -> dict:
    """One lead as a card.

    `details` carries the labelled fields the card shows under the name -
    where the lead came from, who owns it, what is scheduled. They are the
    things a user scans a list for, and the reason the answer no longer has
    to repeat them in prose.
    """
    return {
        "id": lead.get("id"),
        "title": lead.get("name"),
        "subtitle": _join(lead.get("phone"), lead.get("location")),
        "badge": lead.get("status"),
        "details": _details(
            ("Source", _join(lead.get("source"), lead.get("sub_source"))),
            ("Owner", lead.get("assigned_to")),
            ("Project", lead.get("project")),
            ("Scheduled", lead.get("scheduled_at")),
        ),
    }


def _leads(data: dict) -> list[Block]:
    records = [_lead_row(lead) for lead in data.get("leads", [])]
    total = data.get("total_matching_leads")
    return _record_list("lead", "Matching leads", total, records) + _more_chips(
        total, len(records), "Show me the next ones", "Break these down by status"
    )


def _single_lead(data: dict) -> list[Block]:
    blocks = _record_list("lead", "Lead", None, [_lead_row(data)])
    if blocks:
        blocks.append(_chips("Summarize this lead", "Show this lead's history"))
    return blocks


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


RENDERERS: dict[str, Callable[[dict], list[Block]]] = {
    "search_leads": _leads,
    "get_lead": _single_lead,
    "get_lead_counts": _lead_counts,
    "list_projects": _projects,
    "get_project_count": _project_counts,
    "list_properties": _properties,
    "get_property_count": _property_counts,
    "list_listings": _listings,
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

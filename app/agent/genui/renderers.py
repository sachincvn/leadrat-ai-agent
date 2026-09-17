"""Turning one tool's output into the blocks the client renders.

One renderer per tool, keyed by tool name. A tool with no renderer simply
produces no blocks - the answer is then text only, which is the correct
result for a tool whose output has no shape worth drawing.

Renderers never raise: a block is a bonus on top of the answer, so anything
unexpected in a tool result costs the block, not the turn.
"""

import json
from collections.abc import Callable
from typing import Any

from app.agent.genui.blocks import Block
from app.core.logging import get_logger

log = get_logger(__name__)

# Fields lifted onto a lead row. The client shows what it has room for; the
# rest of the tool output stays with the model.
LEAD_ROW_FIELDS = ("id", "name", "phone", "status", "source", "location", "project")

# Only counts a user actually asks about. The counts API returns far more
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
MAX_STATUS_TILES = 8


def _row(lead: dict) -> dict:
    return {key: lead.get(key) for key in LEAD_ROW_FIELDS if lead.get(key)}


def _chips(*prompts: str) -> Block:
    return Block(name="action_chips", props={"prompts": list(prompts)})


def _lead_list(data: dict) -> list[Block]:
    leads = [_row(lead) for lead in data.get("leads", []) if lead.get("id")]
    if not leads:
        return []

    blocks = [
        Block(
            name="lead_list",
            props={
                "title": "Matching leads",
                "total": data.get("total_matching_leads"),
                "leads": leads,
            },
        )
    ]
    # Chips are offered only where there is more to see; on a complete result
    # a "show the next ones" chip would return nothing.
    total = data.get("total_matching_leads") or 0
    if total > len(leads):
        blocks.append(_chips("Show me the next ones", "Break these down by status"))
    return blocks


def _single_lead(data: dict) -> list[Block]:
    row = _row(data)
    if not row.get("id"):
        return []
    return [
        Block(name="lead_list", props={"title": "Lead", "total": None, "leads": [row]}),
        _chips("Summarize this lead", "Show this lead's history"),
    ]


def _tiles(source: dict | None, fields: tuple[tuple[str, str], ...]) -> list[dict]:
    if not source:
        return []
    return [
        {"label": label, "value": source[key]}
        for key, label in fields
        if source.get(key) is not None
    ]


def _lead_counts(data: dict) -> list[Block]:
    tiles = _tiles(data.get("active_counts"), ACTIVE_COUNT_TILES)
    if not tiles:
        tiles = _tiles(data.get("base_filter_counts"), BASE_COUNT_TILES)

    title = "Lead counts"
    if not tiles:
        # A custom-status tenant answers with per-status counts instead.
        tiles = [
            {"label": status["name"], "value": status.get("count", 0)}
            for status in data.get("status_counts", [])
            if status.get("name")
        ][:MAX_STATUS_TILES]
        title = "Leads by status"

    if not tiles:
        return []
    return [Block(name="stat_tiles", props={"title": title, "tiles": tiles})]


RENDERERS: dict[str, Callable[[Any], list[Block]]] = {
    "search_leads": _lead_list,
    "get_lead": _single_lead,
    "get_lead_counts": _lead_counts,
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

    if not isinstance(data, dict):
        return []

    try:
        return renderer(data)
    except Exception:  # noqa: BLE001 - a block is never worth failing a turn over
        log.warning("genui renderer failed for %s", tool_name, exc_info=True)
        return []

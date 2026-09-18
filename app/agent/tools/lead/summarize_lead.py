"""Tool: everything needed to decide what to do with one lead.

get_lead says what a lead is and get_lead_history says what has happened to
it; deciding the next move needs both, plus the arithmetic nobody should ask
a language model to do - how long the lead has sat, whether the visit that
was booked has now passed, how long since anyone touched it.

So the dates are turned into days here, and the facts worth acting on are
listed as signals. The model writes the advice; it does not compute the
numbers it is advising from.
"""

import json

from langchain_core.tools import tool

from app.core.clock import now
from app.integrations.crm.leadrat.client import LeadratClient
from app.integrations.crm.factory import get_crm_client
from app.schemas.lead import Lead, LeadHistoryEntry

HISTORY_ENTRIES = 10

# A lead nobody has touched in this long is the thing worth saying first.
STALE_DAYS = 7
# Sat in the same status this long without moving.
SLOW_DAYS = 21


def _days_since(value: str | None) -> int | None:
    """Whole days between an ISO timestamp and now, or None if unusable."""
    if not value:
        return None
    try:
        from datetime import datetime

        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=now().tzinfo)
    return (now() - moment).days


def _signal(text: str, tone: str) -> dict:
    """One fact worth acting on. Tone is what the UI colours it by."""
    return {"text": text, "tone": tone}


def _plural(days: int) -> str:
    return "day" if abs(days) == 1 else "days"


def _scheduling_signals(lead: Lead) -> list[dict]:
    days = _days_since(lead.scheduled_at)
    if days is None:
        return [_signal("Nothing scheduled", "warn")]
    if days > 0:
        return [_signal(f"Scheduled {days} {_plural(days)} ago, not closed out", "alert")]
    if days == 0:
        return [_signal("Scheduled for today", "good")]
    return [_signal(f"Scheduled in {abs(days)} {_plural(days)}", "good")]


def _activity_signals(lead: Lead) -> list[dict]:
    signals = []

    untouched = _days_since(lead.last_modified_at)
    if untouched is not None and untouched >= STALE_DAYS:
        signals.append(
            _signal(f"No update in {untouched} {_plural(untouched)}", "alert")
        )

    age = _days_since(lead.created_at)
    if age is not None and age >= SLOW_DAYS:
        signals.append(
            _signal(f"In the pipeline {age} {_plural(age)}", "warn")
        )

    return signals


def _missing_signals(lead: Lead) -> list[dict]:
    """What the record does not say, where that is what blocks the next step."""
    missing = [
        label
        for label, value in (
            ("phone", lead.phone),
            ("requirement", lead.requirement),
            ("project", lead.project),
        )
        if not value
    ]
    if not missing:
        return []
    return [_signal(f"No {', no '.join(missing)} on record", "warn")]


def _last_touch(entries: list[LeadHistoryEntry]) -> dict | None:
    if not entries:
        return None
    latest = entries[0]
    days = _days_since(latest.updated_at)
    return {
        "what": latest.field_name or latest.category or latest.action_type or "Updated",
        "by": latest.updated_by,
        "days_ago": days,
    }


@tool
def summarize_lead(lead_id: str) -> str:
    """Everything needed to advise on one lead: its record, its recent history,
    and the timings worked out - how long it has been in the pipeline, how long
    since anyone touched it, whether what was scheduled has already passed.

    Use this for "summarize this lead", "what should I do with this lead",
    "brief me on this lead" - anything asking what to DO about a lead rather
    than a single fact about it. Use get_lead for one detail and
    get_lead_history for the change log on its own.

    lead_id - the lead's id. Don't have it? search_leads first; never guess.
    """
    client: LeadratClient = get_crm_client()
    lead = client.get_lead(lead_id)
    history = client.get_lead_history(lead_id, limit=HISTORY_ENTRIES)

    signals = (
        _scheduling_signals(lead) + _activity_signals(lead) + _missing_signals(lead)
    )

    return json.dumps(
        {
            "lead": lead.model_dump(exclude_none=True),
            "days_in_pipeline": _days_since(lead.created_at),
            "days_since_update": _days_since(lead.last_modified_at),
            "days_until_scheduled": (
                -d if (d := _days_since(lead.scheduled_at)) is not None else None
            ),
            "signals": signals,
            "last_touch": _last_touch(history.entries),
            "recent_history": [
                entry.model_dump(exclude_none=True) for entry in history.entries
            ],
        },
        default=str,
    )

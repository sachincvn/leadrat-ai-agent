"""What "today" means to this server.

An LLM has no clock. Asked for "leads created this week" it will happily emit
ISO dates from around its training cutoff, and the CRM will answer honestly
about a week in the past. So the current date is never left to the model: it is
stated in the prompt every turn, and any relative word that still arrives in a
tool call is resolved here.

The zone is the one the CRM itself reports in (Asia/Calcutta, matching the
`timeZoneId` on every lead request), not the server's local zone - a container
running in UTC must not shift "today" by five and a half hours.
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CRM_TZ = ZoneInfo("Asia/Calcutta")


def now() -> datetime:
    return datetime.now(CRM_TZ)


def today() -> date:
    return now().date()


def today_iso() -> str:
    return today().isoformat()


def describe_today() -> str:
    """The one line of date context the model gets, e.g. "Thursday, 18 September 2026"."""
    return now().strftime("%A, %d %B %Y")


def _monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _previous_month_start(day: date) -> date:
    return (_month_start(day) - timedelta(days=1)).replace(day=1)


def resolve_relative_date(value: str) -> str | None:
    """Turn a relative word into an ISO date, or None if it isn't one.

    Only single days resolve here. A span ("last 7 days") is two different
    dates depending on which end you ask for, so it is handled by the caller,
    which knows whether it is filling from_date or to_date.
    """
    key = " ".join(value.strip().lower().replace("_", " ").split())
    day = today()
    singles: dict[str, date] = {
        "today": day,
        "now": day,
        "yesterday": day - timedelta(days=1),
        "tomorrow": day + timedelta(days=1),
    }
    return singles[key].isoformat() if key in singles else None


def resolve_range(value: str) -> tuple[str, str] | None:
    """Turn a relative span into (from_date, to_date), or None if it isn't one."""
    key = " ".join(value.strip().lower().replace("_", " ").split())
    day = today()

    ranges: dict[str, tuple[date, date]] = {
        "this week": (_monday_of(day), day),
        "last week": (_monday_of(day) - timedelta(days=7), _monday_of(day) - timedelta(days=1)),
        "this month": (_month_start(day), day),
        "last month": (_previous_month_start(day), _month_start(day) - timedelta(days=1)),
        "this year": (day.replace(month=1, day=1), day),
        "last 7 days": (day - timedelta(days=6), day),
        "last 30 days": (day - timedelta(days=29), day),
        "last 90 days": (day - timedelta(days=89), day),
    }
    span = ranges.get(key)
    return (span[0].isoformat(), span[1].isoformat()) if span else None


def to_utc_instant(value: str | None, end_of_day: bool = False) -> str | None:
    """A date the way Leadrat's "dates" array wants it.

    A plain date means a day in the tenant's own time zone, not in UTC, and the
    backend is given UTC instants - so "2026-06-23" is the start of that day in
    IST, which is "2026-06-22T18:30:00Z". Sending the bare date instead matches
    nothing at all, which is why every window came back empty.

    `end_of_day` is what makes a single day mean a day. Both ends of a range
    are dates, and turning both into the start of their day leaves "today to
    today" describing one instant - a window nothing can fall inside, which is
    why a day's worth of leads came back as none. The closing end is therefore
    the last moment of its day, not the first.

    A value that already carries a time is passed through, as is anything that
    is not an ISO date: the backend validates those itself.
    """
    if value is None:
        return None

    text = value.strip()
    if not text or "T" in text:
        return text or None

    try:
        day = date.fromisoformat(text)
    except ValueError:
        return text

    moment = datetime(day.year, day.month, day.day, tzinfo=CRM_TZ)
    if end_of_day:
        moment += timedelta(days=1, seconds=-1)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

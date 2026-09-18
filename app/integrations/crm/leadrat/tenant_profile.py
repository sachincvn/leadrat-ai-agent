"""Per-tenant and per-caller facts the CRM decides, cached for one request.

Two things about a Leadrat tenant change how a request must be made, and
neither can be guessed from the ask itself:

* `isCustomStatusEnabled` picks which lead endpoint holds that tenant's data -
  "new/all" or "custom-filters". Leadrat's own MCP server reads the setting and
  routes on it; firing the wrong one first and retrying on the failure costs a
  round trip on every call and only works when the wrong endpoint fails loudly.
* The caller's role permissions decide what they may see. `CanAccessAllLeads`
  is sent on every lead request, and the caller's own user id is needed
  whenever they say "my".

Each is fetched at most once per request. They are properties of the caller's
token, so the cache lives in a ContextVar with the token itself rather than in
a module global that would leak one caller's tenant into another's request.
"""

from contextvars import ContextVar
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)

# Permission strings as the Leadrat backend spells them, matching the constants
# in the MCP server's UserProfileServiceImpl.
VIEW_ALL_LEADS = "Permissions.Leads.ViewAllLeads"
VIEW_LEAD_SOURCE = "Permissions.Leads.ViewLeadSource"
VIEW_UNASSIGNED_LEADS = "Permissions.Leads.ViewUnAssignedLead"
VIEW_ALL_USERS = "Permissions.Reports.ViewAllUsers"
VIEW_REPORTEES = "Permissions.Reports.ViewReportees"

# ReportPermission, the scope every report body carries. -1 is not a wire value:
# a caller with neither permission may not run a report at all.
REPORT_ALL_USERS = 0
REPORT_REPORTEES = 1
REPORT_NONE = -1

_cache: ContextVar[dict[str, Any] | None] = ContextVar("leadrat_tenant_profile", default=None)


def _store() -> dict[str, Any]:
    current = _cache.get()
    if current is None:
        current = {}
        _cache.set(current)
    return current


def cached(key: str, produce):
    """Call `produce` once per request for this key; reuse the answer after.

    A failure is cached too, as its fallback value - a tenant setting that
    cannot be read will not start working halfway through the same turn, and
    retrying it on every endpoint call would multiply one outage by the number
    of tools the model runs.
    """
    store = _store()
    if key not in store:
        store[key] = produce()
    return store[key]


def reset() -> None:
    """Forget everything cached for the current request."""
    _cache.set({})

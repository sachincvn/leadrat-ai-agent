"""UI action registry - the contract between the model and the browser.

Every entry becomes one tool the model can call. Unlike the CRM tools, these are
never executed on the server: the model picks an action, this module expands it
into concrete UI steps, and the browser runs them against the real screen.

`target` always names a `data-agent-id` attribute in the frontend - never a CSS
selector, which would break on the next restyle.

Placeholders `{{param}}` are filled by resolver.resolve().
"""

from dataclasses import dataclass
from typing import Any

PAGES = ("dashboard", "leads")
READABLE = ("visible_leads", "status_counts", "current_filters")


@dataclass(frozen=True)
class Param:
    name: str
    description: str
    required: bool = False
    enum: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Action:
    name: str
    description: str
    params: list[Param]
    steps: list[dict[str, Any]]
    destructive: bool = False
    # Actions whose effect stays local until Leadrat exposes a write endpoint.
    # The UI flow, the confirm gate and the validation are already real.
    writes_to_crm: bool = False


ACTIONS: list[Action] = [
    Action(
        name="navigate_to",
        description=(
            "Move the user to a page of the app. Call this before any action that "
            "lives on a different page than the one currently open."
        ),
        params=[
            Param("page", "Which page to open.", required=True, enum=PAGES),
        ],
        steps=[
            {"type": "navigate", "to": "{{page}}", "say": "Opening the {{page}} page"},
        ],
    ),
    Action(
        name="filter_leads",
        description=(
            "Filter the leads table on screen. Pass only the values the user "
            "actually stated; leave the rest out. Use this for requests like "
            "'show me leads from Bangalore' or 'find leads from referrals'. "
            "The result reports the rows now visible."
        ),
        params=[
            Param("keyword", "A name or phone number to search for."),
            Param("location", "City, exactly as it appears in the CRM."),
            Param("source", "Lead source, e.g. Facebook, Google Ads, Referral, Walk In."),
            Param("status", "Lead status, e.g. New, Interested, Qualified."),
        ],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Going to the Leads page"},
            {
                "type": "fill",
                "target": "leads.filter-keyword",
                "value": "{{keyword}}",
                "optional": True,
                "say": 'Searching for "{{keyword}}"',
            },
            {
                "type": "fill",
                "target": "leads.filter-location",
                "value": "{{location}}",
                "optional": True,
                "say": "Filtering location by {{location}}",
            },
            {
                "type": "fill",
                "target": "leads.filter-source",
                "value": "{{source}}",
                "optional": True,
                "say": "Filtering source by {{source}}",
            },
            {
                "type": "fill",
                "target": "leads.filter-status",
                "value": "{{status}}",
                "optional": True,
                "say": "Filtering status by {{status}}",
            },
            {"type": "click", "target": "leads.apply-filters", "say": "Applying the filters"},
            {
                "type": "readState",
                "key": "visible_leads",
                "say": "Reading the rows that came back",
            },
        ],
    ),
    Action(
        name="clear_filters",
        description="Remove every filter on the leads table and show the full list again.",
        params=[],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Going to the Leads page"},
            {"type": "click", "target": "leads.clear-filters", "say": "Clearing the filters"},
            {"type": "readState", "key": "visible_leads", "say": "Reading the full list"},
        ],
    ),
    Action(
        name="open_lead",
        description=(
            "Open one lead's detail panel. Needs the lead id - call filter_leads or "
            "read_screen first if you do not have it. Never invent an id."
        ),
        params=[
            Param("lead_id", "Id of the lead, as returned by a previous tool.", required=True),
        ],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Going to the Leads page"},
            {
                "type": "click",
                "target": "leads.row.{{lead_id}}.open",
                "say": "Opening lead {{lead_id}}",
            },
            {"type": "waitFor", "target": "lead-detail.panel", "say": "Waiting for the details"},
        ],
    ),
    Action(
        name="create_lead",
        description=(
            "Open the new-lead form and fill it in. Ask the user for any field you "
            "do not know instead of inventing a value - never make up a phone number."
        ),
        params=[
            Param("name", "Full name of the lead.", required=True),
            Param("phone", "Phone number.", required=True),
            Param("source", "Where the lead came from, e.g. Referral, Walk In."),
            Param("location", "City."),
        ],
        writes_to_crm=True,
        steps=[
            {"type": "navigate", "to": "leads", "say": "Going to the Leads page"},
            {
                "type": "click",
                "target": "leads.create-button",
                "say": "Opening the new-lead form",
            },
            {"type": "waitFor", "target": "lead-form.name", "say": "Waiting for the form"},
            {
                "type": "fill",
                "target": "lead-form.name",
                "value": "{{name}}",
                "say": "Typing the name",
            },
            {
                "type": "fill",
                "target": "lead-form.phone",
                "value": "{{phone}}",
                "say": "Typing the phone number",
            },
            {
                "type": "fill",
                "target": "lead-form.source",
                "value": "{{source}}",
                "optional": True,
                "say": "Setting the source to {{source}}",
            },
            {
                "type": "fill",
                "target": "lead-form.location",
                "value": "{{location}}",
                "optional": True,
                "say": "Setting the location to {{location}}",
            },
            {
                "type": "confirm",
                "message": "Create this lead?",
                "say": "Asking you to confirm",
            },
            {"type": "click", "target": "lead-form.submit", "say": "Saving the lead"},
            {
                "type": "waitForGone",
                "target": "lead-form.name",
                "say": "Waiting for the form to close",
            },
        ],
    ),
    Action(
        name="assign_owner",
        description=(
            "Assign a lead to a teammate. Needs the lead id and the teammate's name "
            "exactly as it appears in the CRM - call list_users if you are unsure."
        ),
        params=[
            Param("lead_id", "Id of the lead.", required=True),
            Param("owner_name", "Teammate's full name, as shown in the CRM.", required=True),
        ],
        writes_to_crm=True,
        steps=[
            {"type": "navigate", "to": "leads", "say": "Going to the Leads page"},
            {
                "type": "click",
                "target": "leads.row.{{lead_id}}.owner-menu",
                "say": "Opening the owner menu for {{lead_id}}",
            },
            {
                "type": "waitFor",
                "target": "owner-menu.{{owner_name}}",
                "say": "Waiting for the menu",
            },
            {
                "type": "confirm",
                "message": "Assign lead {{lead_id}} to {{owner_name}}?",
                "say": "Asking you to confirm",
            },
            {
                "type": "click",
                "target": "owner-menu.{{owner_name}}",
                "say": "Picking {{owner_name}}",
            },
        ],
    ),
    Action(
        name="read_screen",
        description=(
            "Read what is currently rendered on screen. Use this before answering a "
            "question about what the user is looking at, and to get lead ids."
        ),
        params=[
            Param("key", "Which slice of the screen to read.", required=True, enum=READABLE),
        ],
        steps=[
            {"type": "readState", "key": "{{key}}", "say": "Reading {{key}} from the screen"},
        ],
    ),
]

ACTIONS_BY_NAME: dict[str, Action] = {a.name: a for a in ACTIONS}
ACTION_NAMES: frozenset[str] = frozenset(ACTIONS_BY_NAME)

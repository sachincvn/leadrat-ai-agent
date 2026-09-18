"""UI action registry - the contract between the model and the browser.

Every entry becomes one tool the model can call. Unlike the CRM tools, these are
never executed on the server: the model picks an action, this module expands it
into concrete UI steps, and the browser runs them against the real screen.

`target` always names a `data-agent-id` attribute in the frontend - never a CSS
selector, which would break on the next restyle. An action whose target does
not exist in the client yet does not belong here: the model would offer it,
the browser would fail on it, and the user would be told the app did something
it did not do.

Placeholders `{{param}}` are filled by resolver.resolve().
"""

from dataclasses import dataclass
from typing import Any

# Every page an action may send the user to. A name here must be one the web
# client can route - see the client's own page map.
PAGES = (
    "dashboard",
    "leads",
    "projects",
    "properties",
    "tasks",
    "reports",
)
READABLE = ("visible_leads", "current_page", "lead_form")


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
            "Take the user to a page of the app. Use this when they ask to go "
            "somewhere, or before an action that lives on another page."
        ),
        params=[
            Param("page", "Which page to open.", required=True, enum=PAGES),
        ],
        steps=[
            {"type": "navigate", "to": "{{page}}", "say": "Opening {{page}}"},
        ],
    ),
    Action(
        name="search_leads_on_screen",
        description=(
            "Type a search into the leads page and show the user the result. Use "
            "this when they want to SEE leads on screen - 'show me leads for "
            "Raj', 'search for 98765'. To answer a question about leads without "
            "moving them, use search_leads instead."
        ),
        params=[
            Param("keyword", "A name, phone number or email to search for.", required=True),
        ],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Opening the leads page"},
            {
                "type": "fill",
                "target": "leads.search",
                "value": "{{keyword}}",
                "submit": True,
                "say": 'Searching for "{{keyword}}"',
            },
            {"type": "readState", "key": "visible_leads", "say": "Reading what came back"},
        ],
    ),
    Action(
        name="clear_lead_search",
        description="Empty the search box on the leads page and show the full list again.",
        params=[],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Opening the leads page"},
            {
                "type": "fill",
                "target": "leads.search",
                "value": "",
                "submit": True,
                "say": "Clearing the search",
            },
            {"type": "readState", "key": "visible_leads", "say": "Reading the full list"},
        ],
    ),
    Action(
        name="open_lead",
        description=(
            "Open one lead's own page. Needs the lead's id - find it with "
            "search_leads first, and never invent one."
        ),
        params=[
            Param("lead_id", "Id of the lead, as returned by a previous tool.", required=True),
        ],
        steps=[
            {
                "type": "navigate",
                "to": "lead/{{lead_id}}",
                "say": "Opening the lead",
            },
        ],
    ),
    Action(
        name="open_new_lead_form",
        description=(
            "Open the form for adding a lead. Call this FIRST when the user "
            "wants to add one, before asking them for anything: the form "
            "reports which fields it requires, and the user can see what is "
            "being filled in. Then use fill_lead_form."
        ),
        params=[],
        steps=[
            {"type": "navigate", "to": "new-lead", "say": "Opening the new lead form"},
            {"type": "waitFor", "target": "lead-form.name", "say": "Waiting for the form"},
            {"type": "readState", "key": "lead_form", "say": "Checking what the form needs"},
        ],
    ),
    Action(
        name="fill_lead_form",
        description=(
            "Type into the new-lead form that is already open. Pass only the "
            "values the user actually gave you; anything you leave out is left "
            "alone, so this can be called again to correct one field without "
            "touching the rest. It reports back what the form is now "
            "complaining about, which is what to ask the user about next. It "
            "never saves - the user does that."
        ),
        params=[
            Param("name", "Full name of the lead."),
            Param("phone", "Contact number, digits as the user gave them."),
            Param("email", "Email address."),
            Param("source", "Where the lead came from, e.g. Referral, Walk In."),
        ],
        steps=[
            {
                "type": "fill",
                "target": "lead-form.name",
                "value": "{{name}}",
                "optional": True,
                "say": "Typing the name",
            },
            {
                "type": "fill",
                "target": "lead-form.phone",
                "value": "{{phone}}",
                "optional": True,
                "say": "Typing the phone number",
            },
            {
                "type": "fill",
                "target": "lead-form.email",
                "value": "{{email}}",
                "optional": True,
                "say": "Typing the email",
            },
            {
                "type": "select",
                "target": "lead-form.source",
                "value": "{{source}}",
                "optional": True,
                "say": "Choosing {{source}} as the source",
            },
            {"type": "readState", "key": "lead_form", "say": "Checking the form"},
        ],
    ),
    Action(
        name="read_screen",
        description=(
            "Read what is currently on screen. Use it before answering a question "
            "about what the user is looking at."
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

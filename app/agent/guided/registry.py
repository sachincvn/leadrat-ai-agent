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
    "prospects",
    "projects",
    "properties",
    "listings",
    "tasks",
    "reports",
    "teams",
    "attendance",
    "invoice",
    "whatsapp",
    "settings",
    "profile",
)
# The chips along the top of the leads page, by their own labels.
QUICK_FILTERS = ("New", "Today", "Overdue", "Pending", "Booked", "Site visits", "Meetings")

READABLE = (
    "visible_leads",
    "current_page",
    "lead_form",
    "lead_saved",
    "integration_form",
)


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
            Param(
                "page",
                "Which page to open. The app's own names for some of these "
                "differ: settings is Global Config, prospects is Data, teams "
                "is Users, listings is the property listing site.",
                required=True,
                enum=PAGES,
            ),
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
            Param(
                "keyword",
                "Exactly what the user asked for - their words, not a "
                "correction or an expansion of them. 'Shiv' is searched as "
                "Shiv; the CRM matches it anywhere in a name by itself.",
                required=True,
            ),
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
            # Through the button on the leads page rather than straight to the
            # form's route: the user is being shown where Add Lead is, and a
            # page that simply appears teaches them nothing.
            {"type": "navigate", "to": "leads", "say": "Opening the leads page"},
            {"type": "click", "target": "leads.add-lead", "say": "Clicking Add Lead"},
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
            Param(
                "phone",
                "Contact number. Include the country code with a + when the "
                "user names a country - '+91 9898989834' - because the field "
                "reads the country off the number itself. Digits alone are "
                "taken as the country the form is already set to.",
            ),
            Param("email", "Email address."),
            Param("source", "Where the lead came from, e.g. Referral, Walk In."),
            Param(
                "country",
                "The phone number's country, by name - 'India', 'United Arab "
                "Emirates'. The form defaults to one country and rejects a "
                "number that does not match it, so pass this whenever the "
                "user names a country or their number is rejected. Not needed "
                "when the number already carries its code.",
            ),
            Param("sub_source", "The sub-source under the source, if they said one."),
            Param("owner", "Who to assign the lead to, by name as it appears in the CRM."),
            Param("city", "The city the lead is enquiring about."),
            Param("min_budget", "Lower end of their budget, digits only."),
            Param("max_budget", "Upper end of their budget, digits only."),
            Param("notes", "Anything they said about the lead that is worth recording."),
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
                "type": "selectCountry",
                "target": "lead-form.phone",
                "value": "{{country}}",
                "optional": True,
                "say": "Setting the country to {{country}}",
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
            {
                "type": "select",
                "target": "lead-form.sub-source",
                "value": "{{sub_source}}",
                "optional": True,
                "say": "Choosing {{sub_source}}",
            },
            {
                "type": "select",
                "target": "lead-form.owner",
                "value": "{{owner}}",
                "optional": True,
                "say": "Assigning to {{owner}}",
            },
            {
                "type": "fill",
                "target": "lead-form.city",
                "value": "{{city}}",
                "optional": True,
                "say": "Typing the city",
            },
            {
                "type": "fill",
                "target": "lead-form.min-budget",
                "value": "{{min_budget}}",
                "optional": True,
                "say": "Typing the minimum budget",
            },
            {
                "type": "fill",
                "target": "lead-form.max-budget",
                "value": "{{max_budget}}",
                "optional": True,
                "say": "Typing the maximum budget",
            },
            {
                "type": "fill",
                "target": "lead-form.notes",
                "value": "{{notes}}",
                "optional": True,
                "say": "Adding the note",
            },
            {"type": "readState", "key": "lead_form", "say": "Checking the form"},
        ],
    ),
    Action(
        name="save_lead_form",
        description=(
            "Save the new-lead form that is on screen. This is the only action "
            "that writes to the CRM, and the user is asked to confirm before it "
            "happens. Call it when they say to save, and only once the form has "
            "what it needs - check with fill_lead_form first if you are unsure."
        ),
        params=[],
        writes_to_crm=True,
        steps=[
            {
                "type": "confirm",
                "message": "Save this lead?",
                "say": "Asking you to confirm",
            },
            {"type": "click", "target": "lead-form.save", "say": "Saving the lead"},
            # The click starts the request; this waits for it to finish and
            # says whether it did, rather than reading the form back mid-save.
            {"type": "readState", "key": "lead_saved", "say": "Waiting for the save"},
        ],
    ),
    Action(
        name="open_integration",
        description=(
            "Open the setup page for a lead-source integration - 99acres, "
            "Magicbricks, Housing, Facebook and the rest of the cards on the "
            "settings page - and click Add Account so the account form is "
            "ready. Use this when the user wants to connect or set up a "
            "portal. Then use fill_integration_form."
        ),
        params=[
            Param(
                "partner",
                "The integration as the card names it: '99acres', "
                "'Magicbricks', 'Housing', 'Facebook'.",
                required=True,
            ),
        ],
        steps=[
            {"type": "navigate", "to": "settings", "say": "Opening settings"},
            {
                "type": "click",
                "target": "integration.{{partner}}",
                "say": "Opening {{partner}}",
            },
            {
                "type": "click",
                "target": "integration.add-account",
                "say": "Clicking Add Account",
            },
            {
                "type": "waitFor",
                "target": "integration-form.account-name",
                "say": "Waiting for the account form",
            },
            {
                "type": "readState",
                "key": "integration_form",
                "say": "Checking what the form needs",
            },
        ],
    ),
    Action(
        name="fill_integration_form",
        description=(
            "Type into the integration account form that is already open. "
            "Account name and the relationship manager's email are required by "
            "the form; the login id is optional. Pass only what the user gave "
            "you - anything left out is left alone, so this can be called "
            "again to fix one field. It reports what the form is complaining "
            "about. It does not submit."
        ),
        params=[
            Param("account_name", "A name for this account, e.g. the agency's name."),
            Param("login_email", "The login id or email used with the portal."),
            Param(
                "manager_email",
                "The portal relationship manager's email. This is who the "
                "integration details are sent to.",
            ),
        ],
        steps=[
            {
                "type": "fill",
                "target": "integration-form.account-name",
                "value": "{{account_name}}",
                "optional": True,
                "say": "Typing the account name",
            },
            {
                "type": "fill",
                "target": "integration-form.login-email",
                "value": "{{login_email}}",
                "optional": True,
                "say": "Typing the login id",
            },
            {
                "type": "fill",
                "target": "integration-form.manager-email",
                "value": "{{manager_email}}",
                "submit": True,
                "optional": True,
                "say": "Adding the relationship manager's email",
            },
            {
                "type": "readState",
                "key": "integration_form",
                "say": "Checking the form",
            },
        ],
    ),
    Action(
        name="submit_integration_form",
        description=(
            "Submit the integration account form. This sends the integration "
            "details to the relationship manager's email, so the user confirms "
            "first. Once it is through, tell them what happens next: the "
            "portal's relationship manager has to wire it up at their end, and "
            "leads start arriving in the CRM once they do."
        ),
        params=[],
        writes_to_crm=True,
        steps=[
            {
                "type": "confirm",
                "message": "Send these integration details to the relationship manager?",
                "say": "Asking you to confirm",
            },
            {
                "type": "click",
                "target": "integration-form.submit",
                "say": "Submitting the account",
            },
            {
                "type": "readState",
                "key": "integration_form",
                "say": "Checking the result",
            },
        ],
    ),
    Action(
        name="filter_leads",
        description=(
            "Filter the leads list on screen. Opens the filter panel, sets "
            "whatever the user asked for and applies it, then reports the rows "
            "that came back. Pass every filter they named in one call - this "
            "is for 'show me interested leads from 99acres in Pune assigned to "
            "Abid', not one field at a time."
        ),
        params=[
            Param("status", "Lead status, as the tenant names it - check list_statuses."),
            Param("sub_status", "Sub-status under that status."),
            Param("source", "Where the leads came from, e.g. 99acres, Facebook."),
            Param("city", "City."),
            Param("owner", "Who the leads are assigned to, by name."),
        ],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Opening the leads page"},
            {"type": "click", "target": "leads.filters", "say": "Opening the filters"},
            {
                "type": "waitFor",
                "target": "lead-filter.apply",
                "say": "Waiting for the filter panel",
            },
            {
                "type": "select",
                "target": "lead-filter.status",
                "value": "{{status}}",
                "optional": True,
                "say": "Setting status to {{status}}",
            },
            {
                "type": "select",
                "target": "lead-filter.sub-status",
                "value": "{{sub_status}}",
                "optional": True,
                "say": "Setting sub-status to {{sub_status}}",
            },
            {
                "type": "select",
                "target": "lead-filter.source",
                "value": "{{source}}",
                "optional": True,
                "say": "Setting source to {{source}}",
            },
            {
                "type": "select",
                "target": "lead-filter.city",
                "value": "{{city}}",
                "optional": True,
                "say": "Setting city to {{city}}",
            },
            {
                "type": "select",
                "target": "lead-filter.owner",
                "value": "{{owner}}",
                "optional": True,
                "say": "Assigning filter to {{owner}}",
            },
            {"type": "click", "target": "lead-filter.apply", "say": "Applying the filters"},
            {"type": "readState", "key": "visible_leads", "say": "Reading what came back"},
        ],
    ),
    Action(
        name="filter_leads_by_view",
        description=(
            "Switch the leads list to one of the views along the top of the "
            "page - New, Today, Overdue, Pending, Booked, Site visits, "
            "Meetings. Use this for 'show me overdue leads' or 'what site "
            "visits are there', which are views rather than filters."
        ),
        params=[
            Param("view", "Which view to switch to.", required=True, enum=QUICK_FILTERS),
        ],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Opening the leads page"},
            {
                "type": "click",
                "target": "leads.quick-filter.{{view}}",
                "say": "Switching to {{view}}",
            },
            {"type": "readState", "key": "visible_leads", "say": "Reading what came back"},
        ],
    ),
    Action(
        name="clear_lead_filters",
        description=(
            "Clear every filter on the leads list and show the full list "
            "again. Use this for 'clear the filters', 'start again', 'show me "
            "everything'."
        ),
        params=[],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Opening the leads page"},
            {"type": "click", "target": "leads.filters", "say": "Opening the filters"},
            {
                "type": "waitFor",
                "target": "lead-filter.reset",
                "say": "Waiting for the filter panel",
            },
            {"type": "click", "target": "lead-filter.reset", "say": "Clearing every filter"},
            {"type": "readState", "key": "visible_leads", "say": "Reading the full list"},
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

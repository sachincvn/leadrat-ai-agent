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

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any

# --- value checks the form itself enforces ------------------------------------

# Angular's own validators on the rotation form: days 0-365, hours 0-23,
# minutes 0-59, and a rotation count the dropdown actually offers. Checking
# them here means the model is told what is wrong while it can still fix it,
# rather than the walkthrough typing a value the form then rejects in red.
MAX_ROTATION_DAYS = 365
MAX_ROTATIONS = 10

_TIME = re.compile(r"^(\d{1,2})(?::([0-5]\d))?\s*(am|pm)?$", re.IGNORECASE)


def _whole_number(value: str, *, low: int, high: int, unit: str) -> str | None:
    if not value.strip().lstrip("+").isdigit():
        return f'"{value}" is not a whole number of {unit}'
    number = int(value)
    if not low <= number <= high:
        return f"{unit} must be between {low} and {high} (got {number})"
    return None


def _check_time(value: str) -> str | None:
    """A time the picker can actually be set to.

    The field is a 12-hour picker, so a bare "9" is ambiguous in the one way
    that matters: nine in the morning and nine at night are both plausible
    shift boundaries, and the form will accept whichever it is given. Asking
    for the meridiem is cheaper than a shift saved twelve hours out.
    """
    match = _TIME.match(value.strip())
    if not match:
        return f'"{value}" is not a time - give it as "9:00 AM" or "18:30"'

    hour = int(match.group(1))
    meridiem = match.group(3)
    if meridiem:
        if not 1 <= hour <= 12:
            return f'"{value}" is not a time - with AM or PM the hour is 1 to 12'
    elif hour > 23:
        return f'"{value}" is not a time - the hour is 0 to 23'
    elif hour <= 12:
        return f'"{value}" could be morning or evening - say AM or PM'
    return None


def _check_days(value: str) -> str | None:
    return _whole_number(value, low=0, high=MAX_ROTATION_DAYS, unit="days")


def _check_hours(value: str) -> str | None:
    return _whole_number(value, low=0, high=23, unit="hours")


def _check_minutes(value: str) -> str | None:
    return _whole_number(value, low=0, high=59, unit="minutes")


def _check_rotations(value: str) -> str | None:
    return _whole_number(value, low=1, high=MAX_ROTATIONS, unit="rotations")


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
    "rotation_form",
)


@dataclass(frozen=True)
class Param:
    name: str
    description: str
    required: bool = False
    enum: tuple[str, ...] | None = None
    # Checked before a plan is built, for values an enum cannot express - a
    # time, a count, a number within a range. Returns the problem in the words
    # the model should hear, or None when the value is fine. A form that
    # rejects a value after the walkthrough has typed it wastes the run and
    # leaves the screen half filled.
    check: Callable[[str], str | None] | None = None


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
            {"type": "navigate", "to": "leads", "say": "Leads, in the menu on the left"},
            {
                "type": "fill",
                "target": "leads.search",
                "value": "{{keyword}}",
                "submit": True,
                "say": 'Typing "{{keyword}}" in the search box, then Enter',
            },
            {"type": "readState", "key": "visible_leads", "say": "Reading the rows that came back"},
        ],
    ),
    Action(
        name="clear_lead_search",
        description="Empty the search box on the leads page and show the full list again.",
        params=[],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Leads, in the menu on the left"},
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
            {"type": "navigate", "to": "leads", "say": "Leads, in the menu on the left"},
            {"type": "click", "target": "leads.add-lead", "say": "Add Lead, top right of the leads list"},
            {"type": "waitFor", "target": "lead-form.name", "say": "The new lead form opens here"},
            {"type": "readState", "key": "lead_form", "say": "Reading which fields it needs"},
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
                "say": "Name - the one field it will not save without",
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
                "say": "Contact number, with its country beside it",
            },
            {
                "type": "fill",
                "target": "lead-form.email",
                "value": "{{email}}",
                "optional": True,
                "say": "Email, under the contact number",
            },
            {
                "type": "select",
                "target": "lead-form.source",
                "value": "{{source}}",
                "optional": True,
                "say": "Source - where this lead came from",
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
                "say": "Assign To - who owns this lead now",
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
                "say": "Notes, at the bottom of the form",
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
            {"type": "click", "target": "lead-form.save", "say": "Save, bottom right - this is the one that writes it"},
            # The click starts the request; this waits for it to finish and
            # says whether it did, rather than reading the form back mid-save.
            {"type": "readState", "key": "lead_saved", "say": "Waiting for the CRM to take it"},
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
            {"type": "navigate", "to": "settings", "say": "Global Config, in the menu on the left"},
            {
                "type": "click",
                "target": "integration.{{partner}}",
                "say": "Connect Now on the {{partner}} card",
            },
            {
                "type": "click",
                "target": "integration.add-account",
                "say": "Add Account - each portal login is one account",
            },
            {
                "type": "waitFor",
                "target": "integration-form.account-name",
                "say": "The account form opens from the right",
            },
            {
                "type": "readState",
                "key": "integration_form",
                "say": "Reading which fields it needs",
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
                "say": "Account Name - whatever you will recognise it by",
            },
            {
                "type": "fill",
                "target": "integration-form.login-email",
                "value": "{{login_email}}",
                "optional": True,
                "say": "Login Id - the one you use on the portal",
            },
            {
                "type": "fill",
                "target": "integration-form.manager-email",
                "value": "{{manager_email}}",
                "submit": True,
                "optional": True,
                "say": "Relationship Manager Email - who receives the setup details",
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
                "say": "Add Account - this sends the details to them",
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
            Param(
                "owner",
                "Who the leads are assigned to. Pass the name the user said - "
                "the panel matches it against the list itself, so a first name "
                "is enough and looking it up first is not needed.",
            ),
        ],
        steps=[
            {"type": "navigate", "to": "leads", "say": "Leads, in the menu on the left"},
            {"type": "click", "target": "leads.filters", "say": "Filters, above the leads list"},
            {
                "type": "waitFor",
                "target": "lead-filter.apply",
                "say": "The filter panel opens from the top",
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
                "target": "lead-filter.owner",
                "value": "{{owner}}",
                "optional": True,
                "say": "Assigned To - whose leads these are",
            },
            {
                # A lead has a primary and a secondary owner, and the panel
                # filters on the primary one unless told otherwise - so asking
                # for someone's leads misses the ones they share.
                "type": "select",
                "target": "lead-filter.owner-scope",
                "value": "Both",
                "optional": True,
                # Naming {{owner}} here is what ties this step to that one:
                # an optional step whose placeholders are unfilled is skipped,
                # so this runs only when an owner was actually asked for.
                "say": "Both owners, so {{owner}}'s shared leads count too",
            },
            {"type": "click", "target": "lead-filter.apply", "say": "Search - applies everything set above"},
            {"type": "readState", "key": "visible_leads", "say": "Reading the rows that came back"},
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
            {"type": "navigate", "to": "leads", "say": "Leads, in the menu on the left"},
            {
                "type": "click",
                "target": "leads.quick-filter.{{view}}",
                "say": "Switching to {{view}}",
            },
            {"type": "readState", "key": "visible_leads", "say": "Reading the rows that came back"},
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
            {"type": "navigate", "to": "leads", "say": "Leads, in the menu on the left"},
            {"type": "click", "target": "leads.filters", "say": "Filters, above the leads list"},
            {
                "type": "waitFor",
                "target": "lead-filter.reset",
                "say": "The filter panel opens from the top",
            },
            {"type": "click", "target": "lead-filter.reset", "say": "Reset - clears every filter at once"},
            {"type": "readState", "key": "visible_leads", "say": "Reading the full list"},
        ],
    ),
    Action(
        name="open_lead_rotation",
        description=(
            "Open lead rotation for a portal account: the integration, its "
            "Assign To sheet, Select Team, and the rotation switch turned on. "
            "It stops there, because the team is the user's choice and the "
            "list is theirs to read - ask them to pick it on screen, and when "
            "they have, read the form again. A team that is already set up "
            "brings its rotation with it, so usually the only thing left is "
            "to save."
        ),
        params=[
            Param(
                "partner",
                "The integration as the card names it: 99acres, Magicbricks, "
                "Housing.",
                required=True,
            ),
        ],
        steps=[
            {"type": "navigate", "to": "settings", "say": "Global Config, in the menu on the left"},
            {
                "type": "click",
                "target": "integration.{{partner}}",
                "say": "Connect Now on the {{partner}} card",
            },
            {
                "type": "click",
                "target": "integration.assign-to",
                "say": "Assign To, on the account row",
            },
            {
                "type": "waitFor",
                "target": "assignment.select-team",
                "say": "Waiting for the assignment sheet",
            },
            {
                "type": "click",
                "target": "assignment.select-team",
                "say": "Select Team - rotation shares leads across a team, not one person",
            },
            {
                "type": "click",
                "target": "rotation.switch",
                "say": "Lead Rotation, on - its settings appear underneath",
            },
            {
                "type": "waitFor",
                "target": "rotation.team-name",
                "say": "Waiting for the rotation settings",
            },
            {
                "type": "readState",
                "key": "rotation_form",
                "say": "Reading what rotation needs",
            },
        ],
    ),
    Action(
        name="fill_lead_rotation",
        description=(
            "Fill the lead rotation settings already on screen. Ask the user "
            "only for the fields they can actually set: the team, the shift "
            "from and to, how long a lead waits before it moves on, and how "
            "many times it may move. The team name and team leader come with "
            "the group and are greyed out - never ask for them, and do not "
            "pass them. Pass only what the user gave you: anything left out is "
            "left alone, so this can be called again to fix one field. It "
            "reports what is still missing, and it does not save. It is only "
            "needed when the team the user picked did not bring a setting with "
            "it - most of the time the form is complete and this is skipped."
        ),
        params=[
            Param(
                "shift_from",
                'Start of the shift, with AM or PM: "9:00 AM". The picker is a '
                "12-hour one, so a bare hour is ambiguous and is refused.",
                check=_check_time,
            ),
            Param("shift_to", 'End of the shift, with AM or PM: "6:00 PM".', check=_check_time),
            Param(
                "rotation_days",
                "Days a lead waits before it rotates, 0 to 365. Days, hours and "
                "minutes add up to one wait - 90 minutes is 1 hour 30 minutes, "
                "not 90 in the minutes box.",
                check=_check_days,
            ),
            Param("rotation_hours", "Hours a lead waits, 0 to 23.", check=_check_hours),
            Param("rotation_minutes", "Minutes a lead waits, 0 to 59.", check=_check_minutes),
            Param(
                "rotations",
                "How many times a lead may rotate, 1 to 10.",
                check=_check_rotations,
            ),
            Param("buffer_minutes", "Optional buffer in minutes between rotations."),
        ],
        steps=[
            {
                # Not a fill: the field is readonly and only its picker can set
                # it, so typing into it changes nothing and reports success.
                "type": "setTime",
                "target": "rotation.shift-from",
                "value": "{{shift_from}}",
                "optional": True,
                "say": "Shift starts at {{shift_from}}",
            },
            {
                "type": "setTime",
                "target": "rotation.shift-to",
                "value": "{{shift_to}}",
                "optional": True,
                "say": "Shift ends at {{shift_to}}",
            },
            {
                "type": "fill",
                "target": "rotation.days",
                "value": "{{rotation_days}}",
                "optional": True,
                "say": "Rotation time - {{rotation_days}} days",
            },
            {
                "type": "fill",
                "target": "rotation.hours",
                "value": "{{rotation_hours}}",
                "optional": True,
                "say": "Rotation time - {{rotation_hours}} hours",
            },
            {
                "type": "fill",
                "target": "rotation.minutes",
                "value": "{{rotation_minutes}}",
                "optional": True,
                "say": "Rotation time - {{rotation_minutes}} minutes",
            },
            {
                "type": "select",
                "target": "rotation.count",
                "value": "{{rotations}}",
                "optional": True,
                "say": "Number of Rotation - how many times a lead may move",
            },
            {
                "type": "fill",
                "target": "rotation.buffer",
                "value": "{{buffer_minutes}}",
                "optional": True,
                "say": "Buffer time, optional - {{buffer_minutes}} minutes",
            },
            {
                "type": "readState",
                "key": "rotation_form",
                "say": "Checking the rotation settings",
            },
        ],
    ),
    Action(
        name="save_lead_rotation",
        description=(
            "Save the assignment and rotation settings on screen. This writes "
            "to the CRM and starts leads rotating, so the user confirms first. "
            "Call it once fill_lead_rotation reports nothing missing."
        ),
        params=[],
        writes_to_crm=True,
        steps=[
            {
                "type": "confirm",
                "message": "Save this rotation? Leads from this portal will start rotating.",
                "say": "Asking you to confirm",
            },
            {
                "type": "click",
                "target": "assignment.save",
                "say": "Save, bottom right of the sheet",
            },
            {
                "type": "readState",
                "key": "rotation_form",
                "say": "Checking the result",
            },
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

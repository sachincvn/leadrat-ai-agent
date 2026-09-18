"""Making "my" mean the caller, whatever the model forgot.

"Show my Facebook leads" is an ownership question, and the tool has no way to
know it: by the time the call is made the user's words are gone and only the
arguments remain. A model that leaves out the owner turns that ask into "every
Facebook lead in the tenant" - 8,556 of them, belonging to strangers - and the
answer looks right enough that nobody notices it is about someone else's work.

The prompt asks for the owner to be set. A small model does not reliably do it,
and an ownership mistake is not the kind that announces itself, so the ask is
read here as well and the filter added when it is missing.

Only the caller's own words are read, never the tool's output, and only to add
a filter that narrows the result - never to widen one the model chose.
"""

import re

from app.core.logging import get_logger

log = get_logger(__name__)

# Tools that answer about leads, and so can be scoped to an owner.
SCOPED_TOOLS = ("search_leads", "get_lead_counts")

# First person, as a question about one's own work: "my leads", "leads
# assigned to me", "what do I have", "mine".
_FIRST_PERSON = re.compile(
    r"\b(my|mine|i|me)\b",
    re.IGNORECASE,
)

# The same words, but about a group the caller belongs to rather than the
# caller. "My team's leads" is not "my leads", and scoping it to one person
# would quietly answer a different question.
_COLLECTIVE = re.compile(
    r"\b(team|teams|team's|everyone|everybody|all of us|our|us|reportees?|"
    r"department|branch|office|company|organisation|organization)\b",
    re.IGNORECASE,
)

# Someone else is named as the owner, so the ask is not about the caller even
# if it contains "my" ("show me Darshan's leads").
_OWNER_KEYS = ("assigned_to_names", "secondary_user_names")


def is_about_the_caller(message: str) -> bool:
    """Whether the user asked about their own leads, in their own words."""
    if not message:
        return False
    if _COLLECTIVE.search(message):
        return False
    return bool(_FIRST_PERSON.search(message))


def scope_to_caller(message: str, call: dict) -> dict:
    """Add the caller as the owner when they asked about their own leads.

    Returns the call unchanged whenever there is any doubt: a different tool, an
    owner the model did set, or an ask that was never in the first person.
    """
    if call.get("name") not in SCOPED_TOOLS:
        return call

    args = call.get("args")
    if not isinstance(args, dict):
        return call

    if any(args.get(key) for key in _OWNER_KEYS):
        return call

    if not is_about_the_caller(message):
        return call

    log.info("Scoping %s to the caller - the ask was about their own leads", call["name"])
    return {
        **call,
        "args": {**args, "assigned_to_names": ["me"], "owner_selection": "Both"},
    }

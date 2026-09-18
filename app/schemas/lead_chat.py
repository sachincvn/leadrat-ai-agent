"""Stateless single-lead chat contract: no conversation id, nothing persisted."""

from pydantic import BaseModel, Field


class LeadChatRequest(BaseModel):
    # No message = "summarize this lead" - the first interaction for a lead
    # needs nothing but its id.
    message: str | None = None


class LeadChatResponse(BaseModel):
    """Structured lead analysis, so another agent can act on it without

    re-parsing prose. Every field is filled from the lead history alone -
    Message answers the caller's question (or summarizes, if none was
    asked), the rest is always the lead's current at-a-glance state.
    """

    Message: str = Field(
        description="A concise natural-language summary of the lead, written as "
        "one flowing paragraph of plain sentences - never a list. Weave in every "
        "concrete fact the lead history actually contains (name, contact, "
        "requirement, source, assigned user, schedule, notes, etc.) - do not "
        "write a generic or empty-sounding summary when facts are available. "
        "If the caller asked a specific question, answer that question here "
        "instead of summarizing."
    )
    KeyHighlights: list[str] = Field(
        min_length=3,
        max_length=4,
        description="Exactly 3 to 4 bullets that characterize the QUALITY of "
        "this lead - what they reveal about its intent, engagement, fit or "
        "momentum - not administrative facts. Each is formatted as "
        "'<OneWordCategory>: <reason>', e.g. 'Budget: Confirmed ₹2.5 Cr, "
        "matching premium inventory' or 'Intent: Explicitly stated readiness "
        "to close this month'. Never a bullet whose only content is a bare "
        "fact with no interpretation - not 'Contact: phone number available', "
        "not 'Assignment: assigned to Rahul Mehta', not 'Currency: AED' - "
        "those don't tell anyone how this lead is doing. If the lead is thin, "
        "characterize what that means (e.g. 'Origin: Fresh bulk-uploaded "
        "lead, not yet engaged - an untapped early-stage opportunity') rather "
        "than listing which fields happen to be filled in. Only use what's "
        "present in the lead history - never invent, and never phrase a "
        "bullet as a risk or warning."
    )

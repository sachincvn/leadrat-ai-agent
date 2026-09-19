"""Contract for the capability-aware assistant turn.

One endpoint serves every client. A client does not announce a "mode" - it
announces what it is able to do, and the server binds the matching tools:

  capabilities: []               reading tools only  (Streamlit, Slack, cron)
  capabilities: ["ui_actions"]   reading tools + UI actions  (the web app)

Guided vs autopilot is not in this contract on purpose: both produce the same
plan, and the difference is only whether the browser waits for the user's click.
That is a client concern.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

UI_ACTIONS = "ui_actions"


class ToolCall(BaseModel):
    """A tool the model asked for, echoed back so the client can replay it."""

    id: str
    name: str
    args: dict[str, Any] = {}


class ToolResult(BaseModel):
    """What came back from executing one call, in the browser or on the server."""

    id: str
    content: str
    is_error: bool = False


class TranscriptEntry(BaseModel):
    """One entry of the shared transcript. The same shape for every client."""

    role: Literal["user", "assistant", "tool"]
    text: str = ""
    tool_calls: list[ToolCall] = []
    results: list[ToolResult] = []


class PlanStep(BaseModel):
    """One step of a plan, as the browser receives it.

    Every key a registry step can carry must exist here: pydantic drops what
    it does not declare, silently, so a step option missing from this model
    simply never reaches the client - it does not fail, it just stops
    happening.
    """

    type: str
    say: str = ""
    to: str | None = None
    target: str | None = None
    value: str | None = None
    message: str | None = None
    key: str | None = None
    # fill: press Enter afterwards, for a field that searches on submit.
    submit: bool = False


class PlanItem(BaseModel):
    call_id: str
    action: str
    destructive: bool = False
    args: dict[str, str] = {}
    steps: list[PlanStep] = []


class RejectedCall(BaseModel):
    call_id: str
    error: str


class AssistantTurnRequest(BaseModel):
    """A new user message, or the results of the plan from the previous turn."""

    message: str | None = Field(default=None, min_length=1)
    tool_results: list[ToolResult] = []
    history: list[TranscriptEntry] = []
    page_context: dict[str, Any] | None = None
    capabilities: list[str] = []
    lead_id: str | None = None

    @model_validator(mode="after")
    def _one_of(self) -> "AssistantTurnRequest":
        if not self.message and not self.tool_results:
            raise ValueError("Send either 'message' or 'tool_results'.")
        return self

    @property
    def can_drive_ui(self) -> bool:
        return UI_ACTIONS in self.capabilities


class AssistantTurnResponse(BaseModel):
    """Either a reply, or a plan the client must execute and report back on.

    `history_append` is what the client adds to its transcript for this turn,
    so the next request replays exactly what the model saw.
    """

    type: Literal["message", "plan"]
    text: str = ""
    plan: list[PlanItem] = []
    rejected: list[RejectedCall] = []
    tools_used: list[str] = []
    history_append: list[TranscriptEntry] = []

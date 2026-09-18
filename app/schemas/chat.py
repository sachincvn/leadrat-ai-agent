"""Chat request/response contract shared by the API and the UI."""

from pydantic import BaseModel, Field


# A client that renders `block` events declares it, so the answer can stop
# repeating in prose what is already on screen as a card.
RENDERS_BLOCKS = "blocks"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    lead_id: str | None = None
    capabilities: list[str] = []

    @property
    def renders_blocks(self) -> bool:
        return RENDERS_BLOCKS in self.capabilities


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str] = []


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    model: str
    crm: str

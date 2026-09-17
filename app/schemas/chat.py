"""Chat request/response contract shared by the API and the UI."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    lead_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str] = []


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    model: str
    crm: str

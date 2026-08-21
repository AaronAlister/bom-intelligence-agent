from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    bom_id: str
    component_ids: list[str] = Field(default_factory=list)
    task: str
    context: dict[str, Any] = Field(default_factory=dict)
    requested_evidence: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    source: str
    source_id: str | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent: str
    status: Literal["success", "partial", "failed"]
    bom_id: str
    summary: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    execution_metadata: dict[str, Any] = Field(default_factory=dict)

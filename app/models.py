"""Pydantic request/response models."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class StartCallRequest(BaseModel):
    phone_number: str = Field(..., description="E.164 destination, e.g. +14155551234")
    scenario_id: str = Field(..., description="Registered scenario id")
    variables: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Per-call variables interpolated into the scenario (e.g. attendee_name, event_name).",
    )


class StartCallResponse(BaseModel):
    session_id: str
    call_sid: str
    status: str


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    variables: list[str]

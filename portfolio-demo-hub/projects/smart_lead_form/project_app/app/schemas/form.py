# Defines schemas for form configuration and visible step responses.

from typing import Any

from pydantic import BaseModel, Field


class FormConfigResponse(BaseModel):
    client_id: str
    scenario_key: str
    version: str | None = None
    language: str | None = None
    title: str
    description: str | None = None
    steps: list[dict[str, Any]]
    ui_texts: dict[str, Any] | None = None
    visible_steps: list[dict[str, Any]] | None = None


class VisibleStepsRequest(BaseModel):
    client_id: str
    answers: dict[str, Any] = Field(default_factory=dict)


class VisibleStepsResponse(BaseModel):
    client_id: str
    steps: list[dict[str, Any]]

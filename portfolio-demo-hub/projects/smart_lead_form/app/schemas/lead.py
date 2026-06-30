# Defines request and response schemas for leads.

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LeadCreate(BaseModel):
    client_id: str
    scenario_key: str
    service_type: str | None = None
    language_pair: str | None = None
    page_count: str | None = None
    urgency: str | None = None
    meeting_format: str | None = None
    city: str | None = None
    documents_ready: str | None = None

    name: str
    phone: str
    email: str | None = None
    preferred_contact_time: str | None = None
    comment: str | None = None

    estimated_price_min: int | None = None
    estimated_price_max: int | None = None
    currency: str = "₪"
    estimate_message: str | None = None
    disclaimer: str | None = None

    answers: dict[str, Any] = Field(default_factory=dict)


class LeadCreateResponse(BaseModel):
    id: int
    status: str
    message: str


class LeadUpdateResponse(BaseModel):
    id: int
    status: str
    message: str


class LeadResponse(BaseModel):
    id: int
    client_id: str
    scenario_key: str
    service_type: str | None
    language_pair: str | None
    page_count: str | None
    urgency: str | None
    meeting_format: str | None
    city: str | None
    documents_ready: str | None
    name: str
    phone: str
    email: str | None
    preferred_contact_time: str | None
    comment: str | None
    estimated_price_min: int | None
    estimated_price_max: int | None
    currency: str | None
    estimate_message: str | None
    disclaimer: str | None
    answers_json: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int


class LeadStatusUpdate(BaseModel):
    status: str


class LeadStatusUpdateResponse(BaseModel):
    id: int
    status: str


class LeadDeleteResponse(BaseModel):
    id: int
    status: str

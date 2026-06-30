# Defines schemas for pricing estimate requests and responses.

from typing import Any

from pydantic import BaseModel


class CalculateRequest(BaseModel):
    client_id: str
    scenario_key: str | None = None
    answers: dict[str, Any]


class CalculateResponse(BaseModel):
    estimated_price_min: int | None
    estimated_price_max: int | None
    currency: str
    estimate_message: str
    disclaimer: str

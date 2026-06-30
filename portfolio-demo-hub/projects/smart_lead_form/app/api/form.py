# Exposes endpoints for dynamic form configuration and estimate calculation.

from fastapi import APIRouter, HTTPException

from app.schemas.calculator import CalculateRequest, CalculateResponse
from app.schemas.form import FormConfigResponse, VisibleStepsRequest, VisibleStepsResponse
from app.services.form_engine import get_form_config_response, get_visible_steps
from app.services.pricing_engine import calculate_estimate

router = APIRouter(prefix="/api/form", tags=["form"])


def _handle_config_error(exc: Exception) -> None:
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/config", response_model=FormConfigResponse)
def get_form_config(client_id: str) -> dict:
    try:
        return get_form_config_response(client_id)
    except Exception as exc:
        _handle_config_error(exc)


@router.post("/visible-steps", response_model=VisibleStepsResponse)
def get_form_visible_steps(request: VisibleStepsRequest) -> dict:
    try:
        steps = get_visible_steps(request.client_id, request.answers)
        return {"client_id": request.client_id, "steps": steps}
    except Exception as exc:
        _handle_config_error(exc)


@router.post("/calculate", response_model=CalculateResponse)
def calculate_form_estimate(request: CalculateRequest) -> dict:
    try:
        return calculate_estimate(request.client_id, request.answers)
    except Exception as exc:
        _handle_config_error(exc)

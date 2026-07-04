"""JSON API routes for leads, analytics events, and demo session lifecycle."""

import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.models import ContactLead, DemoSession
from app.services.analytics import KNOWN_EVENTS, finish_demo_session, record_event
from app.services.project_loader import get_project

router = APIRouter(prefix="/api")

# Only Hub-created demo IDs may be used for cleanup calls to demo projects.
DEMO_SESSION_ID_RE = re.compile(r"^demo_[0-9a-f]{32}$")


class ContactPayload(BaseModel):
    """Payload from the public contact form."""

    name: str = ""
    phone: str | None = None
    email: str | None = None
    client_type: str | None = None
    interest: str | None = None
    project_status: str | None = None
    project_id: str | None = None
    message: str | None = None
    source_page: str | None = None
    session_id: str | None = None


class AnalyticsPayload(BaseModel):
    """Generic event payload sent by analytics.js and launch.js."""

    event_type: str
    session_id: str | None = None
    demo_session_id: str | None = None
    project_id: str | None = None
    page_url: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        if value not in KNOWN_EVENTS:
            raise ValueError("Unknown analytics event type")
        return value


class HeartbeatPayload(BaseModel):
    """Periodic visitor/demo activity update."""

    session_id: str
    demo_session_id: str | None = None
    project_id: str | None = None
    page_url: str | None = None


class DemoSessionStartPayload(BaseModel):
    """Request body used when the launch wrapper starts or resets a demo."""

    session_id: str | None = None
    previous_demo_session_id: str | None = None
    page_url: str | None = None


class DemoSessionFinishPayload(BaseModel):
    """Optional project hint sent when a wrapper finishes a demo session."""

    project_id: str | None = None


@router.post("/contact")
def submit_contact(payload: ContactPayload, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Validate and save a lead, then record the matching contact_submit event."""
    if not payload.name.strip():
        _record_contact_error(db, payload, request, "missing_name")
        raise HTTPException(status_code=422, detail="Укажите имя.")
    if not (payload.phone and payload.phone.strip()) and not (payload.email and payload.email.strip()):
        _record_contact_error(db, payload, request, "missing_contact")
        raise HTTPException(status_code=422, detail="Укажите email или телефон, чтобы я мог связаться с вами.")
    if not (payload.interest and payload.interest.strip()):
        _record_contact_error(db, payload, request, "missing_interest")
        raise HTTPException(status_code=422, detail="Выберите, что вас интересует.")
    if not (payload.message and len(payload.message.strip()) >= 5):
        _record_contact_error(db, payload, request, "short_message")
        raise HTTPException(status_code=422, detail="Сообщение слишком короткое. Напишите пару слов о задаче.")

    lead = ContactLead(**payload.model_dump())
    db.add(lead)
    record_event(
        db,
        "contact_submit",
        session_id=payload.session_id,
        project_id=payload.project_id,
        page_url=payload.source_page,
        metadata={"interest": payload.interest, "client_type": payload.client_type},
        request=request,
    )
    record_event(
        db,
        "contact_submit_success",
        session_id=payload.session_id,
        project_id=payload.project_id,
        page_url=payload.source_page,
        metadata={"interest": payload.interest, "client_type": payload.client_type},
        request=request,
    )
    db.commit()
    db.refresh(lead)
    return {"success": True, "lead_id": lead.id}


def _record_contact_error(db: Session, payload: ContactPayload, request: Request, error_code: str) -> None:
    """Record a non-personal analytics event for a failed contact submit."""
    record_event(
        db,
        "contact_submit_error",
        session_id=payload.session_id,
        project_id=payload.project_id,
        page_url=payload.source_page,
        metadata={"error": error_code, "interest": payload.interest, "client_type": payload.client_type},
        request=request,
    )
    db.commit()


@router.post("/analytics/event")
def analytics_event(payload: AnalyticsPayload, request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Store one explicit analytics event from the browser."""
    record_event(
        db,
        payload.event_type,
        session_id=payload.session_id,
        demo_session_id=payload.demo_session_id,
        project_id=payload.project_id,
        page_url=payload.page_url,
        metadata=payload.metadata,
        request=request,
    )
    db.commit()
    return {"success": True}


@router.post("/analytics/heartbeat")
def analytics_heartbeat(payload: HeartbeatPayload, request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Store a heartbeat event and refresh session last-seen timestamps."""
    record_event(
        db,
        "heartbeat",
        session_id=payload.session_id,
        demo_session_id=payload.demo_session_id,
        project_id=payload.project_id,
        page_url=payload.page_url,
        request=request,
    )
    db.commit()
    return {"success": True}


@router.post("/demo-session/{project_id}/start")
def demo_start(
    project_id: str,
    payload: DemoSessionStartPayload,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Create a new isolated demo session for a project launch wrapper."""
    project = get_project(project_id)
    if not project or not project.get("has_demo"):
        raise HTTPException(status_code=404, detail="Demo not found")

    if payload.previous_demo_session_id:
        previous_demo = finish_demo_session(db, payload.previous_demo_session_id)
        if previous_demo:
            _cleanup_demo_project(previous_demo.project_id, payload.previous_demo_session_id)

    session_id = payload.session_id or f"session_{uuid4().hex}"
    demo_session_id = f"demo_{uuid4().hex}"
    db.add(
        DemoSession(
            demo_session_id=demo_session_id,
            session_id=session_id,
            project_id=project_id,
            opened_demo=True,
        )
    )
    record_event(
        db,
        "demo_launch",
        session_id=session_id,
        demo_session_id=demo_session_id,
        project_id=project_id,
        page_url=payload.page_url or str(request.url),
        request=request,
    )
    db.commit()
    return {
        "session_id": session_id,
        "demo_session_id": demo_session_id,
    }


@router.post("/demo-session/{demo_session_id}/finish")
def demo_finish(
    demo_session_id: str,
    request: Request,
    payload: DemoSessionFinishPayload | None = None,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Finish a Hub demo session and ask the underlying demo project to clean up."""
    demo = finish_demo_session(db, demo_session_id)
    if not demo:
        raise HTTPException(status_code=404, detail="Demo session not found")
    project_id = payload.project_id if payload and payload.project_id else demo.project_id
    record_event(
        db,
        "demo_finish",
        session_id=demo.session_id,
        demo_session_id=demo_session_id,
        project_id=project_id,
        page_url=str(request.url),
        request=request,
    )
    cleanup_ok = _cleanup_demo_project(project_id, demo_session_id)
    db.commit()
    return {"success": True, "cleanup": cleanup_ok}


def _cleanup_demo_project(project_id: str | None, demo_session_id: str) -> bool:
    """Call the demo project's DELETE endpoint to remove per-session demo data."""
    if not project_id:
        return False
    if not DEMO_SESSION_ID_RE.fullmatch(demo_session_id):
        return False

    project = get_project(project_id)
    if not project:
        return False

    cleanup_path = project.get("cleanup_path")
    if not cleanup_path:
        demo_path = str(project.get("demo_path", ""))
        cleanup_path = f"{demo_path.rstrip('/')}/demo-session/{{demo_session_id}}"

    cleanup_url = cleanup_path.replace("{demo_session_id}", quote(demo_session_id, safe=""))
    base_url = get_settings().demo_internal_base_url.rstrip("/")
    if cleanup_url.startswith("/"):
        cleanup_url = f"{base_url}{cleanup_url}"
    elif not _is_allowed_cleanup_url(cleanup_url, base_url):
        return False

    try:
        request = UrlRequest(cleanup_url, method="DELETE")
        with urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, ValueError):
        return False


def _is_allowed_cleanup_url(cleanup_url: str, base_url: str) -> bool:
    """Allow cleanup calls only to relative URLs or the configured internal base."""
    cleanup_parts = urlparse(cleanup_url)
    if not cleanup_parts.scheme and not cleanup_parts.netloc:
        return cleanup_url.startswith("/")
    if cleanup_parts.scheme not in {"http", "https"}:
        return False
    base_parts = urlparse(base_url)
    return cleanup_parts.scheme == base_parts.scheme and cleanup_parts.netloc == base_parts.netloc

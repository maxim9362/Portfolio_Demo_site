from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ContactLead, DemoSession
from app.config import get_settings
from app.services.analytics import finish_demo_session, record_event
from app.services.project_loader import get_project

router = APIRouter(prefix="/api")


class ContactPayload(BaseModel):
    name: str = Field(min_length=1)
    phone: str | None = None
    email: str | None = None
    client_type: str | None = None
    project_id: str | None = None
    message: str | None = None
    source_page: str | None = None
    session_id: str | None = None


class AnalyticsPayload(BaseModel):
    event_type: str
    session_id: str | None = None
    demo_session_id: str | None = None
    project_id: str | None = None
    page_url: str | None = None
    metadata: dict[str, Any] | None = None


class HeartbeatPayload(BaseModel):
    session_id: str
    demo_session_id: str | None = None
    project_id: str | None = None
    page_url: str | None = None


class DemoSessionStartPayload(BaseModel):
    session_id: str | None = None
    previous_demo_session_id: str | None = None
    page_url: str | None = None


class DemoSessionFinishPayload(BaseModel):
    project_id: str | None = None


@router.post("/contact")
def submit_contact(payload: ContactPayload, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Name is required")
    if not (payload.phone and payload.phone.strip()) and not (payload.email and payload.email.strip()):
        raise HTTPException(status_code=422, detail="Phone or email is required")

    lead = ContactLead(**payload.model_dump())
    db.add(lead)
    record_event(
        db,
        "contact_submit",
        session_id=payload.session_id,
        project_id=payload.project_id,
        page_url=payload.source_page,
        request=request,
    )
    db.commit()
    db.refresh(lead)
    return {"success": True, "lead_id": lead.id}


@router.post("/analytics/event")
def analytics_event(payload: AnalyticsPayload, request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
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
    if not project_id:
        return False

    project = get_project(project_id)
    if not project:
        return False

    cleanup_path = project.get("cleanup_path")
    if not cleanup_path:
        demo_path = str(project.get("demo_path", ""))
        cleanup_path = f"{demo_path.rstrip('/')}/demo-session/{{demo_session_id}}"

    cleanup_url = cleanup_path.replace("{demo_session_id}", demo_session_id)
    if cleanup_url.startswith("/"):
        cleanup_url = f"{get_settings().demo_internal_base_url.rstrip('/')}{cleanup_url}"

    try:
        request = UrlRequest(cleanup_url, method="DELETE")
        with urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, ValueError):
        return False

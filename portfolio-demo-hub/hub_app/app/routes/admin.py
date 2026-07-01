import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.models import AnalyticsEvent, ContactLead, DemoSession, VisitorSession
from app.services.project_loader import load_projects

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    settings = get_settings()
    valid_user = secrets.compare_digest(credentials.username, settings.admin_username)
    valid_password = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (valid_user and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def duration(value: int | None) -> str:
    if not value:
        return "0s"
    seconds = max(0, int(value))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def demo_duration(item: DemoSession) -> int:
    if item.duration_seconds is not None:
        return item.duration_seconds
    if item.started_at:
        end = item.ended_at or item.last_seen_at or datetime.now(UTC)
        return max(0, int((end - item.started_at).total_seconds()))
    return 0


def referer_or(path: str, request: Request) -> str:
    return request.headers.get("referer") or path


def project_options() -> list[dict[str, Any]]:
    return load_projects()


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    total_page_views = db.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "page_view").count()
    unique_sessions = db.query(VisitorSession).count()
    leads_count = db.query(ContactLead).count()
    demo_launches = db.query(DemoSession).count()
    admin_opens = db.query(AnalyticsEvent).filter(AnalyticsEvent.event_type == "admin_tab_open").count()
    avg_site = round(db.query(func.avg(VisitorSession.duration_seconds)).scalar() or 0)
    avg_demo = round(db.query(func.avg(DemoSession.duration_seconds)).scalar() or 0)
    popular_project_row = (
        db.query(AnalyticsEvent.project_id, func.count(AnalyticsEvent.id).label("count"))
        .filter(AnalyticsEvent.project_id.isnot(None))
        .filter(AnalyticsEvent.event_type.in_(["project_view", "demo_launch", "project_demo_button_click"]))
        .group_by(AnalyticsEvent.project_id)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .first()
    )
    recent_events = db.query(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(20).all()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "metrics": {
                "page_views": total_page_views,
                "unique_sessions": unique_sessions,
                "leads": leads_count,
                "demo_launches": demo_launches,
                "admin_opens": admin_opens,
                "avg_site": duration(avg_site),
                "avg_demo": duration(avg_demo),
                "popular_project": popular_project_row[0] if popular_project_row else "none",
            },
            "recent_events": recent_events,
        },
    )


@router.get("/leads", response_class=HTMLResponse)
def leads(
    request: Request,
    status_filter: str | None = None,
    project_id: str | None = None,
    client_type: str | None = None,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    query = db.query(ContactLead)
    if status_filter:
        query = query.filter(ContactLead.status == status_filter)
    if project_id:
        query = query.filter(ContactLead.project_id == project_id)
    if client_type:
        query = query.filter(ContactLead.client_type == client_type)

    items = query.order_by(ContactLead.created_at.desc()).limit(300).all()
    client_types = [
        row[0]
        for row in db.query(ContactLead.client_type)
        .filter(ContactLead.client_type.isnot(None))
        .distinct()
        .order_by(ContactLead.client_type)
        .all()
    ]
    return templates.TemplateResponse(
        "admin/leads.html",
        {
            "request": request,
            "leads": items,
            "projects": project_options(),
            "client_types": client_types,
            "filters": {
                "status": status_filter or "",
                "project_id": project_id or "",
                "client_type": client_type or "",
            },
        },
    )


@router.post("/leads/{lead_id}/viewed")
def lead_viewed(lead_id: int, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    lead = db.get(ContactLead, lead_id)
    if lead:
        lead.status = "viewed"
        db.commit()
    return RedirectResponse(referer_or("/admin/leads", request), status_code=303)


@router.post("/leads/{lead_id}/archive")
def lead_archive(lead_id: int, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    lead = db.get(ContactLead, lead_id)
    if lead:
        lead.status = "archived"
        db.commit()
    return RedirectResponse(referer_or("/admin/leads", request), status_code=303)


@router.post("/leads/{lead_id}/restore")
def lead_restore(lead_id: int, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    lead = db.get(ContactLead, lead_id)
    if lead:
        lead.status = "new"
        db.commit()
    return RedirectResponse(referer_or("/admin/leads", request), status_code=303)


@router.get("/sessions", response_class=HTMLResponse)
def sessions(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    items = db.query(VisitorSession).order_by(VisitorSession.last_seen_at.desc().nullslast()).limit(300).all()
    rows = []
    for item in items:
        event_count = db.query(AnalyticsEvent).filter(AnalyticsEvent.session_id == item.session_id).count()
        viewed_projects = (
            db.query(func.count(distinct(AnalyticsEvent.project_id)))
            .filter(AnalyticsEvent.session_id == item.session_id)
            .filter(AnalyticsEvent.event_type == "project_view")
            .filter(AnalyticsEvent.project_id.isnot(None))
            .scalar()
            or 0
        )
        demo_count = db.query(DemoSession).filter(DemoSession.session_id == item.session_id).count()
        has_lead = db.query(ContactLead).filter(ContactLead.session_id == item.session_id).first() is not None
        rows.append(
            {
                "item": item,
                "event_count": event_count,
                "viewed_projects": viewed_projects,
                "demo_count": demo_count,
                "has_lead": has_lead,
                "duration": duration(item.duration_seconds),
            }
        )
    return templates.TemplateResponse("admin/sessions.html", {"request": request, "sessions": rows})


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
def session_detail(session_id: str, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    visitor = db.query(VisitorSession).filter(VisitorSession.session_id == session_id).one_or_none()
    if not visitor:
        raise HTTPException(status_code=404, detail="Session not found")

    events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.session_id == session_id)
        .order_by(AnalyticsEvent.created_at.asc())
        .all()
    )
    leads = db.query(ContactLead).filter(ContactLead.session_id == session_id).order_by(ContactLead.created_at.desc()).all()
    demos = db.query(DemoSession).filter(DemoSession.session_id == session_id).order_by(DemoSession.started_at.desc()).all()
    pages = [event for event in events if event.event_type == "page_view"]
    projects = [event for event in events if event.event_type == "project_view"]
    admin_opens = [event for event in events if event.event_type == "admin_tab_open"]
    return templates.TemplateResponse(
        "admin/session_detail.html",
        {
            "request": request,
            "session": visitor,
            "duration": duration(visitor.duration_seconds),
            "events": events,
            "leads": leads,
            "demos": demos,
            "pages": pages,
            "projects": projects,
            "admin_opens": admin_opens,
        },
    )


@router.get("/analytics", response_class=HTMLResponse)
def analytics(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    events = db.query(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(300).all()
    popular_pages = (
        db.query(AnalyticsEvent.page_url, func.count(AnalyticsEvent.id).label("count"))
        .filter(AnalyticsEvent.event_type == "page_view")
        .filter(AnalyticsEvent.page_url.isnot(None))
        .group_by(AnalyticsEvent.page_url)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(20)
        .all()
    )
    popular_projects = _event_counts(db, "project_view")
    demo_by_project = _event_counts(db, "demo_launch")
    admin_by_project = _event_counts(db, "admin_tab_open")
    project_views = dict(popular_projects)
    demo_launch_counts = dict(demo_by_project)
    lead_counts = {
        row[0]: row[1]
        for row in db.query(ContactLead.project_id, func.count(ContactLead.id))
        .filter(ContactLead.project_id.isnot(None))
        .group_by(ContactLead.project_id)
        .all()
    }
    projects = sorted(set(project_views) | set(demo_launch_counts) | set(lead_counts))
    conversions = []
    for project_id in projects:
        views = project_views.get(project_id, 0)
        launches = demo_launch_counts.get(project_id, 0)
        leads_count = lead_counts.get(project_id, 0)
        conversions.append(
            {
                "project_id": project_id,
                "views": views,
                "launches": launches,
                "leads": leads_count,
                "view_to_demo": round((launches / views) * 100, 1) if views else 0,
                "demo_to_lead": round((leads_count / launches) * 100, 1) if launches else 0,
            }
        )
    return templates.TemplateResponse(
        "admin/analytics.html",
        {
            "request": request,
            "events": events,
            "popular_pages": popular_pages,
            "popular_projects": popular_projects,
            "demo_by_project": demo_by_project,
            "admin_by_project": admin_by_project,
            "conversions": conversions,
        },
    )


@router.get("/demo-sessions", response_class=HTMLResponse)
def demo_sessions(
    request: Request,
    project_id: str | None = None,
    status_filter: str | None = None,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    query = db.query(DemoSession)
    if project_id:
        query = query.filter(DemoSession.project_id == project_id)
    if status_filter:
        query = query.filter(DemoSession.status == status_filter)
    sessions = query.order_by(DemoSession.created_at.desc()).limit(300).all()
    return templates.TemplateResponse(
        "admin/demo_sessions.html",
        {
            "request": request,
            "sessions": sessions,
            "projects": project_options(),
            "filters": {"project_id": project_id or "", "status": status_filter or ""},
            "duration": demo_duration,
            "format_duration": duration,
        },
    )


@router.get("/demo-sessions/{demo_session_id}", response_class=HTMLResponse)
def demo_session_detail(demo_session_id: str, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    item = db.query(DemoSession).filter(DemoSession.demo_session_id == demo_session_id).one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Demo session not found")
    events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.demo_session_id == demo_session_id)
        .order_by(AnalyticsEvent.created_at.asc())
        .all()
    )
    return templates.TemplateResponse(
        "admin/demo_session_detail.html",
        {
            "request": request,
            "item": item,
            "events": events,
            "duration": duration(demo_duration(item)),
        },
    )


@router.get("/projects", response_class=HTMLResponse)
def admin_projects(request: Request, _: str = Depends(require_admin)) -> HTMLResponse:
    return templates.TemplateResponse("admin/projects.html", {"request": request, "projects": load_projects()})


def _event_counts(db: Session, event_type: str) -> list[tuple[str, int]]:
    return [
        (row[0], row[1])
        for row in (
            db.query(AnalyticsEvent.project_id, func.count(AnalyticsEvent.id).label("count"))
            .filter(AnalyticsEvent.event_type == event_type)
            .filter(AnalyticsEvent.project_id.isnot(None))
            .group_by(AnalyticsEvent.project_id)
            .order_by(func.count(AnalyticsEvent.id).desc())
            .all()
        )
    ]

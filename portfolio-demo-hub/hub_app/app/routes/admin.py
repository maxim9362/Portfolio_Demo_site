import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
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


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    visits = db.query(VisitorSession).count()
    leads = db.query(ContactLead).count()
    demo_launches = db.query(DemoSession).count()
    avg_site = db.query(func.avg(VisitorSession.duration_seconds)).scalar() or 0
    avg_demo = db.query(func.avg(DemoSession.duration_seconds)).scalar() or 0
    recent_events = db.query(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(10).all()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "metrics": {
                "visits": visits,
                "leads": leads,
                "demo_launches": demo_launches,
                "avg_site": round(avg_site or 0),
                "avg_demo": round(avg_demo or 0),
            },
            "recent_events": recent_events,
        },
    )


@router.get("/leads", response_class=HTMLResponse)
def leads(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    items = db.query(ContactLead).order_by(ContactLead.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin/leads.html", {"request": request, "leads": items})


@router.post("/leads/{lead_id}/viewed")
def lead_viewed(lead_id: int, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    lead = db.get(ContactLead, lead_id)
    if lead:
        lead.status = "viewed"
        db.commit()
    return RedirectResponse("/admin/leads", status_code=303)


@router.post("/leads/{lead_id}/archive")
def lead_archive(lead_id: int, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    lead = db.get(ContactLead, lead_id)
    if lead:
        lead.status = "archived"
        db.commit()
    return RedirectResponse("/admin/leads", status_code=303)


@router.get("/analytics", response_class=HTMLResponse)
def analytics(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    events = db.query(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(300).all()
    return templates.TemplateResponse("admin/analytics.html", {"request": request, "events": events})


@router.get("/demo-sessions", response_class=HTMLResponse)
def demo_sessions(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    sessions = db.query(DemoSession).order_by(DemoSession.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin/demo_sessions.html", {"request": request, "sessions": sessions})


@router.get("/projects", response_class=HTMLResponse)
def admin_projects(request: Request, _: str = Depends(require_admin)) -> HTMLResponse:
    return templates.TemplateResponse("admin/projects.html", {"request": request, "projects": load_projects()})

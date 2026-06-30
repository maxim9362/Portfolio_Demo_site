from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DemoSession
from app.services.analytics import record_event
from app.services.project_loader import get_project, load_projects

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, "projects": load_projects()})


@router.get("/for-partners", response_class=HTMLResponse)
def for_partners(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("for_partners.html", {"request": request})


@router.get("/projects", response_class=HTMLResponse)
def projects(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("projects.html", {"request": request, "projects": load_projects()})


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    session_id = request.query_params.get("session_id")
    if session_id:
        record_event(db, "project_view", session_id=session_id, project_id=project_id, page_url=str(request.url), request=request)
        db.commit()
    return templates.TemplateResponse("project_detail.html", {"request": request, "project": project})


@router.get("/launch/{project_id}", response_class=HTMLResponse)
def launch(
    request: Request,
    project_id: str,
    session_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    project = get_project(project_id)
    if not project or not project.get("has_demo"):
        raise HTTPException(status_code=404, detail="Demo not found")

    session_id = session_id or f"session_{uuid4().hex}"
    demo_session_id = f"demo_{uuid4().hex}"
    demo_session = DemoSession(
        demo_session_id=demo_session_id,
        session_id=session_id,
        project_id=project_id,
        opened_demo=True,
    )
    db.add(demo_session)
    record_event(
        db,
        "demo_launch",
        session_id=session_id,
        demo_session_id=demo_session_id,
        project_id=project_id,
        page_url=str(request.url),
        request=request,
    )
    db.commit()

    return templates.TemplateResponse(
        "launch.html",
        {
            "request": request,
            "project": project,
            "session_id": session_id,
            "demo_session_id": demo_session_id,
        },
    )


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request, project_id: str | None = Query(default=None)) -> HTMLResponse:
    return templates.TemplateResponse(
        "contact.html",
        {"request": request, "projects": load_projects(), "selected_project_id": project_id},
    )

from uuid import uuid4
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.db.models import DemoSession
from app.services.analytics import record_event
from app.services.project_loader import get_project, load_projects

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
PROJECT_META_DESCRIPTIONS = {
    "ai-site-consultant": "Демо AI-консультанта для сайта: чат отвечает посетителям, объясняет услуги, собирает заявки и показывает владельцу историю общения.",
    "smart-lead-form": "Демо умной формы заявки: пользователь проходит вопросы, получает пример расчёта и оставляет структурированную заявку.",
}


def site_url() -> str:
    return get_settings().site_url.rstrip("/")


def absolute_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    return f"{site_url()}/{path.lstrip('/')}"


def public_context(path: str, **extra):
    canonical_url = absolute_url(path)
    return {
        "canonical_url": canonical_url,
        "og_url": canonical_url,
        "og_image": extra.pop("og_image", None),
        **extra,
    }


def person_schema() -> dict[str, str]:
    return {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Maxim",
        "brand": "Maxim AI Automation",
        "jobTitle": "AI Automation Developer",
        "description": "AI automation solutions for websites, WhatsApp and lead generation.",
    }


def service_schema(project: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": project.get("title", ""),
        "description": project.get("short_description", ""),
        "provider": {
            "@type": "Person",
            "name": "Maxim",
            "brand": "Maxim AI Automation",
        },
    }


def contact_channels() -> dict[str, str]:
    settings = get_settings()
    telegram = settings.contact_telegram.lstrip("@")
    whatsapp = "".join(char for char in settings.contact_whatsapp if char.isdigit())
    return {
        "telegram_label": f"@{telegram}",
        "telegram_url": f"https://t.me/{telegram}",
        "email": settings.contact_email,
        "email_url": f"mailto:{settings.contact_email}",
        "whatsapp_label": f"+{whatsapp}",
        "whatsapp_url": f"https://wa.me/{whatsapp}",
        "facebook_url": settings.contact_facebook,
        "photo_url": settings.contact_photo_url,
    }


@router.get("/robots.txt", response_class=Response)
def robots_txt() -> Response:
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            "Disallow: /admin",
            "Disallow: /admin/",
            "Disallow: /api/",
            "Disallow: /launch/",
            "",
            f"Sitemap: {absolute_url('/sitemap.xml')}",
            "",
        ]
    )
    return Response(body, media_type="text/plain")


@router.get("/sitemap.xml", response_class=Response)
def sitemap_xml() -> Response:
    urls = [
        ("/", "weekly", "1.0"),
        ("/projects", "weekly", "0.9"),
        *[(f"/projects/{project['id']}", "monthly", "0.8") for project in load_projects()],
        ("/contact", "monthly", "0.6"),
        ("/for-partners", "monthly", "0.7"),
    ]
    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, changefreq, priority in urls:
        body.extend(
            [
                "  <url>",
                f"    <loc>{escape(absolute_url(path) or '')}</loc>",
                f"    <changefreq>{changefreq}</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ]
        )
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        public_context(
            "/",
            request=request,
            projects=load_projects(),
            schema_data=person_schema(),
        ),
    )


@router.get("/for-partners", response_class=HTMLResponse)
def for_partners(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("for_partners.html", public_context("/for-partners", request=request))


@router.get("/projects", response_class=HTMLResponse)
def projects(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("projects.html", public_context("/projects", request=request, projects=load_projects()))


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    session_id = request.query_params.get("session_id")
    if session_id:
        record_event(db, "project_view", session_id=session_id, project_id=project_id, page_url=str(request.url), request=request)
        db.commit()
    return templates.TemplateResponse(
        "project_detail.html",
        public_context(
            f"/projects/{project_id}",
            request=request,
            project=project,
            meta_description=PROJECT_META_DESCRIPTIONS.get(project_id, project.get("short_description", "")),
            og_image=absolute_url(project.get("preview_image")),
            schema_data=service_schema(project),
        ),
    )


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
        public_context(
            "/contact",
            request=request,
            projects=load_projects(),
            selected_project_id=project_id,
            contact=contact_channels(),
        ),
    )

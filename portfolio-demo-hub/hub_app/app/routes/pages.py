"""Public website routes, SEO helpers, and the demo launch wrapper page."""

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

# Project-specific meta descriptions override short descriptions for SEO snippets.
PROJECT_META_DESCRIPTIONS = {
    "ai-site-consultant": "Демо AI-консультанта для сайта: посетитель получает ответы и оставляет заявку, а владелец видит контакты и историю общения.",
    "smart-lead-form": "Демо умной формы заявки: клиент отвечает на нужные вопросы, а владелец получает понятное структурированное обращение.",
}


def site_url() -> str:
    """Return the configured public site URL without a trailing slash."""
    return get_settings().site_url.rstrip("/")


def absolute_url(path: str | None) -> str | None:
    """Convert a relative site path into an absolute public URL."""
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    return f"{site_url()}/{path.lstrip('/')}"


def public_context(path: str, **extra):
    """Build shared template context for canonical/Open Graph metadata."""
    canonical_url = absolute_url(path)
    return {
        "canonical_url": canonical_url,
        "og_url": canonical_url,
        "og_image": extra.pop("og_image", None),
        **extra,
    }


def person_schema() -> dict[str, str]:
    """Structured data that describes the portfolio owner for search engines."""
    return {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Maxim",
        "brand": "Maxim AI Automation",
        "jobTitle": "AI Automation Developer",
        "description": "AI automation solutions for websites, WhatsApp and lead generation.",
    }


def service_schema(project: dict) -> dict:
    """Structured data for one project detail page."""
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
    """Normalize contact settings into labels and clickable URLs for templates."""
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
    """Robots file: allow public pages and hide admin/API/launch internals."""
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
    """Generate a small sitemap from static pages and active project configs."""
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
    """Landing page with the main offer and highlighted active projects."""
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
    """Partner-facing page for designers, marketers, SEO specialists, and agencies."""
    return templates.TemplateResponse("for_partners.html", public_context("/for-partners", request=request))


@router.get("/projects", response_class=HTMLResponse)
def projects(request: Request) -> HTMLResponse:
    """Catalog page that lists active projects from the project loader."""
    return templates.TemplateResponse("projects.html", public_context("/projects", request=request, projects=load_projects()))


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """Project detail page with analytics tracking when a session_id is present."""
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
    """Create a Hub demo session and render the iframe wrapper for one project."""
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
    """Contact page with optional project preselection from query parameters."""
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

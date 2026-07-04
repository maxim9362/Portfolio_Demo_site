"""Protected admin pages for leads, analytics, visitors, demos, and projects."""

import secrets
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse

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

CLIENT_TYPE_LABELS = {
    "web_designer": "Веб-дизайнер",
    "wordpress_developer": "WordPress-разработчик",
    "seo_specialist": "SEO-специалист",
    "marketer": "Маркетолог",
    "small_agency": "Небольшое агентство",
    "freelancer": "Фрилансер",
    "business_owner": "Владелец бизнеса",
    "agency": "Агентство",
    "designer": "Дизайнер / разработчик",
    "other": "Другое",
}

INTEREST_LABELS = {
    "ai_site_consultant": "AI-консультант для сайта клиента",
    "smart_lead_form": "Умная форма заявки",
    "website_development": "Разработка сайта / landing page",
    "lead_automation": "Автоматизация заявок",
    "wordpress_integration": "Подключение к WordPress-сайту",
    "white_label": "White-label сотрудничество",
    "ongoing_partnership": "Постоянное партнёрство",
    "other": "Другое",
}

PROJECT_STATUS_LABELS = {
    "has_client": "Есть конкретный клиент",
    "has_idea": "Есть идея",
    "exploring_partnership": "Смотрит варианты сотрудничества",
    "just_researching": "Пока изучает",
}

EVENT_LABELS = {
    "page_view": "Просмотр страницы",
    "partner_page_view": "Просмотр страницы партнёрам",
    "project_view": "Просмотр проекта",
    "service_page_view": "Просмотр услуги",
    "contact_open": "Открыл контакты",
    "contact_page_view": "Страница контактов",
    "contact_form_start": "Начал форму",
    "contact_submit": "Отправка заявки",
    "contact_submit_success": "Заявка сохранена",
    "contact_submit_error": "Ошибка в форме",
    "demo_launch": "Запуск демо",
    "demo_share_link": "Поделился демо",
    "demo_tab_open": "Открыл демо",
    "admin_tab_open": "Открыл админку",
    "demo_finish": "Завершил демо",
    "cta_click": "Клик по кнопке",
    "contact_button_click": "Клик на контакт",
    "project_demo_button_click": "Клик на запуск демо",
    "heartbeat": "Активность на странице",
    "session_end": "Сессия завершена",
}

EVENT_TONES = {
    "contact_submit": "lead",
    "contact_submit_success": "lead",
    "contact_form_start": "lead",
    "demo_launch": "demo",
    "demo_share_link": "demo",
    "demo_tab_open": "demo",
    "admin_tab_open": "demo",
    "demo_finish": "demo",
    "project_view": "project",
    "project_demo_button_click": "project",
    "page_view": "page",
    "partner_page_view": "page",
    "service_page_view": "page",
    "heartbeat": "technical",
    "session_end": "technical",
}

NOISY_DASHBOARD_EVENTS = {"heartbeat"}


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Basic Auth dependency used by every admin route."""
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
    """Format seconds into compact human-readable admin labels."""
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


def duration_ru(value: int | None) -> str:
    """Format seconds for human-readable Russian admin labels."""
    if value is None:
        return ""
    seconds = max(0, int(value))
    if seconds < 10:
        return "меньше 10 сек"
    if seconds < 60:
        return f"{seconds} сек"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} мин {sec} сек" if sec else f"{minutes} мин"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes} мин" if minutes else f"{hours} ч"


def format_datetime(value: datetime | None) -> str:
    """Format database datetimes into compact labels for admin screens."""
    if not value:
        return ""
    return value.strftime("%d.%m.%Y %H:%M")


def time_ago(value: datetime | None) -> str:
    """Return a short relative time label such as '5 мин назад'."""
    if not value:
        return ""
    current = datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    seconds = max(0, int((current - value).total_seconds()))
    if seconds < 60:
        return "только что"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} мин назад"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} ч назад"
    days = hours // 24
    return f"{days} дн назад"


def clean_page_url(page_url: str | None) -> str:
    """Show only the useful path instead of a full localhost URL."""
    if not page_url:
        return ""
    parsed = urlparse(page_url)
    path = parsed.path or "/"
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"session_id", "demo_session_id"}
    ]
    clean_query = urlencode(query_items)
    return f"{path}?{clean_query}" if clean_query else path


def short_id(value: str | None) -> str:
    """Shorten long technical ids while keeping links useful."""
    if not value:
        return ""
    if len(value) <= 18:
        return value
    return f"{value[:14]}..."


def time_on_page_seconds(event: AnalyticsEvent, db: Session) -> int | None:
    """Estimate how long the visitor stayed on this event's page."""
    if not event.session_id or not event.page_url or not event.created_at:
        return None

    current_page = clean_page_url(event.page_url)
    later_events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.session_id == event.session_id)
        .filter(AnalyticsEvent.created_at > event.created_at)
        .order_by(AnalyticsEvent.created_at.asc())
        .limit(80)
        .all()
    )

    end_at: datetime | None = None
    for later_event in later_events:
        later_page = clean_page_url(later_event.page_url)
        if later_event.event_type == "session_end":
            end_at = later_event.created_at
            break
        if later_page and later_page != current_page:
            end_at = later_event.created_at
            break

    if end_at is None:
        visitor = db.query(VisitorSession).filter(VisitorSession.session_id == event.session_id).one_or_none()
        if visitor:
            end_at = visitor.ended_at or visitor.last_seen_at

    if not end_at:
        return None
    if event.created_at.tzinfo is None:
        start_at = event.created_at.replace(tzinfo=UTC)
    else:
        start_at = event.created_at
    if end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=UTC)
    return max(0, int((end_at - start_at).total_seconds()))


def event_description(event: AnalyticsEvent) -> str:
    """Translate a raw analytics event into a human-readable sentence."""
    page = clean_page_url(event.page_url)
    project = event.project_id or ""
    if event.event_type in {"page_view", "partner_page_view", "service_page_view"}:
        return f"Посетитель открыл страницу {page or 'сайта'}."
    if event.event_type == "project_view":
        return f"Посетитель смотрел проект {project or page}."
    if event.event_type == "demo_launch":
        return f"Посетитель запустил демо {project or 'проекта'}."
    if event.event_type == "demo_share_link":
        return f"Посетитель скопировал или отправил ссылку на демо {project or 'проекта'}."
    if event.event_type == "demo_tab_open":
        return f"Посетитель переключился на демо {project or 'проекта'}."
    if event.event_type == "admin_tab_open":
        return f"Посетитель открыл админку {project or 'проекта'}."
    if event.event_type == "demo_finish":
        return f"Посетитель завершил демо {project or 'проекта'}."
    if event.event_type in {"contact_open", "contact_page_view"}:
        return "Посетитель открыл страницу контактов."
    if event.event_type == "contact_form_start":
        return "Посетитель начал заполнять контактную форму."
    if event.event_type in {"contact_submit", "contact_submit_success"}:
        return "Посетитель отправил заявку через контактную форму."
    if event.event_type == "contact_submit_error":
        return "Форма не отправилась: нужно проверить, какие поля не заполнены."
    if event.event_type == "project_demo_button_click":
        return f"Посетитель нажал кнопку запуска демо {project or 'проекта'}."
    if event.event_type in {"cta_click", "contact_button_click"}:
        return f"Посетитель нажал кнопку на странице {page or 'сайта'}."
    if event.event_type == "heartbeat":
        return "Технический сигнал: вкладка сайта была открыта и активна."
    if event.event_type == "session_end":
        return "Браузер сообщил о завершении сессии или закрытии вкладки."
    return f"Событие: {event.event_type}."


def event_row(event: AnalyticsEvent, db: Session | None = None) -> dict[str, Any]:
    """Prepare one analytics event for readable admin templates."""
    page_seconds = time_on_page_seconds(event, db) if db else None
    return {
        "item": event,
        "label": EVENT_LABELS.get(event.event_type, event.event_type),
        "description": event_description(event),
        "tone": EVENT_TONES.get(event.event_type, "default"),
        "created_at": format_datetime(event.created_at),
        "time_ago": time_ago(event.created_at),
        "page": clean_page_url(event.page_url),
        "time_on_page": duration_ru(page_seconds),
        "project": event.project_id or "",
        "session_short": short_id(event.session_id),
        "demo_session_short": short_id(event.demo_session_id),
    }


def demo_duration(item: DemoSession) -> int:
    """Return stored demo duration or calculate a live duration for active demos."""
    if item.duration_seconds is not None:
        return item.duration_seconds
    if item.started_at:
        end = item.ended_at or item.last_seen_at or datetime.now(UTC)
        return max(0, int((end - item.started_at).total_seconds()))
    return 0


def referer_or(path: str, request: Request) -> str:
    """Redirect back to the previous admin page after POST actions."""
    return request.headers.get("referer") or path


def project_options() -> list[dict[str, Any]]:
    """Load active project metadata for admin filters and project tables."""
    return load_projects()


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    """Admin overview with core portfolio metrics and the latest events."""
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
    recent_events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.event_type.notin_(NOISY_DASHBOARD_EVENTS))
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(12)
        .all()
    )
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
            "recent_events": [event_row(event, db) for event in recent_events],
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
    """List contact leads with simple filters for status, project, and client type."""
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
            "client_type_labels": CLIENT_TYPE_LABELS,
            "interest_labels": INTEREST_LABELS,
            "project_status_labels": PROJECT_STATUS_LABELS,
        },
    )


@router.post("/leads/{lead_id}/viewed")
def lead_viewed(lead_id: int, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    """Mark a lead as viewed from the leads table."""
    return update_lead_status(lead_id, "viewed", request, db)


@router.post("/leads/{lead_id}/archive")
def lead_archive(lead_id: int, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    """Archive a lead without deleting it from the database."""
    return update_lead_status(lead_id, "archived", request, db)


@router.post("/leads/{lead_id}/restore")
def lead_restore(lead_id: int, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> RedirectResponse:
    """Restore an archived/viewed lead to the new status."""
    return update_lead_status(lead_id, "new", request, db)


def update_lead_status(lead_id: int, new_status: str, request: Request, db: Session) -> RedirectResponse:
    """Shared status update helper for all lead action buttons."""
    if new_status not in {"new", "viewed", "archived"}:
        raise HTTPException(status_code=400, detail="Invalid lead status")
    lead = db.get(ContactLead, lead_id)
    if lead:
        lead.status = new_status
        db.commit()
    return RedirectResponse(referer_or("/admin/leads", request), status_code=303)


@router.get("/sessions", response_class=HTMLResponse)
def sessions(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    """Show visitor sessions enriched with event, demo, project, and lead counts."""
    items = db.query(VisitorSession).order_by(VisitorSession.last_seen_at.desc().nullslast()).limit(300).all()
    session_ids = [item.session_id for item in items]
    event_counts = dict(
        db.query(AnalyticsEvent.session_id, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.session_id.in_(session_ids))
        .group_by(AnalyticsEvent.session_id)
        .all()
    )
    viewed_projects = dict(
        db.query(AnalyticsEvent.session_id, func.count(distinct(AnalyticsEvent.project_id)))
        .filter(AnalyticsEvent.session_id.in_(session_ids))
        .filter(AnalyticsEvent.event_type == "project_view")
        .filter(AnalyticsEvent.project_id.isnot(None))
        .group_by(AnalyticsEvent.session_id)
        .all()
    )
    demo_counts = dict(
        db.query(DemoSession.session_id, func.count(DemoSession.id))
        .filter(DemoSession.session_id.in_(session_ids))
        .group_by(DemoSession.session_id)
        .all()
    )
    lead_session_ids = {
        row[0]
        for row in db.query(ContactLead.session_id)
        .filter(ContactLead.session_id.in_(session_ids))
        .filter(ContactLead.session_id.isnot(None))
        .distinct()
        .all()
    }
    rows = []
    for item in items:
        rows.append(
            {
                "item": item,
                "event_count": event_counts.get(item.session_id, 0),
                "viewed_projects": viewed_projects.get(item.session_id, 0),
                "demo_count": demo_counts.get(item.session_id, 0),
                "has_lead": item.session_id in lead_session_ids,
                "duration": duration(item.duration_seconds),
            }
        )
    return templates.TemplateResponse("admin/sessions.html", {"request": request, "sessions": rows})


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
def session_detail(session_id: str, request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)) -> HTMLResponse:
    """Show a single visitor journey: pages, projects, demos, events, and leads."""
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
    """Show raw events plus page, project, demo, admin, and conversion summaries."""
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
            "event_rows": [event_row(event, db) for event in events],
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
    """List wrapper-level demo sessions with filters and duration labels."""
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
    """Show one demo launch and all analytics events tied to it."""
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
    """Show active projects exactly as the public project loader sees them."""
    return templates.TemplateResponse("admin/projects.html", {"request": request, "projects": load_projects()})


def _event_counts(db: Session, event_type: str) -> list[tuple[str, int]]:
    """Return project-level counts for one analytics event type."""
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

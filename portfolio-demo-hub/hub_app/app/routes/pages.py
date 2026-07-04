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
DEFAULT_OG_IMAGE = "/static/img/maxim-profile.jpg"

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
    og_image = extra.pop("og_image", None) or DEFAULT_OG_IMAGE
    return {
        "canonical_url": canonical_url,
        "og_url": canonical_url,
        "og_image": absolute_url(og_image),
        **extra,
    }


def professional_service_schema() -> dict:
    """Structured data for the main Maxim AI Automation service brand."""
    return {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": "Maxim AI Automation",
        "url": site_url(),
        "description": (
            "Технический партнёр для дизайнеров, WordPress-разработчиков, SEO-специалистов "
            "и маркетологов: AI-консультанты, умные формы заявок, автоматизация и "
            "техническая реализация сайтов."
        ),
        "areaServed": "Israel",
        "serviceType": [
            "AI chatbot for websites",
            "Smart lead forms",
            "Website development",
            "Business automation",
        ],
    }


def software_application_schema(project: dict) -> dict:
    """Structured data for one public demo project page."""
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": project.get("title", ""),
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "description": project.get("short_description", ""),
        "url": absolute_url(f"/projects/{project.get('id', '')}"),
        "provider": {"@type": "ProfessionalService", "name": "Maxim AI Automation"},
    }


def solution_schema(solution: dict) -> dict:
    """Structured data for public service/solution pages."""
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": solution.get("h1", ""),
        "description": solution.get("description", ""),
        "url": absolute_url(solution.get("url", "")),
        "provider": {"@type": "ProfessionalService", "name": "Maxim AI Automation"},
        "areaServed": "Israel",
    }


def webpage_schema(name: str, description: str, path: str) -> dict:
    """Simple WebPage structured data for public utility pages."""
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": name,
        "description": description,
        "url": absolute_url(path),
        "publisher": {"@type": "ProfessionalService", "name": "Maxim AI Automation"},
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


SOLUTION_PAGES = {
    "ai-chatbot-for-website": {
        "url": "/ai-chatbot-for-website",
        "title": "AI-консультант для сайтов клиентов — Maxim AI Automation",
        "description": "AI-консультант для сайта клиента: чат отвечает посетителям, объясняет услуги, помогает оставить заявку и показывает владельцу историю обращения.",
        "eyebrow": "AI-консультант для сайта",
        "h1": "AI-консультант для сайтов клиентов",
        "hero": "Решение, которое можно добавить к сайту клиента: AI-консультант отвечает посетителям, объясняет услуги и помогает оставить заявку.",
        "plain_title": "Что это простыми словами",
        "plain": "AI-консультант — это чат на сайте, который помогает посетителю быстро получить ответ. Он может объяснить услуги, условия, цены, частые вопросы и помочь оставить заявку.",
        "audience": ["веб-дизайнеры", "WordPress-разработчики", "SEO-специалисты", "маркетологи", "агентства с клиентскими сайтами"],
        "partner_value": ["можно предложить клиенту не просто сайт, а сайт с помощником для обращений", "легче показать ценность через живое демо", "решение можно адаптировать под нишу клиента"],
        "client_value": ["посетители получают ответы быстрее", "заявки становятся понятнее", "владелец видит историю общения и контакты"],
        "steps": ["посетитель задаёт вопрос", "чат уточняет детали", "клиент оставляет контакт", "владелец видит заявку в админке"],
        "adapt": ["тексты", "услуги", "цены", "частые вопросы", "тон общения", "поля заявки", "внешний вид"],
        "demo_links": [
            {"label": "Запустить демо AI-консультанта", "href": "/launch/ai-site-consultant", "primary": True},
            {"label": "Подробнее о демо", "href": "/projects/ai-site-consultant", "primary": False},
        ],
        "related": [
            {"label": "Умная форма заявки", "href": "/smart-lead-form"},
            {"label": "AI и формы для WordPress", "href": "/wordpress-ai-integration"},
        ],
    },
    "smart-lead-form": {
        "url": "/smart-lead-form",
        "title": "Умная форма заявки для сайтов клиентов — Maxim AI Automation",
        "description": "Умная форма заявки для сайта клиента: задаёт нужные вопросы, собирает детали обращения и передаёт владельцу понятную структурированную заявку.",
        "eyebrow": "Умная форма заявки",
        "h1": "Умная форма заявки для сайтов клиентов",
        "hero": "Обычная форма собирает имя и телефон. Умная форма помогает посетителю описать задачу и передаёт владельцу уже понятную заявку.",
        "plain_title": "Чем лучше обычной формы",
        "plain": "Обычная форма часто даёт владельцу только контакт. Умная форма заранее уточняет услугу, город, срочность, детали задачи и удобное время связи.",
        "audience": ["дизайнеры сайтов услуг", "WordPress-разработчики", "SEO-специалисты", "маркетологи", "агентства"],
        "partner_value": ["можно заменить слабую форму на более полезный сценарий", "клиенту проще понять пользу через демо", "форму можно адаптировать под разные ниши"],
        "client_value": ["меньше лишней переписки", "заявка содержит важные детали", "владельцу проще обработать обращение"],
        "steps": ["посетитель выбирает услугу", "форма задаёт уточняющие вопросы", "собираются контакты", "владелец получает подробную заявку"],
        "adapt": ["вопросы", "варианты ответов", "логика расчёта", "ниша", "форма заявки", "тексты", "внешний вид"],
        "demo_links": [
            {"label": "Запустить демо умной формы", "href": "/launch/smart-lead-form", "primary": True},
            {"label": "Подробнее о демо", "href": "/projects/smart-lead-form", "primary": False},
        ],
        "related": [
            {"label": "AI-консультант для сайта", "href": "/ai-chatbot-for-website"},
            {"label": "Автоматизация для агентств", "href": "/automation-for-agencies"},
        ],
    },
    "wordpress-ai-integration": {
        "url": "/wordpress-ai-integration",
        "title": "AI-консультант и умные формы для WordPress-сайтов — Maxim AI Automation",
        "description": "Внешний AI-консультант и умная форма заявки для WordPress-сайтов клиентов. Можно подключить как отдельный виджет без полной переделки сайта.",
        "eyebrow": "Для WordPress-проектов",
        "h1": "AI-консультант и умные формы для WordPress-сайтов",
        "hero": "Если вы делаете сайты на WordPress, можно добавить клиенту внешний AI-консультант или умную форму заявки без полной переделки сайта.",
        "plain_title": "Как это подключается простыми словами",
        "plain": "Решение работает как внешний модуль: его можно встроить на сайт клиента через отдельный скрипт или виджет. Это удобно, когда не хочется полностью переделывать сайт.",
        "audience": ["WordPress-разработчики", "дизайнеры на конструкторах", "SEO-специалисты", "поддержка клиентских сайтов"],
        "partner_value": ["можно добавить новую услугу к WordPress-сайту", "не нужно перестраивать весь проект", "можно показать клиенту живое демо"],
        "client_value": ["сайт начинает лучше собирать обращения", "посетители быстрее получают ответы", "владелец получает более понятные заявки"],
        "steps": ["выбираем сценарий", "адаптируем тексты и вопросы", "подключаем внешний модуль", "проверяем путь заявки"],
        "adapt": ["виджет", "тексты", "вопросы", "поля заявки", "цвета", "сценарий", "админка"],
        "demo_links": [
            {"label": "Демо AI-консультанта", "href": "/launch/ai-site-consultant", "primary": True},
            {"label": "Демо умной формы", "href": "/launch/smart-lead-form", "primary": False},
        ],
        "related": [
            {"label": "AI-консультант для сайта", "href": "/ai-chatbot-for-website"},
            {"label": "Умная форма заявки", "href": "/smart-lead-form"},
        ],
    },
    "automation-for-agencies": {
        "url": "/automation-for-agencies",
        "title": "Автоматизация заявок для агентств и специалистов по сайтам — Maxim AI Automation",
        "description": "Автоматизация заявок для клиентов агентств, дизайнеров, SEO-специалистов и маркетологов: AI-консультанты, умные формы, админки и обработка обращений.",
        "eyebrow": "Автоматизация для агентств",
        "h1": "Автоматизация заявок для агентств и клиентских сайтов",
        "hero": "Помогаю добавлять к проектам клиентов автоматизацию: сбор заявок, понятные формы, AI-консультантов, админки и удобную обработку обращений.",
        "plain_title": "Какие проблемы решает автоматизация",
        "plain": "Автоматизация помогает не терять обращения, заранее собирать важные детали и передавать владельцу бизнеса заявку в удобном виде.",
        "audience": ["небольшие digital-агентства", "маркетологи", "SEO-команды", "фрилансеры с клиентскими проектами"],
        "partner_value": ["можно расширить предложение без найма отдельной команды", "проще показать клиенту рабочий сценарий", "можно начать с одного клиента"],
        "client_value": ["заявки становятся понятнее", "меньше ручных уточнений", "обращения удобнее обрабатывать"],
        "steps": ["описываем проблему клиента", "выбираем сценарий автоматизации", "показываем демо", "адаптируем под нишу", "запускаем"],
        "adapt": ["сбор заявок", "формы", "чат", "админка", "поля заявки", "логика обработки", "передача данных"],
        "demo_links": [
            {"label": "Посмотреть живые демо", "href": "/projects", "primary": True},
            {"label": "Обсудить задачу", "href": "/contact", "primary": False},
        ],
        "related": [
            {"label": "AI-консультант для сайта", "href": "/ai-chatbot-for-website"},
            {"label": "Умная форма заявки", "href": "/smart-lead-form"},
        ],
    },
    "website-development-for-partners": {
        "url": "/website-development-for-partners",
        "title": "Разработка сайтов для дизайнеров, маркетологов и SEO — Maxim AI Automation",
        "description": "Техническая реализация сайтов для дизайнеров, SEO-специалистов, маркетологов и агентств: страницы, формы, backend-логика, заявки и интеграции.",
        "eyebrow": "Разработка сайтов для партнёров",
        "h1": "Разработка сайтов для дизайнеров, маркетологов и SEO-специалистов",
        "hero": "Если у вас есть клиент, дизайн, идея или SEO-задача, я могу помочь с технической реализацией сайта, формами, заявками, backend-логикой и интеграциями.",
        "plain_title": "Когда партнёру нужен технический исполнитель",
        "plain": "Когда есть клиентская задача, но не хочется искать отдельную backend-команду, можно подключить меня для реализации конкретной технической части.",
        "audience": ["веб-дизайнеры", "маркетологи", "SEO-специалисты", "небольшие агентства", "фрилансеры"],
        "partner_value": ["можно вести клиента самому", "техническую часть можно передать мне", "можно добавить к сайту AI, формы и автоматизацию"],
        "client_value": ["клиент получает рабочий сайт", "заявки собираются понятнее", "проект можно развивать после запуска"],
        "steps": ["вы приносите задачу", "согласуем структуру", "реализую техническую часть", "проверяем заявки", "запускаем"],
        "adapt": ["верстка страниц", "формы заявок", "backend-логика", "админка", "AI-виджет", "умная форма", "автоматизация обращений"],
        "demo_links": [
            {"label": "Посмотреть живые демо", "href": "/projects", "primary": True},
            {"label": "Для партнёров", "href": "/for-partners", "primary": False},
        ],
        "related": [
            {"label": "AI и формы для WordPress", "href": "/wordpress-ai-integration"},
            {"label": "Автоматизация для агентств", "href": "/automation-for-agencies"},
        ],
    },
}

SOLUTION_FAQ = [
    ("Можно ли подключить это к уже готовому сайту?", "Да, во многих случаях решение можно добавить как внешний модуль, виджет или отдельную форму без полной переделки сайта."),
    ("Можно ли показать клиенту демо до продажи?", "Да. Для этого есть живые демо, которые помогают быстро объяснить идею и пользу."),
    ("Можно ли адаптировать решение под нишу клиента?", "Да. Меняются тексты, вопросы, услуги, поля заявки, внешний вид и логика обработки."),
    ("Вы будете общаться с моим клиентом напрямую?", "Не обязательно. Можно работать через вас, чтобы клиент оставался вашим."),
    ("Можно ли начать с одного проекта?", "Да. Обычно удобно начать с одного понятного сценария и проверить формат сотрудничества."),
]


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
            "Disallow: /api",
            "Disallow: /api/",
            "Disallow: /launch",
            "Disallow: /launch/",
            "Disallow: /demo",
            "Disallow: /demo/",
            "Disallow: /admin-demo",
            "Disallow: /admin-demo/",
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
        ("/for-partners", "monthly", "0.8"),
        ("/services", "monthly", "0.8"),
        *[(solution["url"], "monthly", "0.8") for solution in SOLUTION_PAGES.values()],
        ("/projects", "weekly", "0.9"),
        *[(f"/projects/{project['id']}", "monthly", "0.8") for project in load_projects()],
        ("/contact", "monthly", "0.6"),
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
            schema_data=professional_service_schema(),
        ),
    )


@router.get("/for-partners", response_class=HTMLResponse)
def for_partners(request: Request) -> HTMLResponse:
    """Partner-facing page for designers, marketers, SEO specialists, and agencies."""
    return templates.TemplateResponse(
        "for_partners.html",
        public_context(
            "/for-partners",
            request=request,
            schema_data=webpage_schema(
                "Партнёр по AI и автоматизации для веб-дизайнеров и агентств",
                "Техническая помощь для партнёров: AI-консультанты, умные формы заявок, админки и автоматизация.",
                "/for-partners",
            ),
        ),
    )


@router.get("/services", response_class=HTMLResponse)
def services(request: Request) -> HTMLResponse:
    """Overview page for partner-ready services and solution pages."""
    return templates.TemplateResponse(
        "services.html",
        public_context(
            "/services",
            request=request,
            solutions=SOLUTION_PAGES,
            schema_data=webpage_schema(
                "Решения для сайтов клиентов",
                "AI-консультанты, умные формы заявок, автоматизация и техническая реализация сайтов для партнёров.",
                "/services",
            ),
        ),
    )


@router.get("/ai-chatbot-for-website", response_class=HTMLResponse)
@router.get("/smart-lead-form", response_class=HTMLResponse)
@router.get("/wordpress-ai-integration", response_class=HTMLResponse)
@router.get("/automation-for-agencies", response_class=HTMLResponse)
@router.get("/website-development-for-partners", response_class=HTMLResponse)
def solution_detail(request: Request) -> HTMLResponse:
    """Render one public solution page for partners from the shared content map."""
    slug = request.url.path.strip("/")
    solution = SOLUTION_PAGES.get(slug)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    return templates.TemplateResponse(
        "solution_detail.html",
        public_context(
            solution["url"],
            request=request,
            solution=solution,
            solutions=SOLUTION_PAGES,
            faq_items=SOLUTION_FAQ,
            schema_data=solution_schema(solution),
        ),
    )


@router.get("/projects", response_class=HTMLResponse)
def projects(request: Request) -> HTMLResponse:
    """Catalog page that lists active projects from the project loader."""
    return templates.TemplateResponse(
        "projects.html",
        public_context(
            "/projects",
            request=request,
            projects=load_projects(),
            schema_data=webpage_schema(
                "Живые демо AI-консультантов и умных форм заявок",
                "Живые демо решений для сайтов клиентов: AI-консультант, умная форма заявки и админка.",
                "/projects",
            ),
        ),
    )


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
            schema_data=software_application_schema(project),
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
def contact(
    request: Request,
    project_id: str | None = Query(default=None),
    project: str | None = Query(default=None),
    interest: str | None = Query(default=None),
) -> HTMLResponse:
    """Contact page with optional project preselection from query parameters."""
    selected_project_id = project_id or project
    selected_interest = interest or {
        "ai-site-consultant": "ai_site_consultant",
        "smart-lead-form": "smart_lead_form",
    }.get(selected_project_id or "", "")
    return templates.TemplateResponse(
        "contact.html",
        public_context(
            "/contact",
            request=request,
            projects=load_projects(),
            selected_project_id=selected_project_id,
            selected_interest=selected_interest,
            contact=contact_channels(),
            schema_data=webpage_schema(
                "Обсудить сайт или автоматизацию заявок",
                "Контактная страница Maxim AI Automation для обсуждения сайта, AI-консультанта, умной формы или партнёрства.",
                "/contact",
            ),
        ),
    )

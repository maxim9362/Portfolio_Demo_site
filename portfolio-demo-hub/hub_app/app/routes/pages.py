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
    "ai-site-consultant": "Р”РµРјРѕ AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚Р° РґР»СЏ СЃР°Р№С‚Р°: РїРѕСЃРµС‚РёС‚РµР»СЊ РїРѕР»СѓС‡Р°РµС‚ РѕС‚РІРµС‚С‹ Рё РѕСЃС‚Р°РІР»СЏРµС‚ Р·Р°СЏРІРєСѓ, Р° РІР»Р°РґРµР»РµС† РІРёРґРёС‚ РєРѕРЅС‚Р°РєС‚С‹ Рё РёСЃС‚РѕСЂРёСЋ РѕР±С‰РµРЅРёСЏ.",
    "smart-lead-form": "Р”РµРјРѕ СѓРјРЅРѕР№ С„РѕСЂРјС‹ Р·Р°СЏРІРєРё: РєР»РёРµРЅС‚ РѕС‚РІРµС‡Р°РµС‚ РЅР° РЅСѓР¶РЅС‹Рµ РІРѕРїСЂРѕСЃС‹, Р° РІР»Р°РґРµР»РµС† РїРѕР»СѓС‡Р°РµС‚ РїРѕРЅСЏС‚РЅРѕРµ СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅРѕРµ РѕР±СЂР°С‰РµРЅРёРµ.",
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
    """Structured data for the main AI Automation service brand."""
    return {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": "AI Automation",
        "url": site_url(),
        "description": (
            "РўРµС…РЅРёС‡РµСЃРєРёР№ РїР°СЂС‚РЅС‘СЂ РґР»СЏ РґРёР·Р°Р№РЅРµСЂРѕРІ, WordPress-СЂР°Р·СЂР°Р±РѕС‚С‡РёРєРѕРІ, SEO-СЃРїРµС†РёР°Р»РёСЃС‚РѕРІ "
            "Рё РјР°СЂРєРµС‚РѕР»РѕРіРѕРІ: AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚С‹, СѓРјРЅС‹Рµ С„РѕСЂРјС‹ Р·Р°СЏРІРѕРє, Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЏ Рё "
            "С‚РµС…РЅРёС‡РµСЃРєР°СЏ СЂРµР°Р»РёР·Р°С†РёСЏ СЃР°Р№С‚РѕРІ."
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
        "provider": {"@type": "ProfessionalService", "name": "AI Automation"},
    }


def solution_schema(solution: dict) -> dict:
    """Structured data for public service/solution pages."""
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": solution.get("h1", ""),
        "description": solution.get("description", ""),
        "url": absolute_url(solution.get("url", "")),
        "provider": {"@type": "ProfessionalService", "name": "AI Automation"},
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
        "publisher": {"@type": "ProfessionalService", "name": "AI Automation"},
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
        "title": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РґР»СЏ СЃР°Р№С‚РѕРІ РєР»РёРµРЅС‚РѕРІ вЂ” AI Automation",
        "description": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РґР»СЏ СЃР°Р№С‚Р° РєР»РёРµРЅС‚Р°: С‡Р°С‚ РѕС‚РІРµС‡Р°РµС‚ РїРѕСЃРµС‚РёС‚РµР»СЏРј, РѕР±СЉСЏСЃРЅСЏРµС‚ СѓСЃР»СѓРіРё, РїРѕРјРѕРіР°РµС‚ РѕСЃС‚Р°РІРёС‚СЊ Р·Р°СЏРІРєСѓ Рё РїРѕРєР°Р·С‹РІР°РµС‚ РІР»Р°РґРµР»СЊС†Сѓ РёСЃС‚РѕСЂРёСЋ РѕР±СЂР°С‰РµРЅРёСЏ.",
        "eyebrow": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РґР»СЏ СЃР°Р№С‚Р°",
        "h1": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РґР»СЏ СЃР°Р№С‚РѕРІ РєР»РёРµРЅС‚РѕРІ",
        "hero": "Р РµС€РµРЅРёРµ, РєРѕС‚РѕСЂРѕРµ РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ Рє СЃР°Р№С‚Сѓ РєР»РёРµРЅС‚Р°: AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РѕС‚РІРµС‡Р°РµС‚ РїРѕСЃРµС‚РёС‚РµР»СЏРј, РѕР±СЉСЏСЃРЅСЏРµС‚ СѓСЃР»СѓРіРё Рё РїРѕРјРѕРіР°РµС‚ РѕСЃС‚Р°РІРёС‚СЊ Р·Р°СЏРІРєСѓ.",
        "plain_title": "Р§С‚Рѕ СЌС‚Рѕ РїСЂРѕСЃС‚С‹РјРё СЃР»РѕРІР°РјРё",
        "plain": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ вЂ” СЌС‚Рѕ С‡Р°С‚ РЅР° СЃР°Р№С‚Рµ, РєРѕС‚РѕСЂС‹Р№ РїРѕРјРѕРіР°РµС‚ РїРѕСЃРµС‚РёС‚РµР»СЋ Р±С‹СЃС‚СЂРѕ РїРѕР»СѓС‡РёС‚СЊ РѕС‚РІРµС‚. РћРЅ РјРѕР¶РµС‚ РѕР±СЉСЏСЃРЅРёС‚СЊ СѓСЃР»СѓРіРё, СѓСЃР»РѕРІРёСЏ, С†РµРЅС‹, С‡Р°СЃС‚С‹Рµ РІРѕРїСЂРѕСЃС‹ Рё РїРѕРјРѕС‡СЊ РѕСЃС‚Р°РІРёС‚СЊ Р·Р°СЏРІРєСѓ.",
        "audience": ["РІРµР±-РґРёР·Р°Р№РЅРµСЂС‹", "WordPress-СЂР°Р·СЂР°Р±РѕС‚С‡РёРєРё", "SEO-СЃРїРµС†РёР°Р»РёСЃС‚С‹", "РјР°СЂРєРµС‚РѕР»РѕРіРё", "Р°РіРµРЅС‚СЃС‚РІР° СЃ РєР»РёРµРЅС‚СЃРєРёРјРё СЃР°Р№С‚Р°РјРё"],
        "partner_value": ["РјРѕР¶РЅРѕ РїСЂРµРґР»РѕР¶РёС‚СЊ РєР»РёРµРЅС‚Сѓ РЅРµ РїСЂРѕСЃС‚Рѕ СЃР°Р№С‚, Р° СЃР°Р№С‚ СЃ РїРѕРјРѕС‰РЅРёРєРѕРј РґР»СЏ РѕР±СЂР°С‰РµРЅРёР№", "Р»РµРіС‡Рµ РїРѕРєР°Р·Р°С‚СЊ С†РµРЅРЅРѕСЃС‚СЊ С‡РµСЂРµР· Р¶РёРІРѕРµ РґРµРјРѕ", "СЂРµС€РµРЅРёРµ РјРѕР¶РЅРѕ Р°РґР°РїС‚РёСЂРѕРІР°С‚СЊ РїРѕРґ РЅРёС€Сѓ РєР»РёРµРЅС‚Р°"],
        "client_value": ["РїРѕСЃРµС‚РёС‚РµР»Рё РїРѕР»СѓС‡Р°СЋС‚ РѕС‚РІРµС‚С‹ Р±С‹СЃС‚СЂРµРµ", "Р·Р°СЏРІРєРё СЃС‚Р°РЅРѕРІСЏС‚СЃСЏ РїРѕРЅСЏС‚РЅРµРµ", "РІР»Р°РґРµР»РµС† РІРёРґРёС‚ РёСЃС‚РѕСЂРёСЋ РѕР±С‰РµРЅРёСЏ Рё РєРѕРЅС‚Р°РєС‚С‹"],
        "steps": ["РїРѕСЃРµС‚РёС‚РµР»СЊ Р·Р°РґР°С‘С‚ РІРѕРїСЂРѕСЃ", "С‡Р°С‚ СѓС‚РѕС‡РЅСЏРµС‚ РґРµС‚Р°Р»Рё", "РєР»РёРµРЅС‚ РѕСЃС‚Р°РІР»СЏРµС‚ РєРѕРЅС‚Р°РєС‚", "РІР»Р°РґРµР»РµС† РІРёРґРёС‚ Р·Р°СЏРІРєСѓ РІ Р°РґРјРёРЅРєРµ"],
        "adapt": ["С‚РµРєСЃС‚С‹", "СѓСЃР»СѓРіРё", "С†РµРЅС‹", "С‡Р°СЃС‚С‹Рµ РІРѕРїСЂРѕСЃС‹", "С‚РѕРЅ РѕР±С‰РµРЅРёСЏ", "РїРѕР»СЏ Р·Р°СЏРІРєРё", "РІРЅРµС€РЅРёР№ РІРёРґ"],
        "demo_links": [
            {"label": "Р—Р°РїСѓСЃС‚РёС‚СЊ РґРµРјРѕ AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚Р°", "href": "/launch/ai-site-consultant", "primary": True},
            {"label": "РџРѕРґСЂРѕР±РЅРµРµ Рѕ РґРµРјРѕ", "href": "/projects/ai-site-consultant", "primary": False},
        ],
        "related": [
            {"label": "РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё", "href": "/smart-lead-form"},
            {"label": "AI Рё С„РѕСЂРјС‹ РґР»СЏ WordPress", "href": "/wordpress-ai-integration"},
        ],
    },
    "smart-lead-form": {
        "url": "/smart-lead-form",
        "title": "РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё РґР»СЏ СЃР°Р№С‚РѕРІ РєР»РёРµРЅС‚РѕРІ вЂ” AI Automation",
        "description": "РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё РґР»СЏ СЃР°Р№С‚Р° РєР»РёРµРЅС‚Р°: Р·Р°РґР°С‘С‚ РЅСѓР¶РЅС‹Рµ РІРѕРїСЂРѕСЃС‹, СЃРѕР±РёСЂР°РµС‚ РґРµС‚Р°Р»Рё РѕР±СЂР°С‰РµРЅРёСЏ Рё РїРµСЂРµРґР°С‘С‚ РІР»Р°РґРµР»СЊС†Сѓ РїРѕРЅСЏС‚РЅСѓСЋ СЃС‚СЂСѓРєС‚СѓСЂРёСЂРѕРІР°РЅРЅСѓСЋ Р·Р°СЏРІРєСѓ.",
        "eyebrow": "РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё",
        "h1": "РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё РґР»СЏ СЃР°Р№С‚РѕРІ РєР»РёРµРЅС‚РѕРІ",
        "hero": "РћР±С‹С‡РЅР°СЏ С„РѕСЂРјР° СЃРѕР±РёСЂР°РµС‚ РёРјСЏ Рё С‚РµР»РµС„РѕРЅ. РЈРјРЅР°СЏ С„РѕСЂРјР° РїРѕРјРѕРіР°РµС‚ РїРѕСЃРµС‚РёС‚РµР»СЋ РѕРїРёСЃР°С‚СЊ Р·Р°РґР°С‡Сѓ Рё РїРµСЂРµРґР°С‘С‚ РІР»Р°РґРµР»СЊС†Сѓ СѓР¶Рµ РїРѕРЅСЏС‚РЅСѓСЋ Р·Р°СЏРІРєСѓ.",
        "plain_title": "Р§РµРј Р»СѓС‡С€Рµ РѕР±С‹С‡РЅРѕР№ С„РѕСЂРјС‹",
        "plain": "РћР±С‹С‡РЅР°СЏ С„РѕСЂРјР° С‡Р°СЃС‚Рѕ РґР°С‘С‚ РІР»Р°РґРµР»СЊС†Сѓ С‚РѕР»СЊРєРѕ РєРѕРЅС‚Р°РєС‚. РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЂР°РЅРµРµ СѓС‚РѕС‡РЅСЏРµС‚ СѓСЃР»СѓРіСѓ, РіРѕСЂРѕРґ, СЃСЂРѕС‡РЅРѕСЃС‚СЊ, РґРµС‚Р°Р»Рё Р·Р°РґР°С‡Рё Рё СѓРґРѕР±РЅРѕРµ РІСЂРµРјСЏ СЃРІСЏР·Рё.",
        "audience": ["РґРёР·Р°Р№РЅРµСЂС‹ СЃР°Р№С‚РѕРІ СѓСЃР»СѓРі", "WordPress-СЂР°Р·СЂР°Р±РѕС‚С‡РёРєРё", "SEO-СЃРїРµС†РёР°Р»РёСЃС‚С‹", "РјР°СЂРєРµС‚РѕР»РѕРіРё", "Р°РіРµРЅС‚СЃС‚РІР°"],
        "partner_value": ["РјРѕР¶РЅРѕ Р·Р°РјРµРЅРёС‚СЊ СЃР»Р°Р±СѓСЋ С„РѕСЂРјСѓ РЅР° Р±РѕР»РµРµ РїРѕР»РµР·РЅС‹Р№ СЃС†РµРЅР°СЂРёР№", "РєР»РёРµРЅС‚Сѓ РїСЂРѕС‰Рµ РїРѕРЅСЏС‚СЊ РїРѕР»СЊР·Сѓ С‡РµСЂРµР· РґРµРјРѕ", "С„РѕСЂРјСѓ РјРѕР¶РЅРѕ Р°РґР°РїС‚РёСЂРѕРІР°С‚СЊ РїРѕРґ СЂР°Р·РЅС‹Рµ РЅРёС€Рё"],
        "client_value": ["РјРµРЅСЊС€Рµ Р»РёС€РЅРµР№ РїРµСЂРµРїРёСЃРєРё", "Р·Р°СЏРІРєР° СЃРѕРґРµСЂР¶РёС‚ РІР°Р¶РЅС‹Рµ РґРµС‚Р°Р»Рё", "РІР»Р°РґРµР»СЊС†Сѓ РїСЂРѕС‰Рµ РѕР±СЂР°Р±РѕС‚Р°С‚СЊ РѕР±СЂР°С‰РµРЅРёРµ"],
        "steps": ["РїРѕСЃРµС‚РёС‚РµР»СЊ РІС‹Р±РёСЂР°РµС‚ СѓСЃР»СѓРіСѓ", "С„РѕСЂРјР° Р·Р°РґР°С‘С‚ СѓС‚РѕС‡РЅСЏСЋС‰РёРµ РІРѕРїСЂРѕСЃС‹", "СЃРѕР±РёСЂР°СЋС‚СЃСЏ РєРѕРЅС‚Р°РєС‚С‹", "РІР»Р°РґРµР»РµС† РїРѕР»СѓС‡Р°РµС‚ РїРѕРґСЂРѕР±РЅСѓСЋ Р·Р°СЏРІРєСѓ"],
        "adapt": ["РІРѕРїСЂРѕСЃС‹", "РІР°СЂРёР°РЅС‚С‹ РѕС‚РІРµС‚РѕРІ", "Р»РѕРіРёРєР° СЂР°СЃС‡С‘С‚Р°", "РЅРёС€Р°", "С„РѕСЂРјР° Р·Р°СЏРІРєРё", "С‚РµРєСЃС‚С‹", "РІРЅРµС€РЅРёР№ РІРёРґ"],
        "demo_links": [
            {"label": "Р—Р°РїСѓСЃС‚РёС‚СЊ РґРµРјРѕ СѓРјРЅРѕР№ С„РѕСЂРјС‹", "href": "/launch/smart-lead-form", "primary": True},
            {"label": "РџРѕРґСЂРѕР±РЅРµРµ Рѕ РґРµРјРѕ", "href": "/projects/smart-lead-form", "primary": False},
        ],
        "related": [
            {"label": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РґР»СЏ СЃР°Р№С‚Р°", "href": "/ai-chatbot-for-website"},
            {"label": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ РґР»СЏ Р°РіРµРЅС‚СЃС‚РІ", "href": "/automation-for-agencies"},
        ],
    },
    "wordpress-ai-integration": {
        "url": "/wordpress-ai-integration",
        "title": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ Рё СѓРјРЅС‹Рµ С„РѕСЂРјС‹ РґР»СЏ WordPress-СЃР°Р№С‚РѕРІ вЂ” AI Automation",
        "description": "Р’РЅРµС€РЅРёР№ AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ Рё СѓРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё РґР»СЏ WordPress-СЃР°Р№С‚РѕРІ РєР»РёРµРЅС‚РѕРІ. РњРѕР¶РЅРѕ РїРѕРґРєР»СЋС‡РёС‚СЊ РєР°Рє РѕС‚РґРµР»СЊРЅС‹Р№ РІРёРґР¶РµС‚ Р±РµР· РїРѕР»РЅРѕР№ РїРµСЂРµРґРµР»РєРё СЃР°Р№С‚Р°.",
        "eyebrow": "Р”Р»СЏ WordPress-РїСЂРѕРµРєС‚РѕРІ",
        "h1": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ Рё СѓРјРЅС‹Рµ С„РѕСЂРјС‹ РґР»СЏ WordPress-СЃР°Р№С‚РѕРІ",
        "hero": "Р•СЃР»Рё РІС‹ РґРµР»Р°РµС‚Рµ СЃР°Р№С‚С‹ РЅР° WordPress, РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ РєР»РёРµРЅС‚Сѓ РІРЅРµС€РЅРёР№ AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РёР»Рё СѓРјРЅСѓСЋ С„РѕСЂРјСѓ Р·Р°СЏРІРєРё Р±РµР· РїРѕР»РЅРѕР№ РїРµСЂРµРґРµР»РєРё СЃР°Р№С‚Р°.",
        "plain_title": "РљР°Рє СЌС‚Рѕ РїРѕРґРєР»СЋС‡Р°РµС‚СЃСЏ РїСЂРѕСЃС‚С‹РјРё СЃР»РѕРІР°РјРё",
        "plain": "Р РµС€РµРЅРёРµ СЂР°Р±РѕС‚Р°РµС‚ РєР°Рє РІРЅРµС€РЅРёР№ РјРѕРґСѓР»СЊ: РµРіРѕ РјРѕР¶РЅРѕ РІСЃС‚СЂРѕРёС‚СЊ РЅР° СЃР°Р№С‚ РєР»РёРµРЅС‚Р° С‡РµСЂРµР· РѕС‚РґРµР»СЊРЅС‹Р№ СЃРєСЂРёРїС‚ РёР»Рё РІРёРґР¶РµС‚. Р­С‚Рѕ СѓРґРѕР±РЅРѕ, РєРѕРіРґР° РЅРµ С…РѕС‡РµС‚СЃСЏ РїРѕР»РЅРѕСЃС‚СЊСЋ РїРµСЂРµРґРµР»С‹РІР°С‚СЊ СЃР°Р№С‚.",
        "audience": ["WordPress-СЂР°Р·СЂР°Р±РѕС‚С‡РёРєРё", "РґРёР·Р°Р№РЅРµСЂС‹ РЅР° РєРѕРЅСЃС‚СЂСѓРєС‚РѕСЂР°С…", "SEO-СЃРїРµС†РёР°Р»РёСЃС‚С‹", "РїРѕРґРґРµСЂР¶РєР° РєР»РёРµРЅС‚СЃРєРёС… СЃР°Р№С‚РѕРІ"],
        "partner_value": ["РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ РЅРѕРІСѓСЋ СѓСЃР»СѓРіСѓ Рє WordPress-СЃР°Р№С‚Сѓ", "РЅРµ РЅСѓР¶РЅРѕ РїРµСЂРµСЃС‚СЂР°РёРІР°С‚СЊ РІРµСЃСЊ РїСЂРѕРµРєС‚", "РјРѕР¶РЅРѕ РїРѕРєР°Р·Р°С‚СЊ РєР»РёРµРЅС‚Сѓ Р¶РёРІРѕРµ РґРµРјРѕ"],
        "client_value": ["СЃР°Р№С‚ РЅР°С‡РёРЅР°РµС‚ Р»СѓС‡С€Рµ СЃРѕР±РёСЂР°С‚СЊ РѕР±СЂР°С‰РµРЅРёСЏ", "РїРѕСЃРµС‚РёС‚РµР»Рё Р±С‹СЃС‚СЂРµРµ РїРѕР»СѓС‡Р°СЋС‚ РѕС‚РІРµС‚С‹", "РІР»Р°РґРµР»РµС† РїРѕР»СѓС‡Р°РµС‚ Р±РѕР»РµРµ РїРѕРЅСЏС‚РЅС‹Рµ Р·Р°СЏРІРєРё"],
        "steps": ["РІС‹Р±РёСЂР°РµРј СЃС†РµРЅР°СЂРёР№", "Р°РґР°РїС‚РёСЂСѓРµРј С‚РµРєСЃС‚С‹ Рё РІРѕРїСЂРѕСЃС‹", "РїРѕРґРєР»СЋС‡Р°РµРј РІРЅРµС€РЅРёР№ РјРѕРґСѓР»СЊ", "РїСЂРѕРІРµСЂСЏРµРј РїСѓС‚СЊ Р·Р°СЏРІРєРё"],
        "adapt": ["РІРёРґР¶РµС‚", "С‚РµРєСЃС‚С‹", "РІРѕРїСЂРѕСЃС‹", "РїРѕР»СЏ Р·Р°СЏРІРєРё", "С†РІРµС‚Р°", "СЃС†РµРЅР°СЂРёР№", "Р°РґРјРёРЅРєР°"],
        "demo_links": [
            {"label": "Р”РµРјРѕ AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚Р°", "href": "/launch/ai-site-consultant", "primary": True},
            {"label": "Р”РµРјРѕ СѓРјРЅРѕР№ С„РѕСЂРјС‹", "href": "/launch/smart-lead-form", "primary": False},
        ],
        "related": [
            {"label": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РґР»СЏ СЃР°Р№С‚Р°", "href": "/ai-chatbot-for-website"},
            {"label": "РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё", "href": "/smart-lead-form"},
        ],
    },
    "automation-for-agencies": {
        "url": "/automation-for-agencies",
        "title": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ Р·Р°СЏРІРѕРє РґР»СЏ Р°РіРµРЅС‚СЃС‚РІ Рё СЃРїРµС†РёР°Р»РёСЃС‚РѕРІ РїРѕ СЃР°Р№С‚Р°Рј вЂ” AI Automation",
        "description": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ Р·Р°СЏРІРѕРє РґР»СЏ РєР»РёРµРЅС‚РѕРІ Р°РіРµРЅС‚СЃС‚РІ, РґРёР·Р°Р№РЅРµСЂРѕРІ, SEO-СЃРїРµС†РёР°Р»РёСЃС‚РѕРІ Рё РјР°СЂРєРµС‚РѕР»РѕРіРѕРІ: AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚С‹, СѓРјРЅС‹Рµ С„РѕСЂРјС‹, Р°РґРјРёРЅРєРё Рё РѕР±СЂР°Р±РѕС‚РєР° РѕР±СЂР°С‰РµРЅРёР№.",
        "eyebrow": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ РґР»СЏ Р°РіРµРЅС‚СЃС‚РІ",
        "h1": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ Р·Р°СЏРІРѕРє РґР»СЏ Р°РіРµРЅС‚СЃС‚РІ Рё РєР»РёРµРЅС‚СЃРєРёС… СЃР°Р№С‚РѕРІ",
        "hero": "РџРѕРјРѕРіР°СЋ РґРѕР±Р°РІР»СЏС‚СЊ Рє РїСЂРѕРµРєС‚Р°Рј РєР»РёРµРЅС‚РѕРІ Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЋ: СЃР±РѕСЂ Р·Р°СЏРІРѕРє, РїРѕРЅСЏС‚РЅС‹Рµ С„РѕСЂРјС‹, AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚РѕРІ, Р°РґРјРёРЅРєРё Рё СѓРґРѕР±РЅСѓСЋ РѕР±СЂР°Р±РѕС‚РєСѓ РѕР±СЂР°С‰РµРЅРёР№.",
        "plain_title": "РљР°РєРёРµ РїСЂРѕР±Р»РµРјС‹ СЂРµС€Р°РµС‚ Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЏ",
        "plain": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ РїРѕРјРѕРіР°РµС‚ РЅРµ С‚РµСЂСЏС‚СЊ РѕР±СЂР°С‰РµРЅРёСЏ, Р·Р°СЂР°РЅРµРµ СЃРѕР±РёСЂР°С‚СЊ РІР°Р¶РЅС‹Рµ РґРµС‚Р°Р»Рё Рё РїРµСЂРµРґР°РІР°С‚СЊ РІР»Р°РґРµР»СЊС†Сѓ Р±РёР·РЅРµСЃР° Р·Р°СЏРІРєСѓ РІ СѓРґРѕР±РЅРѕРј РІРёРґРµ.",
        "audience": ["РЅРµР±РѕР»СЊС€РёРµ digital-Р°РіРµРЅС‚СЃС‚РІР°", "РјР°СЂРєРµС‚РѕР»РѕРіРё", "SEO-РєРѕРјР°РЅРґС‹", "С„СЂРёР»Р°РЅСЃРµСЂС‹ СЃ РєР»РёРµРЅС‚СЃРєРёРјРё РїСЂРѕРµРєС‚Р°РјРё"],
        "partner_value": ["РјРѕР¶РЅРѕ СЂР°СЃС€РёСЂРёС‚СЊ РїСЂРµРґР»РѕР¶РµРЅРёРµ Р±РµР· РЅР°Р№РјР° РѕС‚РґРµР»СЊРЅРѕР№ РєРѕРјР°РЅРґС‹", "РїСЂРѕС‰Рµ РїРѕРєР°Р·Р°С‚СЊ РєР»РёРµРЅС‚Сѓ СЂР°Р±РѕС‡РёР№ СЃС†РµРЅР°СЂРёР№", "РјРѕР¶РЅРѕ РЅР°С‡Р°С‚СЊ СЃ РѕРґРЅРѕРіРѕ РєР»РёРµРЅС‚Р°"],
        "client_value": ["Р·Р°СЏРІРєРё СЃС‚Р°РЅРѕРІСЏС‚СЃСЏ РїРѕРЅСЏС‚РЅРµРµ", "РјРµРЅСЊС€Рµ СЂСѓС‡РЅС‹С… СѓС‚РѕС‡РЅРµРЅРёР№", "РѕР±СЂР°С‰РµРЅРёСЏ СѓРґРѕР±РЅРµРµ РѕР±СЂР°Р±Р°С‚С‹РІР°С‚СЊ"],
        "steps": ["РѕРїРёСЃС‹РІР°РµРј РїСЂРѕР±Р»РµРјСѓ РєР»РёРµРЅС‚Р°", "РІС‹Р±РёСЂР°РµРј СЃС†РµРЅР°СЂРёР№ Р°РІС‚РѕРјР°С‚РёР·Р°С†РёРё", "РїРѕРєР°Р·С‹РІР°РµРј РґРµРјРѕ", "Р°РґР°РїС‚РёСЂСѓРµРј РїРѕРґ РЅРёС€Сѓ", "Р·Р°РїСѓСЃРєР°РµРј"],
        "adapt": ["СЃР±РѕСЂ Р·Р°СЏРІРѕРє", "С„РѕСЂРјС‹", "С‡Р°С‚", "Р°РґРјРёРЅРєР°", "РїРѕР»СЏ Р·Р°СЏРІРєРё", "Р»РѕРіРёРєР° РѕР±СЂР°Р±РѕС‚РєРё", "РїРµСЂРµРґР°С‡Р° РґР°РЅРЅС‹С…"],
        "demo_links": [
            {"label": "РџРѕСЃРјРѕС‚СЂРµС‚СЊ Р¶РёРІС‹Рµ РґРµРјРѕ", "href": "/projects", "primary": True},
            {"label": "РћР±СЃСѓРґРёС‚СЊ Р·Р°РґР°С‡Сѓ", "href": "/contact", "primary": False},
        ],
        "related": [
            {"label": "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ РґР»СЏ СЃР°Р№С‚Р°", "href": "/ai-chatbot-for-website"},
            {"label": "РЈРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё", "href": "/smart-lead-form"},
        ],
    },
    "website-development-for-partners": {
        "url": "/website-development-for-partners",
        "title": "Р Р°Р·СЂР°Р±РѕС‚РєР° СЃР°Р№С‚РѕРІ РґР»СЏ РґРёР·Р°Р№РЅРµСЂРѕРІ, РјР°СЂРєРµС‚РѕР»РѕРіРѕРІ Рё SEO вЂ” AI Automation",
        "description": "РўРµС…РЅРёС‡РµСЃРєР°СЏ СЂРµР°Р»РёР·Р°С†РёСЏ СЃР°Р№С‚РѕРІ РґР»СЏ РґРёР·Р°Р№РЅРµСЂРѕРІ, SEO-СЃРїРµС†РёР°Р»РёСЃС‚РѕРІ, РјР°СЂРєРµС‚РѕР»РѕРіРѕРІ Рё Р°РіРµРЅС‚СЃС‚РІ: СЃС‚СЂР°РЅРёС†С‹, С„РѕСЂРјС‹, backend-Р»РѕРіРёРєР°, Р·Р°СЏРІРєРё Рё РёРЅС‚РµРіСЂР°С†РёРё.",
        "eyebrow": "Р Р°Р·СЂР°Р±РѕС‚РєР° СЃР°Р№С‚РѕРІ РґР»СЏ РїР°СЂС‚РЅС‘СЂРѕРІ",
        "h1": "Р Р°Р·СЂР°Р±РѕС‚РєР° СЃР°Р№С‚РѕРІ РґР»СЏ РґРёР·Р°Р№РЅРµСЂРѕРІ, РјР°СЂРєРµС‚РѕР»РѕРіРѕРІ Рё SEO-СЃРїРµС†РёР°Р»РёСЃС‚РѕРІ",
        "hero": "Р•СЃР»Рё Сѓ РІР°СЃ РµСЃС‚СЊ РєР»РёРµРЅС‚, РґРёР·Р°Р№РЅ, РёРґРµСЏ РёР»Рё SEO-Р·Р°РґР°С‡Р°, СЏ РјРѕРіСѓ РїРѕРјРѕС‡СЊ СЃ С‚РµС…РЅРёС‡РµСЃРєРѕР№ СЂРµР°Р»РёР·Р°С†РёРµР№ СЃР°Р№С‚Р°, С„РѕСЂРјР°РјРё, Р·Р°СЏРІРєР°РјРё, backend-Р»РѕРіРёРєРѕР№ Рё РёРЅС‚РµРіСЂР°С†РёСЏРјРё.",
        "plain_title": "РљРѕРіРґР° РїР°СЂС‚РЅС‘СЂСѓ РЅСѓР¶РµРЅ С‚РµС…РЅРёС‡РµСЃРєРёР№ РёСЃРїРѕР»РЅРёС‚РµР»СЊ",
        "plain": "РљРѕРіРґР° РµСЃС‚СЊ РєР»РёРµРЅС‚СЃРєР°СЏ Р·Р°РґР°С‡Р°, РЅРѕ РЅРµ С…РѕС‡РµС‚СЃСЏ РёСЃРєР°С‚СЊ РѕС‚РґРµР»СЊРЅСѓСЋ backend-РєРѕРјР°РЅРґСѓ, РјРѕР¶РЅРѕ РїРѕРґРєР»СЋС‡РёС‚СЊ РјРµРЅСЏ РґР»СЏ СЂРµР°Р»РёР·Р°С†РёРё РєРѕРЅРєСЂРµС‚РЅРѕР№ С‚РµС…РЅРёС‡РµСЃРєРѕР№ С‡Р°СЃС‚Рё.",
        "audience": ["РІРµР±-РґРёР·Р°Р№РЅРµСЂС‹", "РјР°СЂРєРµС‚РѕР»РѕРіРё", "SEO-СЃРїРµС†РёР°Р»РёСЃС‚С‹", "РЅРµР±РѕР»СЊС€РёРµ Р°РіРµРЅС‚СЃС‚РІР°", "С„СЂРёР»Р°РЅСЃРµСЂС‹"],
        "partner_value": ["РјРѕР¶РЅРѕ РІРµСЃС‚Рё РєР»РёРµРЅС‚Р° СЃР°РјРѕРјСѓ", "С‚РµС…РЅРёС‡РµСЃРєСѓСЋ С‡Р°СЃС‚СЊ РјРѕР¶РЅРѕ РїРµСЂРµРґР°С‚СЊ РјРЅРµ", "РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ Рє СЃР°Р№С‚Сѓ AI, С„РѕСЂРјС‹ Рё Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЋ"],
        "client_value": ["РєР»РёРµРЅС‚ РїРѕР»СѓС‡Р°РµС‚ СЂР°Р±РѕС‡РёР№ СЃР°Р№С‚", "Р·Р°СЏРІРєРё СЃРѕР±РёСЂР°СЋС‚СЃСЏ РїРѕРЅСЏС‚РЅРµРµ", "РїСЂРѕРµРєС‚ РјРѕР¶РЅРѕ СЂР°Р·РІРёРІР°С‚СЊ РїРѕСЃР»Рµ Р·Р°РїСѓСЃРєР°"],
        "steps": ["РІС‹ РїСЂРёРЅРѕСЃРёС‚Рµ Р·Р°РґР°С‡Сѓ", "СЃРѕРіР»Р°СЃСѓРµРј СЃС‚СЂСѓРєС‚СѓСЂСѓ", "СЂРµР°Р»РёР·СѓСЋ С‚РµС…РЅРёС‡РµСЃРєСѓСЋ С‡Р°СЃС‚СЊ", "РїСЂРѕРІРµСЂСЏРµРј Р·Р°СЏРІРєРё", "Р·Р°РїСѓСЃРєР°РµРј"],
        "adapt": ["РІРµСЂСЃС‚РєР° СЃС‚СЂР°РЅРёС†", "С„РѕСЂРјС‹ Р·Р°СЏРІРѕРє", "backend-Р»РѕРіРёРєР°", "Р°РґРјРёРЅРєР°", "AI-РІРёРґР¶РµС‚", "СѓРјРЅР°СЏ С„РѕСЂРјР°", "Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЏ РѕР±СЂР°С‰РµРЅРёР№"],
        "demo_links": [
            {"label": "РџРѕСЃРјРѕС‚СЂРµС‚СЊ Р¶РёРІС‹Рµ РґРµРјРѕ", "href": "/projects", "primary": True},
            {"label": "Р”Р»СЏ РїР°СЂС‚РЅС‘СЂРѕРІ", "href": "/for-partners", "primary": False},
        ],
        "related": [
            {"label": "AI Рё С„РѕСЂРјС‹ РґР»СЏ WordPress", "href": "/wordpress-ai-integration"},
            {"label": "РђРІС‚РѕРјР°С‚РёР·Р°С†РёСЏ РґР»СЏ Р°РіРµРЅС‚СЃС‚РІ", "href": "/automation-for-agencies"},
        ],
    },
}

SOLUTION_FAQ = [
    ("РњРѕР¶РЅРѕ Р»Рё РїРѕРґРєР»СЋС‡РёС‚СЊ СЌС‚Рѕ Рє СѓР¶Рµ РіРѕС‚РѕРІРѕРјСѓ СЃР°Р№С‚Сѓ?", "Р”Р°, РІРѕ РјРЅРѕРіРёС… СЃР»СѓС‡Р°СЏС… СЂРµС€РµРЅРёРµ РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ РєР°Рє РІРЅРµС€РЅРёР№ РјРѕРґСѓР»СЊ, РІРёРґР¶РµС‚ РёР»Рё РѕС‚РґРµР»СЊРЅСѓСЋ С„РѕСЂРјСѓ Р±РµР· РїРѕР»РЅРѕР№ РїРµСЂРµРґРµР»РєРё СЃР°Р№С‚Р°."),
    ("РњРѕР¶РЅРѕ Р»Рё РїРѕРєР°Р·Р°С‚СЊ РєР»РёРµРЅС‚Сѓ РґРµРјРѕ РґРѕ РїСЂРѕРґР°Р¶Рё?", "Р”Р°. Р”Р»СЏ СЌС‚РѕРіРѕ РµСЃС‚СЊ Р¶РёРІС‹Рµ РґРµРјРѕ, РєРѕС‚РѕСЂС‹Рµ РїРѕРјРѕРіР°СЋС‚ Р±С‹СЃС‚СЂРѕ РѕР±СЉСЏСЃРЅРёС‚СЊ РёРґРµСЋ Рё РїРѕР»СЊР·Сѓ."),
    ("РњРѕР¶РЅРѕ Р»Рё Р°РґР°РїС‚РёСЂРѕРІР°С‚СЊ СЂРµС€РµРЅРёРµ РїРѕРґ РЅРёС€Сѓ РєР»РёРµРЅС‚Р°?", "Р”Р°. РњРµРЅСЏСЋС‚СЃСЏ С‚РµРєСЃС‚С‹, РІРѕРїСЂРѕСЃС‹, СѓСЃР»СѓРіРё, РїРѕР»СЏ Р·Р°СЏРІРєРё, РІРЅРµС€РЅРёР№ РІРёРґ Рё Р»РѕРіРёРєР° РѕР±СЂР°Р±РѕС‚РєРё."),
    ("Р’С‹ Р±СѓРґРµС‚Рµ РѕР±С‰Р°С‚СЊСЃСЏ СЃ РјРѕРёРј РєР»РёРµРЅС‚РѕРј РЅР°РїСЂСЏРјСѓСЋ?", "РќРµ РѕР±СЏР·Р°С‚РµР»СЊРЅРѕ. РњРѕР¶РЅРѕ СЂР°Р±РѕС‚Р°С‚СЊ С‡РµСЂРµР· РІР°СЃ, С‡С‚РѕР±С‹ РєР»РёРµРЅС‚ РѕСЃС‚Р°РІР°Р»СЃСЏ РІР°С€РёРј."),
    ("РњРѕР¶РЅРѕ Р»Рё РЅР°С‡Р°С‚СЊ СЃ РѕРґРЅРѕРіРѕ РїСЂРѕРµРєС‚Р°?", "Р”Р°. РћР±С‹С‡РЅРѕ СѓРґРѕР±РЅРѕ РЅР°С‡Р°С‚СЊ СЃ РѕРґРЅРѕРіРѕ РїРѕРЅСЏС‚РЅРѕРіРѕ СЃС†РµРЅР°СЂРёСЏ Рё РїСЂРѕРІРµСЂРёС‚СЊ С„РѕСЂРјР°С‚ СЃРѕС‚СЂСѓРґРЅРёС‡РµСЃС‚РІР°."),
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
                "РџР°СЂС‚РЅС‘СЂ РїРѕ AI Рё Р°РІС‚РѕРјР°С‚РёР·Р°С†РёРё РґР»СЏ РІРµР±-РґРёР·Р°Р№РЅРµСЂРѕРІ Рё Р°РіРµРЅС‚СЃС‚РІ",
                "РўРµС…РЅРёС‡РµСЃРєР°СЏ РїРѕРјРѕС‰СЊ РґР»СЏ РїР°СЂС‚РЅС‘СЂРѕРІ: AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚С‹, СѓРјРЅС‹Рµ С„РѕСЂРјС‹ Р·Р°СЏРІРѕРє, Р°РґРјРёРЅРєРё Рё Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЏ.",
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
                "Р РµС€РµРЅРёСЏ РґР»СЏ СЃР°Р№С‚РѕРІ РєР»РёРµРЅС‚РѕРІ",
                "AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚С‹, СѓРјРЅС‹Рµ С„РѕСЂРјС‹ Р·Р°СЏРІРѕРє, Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЏ Рё С‚РµС…РЅРёС‡РµСЃРєР°СЏ СЂРµР°Р»РёР·Р°С†РёСЏ СЃР°Р№С‚РѕРІ РґР»СЏ РїР°СЂС‚РЅС‘СЂРѕРІ.",
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
                "Р–РёРІС‹Рµ РґРµРјРѕ AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚РѕРІ Рё СѓРјРЅС‹С… С„РѕСЂРј Р·Р°СЏРІРѕРє",
                "Р–РёРІС‹Рµ РґРµРјРѕ СЂРµС€РµРЅРёР№ РґР»СЏ СЃР°Р№С‚РѕРІ РєР»РёРµРЅС‚РѕРІ: AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚, СѓРјРЅР°СЏ С„РѕСЂРјР° Р·Р°СЏРІРєРё Рё Р°РґРјРёРЅРєР°.",
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
                "РћР±СЃСѓРґРёС‚СЊ СЃР°Р№С‚ РёР»Рё Р°РІС‚РѕРјР°С‚РёР·Р°С†РёСЋ Р·Р°СЏРІРѕРє",
                "РљРѕРЅС‚Р°РєС‚РЅР°СЏ СЃС‚СЂР°РЅРёС†Р° AI Automation РґР»СЏ РѕР±СЃСѓР¶РґРµРЅРёСЏ СЃР°Р№С‚Р°, AI-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚Р°, СѓРјРЅРѕР№ С„РѕСЂРјС‹ РёР»Рё РїР°СЂС‚РЅС‘СЂСЃС‚РІР°.",
                "/contact",
            ),
        ),
    )

"""Analytics service functions shared by public APIs and admin metrics.

This module updates visitor/demo session timing and records every event in one
place, so routes do not duplicate tracking logic.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import AnalyticsEvent, DemoSession, VisitorSession


KNOWN_EVENTS = {
    "page_view",
    "project_view",
    "contact_open",
    "contact_page_view",
    "contact_form_start",
    "contact_submit",
    "contact_submit_success",
    "contact_submit_error",
    "demo_launch",
    "demo_share_link",
    "demo_tab_open",
    "admin_tab_open",
    "demo_finish",
    "heartbeat",
    "session_end",
    "cta_click",
    "project_demo_button_click",
    "contact_button_click",
    "partner_page_view",
}

BOT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Googlebot", r"googlebot|adsbot-google|mediapartners-google|apis-google"),
    ("Bingbot", r"bingbot|msnbot"),
    ("YandexBot", r"yandexbot|yandeximages|yandexaccessibilitybot"),
    ("DuckDuckBot", r"duckduckbot"),
    ("Baiduspider", r"baiduspider"),
    ("Facebook crawler", r"facebookexternalhit|facebot"),
    ("Twitter/X bot", r"twitterbot"),
    ("LinkedIn bot", r"linkedinbot"),
    ("TelegramBot", r"telegrambot"),
    ("WhatsApp preview", r"whatsapp"),
    ("AhrefsBot", r"ahrefsbot"),
    ("SemrushBot", r"semrushbot"),
    ("MJ12bot", r"mj12bot"),
    ("DotBot", r"dotbot"),
    ("PetalBot", r"petalbot"),
    ("Bytespider", r"bytespider"),
    ("GPTBot", r"gptbot|chatgpt-user|oai-searchbot"),
    ("Generic crawler", r"bot|crawler|spider|slurp|scrapy|httpclient|headless|lighthouse"),
)

BOT_REGEXES = tuple((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in BOT_PATTERNS)


def now_utc() -> datetime:
    """Use timezone-aware UTC timestamps consistently across analytics tables."""
    return datetime.now(UTC)


def hash_ip(ip: str | None) -> str | None:
    """Hash visitor IPs before storage so analytics do not keep raw addresses."""
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def detect_bot(user_agent: str | None) -> tuple[bool, str | None]:
    """Classify known crawlers and link-preview agents by User-Agent."""
    if not user_agent:
        return True, "Empty User-Agent"
    for name, pattern in BOT_REGEXES:
        if pattern.search(user_agent):
            return True, name
    return False, None


def bot_info_from_request(request: Request | None) -> tuple[bool, str | None]:
    """Return bot classification for the current HTTP request."""
    if not request:
        return False, None
    return detect_bot(request.headers.get("user-agent"))


def get_or_create_visitor_session(db: Session, session_id: str, request: Request | None = None) -> VisitorSession:
    """Return the existing visitor session or create it on the first event."""
    is_bot, bot_name = bot_info_from_request(request)
    visitor = db.query(VisitorSession).filter(VisitorSession.session_id == session_id).one_or_none()
    if visitor:
        if is_bot:
            visitor.is_bot = True
            visitor.bot_name = visitor.bot_name or bot_name
            visitor.traffic_type = "bot"
        return visitor

    visitor = VisitorSession(
        session_id=session_id,
        last_seen_at=now_utc(),
        ip_hash=hash_ip(request.client.host if request and request.client else None),
        user_agent=request.headers.get("user-agent") if request else None,
        is_bot=is_bot,
        bot_name=bot_name,
        traffic_type="bot" if is_bot else "human",
    )
    db.add(visitor)
    db.flush()
    return visitor


def record_event(
    db: Session,
    event_type: str,
    session_id: str | None = None,
    demo_session_id: str | None = None,
    project_id: str | None = None,
    page_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AnalyticsEvent:
    """Record one analytics event and update related session timing fields."""
    timestamp = now_utc()
    is_bot, bot_name = bot_info_from_request(request)
    if session_id:
        visitor = get_or_create_visitor_session(db, session_id, request)
        is_bot = visitor.is_bot
        bot_name = visitor.bot_name or bot_name
        visitor.last_seen_at = timestamp
        if visitor.started_at:
            visitor.duration_seconds = max(
                0,
                int((visitor.last_seen_at - visitor.started_at).total_seconds()),
            )
        if event_type == "session_end":
            visitor.ended_at = timestamp
            if visitor.started_at:
                visitor.duration_seconds = max(
                    0,
                    int((visitor.ended_at - visitor.started_at).total_seconds()),
                )

    if demo_session_id:
        demo = db.query(DemoSession).filter(DemoSession.demo_session_id == demo_session_id).one_or_none()
        if demo:
            demo.last_seen_at = timestamp
            if event_type == "demo_tab_open":
                demo.opened_demo = True
            if event_type == "admin_tab_open":
                demo.opened_admin = True

    event = AnalyticsEvent(
        session_id=session_id,
        demo_session_id=demo_session_id,
        event_type=event_type,
        project_id=project_id,
        page_url=page_url,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        is_bot=is_bot,
        bot_name=bot_name,
    )
    db.add(event)
    db.flush()
    return event


def finish_demo_session(db: Session, demo_session_id: str) -> DemoSession | None:
    """Mark a demo session as finished and calculate its duration."""
    demo = db.query(DemoSession).filter(DemoSession.demo_session_id == demo_session_id).one_or_none()
    if not demo:
        return None
    demo.ended_at = now_utc()
    demo.last_seen_at = demo.ended_at
    demo.status = "finished"
    if demo.started_at:
        demo.duration_seconds = int((demo.ended_at - demo.started_at).total_seconds())
    return demo

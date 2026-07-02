"""Analytics service functions shared by public APIs and admin metrics.

This module updates visitor/demo session timing and records every event in one
place, so routes do not duplicate tracking logic.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import AnalyticsEvent, DemoSession, VisitorSession


KNOWN_EVENTS = {
    "page_view",
    "project_view",
    "contact_open",
    "contact_submit",
    "demo_launch",
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


def now_utc() -> datetime:
    """Use timezone-aware UTC timestamps consistently across analytics tables."""
    return datetime.now(UTC)


def hash_ip(ip: str | None) -> str | None:
    """Hash visitor IPs before storage so analytics do not keep raw addresses."""
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def get_or_create_visitor_session(db: Session, session_id: str, request: Request | None = None) -> VisitorSession:
    """Return the existing visitor session or create it on the first event."""
    visitor = db.query(VisitorSession).filter(VisitorSession.session_id == session_id).one_or_none()
    if visitor:
        return visitor

    visitor = VisitorSession(
        session_id=session_id,
        last_seen_at=now_utc(),
        ip_hash=hash_ip(request.client.host if request and request.client else None),
        user_agent=request.headers.get("user-agent") if request else None,
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
    if session_id:
        visitor = get_or_create_visitor_session(db, session_id, request)
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

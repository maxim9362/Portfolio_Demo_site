# Validates lead data, prevents duplicate fresh submissions, and persists lead records.

import re
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.schemas.lead import LeadCreate
from app.services.email_service import notify_owner_about_new_lead
from app.services.phone_validator import normalize_israeli_phone


logger = logging.getLogger(__name__)
ALLOWED_LEAD_STATUSES = {"new", "in_progress", "done", "cancelled"}
CONTACT_TIME_PATTERN = re.compile(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)")
ISRAEL_TIMEZONE = timezone(timedelta(hours=3), name="Asia/Jerusalem")
LEAD_REPEAT_WINDOW = timedelta(days=1)


def get_contact_time_error(value: str | None, now: datetime | None = None) -> str | None:
    """Validate contact time text against office working hours."""
    if not value:
        return "Invalid contact time"

    match = CONTACT_TIME_PATTERN.search(value)
    if match is None:
        return "Invalid contact time"

    minutes = int(match.group(1)) * 60 + int(match.group(2))
    local_now = now or datetime.now(ISRAEL_TIMEZONE)
    target_date = local_now.date()

    normalized_value = value.lower()
    if "завтра" in normalized_value or "tomorrow" in normalized_value or "מחר" in normalized_value:
        target_date = target_date + timedelta(days=1)

    weekday = target_date.weekday()
    if weekday == 5:
        return "Office closed for shabbat"

    if weekday == 4:
        opens_at = 9 * 60
        closes_at = 13 * 60
    else:
        opens_at = 9 * 60
        closes_at = 18 * 60

    if minutes < opens_at or minutes > closes_at:
        return "Office closed for time"

    return None


def has_recent_lead(db: Session, client_id: str, normalized_phone: str) -> bool:
    """Check whether the same browser/user phone already created a fresh lead."""
    since = datetime.now(timezone.utc) - LEAD_REPEAT_WINDOW
    return (
        db.query(Lead)
        .filter(
            Lead.client_id == client_id,
            Lead.phone == normalized_phone,
            Lead.created_at >= since,
        )
        .first()
        is not None
    )


def create_lead(db: Session, lead_data: LeadCreate) -> Lead:
    """Create a lead after normalizing and validating its phone number."""
    normalized_phone = normalize_israeli_phone(lead_data.phone)

    if normalized_phone is None:
        raise ValueError("Invalid Israeli phone number")

    contact_time_error = get_contact_time_error(lead_data.preferred_contact_time)
    if contact_time_error:
        raise ValueError(contact_time_error)

    if has_recent_lead(db, lead_data.client_id, normalized_phone):
        raise ValueError("Recent lead already exists")

    lead = Lead(
        client_id=lead_data.client_id,
        scenario_key=lead_data.scenario_key,
        service_type=lead_data.service_type,
        language_pair=lead_data.language_pair,
        page_count=lead_data.page_count,
        urgency=lead_data.urgency,
        meeting_format=lead_data.meeting_format,
        city=lead_data.city,
        documents_ready=lead_data.documents_ready,
        name=lead_data.name,
        phone=normalized_phone,
        email=lead_data.email,
        preferred_contact_time=lead_data.preferred_contact_time,
        comment=lead_data.comment,
        estimated_price_min=lead_data.estimated_price_min,
        estimated_price_max=lead_data.estimated_price_max,
        currency=lead_data.currency,
        estimate_message=lead_data.estimate_message,
        disclaimer=lead_data.disclaimer,
        answers_json=lead_data.answers,
        status="new",
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    try:
        notify_owner_about_new_lead(lead)
    except Exception:
        logger.exception("Failed to send owner notification stub")

    return lead


def list_leads(
    db: Session,
    client_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Lead], int]:
    """List leads, optionally filtered by client_id, with total count."""
    query = db.query(Lead)

    if client_id:
        query = query.filter(Lead.client_id == client_id)

    total = query.count()
    items = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()

    return items, total


def get_lead(db: Session, lead_id: int) -> Lead | None:
    return db.query(Lead).filter(Lead.id == lead_id).first()


def update_lead(db: Session, lead_id: int, lead_data: LeadCreate) -> Lead:
    """Update an existing lead from the public widget edit flow."""
    lead = get_lead(db, lead_id)
    if lead is None:
        raise LookupError("Lead not found")

    normalized_phone = normalize_israeli_phone(lead_data.phone)
    if normalized_phone is None:
        raise ValueError("Invalid Israeli phone number")

    contact_time_error = get_contact_time_error(lead_data.preferred_contact_time)
    if contact_time_error:
        raise ValueError(contact_time_error)

    lead.client_id = lead_data.client_id
    lead.scenario_key = lead_data.scenario_key
    lead.service_type = lead_data.service_type
    lead.language_pair = lead_data.language_pair
    lead.page_count = lead_data.page_count
    lead.urgency = lead_data.urgency
    lead.meeting_format = lead_data.meeting_format
    lead.city = lead_data.city
    lead.documents_ready = lead_data.documents_ready
    lead.name = lead_data.name
    lead.phone = normalized_phone
    lead.email = lead_data.email
    lead.preferred_contact_time = lead_data.preferred_contact_time
    lead.comment = lead_data.comment
    lead.estimated_price_min = lead_data.estimated_price_min
    lead.estimated_price_max = lead_data.estimated_price_max
    lead.currency = lead_data.currency
    lead.estimate_message = lead_data.estimate_message
    lead.disclaimer = lead_data.disclaimer
    lead.answers_json = lead_data.answers
    lead.status = "new"

    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def update_lead_status(db: Session, lead_id: int, status: str) -> Lead:
    if status not in ALLOWED_LEAD_STATUSES:
        raise ValueError("Invalid lead status")

    lead = get_lead(db, lead_id)
    if lead is None:
        raise LookupError("Lead not found")

    lead.status = status
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead_id: int) -> None:
    lead = get_lead(db, lead_id)
    if lead is None:
        raise LookupError("Lead not found")

    db.delete(lead)
    db.commit()

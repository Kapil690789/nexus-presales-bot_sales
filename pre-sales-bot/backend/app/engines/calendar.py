from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.app.core.platform import get_platform
from backend.app.core.settings import get_settings
from backend.app.models.entities import TenantRow


def google_ready(tenant: TenantRow) -> bool:
    settings = get_settings()
    token = (tenant.google_refresh_token or settings.google_refresh_token).strip()
    return bool(settings.google_client_id.strip() and settings.google_client_secret.strip() and token)


def dummy_slots(now: datetime | None = None) -> list[dict]:
    origin = now or datetime.now(timezone.utc)
    slots: list[dict] = []
    day = origin + timedelta(days=1)
    while len(slots) < 3:
        if day.weekday() < 5:
            when = day.replace(hour=15, minute=0, second=0, microsecond=0)
            slots.append({"slot_iso": when.isoformat(), "label": when.strftime("%a %b %d, %H:%M UTC")})
        day += timedelta(days=1)
    return slots


def list_slots(tenant: TenantRow) -> tuple[list[dict], bool]:
    if google_ready(tenant):
        try:
            return _google_slots(tenant), True
        except Exception:
            return dummy_slots(), False
    return dummy_slots(), False


def confirm_slot(tenant: TenantRow, slot_iso: str, summary: str, attendee: str) -> dict:
    label = slot_iso
    for slot in dummy_slots():
        if slot["slot_iso"] == slot_iso:
            label = slot["label"]
    if google_ready(tenant):
        try:
            booked = _google_book(tenant, slot_iso, summary, attendee)
            booked["live"] = True
            return booked
        except Exception:
            pass
    return {"slot_iso": slot_iso, "label": label, "live": False, "meet_url": "", "html_link": ""}


def _credentials(tenant: TenantRow):
    from google.oauth2.credentials import Credentials

    settings = get_settings()
    return Credentials(
        token=None,
        refresh_token=(tenant.google_refresh_token or settings.google_refresh_token).strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id.strip(),
        client_secret=settings.google_client_secret.strip(),
        scopes=["https://www.googleapis.com/auth/calendar"],
    )


def _service(tenant: TenantRow):
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=_credentials(tenant), cache_discovery=False)


def _calendar_id(tenant: TenantRow) -> str:
    return (tenant.google_calendar_id or "primary").strip() or "primary"


def _google_slots(tenant: TenantRow) -> list[dict]:
    duration = get_platform().calendar.duration_minutes
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=10)
    body = {
        "timeMin": now.isoformat(),
        "timeMax": end.isoformat(),
        "items": [{"id": _calendar_id(tenant)}],
    }
    busy_raw = _service(tenant).freebusy().query(body=body).execute()
    busy = []
    for item in busy_raw.get("calendars", {}).get(_calendar_id(tenant), {}).get("busy", []):
        busy.append((item.get("start"), item.get("end")))
    slots = []
    cursor = now + timedelta(hours=2)
    while len(slots) < 3 and cursor < end:
        if cursor.weekday() < 5 and 14 <= cursor.hour <= 20:
            slot_end = cursor + timedelta(minutes=duration)
            iso = cursor.isoformat()
            clash = False
            for start, stop in busy:
                if start and stop and start < slot_end.isoformat() and stop > iso:
                    clash = True
                    break
            if not clash:
                slots.append({"slot_iso": iso, "label": cursor.strftime("%a %b %d, %H:%M UTC")})
        cursor += timedelta(hours=1)
    return slots or dummy_slots()


def _google_book(tenant: TenantRow, slot_iso: str, summary: str, attendee: str) -> dict:
    duration = get_platform().calendar.duration_minutes
    start = datetime.fromisoformat(slot_iso)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    end = start + timedelta(minutes=duration)
    event = {
        "summary": summary or "Discovery call",
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "attendees": [{"email": attendee}] if attendee else [],
        "conferenceData": {"createRequest": {"requestId": slot_iso.replace(":", "")[:40]}},
    }
    created = (
        _service(tenant)
        .events()
        .insert(calendarId=_calendar_id(tenant), body=event, conferenceDataVersion=1)
        .execute()
    )
    return {
        "slot_iso": slot_iso,
        "label": start.strftime("%a %b %d, %H:%M UTC"),
        "meet_url": created.get("hangoutLink") or "",
        "html_link": created.get("htmlLink") or "",
        "event_id": created.get("id") or "",
    }

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.app.core.platform import get_platform
from backend.app.core.settings import get_settings
from backend.app.models.entities import TenantRow


def google_ready(tenant: TenantRow) -> bool:
    settings = get_settings()
    token = (tenant.google_refresh_token or settings.google_refresh_token).strip()
    return bool(settings.google_client_id.strip() and settings.google_client_secret.strip() and token)


def _format_slot_label(dt: datetime, tz_name: str = "Asia/Kolkata") -> str:
    from zoneinfo import ZoneInfo
    try:
        tz = ZoneInfo(tz_name.strip() if tz_name else "Asia/Kolkata")
    except Exception:
        tz = timezone.utc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(tz)
    tz_str = local.strftime("%Z")
    if not tz_str or tz_str.startswith(("+", "-")):
        tz_str = tz_name
    return local.strftime(f"%a %b %d, %H:%M {tz_str}")


def dummy_slots(now: datetime | None = None, tz_name: str = "Asia/Kolkata") -> list[dict]:
    origin = now or datetime.now(timezone.utc)
    slots: list[dict] = []
    day = origin + timedelta(days=1)
    while len(slots) < 3:
        if day.weekday() < 5:
            when = day.replace(hour=15, minute=0, second=0, microsecond=0)
            slots.append({"slot_iso": when.isoformat(), "label": _format_slot_label(when, tz_name)})
        day += timedelta(days=1)
    return slots


def list_slots(tenant: TenantRow, tz_name: str = "Asia/Kolkata") -> tuple[list[dict], bool]:
    if google_ready(tenant):
        try:
            return _google_slots(tenant, tz_name=tz_name), True
        except Exception:
            return dummy_slots(tz_name=tz_name), False
    return dummy_slots(tz_name=tz_name), False


def confirm_slot(
    tenant: TenantRow,
    slot_iso: str,
    summary: str,
    attendee: str,
    event_id: str | None = None,
    tz_name: str = "Asia/Kolkata",
) -> dict:
    try:
        start_dt = datetime.fromisoformat(slot_iso)
        label = _format_slot_label(start_dt, tz_name)
    except Exception:
        label = slot_iso
    for slot in dummy_slots(tz_name=tz_name):
        if slot["slot_iso"] == slot_iso:
            label = slot["label"]
    if google_ready(tenant):
        try:
            booked = _google_book(tenant, slot_iso, summary, attendee, event_id=event_id, tz_name=tz_name)
            booked["live"] = True
            return booked
        except Exception:
            pass
    return {
        "slot_iso": slot_iso,
        "label": label,
        "live": False,
        "meet_url": "",
        "html_link": "",
        "event_id": event_id or "",
        "disclaimer": "Demo booking: no calendar invite is sent until Google Calendar is connected.",
        "note": "Demo booking: no calendar invite is sent until Google Calendar is connected.",
    }


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


def _google_slots(tenant: TenantRow, tz_name: str = "Asia/Kolkata") -> list[dict]:
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
                slots.append({"slot_iso": iso, "label": _format_slot_label(cursor, tz_name)})
        cursor += timedelta(hours=1)
    return slots or dummy_slots(tz_name=tz_name)


def _google_book(
    tenant: TenantRow,
    slot_iso: str,
    summary: str,
    attendee: str,
    event_id: str | None = None,
    tz_name: str = "Asia/Kolkata",
) -> dict:
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
    svc = _service(tenant)
    cal_id = _calendar_id(tenant)
    if event_id:
        res = (
            svc.events()
            .patch(calendarId=cal_id, eventId=event_id, body=event)
            .execute()
        )
    else:
        res = (
            svc.events()
            .insert(calendarId=cal_id, body=event, conferenceDataVersion=1)
            .execute()
        )
    return {
        "slot_iso": slot_iso,
        "label": _format_slot_label(start, tz_name),
        "meet_url": res.get("hangoutLink") or "",
        "html_link": res.get("htmlLink") or "",
        "event_id": res.get("id") or event_id or "",
    }

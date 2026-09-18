from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from backend.app.config_loader.loader import get_config
from backend.app.core.settings import get_settings
from backend.app.engines.google_client import CalendarError, get_google_api, is_live

WINDOWS = ("this_week", "next_week", "flex")


def _calendar_config():
    return get_config().calendar


def _tz() -> ZoneInfo:
    return ZoneInfo(_calendar_config().timezone)


def duration_minutes() -> int:
    return int(_calendar_config().duration_minutes)


def calendar_id() -> str:
    return (get_settings().google_calendar_id or _calendar_config().calendar_id or "primary").strip()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _next_weekday(start: datetime, weekday: int, hour: int, minute: int) -> datetime:
    days = (weekday - start.weekday()) % 7
    if days == 0 and (start.hour, start.minute) >= (hour, minute):
        days = 7
    return start.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days)


def _dummy_slots(window: str, now: datetime) -> list[dict]:
    origin = _aware(now)
    start = origin + timedelta(days=7 if window == "next_week" else 0)
    specs = [(1, 10, 30), (2, 15, 0), (3, 11, 0)]
    if window == "flex":
        start = origin + timedelta(days=10)
        specs = [(0, 14, 0), (2, 11, 30), (4, 16, 0)]
    slots = []
    for weekday, hour, minute in specs:
        when = _next_weekday(start, weekday, hour, minute)
        slots.append(_slot_payload(window, when))
    return slots


def _window_dates(window: str, now: datetime) -> tuple[datetime, datetime]:
    local = _aware(now).astimezone(_tz())
    today = local.date()
    week_start = today - timedelta(days=today.weekday())
    if window == "this_week":
        begin = datetime.combine(today, datetime.min.time(), tzinfo=_tz())
        end = datetime.combine(week_start + timedelta(days=7), datetime.min.time(), tzinfo=_tz())
    elif window == "next_week":
        begin = datetime.combine(week_start + timedelta(days=7), datetime.min.time(), tzinfo=_tz())
        end = begin + timedelta(days=7)
    else:
        begin = datetime.combine(week_start + timedelta(days=14), datetime.min.time(), tzinfo=_tz())
        end = begin + timedelta(days=7)
    return begin, end


def _candidate_starts(window: str, now: datetime) -> list[datetime]:
    config = _calendar_config()
    begin, end = _window_dates(window, now)
    local_now = _aware(now).astimezone(_tz())
    open_t = timedelta(hours=config.open_hour, minutes=config.open_minute)
    close_t = timedelta(hours=config.close_hour, minutes=config.close_minute)
    length = timedelta(minutes=config.duration_minutes)
    weekdays = set(config.weekdays)
    starts: list[datetime] = []
    day = begin.date()
    last = (end - timedelta(seconds=1)).date()
    while day <= last:
        if day.weekday() in weekdays:
            cursor = datetime.combine(day, datetime.min.time(), tzinfo=_tz()) + open_t
            close = datetime.combine(day, datetime.min.time(), tzinfo=_tz()) + close_t
            while cursor + length <= close:
                if cursor > local_now:
                    starts.append(cursor)
                cursor += length
        day += timedelta(days=1)
    return starts


def _overlaps(start: datetime, end: datetime, busy: list[tuple[datetime, datetime]]) -> bool:
    for busy_start, busy_end in busy:
        if start < _aware(busy_end) and end > _aware(busy_start):
            return True
    return False


def _slot_payload(window: str, when: datetime) -> dict:
    when = _aware(when)
    return {
        "window": window,
        "slot_iso": when.isoformat(),
        "label": when.astimezone(_tz()).strftime("%a %d %b, %H:%M"),
        "date": when.astimezone(_tz()).date().isoformat(),
    }


def slots_for(window: str = "this_week", *, now: datetime | None = None, db: Any = None) -> list[dict]:
    origin = now or datetime.now(timezone.utc)
    if not is_live(db):
        return _dummy_slots(window, origin)
    config = _calendar_config()
    length = timedelta(minutes=config.duration_minutes)
    starts = _candidate_starts(window, origin)
    if not starts:
        return []
    time_min = starts[0]
    time_max = starts[-1] + length
    try:
        busy = get_google_api().list_busy(calendar_id(), time_min, time_max)
    except Exception as exc:
        raise CalendarError("Could not read calendar availability. Try again in a moment.") from exc
    slots = []
    for start in starts:
        if not _overlaps(start, start + length, busy):
            slots.append(_slot_payload(window, start))
    return slots


def availability_payload(window: str = "this_week", *, now: datetime | None = None, db: Any = None) -> dict:
    config = _calendar_config()
    requested = window if window in WINDOWS else "this_week"
    order = (requested,) + tuple(item for item in WINDOWS if item != requested)
    error = ""
    chosen = requested
    slots: list[dict] = []
    for candidate in order:
        try:
            found = slots_for(candidate, now=now, db=db)
        except CalendarError as exc:
            error = str(exc)
            found = []
        if found:
            chosen = candidate
            slots = found
            error = ""
            break
    return {
        "live": is_live(db),
        "timezone": config.timezone,
        "duration_minutes": config.duration_minutes,
        "window": chosen,
        "slots": slots,
        "days": group_slots_by_day(slots),
        "error": error,
        "requested_window": requested,
    }


def group_slots_by_day(slots: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    labels: dict[str, str] = {}
    for item in slots:
        when = datetime.fromisoformat(item["slot_iso"])
        local = _aware(when).astimezone(_tz())
        key = local.date().isoformat()
        grouped[key].append({"slot_iso": item["slot_iso"], "label": local.strftime("%H:%M")})
        labels[key] = local.strftime("%a %d %b")
    return [{"date": date, "label": labels[date], "slots": grouped[date]} for date in grouped]


def booking_card(window: str = "this_week", booking: dict | None = None, *, db: Any = None) -> dict:
    config = _calendar_config()
    if booking and booking.get("slot_iso"):
        return {
            "type": "booking_confirm",
            "title": "You're booked",
            "slot_iso": booking["slot_iso"],
            "label": booking.get("label") or "",
            "meet_url": booking.get("meet_url") or "",
            "html_link": booking.get("html_link") or "",
            "duration_minutes": config.duration_minutes,
        }
    try:
        payload = availability_payload(window, db=db)
    except CalendarError as exc:
        payload = {
            "live": is_live(db),
            "timezone": config.timezone,
            "duration_minutes": config.duration_minutes,
            "window": window,
            "days": [],
            "slots": [],
            "error": str(exc),
        }
    error = payload.get("error") or (booking or {}).get("error") or ""
    return {
        "type": "booking",
        "title": "Book a call",
        "live": payload["live"],
        "timezone": payload["timezone"],
        "duration_minutes": payload["duration_minutes"],
        "window": payload.get("window") or window,
        "days": payload["days"],
        "slots": payload["slots"],
        "error": error,
    }


def window_chips(window: str = "this_week") -> list[dict]:
    options = [("This week", "this_week"), ("Next week", "next_week"), ("Flexible", "flex")]
    return [{"label": label, "field": "booking_window", "value": value} for label, value in options if value != window]


def slot_chips(window: str = "this_week", *, db: Any = None) -> list[dict]:
    return window_chips(window)


def confirm_slot(
    session_id: str,
    window: str,
    slot_iso: str | None = None,
    *,
    email: str | None = None,
    db: Any = None,
    now: datetime | None = None,
) -> dict:
    if not slot_iso:
        raise CalendarError("Pick a time to book.")
    options = slots_for(window, now=now, db=db)
    chosen = next((item for item in options if item["slot_iso"] == slot_iso), None)
    if not chosen:
        raise CalendarError("That time is no longer available. Pick another slot.")
    start = datetime.fromisoformat(chosen["slot_iso"])
    end = start + timedelta(minutes=duration_minutes())
    if not is_live(db):
        short = (session_id or "session").replace("-", "")[:8]
        return {
            "window": window,
            "slot_iso": chosen["slot_iso"],
            "label": chosen["label"],
            "meet_url": f"https://meet.devconsult.example/{short}",
            "html_link": "",
            "event_id": "",
            "status": "queued_stub",
            "duration_minutes": duration_minutes(),
        }
    config = _calendar_config()
    try:
        created = get_google_api().create_event(
            calendar_id(),
            start,
            end,
            config.title,
            f"Discovery call booked via the pre-sales consultant. Session {session_id}",
            email,
            config.timezone,
        )
    except CalendarError:
        raise
    except Exception as exc:
        raise CalendarError("Could not create the calendar event. Pick another time.") from exc
    meet = created.get("meet_url") or ""
    return {
        "window": window,
        "slot_iso": chosen["slot_iso"],
        "label": chosen["label"],
        "meet_url": meet,
        "html_link": created.get("html_link") or "",
        "event_id": created.get("event_id") or "",
        "status": "created",
        "duration_minutes": duration_minutes(),
    }


def ics_for(booking: dict, summary: str | None = None) -> str:
    config = _calendar_config()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    start = datetime.fromisoformat(booking["slot_iso"]).astimezone(timezone.utc)
    minutes = int(booking.get("duration_minutes") or config.duration_minutes)
    end = start + timedelta(minutes=minutes)
    title = summary or config.title

    def fmt(value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%SZ")

    url = booking.get("meet_url") or ""
    uid = booking.get("event_id") or booking.get("meet_url") or stamp
    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//DevConsult//Presales//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}@devconsult.example",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{fmt(start)}",
            f"DTEND:{fmt(end)}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:Join: {url}",
            f"URL:{url}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )

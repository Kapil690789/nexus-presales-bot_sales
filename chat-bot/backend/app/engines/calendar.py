from __future__ import annotations

from datetime import datetime, timedelta, timezone

WINDOWS = ("this_week", "next_week", "flex")


def _next_weekday(start: datetime, weekday: int, hour: int, minute: int) -> datetime:
    days = (weekday - start.weekday()) % 7
    if days == 0 and (start.hour, start.minute) >= (hour, minute):
        days = 7
    slot = start.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days)
    return slot


def slots_for(window: str = "this_week", *, now: datetime | None = None) -> list[dict]:
    origin = now or datetime.now(timezone.utc)
    if origin.tzinfo is None:
        origin = origin.replace(tzinfo=timezone.utc)
    start = origin + timedelta(days=7 if window == "next_week" else 0)
    specs = [(1, 10, 30), (2, 15, 0), (3, 11, 0)]
    if window == "flex":
        start = origin + timedelta(days=10)
        specs = [(0, 14, 0), (2, 11, 30), (4, 16, 0)]
    slots = []
    for weekday, hour, minute in specs:
        when = _next_weekday(start, weekday, hour, minute)
        slots.append(
            {
                "window": window,
                "slot_iso": when.isoformat(),
                "label": when.strftime("%a %d %b, %H:%M UTC"),
            }
        )
    return slots


def confirm_slot(session_id: str, window: str, slot_iso: str | None = None) -> dict:
    options = slots_for(window)
    chosen = next((item for item in options if slot_iso and item["slot_iso"] == slot_iso), None) or options[0]
    short = (session_id or "session").replace("-", "")[:8]
    return {
        "window": window,
        "slot_iso": chosen["slot_iso"],
        "label": chosen["label"],
        "meet_url": f"https://meet.devconsult.example/{short}",
        "status": "queued_stub",
    }


def slot_chips(window: str = "this_week") -> list[dict]:
    chips = []
    for item in slots_for(window):
        chips.append(
            {
                "label": item["label"],
                "field": "booking_slot",
                "value": item["slot_iso"],
                "also": {"window": window},
            }
        )
    chips.append({"label": "Next week", "field": "booking_window", "value": "next_week"})
    chips.append({"label": "Flexible", "field": "booking_window", "value": "flex"})
    return chips


def ics_for(booking: dict, summary: str = "DevConsult consultation") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    start = datetime.fromisoformat(booking["slot_iso"]).astimezone(timezone.utc)
    end = start + timedelta(minutes=45)
    def fmt(value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%SZ")
    url = booking.get("meet_url") or ""
    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//DevConsult//Presales//EN",
            "BEGIN:VEVENT",
            f"UID:{booking.get('meet_url', stamp)}@devconsult.example",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{fmt(start)}",
            f"DTEND:{fmt(end)}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:Dummy consultation link: {url}",
            f"URL:{url}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )

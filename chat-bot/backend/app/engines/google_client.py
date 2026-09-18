from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.models.entities import CalendarCredentialRow

logger = logging.getLogger("presales.google")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
]

CREDENTIAL_ID = "default"


class CalendarError(Exception):
    """Visitor-facing booking failure."""


class GoogleCalendarAPI(Protocol):
    def list_busy(
        self, calendar_id: str, time_min: datetime, time_max: datetime
    ) -> list[tuple[datetime, datetime]]:
        ...

    def create_event(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        summary: str,
        description: str,
        email: str | None,
        timezone_name: str,
    ) -> dict[str, str]:
        ...


_override_api: GoogleCalendarAPI | None = None


def set_google_client(client: GoogleCalendarAPI | None) -> None:
    global _override_api
    _override_api = client


def google_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_client_id.strip() and settings.google_client_secret.strip())


def credential_row(db: Session) -> CalendarCredentialRow:
    row = db.get(CalendarCredentialRow, CREDENTIAL_ID)
    if row is None:
        row = CalendarCredentialRow(id=CREDENTIAL_ID)
        db.add(row)
        db.flush()
    return row


def stored_refresh_token(db: Session | None = None) -> str:
    settings = get_settings()
    if settings.google_refresh_token.strip():
        return settings.google_refresh_token.strip()
    close = False
    if db is None:
        from backend.app.models.db import SessionLocal

        db = SessionLocal()
        close = True
    try:
        row = db.get(CalendarCredentialRow, CREDENTIAL_ID)
        return (row.refresh_token if row else "") or ""
    finally:
        if close:
            db.close()


def is_live(db: Session | None = None) -> bool:
    if _override_api is not None:
        return True
    return bool(stored_refresh_token(db))


def connection_status(db: Session) -> dict[str, Any]:
    settings = get_settings()
    row = db.get(CalendarCredentialRow, CREDENTIAL_ID)
    env_token = bool(settings.google_refresh_token.strip())
    connected = bool((row and row.refresh_token) or env_token)
    email = (row.email if row else "") or ""
    return {
        "configured": google_configured(),
        "connected": connected,
        "via_env": env_token,
        "email": email,
        "redirect_uri": settings.google_redirect_uri,
        "calendar_id": settings.google_calendar_id or "primary",
        "connected_at": row.connected_at.isoformat() if row and row.connected_at else None,
    }


def _flow(code_verifier: str | None = None):
    settings = get_settings()
    if not google_configured():
        raise CalendarError("Google Calendar is not configured. Add the client id and secret to .env.")
    from google_auth_oauthlib.flow import Flow

    kwargs: dict[str, Any] = {
        "scopes": SCOPES,
        "redirect_uri": settings.google_redirect_uri,
    }
    if code_verifier:
        kwargs["code_verifier"] = code_verifier
        kwargs["autogenerate_code_verifier"] = False

    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id.strip(),
                "client_secret": settings.google_client_secret.strip(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        **kwargs,
    )


def authorization_url(db: Session) -> str:
    flow = _flow()
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    row = credential_row(db)
    row.oauth_state = state
    row.oauth_code_verifier = flow.code_verifier or ""
    db.flush()
    return url


def exchange_code(code: str, code_verifier: str = "") -> dict[str, Any]:
    """Exchange an OAuth code for tokens. Mock this in tests."""
    flow = _flow(code_verifier=code_verifier or None)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        logger.exception("Google token exchange failed")
        raise CalendarError("Google sign-in failed. Click Connect and try again.") from exc
    creds = flow.credentials
    email = _email_from_credentials(creds)
    expiry = creds.expiry
    return {
        "refresh_token": creds.refresh_token or "",
        "access_token": creds.token or "",
        "email": email,
        "expiry": expiry,
        "scopes": " ".join(creds.scopes or SCOPES),
        "token_uri": creds.token_uri or "https://oauth2.googleapis.com/token",
    }


def _email_from_credentials(creds: Any) -> str:
    token = getattr(creds, "id_token", None)
    if token:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import id_token as google_id_token

            info = google_id_token.verify_oauth2_token(token, Request(), get_settings().google_client_id.strip())
            return str(info.get("email") or "")
        except Exception:
            logger.exception("Could not read Google account email from id_token")
    return ""


def complete_oauth(db: Session, code: str, state: str) -> None:
    row = credential_row(db)
    if not state or state != (row.oauth_state or ""):
        raise CalendarError("Google sign-in expired. Connect again from /admin/calendar.")
    tokens = exchange_code(code, row.oauth_code_verifier or "")
    if not tokens.get("refresh_token") and not row.refresh_token:
        raise CalendarError("Google did not return a refresh token. Disconnect, then connect again and grant access.")
    if tokens.get("refresh_token"):
        row.refresh_token = tokens["refresh_token"]
    row.access_token = tokens.get("access_token") or row.access_token
    row.email = tokens.get("email") or row.email
    row.expiry = tokens.get("expiry")
    row.scopes = tokens.get("scopes") or " ".join(SCOPES)
    row.token_uri = tokens.get("token_uri") or row.token_uri
    row.oauth_state = ""
    row.oauth_code_verifier = ""
    row.connected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()


def disconnect_google(db: Session) -> None:
    row = db.get(CalendarCredentialRow, CREDENTIAL_ID)
    if row:
        db.delete(row)
        db.flush()


def _credentials(db: Session | None = None):
    settings = get_settings()
    refresh = stored_refresh_token(db)
    if not refresh:
        raise CalendarError("Google Calendar is not connected.")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    access = ""
    token_uri = "https://oauth2.googleapis.com/token"
    expiry = None
    close = False
    if db is None:
        from backend.app.models.db import SessionLocal

        db = SessionLocal()
        close = True
    try:
        row = db.get(CalendarCredentialRow, CREDENTIAL_ID) if not settings.google_refresh_token.strip() else None
        if row:
            access = row.access_token or ""
            token_uri = row.token_uri or token_uri
            expiry = row.expiry
        creds = Credentials(
            token=access or None,
            refresh_token=refresh,
            token_uri=token_uri,
            client_id=settings.google_client_id.strip(),
            client_secret=settings.google_client_secret.strip(),
            scopes=SCOPES,
            expiry=expiry,
        )
        if not creds.valid:
            creds.refresh(Request())
            if row:
                row.access_token = creds.token or ""
                row.expiry = creds.expiry
                db.flush()
                if close:
                    db.commit()
        return creds
    finally:
        if close:
            db.close()


class LiveGoogleCalendarAPI:
    def _service(self, db: Session | None = None):
        from googleapiclient.discovery import build

        return build("calendar", "v3", credentials=_credentials(db), cache_discovery=False)

    def list_busy(
        self, calendar_id: str, time_min: datetime, time_max: datetime
    ) -> list[tuple[datetime, datetime]]:
        service = self._service()
        payload = (
            service.freebusy()
            .query(
                body={
                    "timeMin": _rfc3339(time_min),
                    "timeMax": _rfc3339(time_max),
                    "items": [{"id": calendar_id}],
                }
            )
            .execute()
        )
        busy = payload.get("calendars", {}).get(calendar_id, {}).get("busy") or []
        return [(_parse_google_dt(item["start"]), _parse_google_dt(item["end"])) for item in busy]

    def create_event(
        self,
        calendar_id: str,
        start: datetime,
        end: datetime,
        summary: str,
        description: str,
        email: str | None,
        timezone_name: str,
    ) -> dict[str, str]:
        service = self._service()
        body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": timezone_name},
            "end": {"dateTime": end.isoformat(), "timeZone": timezone_name},
            "conferenceData": {
                "createRequest": {
                    "requestId": f"presales-{int(start.timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }
        if email:
            body["attendees"] = [{"email": email}]
        event = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=body,
                conferenceDataVersion=1,
                sendUpdates="all" if email else "none",
            )
            .execute()
        )
        meet = _meet_url(event)
        return {
            "event_id": str(event.get("id") or ""),
            "meet_url": meet,
            "html_link": str(event.get("htmlLink") or ""),
        }


def get_google_api() -> GoogleCalendarAPI:
    if _override_api is not None:
        return _override_api
    return LiveGoogleCalendarAPI()


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_google_dt(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _meet_url(event: dict[str, Any]) -> str:
    hangout = str(event.get("hangoutLink") or "")
    if hangout:
        return hangout
    for entry in (event.get("conferenceData") or {}).get("entryPoints") or []:
        if entry.get("entryPointType") == "video" and entry.get("uri"):
            return str(entry["uri"])
    return ""

from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.reservation import Reservation
from app.models.user import User

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def google_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def build_auth_url(state: str) -> str:
    if not google_configured():
        raise RuntimeError("Google OAuth が設定されていません")
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=state)
    flow.redirect_uri = settings.google_redirect_uri
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url


def exchange_code(code: str) -> Credentials:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    flow.fetch_token(code=code)
    return flow.credentials


def _credentials_from_user(user: User) -> Credentials | None:
    if not user.google_refresh_token or not google_configured():
        return None
    return Credentials(
        token=None,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )


def create_calendar_event(user: User, reservation: Reservation) -> str | None:
    creds = _credentials_from_user(user)
    if not creds:
        return None

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    slot = reservation.time_slot
    studio = reservation.studio
    body = {
        "summary": f"スタジオ予約: {studio.name}",
        "description": reservation.note or "撮影スタジオサブスク予約",
        "start": {"dateTime": slot.start_at.astimezone(timezone.utc).isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": slot.end_at.astimezone(timezone.utc).isoformat(), "timeZone": "UTC"},
    }
    event = service.events().insert(calendarId="primary", body=body).execute()
    return event.get("id")


def delete_calendar_event(user: User, event_id: str | None) -> None:
    if not event_id:
        return
    creds = _credentials_from_user(user)
    if not creds:
        return
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except Exception:
        # 既に削除済みなどでもキャンセル処理は継続
        pass


def connect_user(db: Session, user: User, credentials: Credentials) -> User:
    if credentials.refresh_token:
        user.google_refresh_token = credentials.refresh_token
    user.google_calendar_connected = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def disconnect_user(db: Session, user: User) -> User:
    user.google_refresh_token = None
    user.google_calendar_connected = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def demo_sync_note(reservation: Reservation) -> str:
    """Google 未設定時の開発用メッセージ。"""
    return (
        f"[demo] Google Calendar sync skipped for reservation #{reservation.id} "
        f"at {datetime.now(timezone.utc).isoformat()}"
    )


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def can_cancel(start_at: datetime, is_admin: bool, hours_before: int) -> bool:
    if is_admin:
        return True
    deadline = ensure_aware(start_at) - timedelta(hours=hours_before)
    return datetime.now(timezone.utc) <= deadline

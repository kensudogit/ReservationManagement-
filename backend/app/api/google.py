from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import GoogleAuthUrl, MessageOut
from app.services import google_calendar as gcal

router = APIRouter(prefix="/google", tags=["google"])


@router.get("/auth-url", response_model=GoogleAuthUrl)
def auth_url(current_user: User = Depends(get_current_user)) -> GoogleAuthUrl:
    if not gcal.google_configured():
        return GoogleAuthUrl(url="", configured=False)
    url = gcal.build_auth_url(state=str(current_user.id))
    return GoogleAuthUrl(url=url, configured=True)


@router.get("/callback")
def callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    if not gcal.google_configured():
        raise HTTPException(status_code=400, detail="Google OAuth が未設定です")
    try:
        user_id = int(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="不正な state") from exc

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    credentials = gcal.exchange_code(code)
    gcal.connect_user(db, user, credentials)

    qs = urlencode({"google": "connected"})
    return RedirectResponse(f"{settings.frontend_url}/settings?{qs}")


@router.delete("/disconnect", response_model=MessageOut)
def disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    gcal.disconnect_user(db, current_user)
    return MessageOut(message="Google カレンダー連携を解除しました")

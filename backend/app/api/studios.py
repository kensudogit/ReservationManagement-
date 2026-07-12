from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.studio import Studio
from app.models.user import User
from app.schemas import StudioCreate, StudioOut, TimeSlotOut
from app.services import reservations as reservation_service

router = APIRouter(tags=["studios"])


@router.get("/studios", response_model=list[StudioOut])
def list_studios(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Studio]:
    return list(db.scalars(select(Studio).where(Studio.is_active.is_(True)).order_by(Studio.id)).all())


@router.post("/studios", response_model=StudioOut, status_code=201)
def create_studio(
    payload: StudioCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Studio:
    studio = Studio(name=payload.name, description=payload.description, capacity=payload.capacity)
    db.add(studio)
    db.commit()
    db.refresh(studio)
    return studio


@router.get("/slots", response_model=list[TimeSlotOut])
def list_slots(
    studio_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    return reservation_service.search_available_slots(
        db, studio_id=studio_id, date_from=date_from, date_to=date_to
    )

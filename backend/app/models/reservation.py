from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReservationStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    studio_id: Mapped[int] = mapped_column(ForeignKey("studios.id"), index=True)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default=ReservationStatus.CONFIRMED.value, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reservations")
    studio = relationship("Studio", back_populates="reservations")
    time_slot = relationship("TimeSlot", back_populates="reservation")

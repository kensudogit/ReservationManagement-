"""初期データ投入。プランは毎回同期、ユーザー等は既存ならスキップ。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models import Studio, Subscription, TimeSlot, User, UserRole
from app.services import subscriptions as sub_service


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        plans = sub_service.ensure_plans(db)
        standard = next((p for p in plans if p.code == "standard"), plans[0] if plans else None)
        premium = next((p for p in plans if p.code == "premium"), standard)

        # 既存サブスクに plan_id が無ければ紐付け
        if standard:
            orphans = db.scalars(select(Subscription).where(Subscription.plan_id.is_(None))).all()
            for sub in orphans:
                matched = next((p for p in plans if p.name == sub.plan_name), standard)
                sub.plan_id = matched.id
                sub.plan_name = matched.name
                sub.monthly_quota = matched.monthly_quota
                if not getattr(sub, "status", None):
                    sub.status = "active"
                db.add(sub)
            db.commit()

        existing = db.scalars(select(User).limit(1)).first()
        if existing:
            print("Seed skipped (users exist): plans synced")
            return

        admin = User(
            email="admin@studio.local",
            hashed_password=hash_password("admin1234"),
            full_name="Studio Admin",
            role=UserRole.ADMIN.value,
        )
        member = User(
            email="member@studio.local",
            hashed_password=hash_password("member1234"),
            full_name="Demo Member",
            role=UserRole.MEMBER.value,
        )
        db.add_all([admin, member])
        db.flush()

        now = datetime.now(timezone.utc)
        plan = premium or standard
        db.add(
            Subscription(
                user_id=member.id,
                plan_id=plan.id if plan else None,
                plan_name=plan.name if plan else "Standard",
                monthly_quota=plan.monthly_quota if plan else 8,
                used_count=0,
                period_start=now,
                period_end=now + timedelta(days=30),
                status="active",
                auto_renew=True,
                is_active=True,
            )
        )

        studios = [
            Studio(name="Studio A — 白ホリ", description="白ホリゾント。ポートレート向け。", capacity=1),
            Studio(name="Studio B — 黒背景", description="黒背景・機材充実。", capacity=1),
            Studio(name="Studio C — 自然光", description="大きな窓のある自然光スタジオ。", capacity=2),
        ]
        db.add_all(studios)
        db.flush()

        slots: list[TimeSlot] = []
        for studio in studios:
            for day in range(1, 15):
                day_base = (now + timedelta(days=day)).replace(hour=0, minute=0, second=0, microsecond=0)
                slots.append(
                    TimeSlot(
                        studio_id=studio.id,
                        start_at=day_base.replace(hour=10),
                        end_at=day_base.replace(hour=13),
                        is_available=True,
                    )
                )
                slots.append(
                    TimeSlot(
                        studio_id=studio.id,
                        start_at=day_base.replace(hour=14),
                        end_at=day_base.replace(hour=17),
                        is_available=True,
                    )
                )
        db.add_all(slots)
        db.commit()
        print("Seed completed: plans / admin / member / studios / slots")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

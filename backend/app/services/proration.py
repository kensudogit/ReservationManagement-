from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from app.models.studio import Plan, Subscription
from app.services.subscriptions import PERIOD_DAYS, ensure_aware, now_utc


@dataclass
class ProrationPreview:
    from_plan_code: str
    from_plan_name: str
    to_plan_code: str
    to_plan_name: str
    old_price_yen: int
    new_price_yen: int
    period_start: datetime
    period_end: datetime
    remaining_days: int
    total_days: int
    unused_credit_yen: int
    new_charge_yen: int
    proration_yen: int
    tax_yen: int
    total_due_yen: int
    direction: str  # upgrade|downgrade|same
    explanation: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["period_start"] = self.period_start.isoformat()
        data["period_end"] = self.period_end.isoformat()
        return data


def calculate_proration(
    subscription: Subscription,
    new_plan: Plan,
    *,
    tax_rate: float = 0.10,
    at: datetime | None = None,
) -> ProrationPreview:
    now = at or now_utc()
    start = ensure_aware(subscription.period_start)
    end = ensure_aware(subscription.period_end)
    total_seconds = max((end - start).total_seconds(), 1)
    remaining_seconds = max((end - now).total_seconds(), 0)
    total_days = max(int(round(total_seconds / 86400)), 1)
    remaining_days = max(int(round(remaining_seconds / 86400)), 0)
    if remaining_days == 0 and remaining_seconds > 0:
        remaining_days = 1

    old_price = subscription.plan.price_yen if subscription.plan else subscription.monthly_quota and 0
    # prefer denormalized path
    old_price = subscription.plan.price_yen if subscription.plan else 0
    new_price = new_plan.price_yen

    ratio = remaining_seconds / total_seconds
    unused_credit = int(round(old_price * ratio))
    new_charge = int(round(new_price * ratio))
    proration = new_charge - unused_credit

    if new_price > old_price:
        direction = "upgrade"
    elif new_price < old_price:
        direction = "downgrade"
    else:
        direction = "same"

    tax = int(round(max(proration, 0) * tax_rate))
    total_due = proration + tax if proration > 0 else proration

    if direction == "upgrade":
        explanation = (
            f"残期間 {remaining_days}/{total_days} 日分の差額を日割り請求します。"
            f"（新プラン日割り ¥{new_charge:,} − 旧プラン未使用クレジット ¥{unused_credit:,}）"
        )
    elif direction == "downgrade":
        explanation = (
            f"残期間 {remaining_days}/{total_days} 日分の差額をクレジットします。"
            f"（差額 ¥{abs(proration):,} は次回請求に充当、または即時返金扱い）"
        )
    else:
        explanation = "同額プランのため日割り差額はありません。"

    return ProrationPreview(
        from_plan_code=subscription.plan.code if subscription.plan else "",
        from_plan_name=subscription.plan_name,
        to_plan_code=new_plan.code,
        to_plan_name=new_plan.name,
        old_price_yen=old_price,
        new_price_yen=new_price,
        period_start=start,
        period_end=end,
        remaining_days=remaining_days,
        total_days=total_days or PERIOD_DAYS,
        unused_credit_yen=unused_credit,
        new_charge_yen=new_charge,
        proration_yen=proration,
        tax_yen=tax if proration > 0 else 0,
        total_due_yen=total_due,
        direction=direction,
        explanation=explanation,
    )

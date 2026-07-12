from __future__ import annotations

import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import EmailNotification
from app.models.user import User


def send_email(
    db: Session,
    *,
    to_email: str,
    subject: str,
    body: str,
    template_key: str,
    user: User | None = None,
) -> EmailNotification:
    status = "sent"
    error: str | None = None

    if settings.smtp_enabled:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.smtp_from
            msg["To"] = to_email
            msg.set_content(body)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = str(exc)
    else:
        # デモ: コンソールに出力
        print(f"[email:{template_key}] to={to_email} subject={subject}\n{body}\n")

    row = EmailNotification(
        user_id=user.id if user else None,
        to_email=to_email,
        subject=subject,
        body=body,
        template_key=template_key,
        status=status,
        error_message=error,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def notify_plan_changed(db: Session, user: User, *, old_plan: str, new_plan: str, proration_yen: int) -> None:
    body = (
        f"{user.full_name} 様\n\n"
        f"プランが変更されました。\n"
        f"旧プラン: {old_plan}\n"
        f"新プラン: {new_plan}\n"
        f"日割り差額: ¥{proration_yen:,}\n\n"
        f"Studio Reservation Manager\n"
    )
    send_email(
        db,
        to_email=user.email,
        subject=f"[SRM] プラン変更完了（{old_plan} → {new_plan}）",
        body=body,
        template_key="plan_changed",
        user=user,
    )


def notify_invoice_paid(db: Session, user: User, *, invoice_number: str, total_yen: int) -> None:
    body = (
        f"{user.full_name} 様\n\n"
        f"お支払いが確認されました。\n"
        f"請求書番号: {invoice_number}\n"
        f"金額: ¥{total_yen:,}\n\n"
        f"領収書はアプリの「請求書」画面からご確認ください。\n"
        f"Studio Reservation Manager\n"
    )
    send_email(
        db,
        to_email=user.email,
        subject=f"[SRM] 領収書 / お支払い完了（{invoice_number}）",
        body=body,
        template_key="invoice_paid",
        user=user,
    )


def notify_subscription_cancelled(db: Session, user: User, *, period_end: str) -> None:
    body = (
        f"{user.full_name} 様\n\n"
        f"サブスクリプションの解約を受け付けました。\n"
        f"ご利用期限: {period_end}\n"
        f"期限までは残枠をご利用いただけます。\n\n"
        f"Studio Reservation Manager\n"
    )
    send_email(
        db,
        to_email=user.email,
        subject="[SRM] 解約受付のお知らせ",
        body=body,
        template_key="subscription_cancelled",
        user=user,
    )


def notify_payment_failed(db: Session, user: User, *, reason: str) -> None:
    body = (
        f"{user.full_name} 様\n\n"
        f"お支払いに失敗しました。\n"
        f"理由: {reason}\n"
        f"お手数ですがお支払い方法をご確認ください。\n\n"
        f"Studio Reservation Manager\n"
    )
    send_email(
        db,
        to_email=user.email,
        subject="[SRM] お支払い失敗のお知らせ",
        body=body,
        template_key="payment_failed",
        user=user,
    )


def notify_renewal(db: Session, user: User, *, plan_name: str, amount_yen: int) -> None:
    body = (
        f"{user.full_name} 様\n\n"
        f"プラン「{plan_name}」が更新されました。\n"
        f"請求額: ¥{amount_yen:,}\n\n"
        f"Studio Reservation Manager\n"
    )
    send_email(
        db,
        to_email=user.email,
        subject=f"[SRM] 更新・請求のお知らせ（{plan_name}）",
        body=body,
        template_key="renewal",
        user=user,
    )

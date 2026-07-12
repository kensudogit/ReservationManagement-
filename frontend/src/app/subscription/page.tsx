"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  api,
  formatDate,
  formatYen,
  subscriptionStatusLabel,
  type BillingConfig,
  type Plan,
  type ProrationPreview,
  type Subscription,
} from "@/lib/api";

export default function SubscriptionPage() {
  const { user, refresh } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [billing, setBilling] = useState<BillingConfig | null>(null);
  const [preview, setPreview] = useState<ProrationPreview | null>(null);
  const [pendingPlan, setPendingPlan] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setError("");
    try {
      const [planList, mine, cfg] = await Promise.all([
        api.plans(),
        api.mySubscription(),
        api.billingConfig(),
      ]);
      setPlans(planList);
      setSub(mine);
      setBilling(cfg);
    } catch (e) {
      setError(e instanceof Error ? e.message : "取得に失敗しました");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function runSub(action: () => Promise<Subscription>, success: string) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await action();
      setSub(updated);
      setMessage(success);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "処理に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function onPreviewChange(planCode: string) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const p = await api.previewChangePlan(planCode);
      setPreview(p);
      setPendingPlan(planCode);
    } catch (e) {
      setError(e instanceof Error ? e.message : "プレビューに失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function confirmChangePlan() {
    if (!pendingPlan) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.changePlan(pendingPlan);
      setSub(result.subscription);
      setPreview(result.proration);
      setMessage(
        `${result.subscription.plan_name} に変更しました。日割り差額 ${formatYen(result.proration.proration_yen)} / 請求書 ${result.invoice.number}`,
      );
      setPendingPlan(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "プラン変更に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function checkout(planCode: string) {
    setBusy(true);
    setError("");
    try {
      const session = await api.checkout(planCode);
      if (session.url) {
        window.location.href = session.url;
        return;
      }
      setMessage("チェックアウトを開始できませんでした");
    } catch (e) {
      setError(e instanceof Error ? e.message : "決済開始に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  async function openPortal() {
    setBusy(true);
    try {
      const session = await api.billingPortal();
      window.location.href = session.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "ポータルを開けませんでした");
      setBusy(false);
    }
  }

  const currentCode = sub?.plan_code;

  return (
    <div>
      <h1 className="page-title">サブスクリプション</h1>
      <p className="page-lead">
        プラン変更（日割り）、決済、請求書・領収書、メール通知に対応しています。
        {billing?.demo_mode ? " 現在はデモ課金モードです（Stripe 未設定）。" : " Stripe 課金が有効です。"}
      </p>

      {error && <p className="error">{error}</p>}
      {message && <p className="success">{message}</p>}

      <div className="actions" style={{ marginBottom: 20 }}>
        <Link className="ghost-btn" href="/subscription/invoices">
          請求書・領収書
        </Link>
        <Link className="ghost-btn" href="/subscription/notifications">
          通知履歴
        </Link>
        {billing?.stripe_enabled && (
          <button className="ghost-btn" type="button" disabled={busy} onClick={() => void openPortal()}>
            Stripe 顧客ポータル
          </button>
        )}
      </div>

      {sub && (
        <section className="panel" style={{ marginBottom: 24 }}>
          <h2 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>現在の契約</h2>
          <div className="grid grid-3">
            <div>
              <p className="stat-label">プラン</p>
              <p className="stat-value" style={{ fontSize: "1.5rem" }}>
                {sub.plan_name}
              </p>
            </div>
            <div>
              <p className="stat-label">残枠</p>
              <p className="stat-value">
                {sub.remaining}
                <span style={{ fontSize: "1rem", color: "var(--muted)" }}> / {sub.monthly_quota}</span>
              </p>
            </div>
            <div>
              <p className="stat-label">ステータス</p>
              <p className="stat-value" style={{ fontSize: "1.3rem" }}>
                <span className={`badge ${sub.status === "active" ? "ok" : "off"}`}>
                  {subscriptionStatusLabel(sub.status)}
                </span>
              </p>
            </div>
          </div>
          <p style={{ color: "var(--muted)", marginTop: 16, marginBottom: 0 }}>
            契約期間: {formatDate(sub.period_start)} 〜 {formatDate(sub.period_end)}
            {" · "}
            自動更新: {sub.auto_renew ? "ON" : "OFF"}
            {sub.price_yen != null ? ` · ${formatYen(sub.price_yen)} / 月` : ""}
          </p>
          <div className="actions" style={{ marginTop: 18 }}>
            {sub.status === "active" && (
              <button
                className="ghost-btn"
                type="button"
                disabled={busy}
                onClick={() => {
                  if (confirm("解約予約しますか？メール通知も送信されます。")) {
                    void runSub(() => api.cancelSubscription(), "解約を予約しました");
                  }
                }}
              >
                解約する
              </button>
            )}
            {(sub.status === "cancelled" || sub.status === "expired") && (
              <button
                className="btn"
                type="button"
                disabled={busy}
                onClick={() => void runSub(() => api.reactivateSubscription(), "契約を再開しました")}
              >
                契約を再開
              </button>
            )}
            <button
              className="ghost-btn"
              type="button"
              disabled={busy}
              onClick={() => {
                if (confirm("期間を更新しますか？（請求書・メールも発行）")) {
                  void runSub(() => api.renewSubscription(), "期間を更新し請求書を発行しました");
                }
              }}
            >
              期間を更新
            </button>
          </div>
        </section>
      )}

      {preview && (
        <section className="panel" style={{ marginBottom: 24 }}>
          <h2 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>日割りプレビュー</h2>
          <p>{preview.explanation}</p>
          <table className="table">
            <tbody>
              <tr>
                <th>変更</th>
                <td>
                  {preview.from_plan_name} → {preview.to_plan_name}
                </td>
              </tr>
              <tr>
                <th>残日数</th>
                <td>
                  {preview.remaining_days} / {preview.total_days} 日
                </td>
              </tr>
              <tr>
                <th>未使用クレジット</th>
                <td>{formatYen(preview.unused_credit_yen)}</td>
              </tr>
              <tr>
                <th>新プラン日割り</th>
                <td>{formatYen(preview.new_charge_yen)}</td>
              </tr>
              <tr>
                <th>日割り差額</th>
                <td>{formatYen(preview.proration_yen)}</td>
              </tr>
              <tr>
                <th>税</th>
                <td>{formatYen(preview.tax_yen)}</td>
              </tr>
              <tr>
                <th>今回の請求/クレジット</th>
                <td>
                  <strong>{formatYen(preview.total_due_yen)}</strong>
                </td>
              </tr>
            </tbody>
          </table>
          <div className="actions" style={{ marginTop: 16 }}>
            <button className="btn" type="button" disabled={busy} onClick={() => void confirmChangePlan()}>
              日割りを確定して変更
            </button>
            <button
              className="ghost-btn"
              type="button"
              onClick={() => {
                setPreview(null);
                setPendingPlan(null);
              }}
            >
              キャンセル
            </button>
          </div>
        </section>
      )}

      <section>
        <h2 style={{ fontFamily: "var(--font-display)" }}>プラン一覧</h2>
        <div className="plan-grid">
          {plans.map((plan) => {
            const isCurrent = currentCode === plan.code;
            return (
              <article key={plan.id} className={`plan-card ${isCurrent ? "current" : ""}`}>
                <p className="plan-kicker">{isCurrent ? "現在のプラン" : "プラン"}</p>
                <h3>{plan.name}</h3>
                <p className="plan-price">
                  {formatYen(plan.price_yen)}
                  <span>/月</span>
                </p>
                <p className="plan-quota">月 {plan.monthly_quota} 枠</p>
                <p className="plan-desc">{plan.description}</p>
                <div className="actions">
                  {!isCurrent && sub?.status === "active" && (
                    <button
                      className="btn"
                      type="button"
                      disabled={busy}
                      onClick={() => void onPreviewChange(plan.code)}
                    >
                      日割りで変更
                    </button>
                  )}
                  <button
                    className="ghost-btn"
                    type="button"
                    disabled={busy || isCurrent}
                    onClick={() => void checkout(plan.code)}
                  >
                    {billing?.demo_mode ? "デモ決済で契約" : "Stripe で契約"}
                  </button>
                  {isCurrent && (
                    <button className="btn" type="button" disabled>
                      利用中
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

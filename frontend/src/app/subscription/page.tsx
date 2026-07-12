"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  api,
  formatDate,
  formatYen,
  subscriptionStatusLabel,
  type Plan,
  type Subscription,
} from "@/lib/api";

export default function SubscriptionPage() {
  const { user, refresh } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setError("");
    try {
      const [planList, mine] = await Promise.all([api.plans(), api.mySubscription()]);
      setPlans(planList);
      setSub(mine);
    } catch (e) {
      setError(e instanceof Error ? e.message : "取得に失敗しました");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function run(action: () => Promise<Subscription>, success: string) {
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

  const currentCode = sub?.plan_code;

  return (
    <div>
      <h1 className="page-title">サブスクリプション</h1>
      <p className="page-lead">プランの確認・変更、解約、期間更新ができます。</p>

      {error && <p className="error">{error}</p>}
      {message && <p className="success">{message}</p>}

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
                  if (confirm("解約予約しますか？期間終了までは残枠を利用できます。")) {
                    void run(() => api.cancelSubscription(), "解約を予約しました（期間終了まで利用可）");
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
                onClick={() =>
                  void run(() => api.reactivateSubscription(), "契約を再開しました")
                }
              >
                契約を再開
              </button>
            )}
            <button
              className="ghost-btn"
              type="button"
              disabled={busy}
              onClick={() => {
                if (confirm("期間を更新して残枠をリセットしますか？")) {
                  void run(() => api.renewSubscription(), "期間を更新しました");
                }
              }}
            >
              期間を更新
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
                <p className="plan-price">{formatYen(plan.price_yen)}<span>/月</span></p>
                <p className="plan-quota">月 {plan.monthly_quota} 枠</p>
                <p className="plan-desc">{plan.description}</p>
                <button
                  className="btn"
                  type="button"
                  disabled={busy || isCurrent || !user}
                  onClick={() =>
                    void run(
                      () => api.changePlan(plan.code),
                      `${plan.name} プランに変更しました`,
                    )
                  }
                >
                  {isCurrent ? "利用中" : "このプランに変更"}
                </button>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

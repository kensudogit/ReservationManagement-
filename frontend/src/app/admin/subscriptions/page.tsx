"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  api,
  formatDate,
  formatYen,
  subscriptionStatusLabel,
  type Plan,
  type Subscription,
} from "@/lib/api";

export default function AdminSubscriptionsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<Subscription[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    try {
      const [subs, planList] = await Promise.all([api.adminSubscriptions(), api.plans()]);
      setItems(subs);
      setPlans(planList);
    } catch (e) {
      setError(e instanceof Error ? e.message : "取得に失敗しました");
    }
  }

  useEffect(() => {
    if (user && user.role !== "admin") {
      router.replace("/");
      return;
    }
    if (user?.role === "admin") void load();
  }, [user, router]);

  async function onUpdate(userId: number, payload: Parameters<typeof api.adminUpdateSubscription>[1]) {
    setBusyId(userId);
    setError("");
    setMessage("");
    try {
      await api.adminUpdateSubscription(userId, payload);
      setMessage("更新しました");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新に失敗しました");
    } finally {
      setBusyId(null);
    }
  }

  if (user && user.role !== "admin") return null;

  return (
    <div>
      <h1 className="page-title">契約管理</h1>
      <p className="page-lead">会員のサブスクリプションを確認・変更できます（管理者専用）。</p>
      {error && <p className="error">{error}</p>}
      {message && <p className="success">{message}</p>}

      <section className="panel">
        {items.length === 0 && <p style={{ color: "var(--muted)" }}>契約データがありません。</p>}
        {items.map((sub) => (
          <AdminRow
            key={sub.id ?? sub.user_id}
            sub={sub}
            plans={plans}
            busy={busyId === sub.user_id}
            onUpdate={onUpdate}
          />
        ))}
      </section>
    </div>
  );
}

function AdminRow({
  sub,
  plans,
  busy,
  onUpdate,
}: {
  sub: Subscription;
  plans: Plan[];
  busy: boolean;
  onUpdate: (userId: number, payload: Parameters<typeof api.adminUpdateSubscription>[1]) => Promise<void>;
}) {
  const [planCode, setPlanCode] = useState(sub.plan_code || "standard");
  const [status, setStatus] = useState(sub.status);
  const [usedCount, setUsedCount] = useState(String(sub.used_count));

  useEffect(() => {
    setPlanCode(sub.plan_code || "standard");
    setStatus(sub.status);
    setUsedCount(String(sub.used_count));
  }, [sub]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!sub.user_id) return;
    void onUpdate(sub.user_id, {
      plan_code: planCode,
      status,
      used_count: Number(usedCount),
    });
  }

  return (
    <form className="admin-row" onSubmit={onSubmit}>
      <div>
        <strong>{sub.user_name}</strong>
        <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{sub.user_email}</div>
        <div style={{ marginTop: 6, fontSize: "0.9rem" }}>
          {sub.plan_name} · 残 {sub.remaining}/{sub.monthly_quota} ·{" "}
          <span className={`badge ${sub.status === "active" ? "ok" : "off"}`}>
            {subscriptionStatusLabel(sub.status)}
          </span>
        </div>
        <div style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: 4 }}>
          期間 {formatDate(sub.period_start)} 〜 {formatDate(sub.period_end)} · {formatYen(sub.price_yen)}
        </div>
      </div>
      <div className="grid grid-3" style={{ flex: 1 }}>
        <div className="field">
          <label>プラン</label>
          <select value={planCode} onChange={(e) => setPlanCode(e.target.value)}>
            {plans.map((p) => (
              <option key={p.code} value={p.code}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>ステータス</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="active">有効</option>
            <option value="cancelled">解約予定</option>
            <option value="expired">期限切れ</option>
          </select>
        </div>
        <div className="field">
          <label>利用数</label>
          <input type="number" min={0} value={usedCount} onChange={(e) => setUsedCount(e.target.value)} />
        </div>
      </div>
      <button className="btn" type="submit" disabled={busy}>
        {busy ? "更新中…" : "更新"}
      </button>
    </form>
  );
}

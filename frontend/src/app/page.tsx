"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  api,
  formatDate,
  formatDateTime,
  statusLabel,
  subscriptionStatusLabel,
  type Reservation,
} from "@/lib/api";

export default function DashboardPage() {
  const { user, refresh } = useAuth();
  const [upcoming, setUpcoming] = useState<Reservation[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void refresh();
    api
      .reservations({ status: "confirmed", limit: "5" })
      .then(setUpcoming)
      .catch((e) => setError(e.message));
  }, [refresh]);

  const sub = user?.subscription;
  const remaining = sub?.remaining ?? 0;
  const quota = sub?.monthly_quota ?? 0;

  return (
    <div>
      <h1 className="page-title">ダッシュボード</h1>
      <p className="page-lead">
        {user?.full_name} さん、本日のスタジオ予約状況です。空き枠の検索・予約確認・キャンセルができます。
      </p>

      <div className="grid grid-3" style={{ marginBottom: 24 }}>
        <div className="panel">
          <p className="stat-label">今月の残枠</p>
          <p className="stat-value">
            {remaining}
            <span style={{ fontSize: "1rem", color: "var(--muted)" }}> / {quota}</span>
          </p>
        </div>
        <div className="panel">
          <p className="stat-label">プラン</p>
          <p className="stat-value" style={{ fontSize: "1.4rem" }}>
            {sub?.plan_name ?? "未契約"}
          </p>
          {sub && (
            <p style={{ margin: "8px 0 0", color: "var(--muted)", fontSize: "0.85rem" }}>
              {subscriptionStatusLabel(sub.status)} · 〜 {formatDate(sub.period_end)}
            </p>
          )}
        </div>
        <div className="panel">
          <p className="stat-label">Google カレンダー</p>
          <p className="stat-value" style={{ fontSize: "1.4rem" }}>
            {user?.google_calendar_connected ? "連携中" : "未連携"}
          </p>
        </div>
      </div>

      <div className="actions" style={{ marginBottom: 24 }}>
        <Link className="btn" href="/reservations/search">
          空き枠を検索して予約
        </Link>
        <Link className="ghost-btn" href="/subscription">
          プランを変更
        </Link>
        <Link className="ghost-btn" href="/reservations">
          予約一覧を見る
        </Link>
      </div>

      <section className="panel">
        <h2 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>直近の確定予約</h2>
        {error && <p className="error">{error}</p>}
        {!error && upcoming.length === 0 && <p style={{ color: "var(--muted)" }}>確定予約はまだありません。</p>}
        {upcoming.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>日時</th>
                <th>スタジオ</th>
                <th>ステータス</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {upcoming.map((r) => (
                <tr key={r.id}>
                  <td>{formatDateTime(r.start_at)}</td>
                  <td>{r.studio_name}</td>
                  <td>
                    <span className="badge ok">{statusLabel(r.status)}</span>
                  </td>
                  <td>
                    <Link href={`/reservations/${r.id}`}>詳細</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

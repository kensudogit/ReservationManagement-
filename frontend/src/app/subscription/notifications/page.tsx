"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, formatDateTime } from "@/lib/api";

type Notification = {
  id: number;
  to_email: string;
  subject: string;
  template_key: string;
  status: string;
  created_at: string;
};

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .notifications()
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 className="page-title">メール通知履歴</h1>
      <p className="page-lead">
        プラン変更・決済・解約などの通知履歴です。SMTP 未設定時はデモ送信（コンソール + DB 記録）になります。
      </p>
      <div className="actions" style={{ marginBottom: 16 }}>
        <Link className="ghost-btn" href="/subscription">
          サブスクへ戻る
        </Link>
      </div>
      {error && <p className="error">{error}</p>}
      <section className="panel">
        {items.length === 0 && !error && <p style={{ color: "var(--muted)" }}>通知はまだありません。</p>}
        {items.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>日時</th>
                <th>宛先</th>
                <th>件名</th>
                <th>テンプレート</th>
                <th>状態</th>
              </tr>
            </thead>
            <tbody>
              {items.map((n) => (
                <tr key={n.id}>
                  <td>{formatDateTime(n.created_at)}</td>
                  <td>{n.to_email}</td>
                  <td>{n.subject}</td>
                  <td>{n.template_key}</td>
                  <td>
                    <span className={`badge ${n.status === "sent" ? "ok" : "off"}`}>{n.status}</span>
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

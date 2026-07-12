"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, formatDate, formatDateTime, formatYen, type Invoice } from "@/lib/api";

export default function InvoicesPage() {
  const [items, setItems] = useState<Invoice[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .invoices()
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1 className="page-title">請求書・領収書</h1>
      <p className="page-lead">決済・日割り・更新の請求履歴です。詳細から領収書を確認できます。</p>
      <div className="actions" style={{ marginBottom: 16 }}>
        <Link className="ghost-btn" href="/subscription">
          サブスクへ戻る
        </Link>
      </div>
      {error && <p className="error">{error}</p>}
      <section className="panel">
        {items.length === 0 && !error && <p style={{ color: "var(--muted)" }}>請求書はまだありません。</p>}
        {items.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>番号</th>
                <th>種別</th>
                <th>金額</th>
                <th>日割り</th>
                <th>状態</th>
                <th>日時</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.number}</td>
                  <td>{inv.kind}</td>
                  <td>{formatYen(inv.total_yen)}</td>
                  <td>{formatYen(inv.proration_yen)}</td>
                  <td>
                    <span className={`badge ${inv.status === "paid" ? "ok" : "off"}`}>{inv.status}</span>
                  </td>
                  <td>{formatDateTime(inv.paid_at || inv.created_at)}</td>
                  <td>
                    <Link href={`/subscription/invoices/${inv.id}`}>詳細 / 領収書</Link>
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

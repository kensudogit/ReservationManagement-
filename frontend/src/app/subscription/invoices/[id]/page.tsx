"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, formatDate, formatDateTime, formatYen, type Invoice } from "@/lib/api";

export default function InvoiceDetailPage() {
  const params = useParams<{ id: string }>();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState("");
  const [receiptHtml, setReceiptHtml] = useState("");

  useEffect(() => {
    const id = Number(params.id);
    if (!id) return;
    api
      .invoice(id)
      .then(async (inv) => {
        setInvoice(inv);
        const API_URL =
          process.env.NEXT_PUBLIC_API_URL !== undefined
            ? process.env.NEXT_PUBLIC_API_URL
            : "http://localhost:8000";
        const token = localStorage.getItem("token");
        const res = await fetch(`${API_URL}/api/billing/invoices/${id}/receipt`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) setReceiptHtml(await res.text());
      })
      .catch((e) => setError(e.message));
  }, [params.id]);

  if (error) return <p className="error">{error}</p>;
  if (!invoice) return <p style={{ color: "var(--muted)" }}>読み込み中…</p>;

  return (
    <div>
      <h1 className="page-title">請求書 {invoice.number}</h1>
      <p className="page-lead">{invoice.description || "請求詳細と領収書"}</p>
      <div className="actions" style={{ marginBottom: 16 }}>
        <Link className="ghost-btn" href="/subscription/invoices">
          一覧へ
        </Link>
        {invoice.hosted_invoice_url && (
          <a className="ghost-btn" href={invoice.hosted_invoice_url} target="_blank" rel="noreferrer">
            Stripe 請求書
          </a>
        )}
      </div>

      <section className="panel" style={{ marginBottom: 20 }}>
        <table className="table">
          <tbody>
            <tr>
              <th>状態</th>
              <td>{invoice.status}</td>
            </tr>
            <tr>
              <th>種別</th>
              <td>{invoice.kind}</td>
            </tr>
            <tr>
              <th>小計</th>
              <td>{formatYen(invoice.subtotal_yen)}</td>
            </tr>
            <tr>
              <th>税</th>
              <td>{formatYen(invoice.tax_yen)}</td>
            </tr>
            <tr>
              <th>合計</th>
              <td>
                <strong>{formatYen(invoice.total_yen)}</strong>
              </td>
            </tr>
            <tr>
              <th>日割り差額</th>
              <td>{formatYen(invoice.proration_yen)}</td>
            </tr>
            <tr>
              <th>期間</th>
              <td>
                {formatDate(invoice.period_start)} 〜 {formatDate(invoice.period_end)}
              </td>
            </tr>
            <tr>
              <th>支払日時</th>
              <td>{formatDateTime(invoice.paid_at)}</td>
            </tr>
          </tbody>
        </table>
        <h3 style={{ fontFamily: "var(--font-display)" }}>明細</h3>
        <table className="table">
          <tbody>
            {(invoice.line_items || []).map((line, idx) => (
              <tr key={idx}>
                <td>{line.label}</td>
                <td style={{ textAlign: "right" }}>{formatYen(line.amount_yen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {receiptHtml && (
        <section className="panel">
          <h2 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>領収書プレビュー</h2>
          <iframe
            title="receipt"
            srcDoc={receiptHtml}
            style={{ width: "100%", minHeight: 480, border: "1px solid var(--line)", borderRadius: 12, background: "#fff" }}
          />
        </section>
      )}
    </div>
  );
}

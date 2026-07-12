"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, formatDateTime, statusLabel, type Reservation } from "@/lib/api";

export default function ReservationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [item, setItem] = useState<Reservation | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const id = Number(params.id);
    if (!id) return;
    api
      .reservation(id)
      .then(setItem)
      .catch((e) => setError(e.message));
  }, [params.id]);

  async function onCancel() {
    if (!item || !confirm("この予約をキャンセルしますか？")) return;
    try {
      const updated = await api.cancelReservation(item.id);
      setItem(updated);
    } catch (e) {
      alert(e instanceof Error ? e.message : "キャンセルに失敗しました");
    }
  }

  if (error) {
    return (
      <div>
        <p className="error">{error}</p>
        <Link href="/reservations">一覧へ戻る</Link>
      </div>
    );
  }

  if (!item) {
    return <p style={{ color: "var(--muted)" }}>読み込み中…</p>;
  }

  return (
    <div>
      <h1 className="page-title">予約詳細 #{item.id}</h1>
      <p className="page-lead">予約内容の確認とキャンセルを行えます。</p>

      <section className="panel" style={{ maxWidth: 720 }}>
        <table className="table">
          <tbody>
            <tr>
              <th>ステータス</th>
              <td>
                <span className={`badge ${item.status === "confirmed" ? "ok" : "off"}`}>
                  {statusLabel(item.status)}
                </span>
              </td>
            </tr>
            <tr>
              <th>スタジオ</th>
              <td>{item.studio_name}</td>
            </tr>
            <tr>
              <th>開始</th>
              <td>{formatDateTime(item.start_at)}</td>
            </tr>
            <tr>
              <th>終了</th>
              <td>{formatDateTime(item.end_at)}</td>
            </tr>
            <tr>
              <th>予約者</th>
              <td>
                {item.user_name} ({item.user_email})
              </td>
            </tr>
            <tr>
              <th>メモ</th>
              <td>{item.note || "—"}</td>
            </tr>
            <tr>
              <th>Google カレンダー</th>
              <td>{item.google_event_id ? `同期済 (${item.google_event_id})` : "未同期 / 未連携"}</td>
            </tr>
            <tr>
              <th>作成日時</th>
              <td>{formatDateTime(item.created_at)}</td>
            </tr>
            {item.cancelled_at && (
              <tr>
                <th>キャンセル日時</th>
                <td>{formatDateTime(item.cancelled_at)}</td>
              </tr>
            )}
          </tbody>
        </table>

        <div className="actions" style={{ marginTop: 20 }}>
          <button className="ghost-btn" type="button" onClick={() => router.push("/reservations")}>
            一覧へ
          </button>
          {item.status === "confirmed" && (
            <button className="btn danger" type="button" onClick={onCancel}>
              キャンセルする
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

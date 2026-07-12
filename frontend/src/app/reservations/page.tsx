"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, formatDateTime, statusLabel, type Reservation, type Studio } from "@/lib/api";

export default function ReservationsPage() {
  const [items, setItems] = useState<Reservation[]>([]);
  const [studios, setStudios] = useState<Studio[]>([]);
  const [q, setQ] = useState("");
  const [studioId, setStudioId] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(params?: Record<string, string>) {
    setBusy(true);
    setError("");
    try {
      const data = await api.reservations(params);
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "取得に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
    api.studios().then(setStudios).catch(() => undefined);
  }, []);

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const params: Record<string, string> = {};
    if (q) params.q = q;
    if (studioId) params.studio_id = studioId;
    if (status) params.status = status;
    void load(params);
  }

  async function onCancel(id: number) {
    if (!confirm("この予約をキャンセルしますか？")) return;
    try {
      await api.cancelReservation(id);
      await load({
        ...(q ? { q } : {}),
        ...(studioId ? { studio_id: studioId } : {}),
        ...(status ? { status } : {}),
      });
    } catch (e) {
      alert(e instanceof Error ? e.message : "キャンセルに失敗しました");
    }
  }

  return (
    <div>
      <h1 className="page-title">予約確認</h1>
      <p className="page-lead">予約の一覧確認・キーワード検索・キャンセルができます。</p>

      <form className="panel form" onSubmit={onSearch} style={{ marginBottom: 20 }}>
        <div className="grid grid-3">
          <div className="field">
            <label htmlFor="q">キーワード</label>
            <input id="q" placeholder="メモ・氏名など" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="studio">スタジオ</label>
            <select id="studio" value={studioId} onChange={(e) => setStudioId(e.target.value)}>
              <option value="">すべて</option>
              {studios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="status">ステータス</label>
            <select id="status" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">すべて</option>
              <option value="confirmed">確定</option>
              <option value="cancelled">キャンセル済</option>
            </select>
          </div>
        </div>
        <div className="actions">
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "検索中…" : "検索"}
          </button>
          <Link className="ghost-btn" href="/reservations/search">
            空き枠から予約
          </Link>
        </div>
      </form>

      <section className="panel">
        {error && <p className="error">{error}</p>}
        {!error && items.length === 0 && <p style={{ color: "var(--muted)" }}>該当する予約がありません。</p>}
        {items.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>日時</th>
                <th>スタジオ</th>
                <th>ステータス</th>
                <th>カレンダー</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td>{formatDateTime(r.start_at)}</td>
                  <td>{r.studio_name}</td>
                  <td>
                    <span className={`badge ${r.status === "confirmed" ? "ok" : "off"}`}>
                      {statusLabel(r.status)}
                    </span>
                  </td>
                  <td>{r.google_event_id ? "同期済" : "—"}</td>
                  <td className="actions">
                    <Link className="ghost-btn" href={`/reservations/${r.id}`}>
                      詳細
                    </Link>
                    {r.status === "confirmed" && (
                      <button className="btn danger" type="button" onClick={() => onCancel(r.id)}>
                        キャンセル
                      </button>
                    )}
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

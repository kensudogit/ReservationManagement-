"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, formatDateTime, type Studio, type TimeSlot } from "@/lib/api";

export default function SearchPage() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [studios, setStudios] = useState<Studio[]>([]);
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [studioId, setStudioId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.studios().then(setStudios).catch((e) => setError(e.message));
    void searchSlots();
  }, []);

  async function searchSlots(params?: Record<string, string>) {
    setBusy(true);
    setError("");
    try {
      const data = await api.slots(params);
      setSlots(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "空き枠の取得に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const params: Record<string, string> = {};
    if (studioId) params.studio_id = studioId;
    if (dateFrom) params.date_from = new Date(dateFrom).toISOString();
    if (dateTo) params.date_to = new Date(dateTo).toISOString();
    void searchSlots(params);
  }

  async function book(slotId: number) {
    setMessage("");
    try {
      const reserved = await api.createReservation(slotId, note || undefined);
      setMessage(`予約 #${reserved.id} を作成しました`);
      await refresh();
      router.push(`/reservations/${reserved.id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "予約に失敗しました");
    }
  }

  const remaining = user?.subscription?.remaining ?? 0;
  const quota = user?.subscription?.monthly_quota ?? 0;
  const canBook = !!user?.subscription?.is_active && remaining > 0;

  return (
    <div>
      <h1 className="page-title">空き枠検索</h1>
      <p className="page-lead">スタジオと日付で空き枠を検索し、そのまま予約できます。</p>

      <div className="panel" style={{ marginBottom: 20 }}>
        <p style={{ margin: 0 }}>
          サブスク残枠: <strong>{remaining}</strong> / {quota}
          {" · "}
          プラン: {user?.subscription?.plan_name ?? "未契約"}
          {!canBook && (
            <>
              {" — "}
              <Link href="/subscription">プランを確認・変更</Link>
            </>
          )}
        </p>
      </div>

      <form className="panel form" onSubmit={onSearch} style={{ marginBottom: 20 }}>
        <div className="grid grid-3">
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
            <label htmlFor="from">開始日</label>
            <input id="from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="to">終了日</label>
            <input id="to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label htmlFor="note">予約メモ（任意）</label>
          <input
            id="note"
            placeholder="撮影内容・人数など"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        <button className="btn" type="submit" disabled={busy}>
          {busy ? "検索中…" : "空き枠を検索"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {message && <p className="success">{message}</p>}

      <section className="panel">
        <h2 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>空き枠一覧</h2>
        {slots.length === 0 && <p style={{ color: "var(--muted)" }}>条件に合う空き枠がありません。</p>}
        <div className="slot-list">
          {slots.map((slot) => (
            <div className="slot-item" key={slot.id}>
              <div>
                <strong>{slot.studio_name}</strong>
                <div style={{ color: "var(--muted)", marginTop: 4 }}>
                  {formatDateTime(slot.start_at)} 〜 {formatDateTime(slot.end_at)}
                </div>
              </div>
              <button className="btn" type="button" disabled={!canBook} onClick={() => book(slot.id)}>
                {canBook ? "この枠を予約" : "枠不足"}
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

export default function SettingsContent() {
  const { user, refresh } = useAuth();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [configured, setConfigured] = useState(true);

  useEffect(() => {
    if (searchParams.get("google") === "connected") {
      setMessage("Google カレンダー連携が完了しました。");
      void refresh();
    }
  }, [searchParams, refresh]);

  async function connect() {
    setError("");
    try {
      const data = await api.googleAuthUrl();
      setConfigured(data.configured);
      if (!data.configured || !data.url) {
        setError(
          "Google OAuth が未設定です。.env に GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET を設定してください。",
        );
        return;
      }
      window.location.href = data.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "連携開始に失敗しました");
    }
  }

  async function disconnect() {
    if (!confirm("Google カレンダー連携を解除しますか？")) return;
    try {
      const res = await api.googleDisconnect();
      setMessage(res.message);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "解除に失敗しました");
    }
  }

  return (
    <div>
      <h1 className="page-title">設定</h1>
      <p className="page-lead">Google カレンダー連携とアカウント情報を管理します。</p>

      <section className="panel" style={{ maxWidth: 640, marginBottom: 20 }}>
        <h2 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>アカウント</h2>
        <p style={{ margin: "0 0 6px" }}>{user?.full_name}</p>
        <p style={{ margin: 0, color: "var(--muted)" }}>{user?.email}</p>
      </section>

      <section className="panel" style={{ maxWidth: 640 }}>
        <h2 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>Google カレンダー連携</h2>
        <p style={{ color: "var(--muted)", lineHeight: 1.6 }}>
          連携すると、予約の作成・キャンセルが Google カレンダーに自動反映されます。
          現在の状態:{" "}
          <strong style={{ color: "var(--text)" }}>
            {user?.google_calendar_connected ? "連携中" : "未連携"}
          </strong>
        </p>
        {message && <p className="success">{message}</p>}
        {error && <p className="error">{error}</p>}
        {!configured && (
          <p className="error" style={{ marginTop: 8 }}>
            開発環境では未設定でも予約機能は利用できます（カレンダー同期のみスキップ）。
          </p>
        )}
        <div className="actions" style={{ marginTop: 16 }}>
          {!user?.google_calendar_connected ? (
            <button className="btn" type="button" onClick={connect}>
              Google と連携する
            </button>
          ) : (
            <button className="ghost-btn" type="button" onClick={disconnect}>
              連携を解除
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

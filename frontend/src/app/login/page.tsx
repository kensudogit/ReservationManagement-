"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("member@studio.local");
  const [password, setPassword] = useState("member1234");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインに失敗しました");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <p style={{ letterSpacing: "0.12em", textTransform: "uppercase", fontSize: "0.75rem", color: "var(--accent)" }}>
          Studio Reservation Manager
        </p>
        <h1>ログイン</h1>
        <p>サブスク会員向けスタジオ予約システムへようこそ。</p>
        <form className="form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="email">メール</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="password">パスワード</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "認証中…" : "ログイン"}
          </button>
        </form>
        <p style={{ marginTop: 18, marginBottom: 0 }}>
          アカウント未作成の方は <Link href="/register">会員登録</Link>
        </p>
      </div>
    </div>
  );
}

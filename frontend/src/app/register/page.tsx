"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, formatYen, type Plan } from "@/lib/api";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [planCode, setPlanCode] = useState("standard");
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.plans().then(setPlans).catch(() => undefined);
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(email, password, fullName, planCode);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登録に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card" style={{ width: "min(520px, 100%)" }}>
        <p style={{ letterSpacing: "0.12em", textTransform: "uppercase", fontSize: "0.75rem", color: "var(--accent)" }}>
          Studio Reservation Manager
        </p>
        <h1>会員登録</h1>
        <p>プランを選んで登録すると、すぐに予約枠が付与されます。</p>
        <form className="form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="name">お名前</label>
            <input id="name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="email">メール</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="password">パスワード（8文字以上）</label>
            <input
              id="password"
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="plan">プラン</label>
            <select id="plan" value={planCode} onChange={(e) => setPlanCode(e.target.value)}>
              {(plans.length ? plans : [{ code: "standard", name: "Standard", monthly_quota: 4, price_yen: 19800 } as Plan]).map(
                (p) => (
                  <option key={p.code} value={p.code}>
                    {p.name}（月 {p.monthly_quota} 枠 / {formatYen(p.price_yen)}）
                  </option>
                ),
              )}
            </select>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "登録中…" : "登録する"}
          </button>
        </form>
        <p style={{ marginTop: 18, marginBottom: 0 }}>
          既にアカウントがある方は <Link href="/login">ログイン</Link>
        </p>
      </div>
    </div>
  );
}

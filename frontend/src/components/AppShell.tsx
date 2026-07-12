"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { UsageGuideDialog } from "@/components/UsageGuideDialog";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isAuthPage = pathname === "/login" || pathname === "/register";
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    if (isAuthPage || !user) return;
    try {
      const seen = localStorage.getItem("srm_guide_seen");
      if (!seen) {
        setGuideOpen(true);
        localStorage.setItem("srm_guide_seen", "1");
      }
    } catch {
      /* ignore */
    }
  }, [isAuthPage, user]);

  const links = [
    { href: "/", label: "ダッシュボード" },
    { href: "/reservations", label: "予約確認" },
    { href: "/reservations/search", label: "空き枠検索" },
    { href: "/subscription", label: "サブスク" },
    { href: "/settings", label: "設定" },
    ...(user?.role === "admin" ? [{ href: "/admin/subscriptions", label: "契約管理" }] : []),
  ];

  if (loading) {
    return (
      <div className="boot">
        <div className="boot-mark" />
        <p>Loading studio…</p>
      </div>
    );
  }

  if (!user && !isAuthPage) {
    if (typeof window !== "undefined") router.replace("/login");
    return null;
  }

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <span className="brand-mark">SRM</span>
          <div>
            <p className="brand-name">Studio Reservation</p>
            <p className="brand-sub">撮影スタジオ予約</p>
          </div>
        </div>
        <nav>
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href ? "nav-link active" : "nav-link"}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="side-foot">
          <button type="button" className="ghost-btn guide-open-btn" onClick={() => setGuideOpen(true)}>
            利用手順
          </button>
          <p className="user-name">{user?.full_name}</p>
          <p className="user-meta">
            {user?.role === "admin" ? "管理者" : "会員"}
            {user?.subscription ? ` · ${user.subscription.plan_name}` : ""}
          </p>
          <button type="button" className="ghost-btn" onClick={logout}>
            ログアウト
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
      <UsageGuideDialog open={guideOpen} onClose={() => setGuideOpen(false)} />
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function UsageGuideDialog({ open, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) setOffset({ x: 0, y: 0 });
  }, [open]);

  function onPointerDown(e: React.PointerEvent) {
    const el = panelRef.current;
    if (!el) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    dragState.current = {
      x: e.clientX,
      y: e.clientY,
      left: offset.x,
      top: offset.y,
    };
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!dragState.current) return;
    const dx = e.clientX - dragState.current.x;
    const dy = e.clientY - dragState.current.y;
    setOffset({
      x: dragState.current.left + dx,
      y: dragState.current.top + dy,
    });
  }

  function onPointerUp() {
    dragState.current = null;
  }

  if (!open) return null;

  return (
    <div className="guide-overlay" role="presentation" onClick={onClose}>
      <div
        ref={panelRef}
        className="guide-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}
        onClick={(e) => e.stopPropagation()}
      >
        <header
          className="guide-header"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        >
          <button type="button" className="guide-icon-btn" aria-label="メニュー" tabIndex={-1}>
            ☰
          </button>
          <div className="guide-header-center">
            <span className="guide-drag-hint">ドラッグで移動</span>
          </div>
          <button type="button" className="guide-icon-btn" onClick={onClose} aria-label="閉じる">
            ▾
          </button>
        </header>

        <div className="guide-body">
          <p className="guide-kicker">GUIDE &amp; OPS</p>
          <h2 id="guide-title">利用手順</h2>
          <p className="guide-lead">
            Studio Reservation Manager（SRM）は、撮影スタジオのサブスク会員向けに予約・検索・キャンセル・課金・Google
            カレンダー連携を提供する Web アプリです。
          </p>

          <div className="guide-pills">
            <span>Python · FastAPI</span>
            <span>Next.js 15 · React</span>
            <span>PostgreSQL · SaaS</span>
            <span>JWT 認証</span>
            <span>Stripe · 日割り課金</span>
            <span>請求書 · 領収書</span>
            <span>メール通知</span>
            <span>Google Calendar</span>
            <span>Docker · Railway</span>
          </div>

          <section className="guide-section">
            <h3>ARCHITECTURE: Next.js BFF + FastAPI 予約エンジン</h3>
            <p>
              フロント（Next.js）は同一オリジンで FastAPI にプロキシします。予約枠・サブスク・請求は PostgreSQL
              に保存し、Stripe / SMTP はバックエンド経由で呼び出して秘密鍵をフロントに出しません。
            </p>
            <ul>
              <li>
                <strong>Next.js</strong> — ダッシュボード、予約、サブスク、請求書、設定 UI
              </li>
              <li>
                <strong>FastAPI (:8000)</strong> — 認証、空き枠、予約、プラン、Stripe、Webhook、メール
              </li>
              <li>
                <strong>PostgreSQL</strong> — 会員、スタジオ枠、契約、請求書、通知履歴
              </li>
              <li>
                <strong>SaaS</strong> — JWT ログイン、プラン、日割り、請求、利用枠トラッキング
              </li>
              <li>
                <strong>/health &amp; /docs</strong> — ヘルスチェックと Swagger
              </li>
            </ul>
          </section>

          <section className="guide-section">
            <h3>SERVICE TOPOLOGY</h3>
            <pre className="guide-topo">{`Browser (会員 / 管理者)
  │  HTTPS + JWT
  ▼
Next.js :PORT  ──rewrite──▶  FastAPI :8000
  /                     ダッシュボード
  /reservations         予約確認・検索・キャンセル
  /subscription         プラン・決済・日割り
  /subscription/invoices 請求書・領収書
  /settings             Google カレンダー連携
  /admin/subscriptions  管理者の契約管理
         │
         ▼
   PostgreSQL  /  Stripe  /  SMTP  /  Google Calendar API`}</pre>
          </section>

          <section className="guide-section">
            <h3>1. ログイン / 会員登録</h3>
            <ol>
              <li>
                <code>/login</code> でメールとパスワードを入力してログインします。
              </li>
              <li>
                デモ会員: <code>member@studio.local</code> / <code>member1234</code>
              </li>
              <li>
                デモ管理者: <code>admin@studio.local</code> / <code>admin1234</code>
              </li>
              <li>
                新規の方は <code>/register</code> で氏名・メール・パスワード・初期プランを選んで登録します。登録直後に
                Standard 相当の契約と月次枠が付与されます。
              </li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>2. ダッシュボードで状況確認</h3>
            <ol>
              <li>
                ホーム <code>/</code> で「今月の残枠」「プラン」「Google 連携状態」を確認します。
              </li>
              <li>直近の確定予約が一覧表示されます。詳細リンクから予約内容を開けます。</li>
              <li>残枠が 0 の場合は予約できないため、先にサブスク画面でプランを確認・変更してください。</li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>3. 空き枠検索と予約</h3>
            <ol>
              <li>
                左メニュー「空き枠検索」(<code>/reservations/search</code>) を開きます。
              </li>
              <li>スタジオ・開始日・終了日で絞り込み、「空き枠を検索」を押します。</li>
              <li>必要なら予約メモ（撮影内容・人数など）を入力します。</li>
              <li>
                「この枠を予約」で確定します。成功すると残枠が 1 減り、詳細画面へ遷移します。
              </li>
              <li>残枠不足や契約無効の場合はボタンが無効、または API エラーになります。</li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>4. 予約確認・検索・キャンセル</h3>
            <ol>
              <li>
                「予約確認」(<code>/reservations</code>) で自分の予約（管理者は全員分）を一覧します。
              </li>
              <li>キーワード・スタジオ・ステータスで検索できます。</li>
              <li>
                「キャンセル」は開始 <strong>24 時間前まで</strong>可能です（管理者は随時可）。
              </li>
              <li>キャンセル後は枠が再開放され、サブスク利用回数が戻ります。</li>
              <li>Google 連携済みなら、作成時にカレンダー登録・キャンセル時にイベント削除されます。</li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>5. サブスク・決済・日割り</h3>
            <ol>
              <li>
                「サブスク」(<code>/subscription</code>) で契約状態・残枠・期間を確認します。
              </li>
              <li>
                プラン変更は「日割りで変更」→ プレビュー（残日数・クレジット・差額・税）→「確定」。
              </li>
              <li>
                「デモ決済で契約」は Stripe 未設定時の即時課金シミュレーションです。請求書が発行されます。
              </li>
              <li>
                Stripe キー設定時は Checkout / 顧客ポータル / Webhook で本課金になります。
              </li>
              <li>解約は期間終了まで残枠利用可。期間更新では残枠リセットと請求書・メールが発行されます。</li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>6. 請求書・領収書・メール通知</h3>
            <ol>
              <li>
                <code>/subscription/invoices</code> で請求一覧を確認します。
              </li>
              <li>各請求の詳細から HTML 領収書プレビューを表示できます。</li>
              <li>
                <code>/subscription/notifications</code> でプラン変更・支払完了・解約などの通知履歴を確認します。
              </li>
              <li>SMTP 未設定時はコンソール出力 + DB 記録（デモ）。設定後は実メール送信されます。</li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>7. Google カレンダー連携</h3>
            <ol>
              <li>
                「設定」(<code>/settings</code>) を開きます。
              </li>
              <li>
                <code>GOOGLE_CLIENT_ID</code> / <code>SECRET</code> が環境変数にある場合、「Google と連携する」で OAuth
                同意します。
              </li>
              <li>以降の予約作成・キャンセルが primary カレンダーに同期されます。</li>
              <li>未設定でも予約機能は利用できます（同期のみスキップ）。</li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>8. 管理者向け</h3>
            <ol>
              <li>
                管理者でログインすると「契約管理」(<code>/admin/subscriptions</code>) が表示されます。
              </li>
              <li>会員ごとのプラン・ステータス・利用数を変更できます。</li>
              <li>予約一覧では全会員の予約を検索・キャンセルできます。</li>
            </ol>
          </section>

          <section className="guide-section">
            <h3>9. 運用メモ</h3>
            <ul>
              <li>
                ヘルスチェック: <code>GET /health</code>
              </li>
              <li>
                API ドキュメント: <code>/docs</code>
              </li>
              <li>
                必須環境変数: <code>DATABASE_URL</code>, <code>SECRET_KEY</code>
              </li>
              <li>
                任意: <code>STRIPE_*</code>, <code>SMTP_*</code>, <code>GOOGLE_*</code>
              </li>
              <li>
                Railway ではアプリ URL（例: <code>reservationmanagement-production.up.railway.app</code>
                ）を開き、Postgres 公開 URL は開きません。
              </li>
            </ul>
          </section>
        </div>

        <footer className="guide-footer">
          <button type="button" className="guide-primary" onClick={onClose}>
            閉じる
          </button>
        </footer>
      </div>
    </div>
  );
}

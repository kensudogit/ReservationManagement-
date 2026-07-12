# Studio Reservation Manager

撮影スタジオのサブスクリプション予約管理システムです。

## 技術スタック

| 層 | 技術 |
|----|------|
| Frontend | Next.js 15 + React + TypeScript |
| Backend | FastAPI (Python) + SQLAlchemy + Alembic |
| DB | PostgreSQL 16 |
| Infra | Docker Compose |
| 連携 | Google Calendar API (OAuth 2.0) |

## デプロイ (Railway)

単一サービス構成（推奨）: ルート `Dockerfile` が **Next.js + FastAPI** を起動します。

### 必須設定
1. **PostgreSQL** プラグインを追加し、サービスに `DATABASE_URL` を接続
2. **Root Directory:** 空
3. **Dockerfile Path:** `Dockerfile`
4. 環境変数:
   - `SECRET_KEY` — 任意の長いランダム文字列
   - `DATABASE_URL` — Postgres プラグインから自動注入
   - `CORS_ORIGINS` — `https://reservationmanagement-production.up.railway.app`
   - `FRONTEND_URL` — 同上

### 「電車の 404」(The train has not arrived)
アプリが起動していないときに出ます。ほぼ次が原因です。
- `DATABASE_URL` 未設定 / Postgres 未追加
- デプロイ失敗・クラッシュループ
- ドメインが稼働中サービスに紐づいていない

Railway ダッシュボード → 対象サービス → Deployments でログを確認してください。

## サブスクリプション / 課金

| プラン | 月枠 | 月額 |
|--------|------|------|
| Light | 2 | ¥9,800 |
| Standard | 4 | ¥19,800 |
| Premium | 8 | ¥34,800 |
| Unlimited | 20 | ¥59,800 |

実装済み:
- プラン選択・変更・解約・再開・期間更新
- **Stripe 決済**（Checkout / Portal / Webhook）※キー未設定時はデモ課金
- **日割り proration**（プラン変更プレビュー + 請求書）
- **請求書 / 領収書**（`/subscription/invoices`）
- **メール通知**（SMTP またはデモ記録 `/subscription/notifications`）

画面: `/subscription` · `/subscription/invoices` · `/admin/subscriptions`

## ドキュメント

- [要件定義](docs/requirements.md)
- [設計](docs/design.md)
- [保守・運用](docs/operations.md)

## クイックスタート

```bash
cd ReservationManagement
copy .env.example .env   # Windows
# Windows で buildx エラーが出る場合:
#   set COMPOSE_BAKE=false
docker compose up --build
```

| URL | 用途 |
|-----|------|
| http://localhost:3020 | フロントエンド |
| http://localhost:8000/docs | API ドキュメント |

### デモアカウント

| ロール | メール | パスワード |
|--------|--------|------------|
| 管理者 | admin@studio.local | admin1234 |
| 会員 | member@studio.local | member1234 |

## ローカル個別起動

```bash
# 1) DB
docker compose up -d db

# 2) Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# DATABASE_URL を localhost 向けに調整
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000

# 3) Frontend
cd frontend
npm install
npm run dev
```

## Google カレンダー連携

1. [Google Cloud Console](https://console.cloud.google.com/) で OAuth クライアントを作成
2. Calendar API を有効化
3. `.env` に `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` を設定
4. リダイレクト URI: `http://localhost:8000/api/google/callback`
5. アプリの「設定」から連携

未設定でも予約・検索・キャンセルは動作します（カレンダー同期のみスキップ）。

## ディレクトリ

```
ReservationManagement/
├── docs/
├── backend/          # FastAPI
├── frontend/         # Next.js
├── docker-compose.yml
└── README.md
```
"# ReservationManagement-" 

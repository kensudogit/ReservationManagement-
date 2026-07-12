# 設計書 — Studio Reservation Manager

## 1. システム構成

```
┌─────────────┐     REST/JSON      ┌──────────────┐      ┌────────────┐
│  Next.js    │ ◄────────────────► │   FastAPI    │ ◄──► │ PostgreSQL │
│  (Frontend) │                    │   (Backend)  │      └────────────┘
└─────────────┘                    └──────┬───────┘
                                          │ OAuth2
                                          ▼
                                   ┌──────────────┐
                                   │ Google       │
                                   │ Calendar API │
                                   └──────────────┘
```

## 2. ディレクトリ構成

```
ReservationManagement/
├── docs/                 # 要件・設計・運用
├── backend/              # FastAPI
│   └── app/
│       ├── api/          # ルーター
│       ├── core/         # 設定・セキュリティ
│       ├── models/       # SQLAlchemy
│       ├── schemas/      # Pydantic
│       └── services/     # ビジネスロジック
├── frontend/             # Next.js
├── docker-compose.yml
└── README.md
```

## 3. ER 図（論理）

```
users
  id PK, email UNIQUE, hashed_password, full_name, role(member|admin),
  google_refresh_token, google_calendar_connected, created_at

studios
  id PK, name, description, capacity, is_active

time_slots
  id PK, studio_id FK, start_at, end_at, is_available

subscriptions
  id PK, user_id FK, plan_name, monthly_quota, used_count,
  period_start, period_end, is_active

reservations
  id PK, user_id FK, studio_id FK, time_slot_id FK,
  status(confirmed|cancelled), note,
  google_event_id, created_at, cancelled_at
```

## 4. API 設計（主要）

| Method | Path | 説明 |
|--------|------|------|
| POST | /api/auth/register | 会員登録 |
| POST | /api/auth/login | ログイン |
| GET | /api/auth/me | 自分の情報 |
| GET | /api/studios | スタジオ一覧 |
| GET | /api/slots | 空き枠検索 |
| GET | /api/reservations | 予約一覧・検索 |
| GET | /api/reservations/{id} | 予約詳細 |
| POST | /api/reservations | 予約作成 |
| POST | /api/reservations/{id}/cancel | キャンセル |
| GET | /api/google/auth-url | OAuth URL 取得 |
| GET | /api/google/callback | OAuth コールバック |
| DELETE | /api/google/disconnect | 連携解除 |

## 5. 画面設計

| 画面 | パス | 概要 |
|------|------|------|
| ログイン / 登録 | /login, /register | 認証 |
| ダッシュボード | / | 直近予約・残枠 |
| 予約検索・空き枠 | /reservations/search | 検索・新規予約 |
| 予約一覧 | /reservations | 確認・キャンセル |
| 予約詳細 | /reservations/[id] | 詳細表示 |
| 設定 | /settings | Google 連携 |
| 管理 | /admin | スタジオ・予約管理（admin） |

## 6. キャンセルポリシー

- 会員: 枠開始時刻の 24 時間前までキャンセル可
- 管理者: いつでもキャンセル可
- キャンセル後は枠を再開放し、サブスク利用回数を減算

## 7. Google カレンダー同期

1. ユーザーが設定画面から OAuth 同意
2. refresh_token を DB に保存（暗号化推奨・開発は平文可）
3. 予約作成時に primary カレンダーへイベント作成、`google_event_id` を保存
4. キャンセル時にイベント削除

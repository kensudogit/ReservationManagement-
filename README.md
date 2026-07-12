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

## デプロイ (Railway 等)

### API サービス
- **Root Directory:** 空
- **Dockerfile Path:** `Dockerfile`
- 環境変数: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `FRONTEND_URL`, `PORT`

### Web (フロント) サービス
- **Root Directory:** 空（重要: `frontend` と入れない）
- **Dockerfile Path:** `Dockerfile.frontend`
- 環境変数: `NEXT_PUBLIC_API_URL` = API の公開 URL

Root Directory を `frontend` にすると、ビルダーが存在しないパスを参照して次のエラーになります。

```
lstat .../frontend : no such file or directory
```

```bash
# ローカル確認
docker build -t srm-api .
docker build -t srm-web -f Dockerfile.frontend .
```


| プラン | 月枠 | 月額 |
|--------|------|------|
| Light | 2 | ¥9,800 |
| Standard | 4 | ¥19,800 |
| Premium | 8 | ¥34,800 |
| Unlimited | 20 | ¥59,800 |

機能:
- 登録時のプラン選択
- プラン変更（アップ/ダウン）
- 解約予約（期間終了まで利用可）/ 再開
- 期間更新（残枠リセット）と自動更新
- 管理者による契約管理

画面: `/subscription`（会員） / `/admin/subscriptions`（管理者）

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

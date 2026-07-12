# 保守・運用ガイド

## 1. ローカル起動

```bash
# 環境変数
cp .env.example .env

# 一括起動（DB + API + Web）
docker compose up --build

# フロント: http://localhost:3020
# API ドキュメント: http://localhost:8000/docs
```

### 個別起動（開発）

```bash
# DB
docker compose up -d db

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## 2. シードデータ

初回起動時に `backend/app/seed.py` が実行され、管理者・デモ会員・スタジオ・枠が投入されます。

| アカウント | メール | パスワード |
|------------|--------|------------|
| 管理者 | admin@studio.local | admin1234 |
| 会員 | member@studio.local | member1234 |

## 3. 環境変数

| 変数 | 説明 |
|------|------|
| DATABASE_URL | PostgreSQL 接続文字列 |
| SECRET_KEY | JWT 署名鍵 |
| GOOGLE_CLIENT_ID / SECRET | Google OAuth |
| GOOGLE_REDIRECT_URI | OAuth コールバック URL |
| NEXT_PUBLIC_API_URL | フロントから見る API ベース URL |
| CANCEL_HOURS_BEFORE | キャンセル可能期限（時間） |

## 4. バックアップ

```bash
docker compose exec db pg_dump -U srm srm > backup_$(date +%Y%m%d).sql
```

復元:

```bash
docker compose exec -T db psql -U srm srm < backup_YYYYMMDD.sql
```

## 5. ログ・ヘルスチェック

- API: `GET /health`
- コンテナ: `docker compose ps` / `docker compose logs -f api`

## 6. 障害対応メモ

| 症状 | 確認 |
|------|------|
| ログインできない | DB 起動、シード実行、SECRET_KEY 一致 |
| Google 連携失敗 | Client ID/Secret、リダイレクト URI、カレンダー API 有効化 |
| 予約できない | 枠の is_available、サブスク残枠、重複予約 |

## 7. 今後の運用タスク

- [ ] 本番用 SECRET_KEY / DB パスワードのローテーション
- [ ] Google refresh_token の暗号化保存
- [ ] 定期バックアップジョブ（cron / Cloud Scheduler）
- [ ] 監視（Uptime / Sentry）の導入

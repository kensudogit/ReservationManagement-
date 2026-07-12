#!/bin/sh
set -eu

export DATABASE_URL="$(python - <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("ERROR: DATABASE_URL is not set", file=sys.stderr)
    sys.exit(1)
if url.startswith("postgres://"):
    url = "postgresql+psycopg://" + url[len("postgres://"):]
elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
    url = "postgresql+psycopg://" + url[len("postgresql://"):]

engine = create_engine(url, pool_pre_ping=True)
for attempt in range(1, 31):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"database ready (attempt {attempt})", file=sys.stderr)
        break
    except Exception as exc:
        print(f"waiting for database ({attempt}/30): {exc}", file=sys.stderr)
        time.sleep(2)
else:
    sys.exit(1)
print(url)
PY
)"

alembic upgrade head
python -m app.seed || true
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

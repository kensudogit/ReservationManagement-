#!/bin/sh
set -eu

echo "[start] PORT=${PORT:-3000}"

export DATABASE_URL="$(python - <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("ERROR: DATABASE_URL is not set", file=sys.stderr)
    print("Add Railway PostgreSQL and link DATABASE_URL to this service.", file=sys.stderr)
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
        print(f"[start] database ready (attempt {attempt})", file=sys.stderr)
        break
    except Exception as exc:
        print(f"[start] waiting for database ({attempt}/30): {exc}", file=sys.stderr)
        time.sleep(2)
else:
    print("[start] ERROR: database not reachable", file=sys.stderr)
    sys.exit(1)

print(url)
PY
)"

echo "[start] running migrations"
alembic upgrade head

echo "[start] seeding"
python -m app.seed || true

echo "[start] launching API on 127.0.0.1:8000"
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

# Wait until API actually answers (import errors can take >2s)
ready=0
i=1
while [ "$i" -le 30 ]; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "[start] ERROR: API process exited during boot" >&2
    wait "$API_PID" || true
    exit 1
  fi
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "[start] ERROR: API failed health check" >&2
  kill "$API_PID" 2>/dev/null || true
  wait "$API_PID" || true
  exit 1
fi

echo "[start] API healthy"
echo "[start] launching Next.js on 0.0.0.0:${PORT:-3000}"
exec npx next start -H 0.0.0.0 -p "${PORT:-3000}"

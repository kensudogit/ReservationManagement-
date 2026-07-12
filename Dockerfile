# All-in-one production image: FastAPI (internal) + Next.js (public PORT)
# Railway: Root Directory empty, Dockerfile Path = Dockerfile
# Required: PostgreSQL plugin → DATABASE_URL

FROM node:22-bookworm AS web-build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
# Same-origin API via Next rewrites
ENV NEXT_PUBLIC_API_URL=
ENV API_INTERNAL_URL=http://127.0.0.1:8000
RUN npm run build

FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=web-build /web/.next ./.next
COPY --from=web-build /web/public ./public
COPY --from=web-build /web/package.json ./package.json
COPY --from=web-build /web/next.config.js ./next.config.js
COPY --from=web-build /web/node_modules ./node_modules

RUN chmod +x /app/scripts/start.sh \
    && mkdir -p /app/scripts

ENV PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_PUBLIC_API_URL= \
    API_INTERNAL_URL=http://127.0.0.1:8000 \
    HOSTNAME=0.0.0.0

EXPOSE 3000

CMD ["/app/scripts/start.sh"]

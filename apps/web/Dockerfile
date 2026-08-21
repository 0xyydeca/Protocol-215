# protocol-215-web — FastAPI + built React (same-origin)
# Build from repository root: docker build -f apps/web/Dockerfile .

FROM node:22-alpine AS frontend
WORKDIR /ui
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_ASSETS_DIR=/app/static \
    PORT=8080

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY apps/api ./apps/api
RUN uv sync --frozen --no-dev --extra cloud || uv sync --frozen --no-dev

COPY --from=frontend /ui/dist /app/static

EXPOSE 8080
CMD ["uv", "run", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]

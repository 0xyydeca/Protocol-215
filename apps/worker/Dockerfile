# protocol-215-worker — Pub/Sub push consumer (private Cloud Run)
# Build from repository root: docker build -f apps/worker/Dockerfile .

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    WORKER_REQUIRE_OIDC=true

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY apps/worker ./apps/worker
COPY fixtures ./fixtures
RUN uv sync --frozen --no-dev --extra cloud || uv sync --frozen --no-dev

EXPOSE 8080
CMD ["uv", "run", "uvicorn", "apps.worker.main:app", "--host", "0.0.0.0", "--port", "8080"]

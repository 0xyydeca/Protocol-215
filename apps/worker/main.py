"""FastAPI Cloud Run worker — production ASGI entrypoint."""

from protocol215.cloud.http_worker import create_worker_app
from protocol215.cloud.production import create_production_worker_app

# Re-export for tests that import create_worker_app from apps.worker.main
__all__ = ["app", "create_worker_app", "create_production_worker_app"]

# Production module-level app always has AmendmentWorkerHandler wired.
app = create_production_worker_app()

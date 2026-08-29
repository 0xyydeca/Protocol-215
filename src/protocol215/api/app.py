"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from protocol215.api.container import AppContainer, build_container
from protocol215.api.errors import ApiError, api_error_handler, unhandled_error_handler
from protocol215.api.routes import router
from protocol215.config import Settings, get_settings
from protocol215.health import liveness, readiness
from protocol215.observability import configure_logging


def create_app(settings: Settings | None = None, container: AppContainer | None = None) -> FastAPI:
    configure_logging()
    cfg = settings or get_settings()
    shared = container

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = shared or build_container(cfg)
        yield

    app = FastAPI(
        title="Protocol 215 API",
        description="Clinical Amendment Preflight — synthetic proof of concept",
        version="0.1.0",
        lifespan=lifespan,
    )
    # Browser cookies are not used; keep credentials off. Never pair "*" with credentials.
    origins = [o for o in cfg.cors_origin_list if o != "*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Correlation-ID"],
    )
    app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return liveness(cfg)

    @app.get("/readyz")
    def readyz(response: Response) -> dict[str, object]:
        container = getattr(app.state, "container", None)
        payload = readiness(cfg, container=container)
        if payload["status"] != "ok":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return payload

    app.include_router(router)
    if shared is not None:
        app.state.container = shared

    # Same-origin SPA: serve Vite build when STATIC_ASSETS_DIR is configured (Cloud Run web).
    if cfg.static_assets_dir is not None and cfg.static_assets_dir.is_dir():
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        assets = cfg.static_assets_dir
        index = assets / "index.html"
        app.mount("/assets", StaticFiles(directory=assets / "assets"), name="assets")

        _SPA_RESERVED = {
            "healthz",
            "readyz",
            "docs",
            "openapi.json",
            "redoc",
        }

        @app.get("/")
        def spa_index() -> FileResponse:
            return FileResponse(index)

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            head = full_path.split("/", 1)[0]
            if head in _SPA_RESERVED or full_path.startswith("api/"):
                from fastapi import HTTPException

                raise HTTPException(status_code=404, detail="Not Found")
            candidate = assets / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)

    return app

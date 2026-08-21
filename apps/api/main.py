"""FastAPI entrypoint for protocol-215-api (local / Cloud Run web companion)."""

from protocol215.api.app import create_app

app = create_app()

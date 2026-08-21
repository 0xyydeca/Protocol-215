# THIRD_PARTY_NOTICES.md — Protocol 215

This project depends on open-source components. Licenses remain with their respective authors. Below is a practical inventory for hackathon disclosure—not a complete SPDX SBOM.

## Runtime (Python)

| Package | Role |
| --- | --- |
| FastAPI / Starlette / Uvicorn | HTTP API |
| Pydantic / pydantic-settings | Schemas & settings |
| google-adk | Agent workflow graph |
| google-genai | Gemini / Vertex client |
| tenacity | Retries |
| structlog | Logging |
| httpx | HTTP client |
| pypdf / reportlab | PDF read / fixture generation |

Optional cloud extras (`pyproject.toml` `[cloud]`): `google-cloud-storage`, `google-cloud-firestore`, `google-cloud-pubsub`, `google-cloud-logging`, `google-auth`.

## Frontend

| Package | Role |
| --- | --- |
| React | UI |
| Vite | Build / dev server |
| TypeScript | Types |
| Vitest / Testing Library | Unit tests |
| Playwright | E2E (optional local) |

Exact versions: `apps/web/package-lock.json`, `uv.lock`.

## Infrastructure / tooling

Terraform Google provider, Docker, pytest, ruff, mypy, uv.

## Synthetic content

AURORA-101 protocol text and twin data are original synthetic fixtures for this hackathon (`fixtures/`). They are not real trial documents.

## Notices

Distribute third-party licenses with any binary redistribution per each package’s terms. Apache-2.0 covers **this** repository’s original code (`LICENSE`); it does not re-license dependencies.

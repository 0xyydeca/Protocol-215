.PHONY: bootstrap check api web worker test fmt lint typecheck reset-demo \
	terraform-fmt terraform-validate build-images

UV_BIN ?= $(shell if [ -x .tools/uv ]; then echo .tools/uv; elif command -v uv >/dev/null 2>&1; then command -v uv; else echo uv; fi)

bootstrap:
	bash scripts/bootstrap.sh

check:
	bash scripts/check.sh

api:
	bash scripts/run_local.sh

web:
	cd apps/web && npm run dev

worker:
	$(UV_BIN) run python apps/worker/main.py

test:
	$(UV_BIN) run pytest
	cd apps/web && npm test -- --run

fmt:
	$(UV_BIN) run ruff format src apps/api apps/worker tests

lint:
	$(UV_BIN) run ruff check src apps/api apps/worker tests

typecheck:
	$(UV_BIN) run mypy src/protocol215

reset-demo:
	bash scripts/reset_demo.sh

terraform-fmt:
	cd infra/terraform && terraform fmt -recursive && terraform fmt -check -recursive

terraform-validate:
	cd infra/terraform && terraform init -backend=false -input=false && terraform validate

build-images:
	bash scripts/build_images.sh

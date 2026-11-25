RUFF ?= .venv/bin/ruff

.PHONY: lint fmt fmt-check

# Check only: lint + format check, no writes
lint:
	$(RUFF) check .
	$(RUFF) format --check .

# Apply safe fixes + format
fmt:
	$(RUFF) check --fix .
	$(RUFF) format .

# Format check only, no writes
fmt-check:
	$(RUFF) format --check .

MYPY ?= .venv/bin/mypy

.PHONY: typecheck

# Type check src/suprsend (config in pyproject.toml)
typecheck:
	$(MYPY)

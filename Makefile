.PHONY: help install dev test lint format typecheck serve clean watch

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

dev: ## Install with dev dependencies
	uv sync --all-extras
	uv run playwright install chromium

test: ## Run all tests
	uv run pytest tests/ -v --cov=src --cov-report=term-missing

test-unit: ## Run unit tests only
	uv run pytest tests/unit -v -m unit

test-integration: ## Run integration tests
	uv run pytest tests/integration -v -m integration

lint: ## Run linter
	uv run ruff check src/ tests/

format: ## Format code
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck: ## Run type checker
	uv run mypy src/

serve: ## Start the FastAPI development server
	uv run uvicorn src.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000

scrape: ## Run a single scrape (usage: make scrape URL=https://catalog.csus.edu NAME="Sacramento State")
	uv run python scripts/run_single_scrape.py --url $(URL) --name "$(NAME)"

scrape-major: ## Search + scrape a specific major (usage: make scrape-major NAME="MIT" MAJOR="Computer Science")
	uv run python scripts/run_single_scrape.py --name "$(NAME)" --major "$(MAJOR)"

watch: ## Watch a running scrape job (usage: make watch JOB=<job-id>)
	uv run python scripts/pipeline_watch.py $(JOB)

clean: ## Remove build artifacts and caches
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

check: lint typecheck test ## Run all checks (lint + typecheck + test)

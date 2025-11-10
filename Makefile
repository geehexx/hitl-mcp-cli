.PHONY: help install test lint format type-check security clean pre-commit

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync --all-extras

test:  ## Run tests with coverage
	uv run pytest --cov --cov-report=html --cov-report=term-missing

test-fast:  ## Run tests without coverage
	uv run pytest -x

lint:  ## Run linters
	uv run ruff check .
	uv run interrogate hitl_mcp_cli/

format:  ## Format code
	uv run black .
	uv run isort .
	uv run ruff check --fix .

type-check:  ## Run type checking
	uv run mypy hitl_mcp_cli/

security:  ## Run security checks
	uv run bandit -r hitl_mcp_cli/

pre-commit:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

clean:  ## Clean build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

all: format lint type-check test  ## Run all checks

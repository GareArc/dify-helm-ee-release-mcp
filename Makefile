.PHONY: help install dev lint format typecheck test test-cov clean build run docker-build docker-run docker-push

# Variables
PYTHON := uv run python
APP_NAME := helm-release-mcp
VERSION := $(shell grep -m1 'version' pyproject.toml | cut -d'"' -f2)
DOCKER_REGISTRY ?= ghcr.io
DOCKER_ORG ?=
DOCKER_IMAGE := $(DOCKER_REGISTRY)/$(DOCKER_ORG)/$(APP_NAME)

# Colors
BLUE := \033[34m
GREEN := \033[32m
RESET := \033[0m

help: ## Show this help
	@echo "$(BLUE)$(APP_NAME)$(RESET) v$(VERSION)"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

# ============================================================================
# Development
# ============================================================================

install: ## Install dependencies
	uv sync

dev: ## Install with dev dependencies
	uv sync --all-extras

lint: ## Run linter (ruff)
	uv run ruff check src/ tests/

lint-fix: ## Run linter and fix issues
	uv run ruff check --fix src/ tests/

format: ## Format code (ruff)
	uv run ruff format src/ tests/

format-check: ## Check code formatting
	uv run ruff format --check src/ tests/

typecheck: ## Run type checker (mypy)
	uv run mypy src/

check: lint typecheck ## Run all checks (lint + typecheck)

# ============================================================================
# Testing
# ============================================================================

test: ## Run tests
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=src/helm_release_mcp --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode
	uv run pytest-watch tests/

# ============================================================================
# Running
# ============================================================================

.PHONY: check-tokens
check-tokens:
ifndef HELM_MCP_GITHUB_TOKEN
	$(error HELM_MCP_GITHUB_TOKEN is not set. Run: export HELM_MCP_GITHUB_TOKEN=ghp_xxx)
endif
ifndef DIFY_GITHUB_TOKEN
	$(error DIFY_GITHUB_TOKEN is not set. Run: export DIFY_GITHUB_TOKEN=ghp_xxx)
endif
ifndef DIFY_HELM_GITHUB_TOKEN
	$(error DIFY_HELM_GITHUB_TOKEN is not set. Run: export DIFY_HELM_GITHUB_TOKEN=ghp_xxx)
endif
ifndef DIFY_ENTERPRISE_GITHUB_TOKEN
	$(error DIFY_ENTERPRISE_GITHUB_TOKEN is not set. Run: export DIFY_ENTERPRISE_GITHUB_TOKEN=ghp_xxx)
endif
ifndef DIFY_ENTERPRISE_FRONTEND_GITHUB_TOKEN
	$(error DIFY_ENTERPRISE_FRONTEND_GITHUB_TOKEN is not set. Run: export DIFY_ENTERPRISE_FRONTEND_GITHUB_TOKEN=ghp_xxx)
endif

run: check-tokens ## Run the MCP server (requires GitHub tokens)
	uv run $(APP_NAME)

run-debug: check-tokens ## Run with debug logging
	HELM_MCP_LOG_LEVEL=DEBUG uv run $(APP_NAME)

# ============================================================================
# Building
# ============================================================================

build: ## Build the package
	uv build

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Build Docker image
	./scripts/docker-build.sh

docker-run: ## Run Docker container
	docker run --rm -it \
		-e HELM_MCP_GITHUB_TOKEN \
		-v $(PWD)/config:/app/config:ro \
		$(DOCKER_IMAGE):latest

docker-push: ## Push Docker image to registry
	./scripts/docker-push.sh

# ============================================================================
# Release
# ============================================================================

version: ## Show current version
	@echo $(VERSION)

tag: ## Create git tag for current version
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	git push origin v$(VERSION)

# ============================================================================
# Utilities
# ============================================================================

tree: ## Show project structure
	@tree -I '__pycache__|*.egg-info|.venv|.git|.mypy_cache|.ruff_cache|htmlcov' -a

loc: ## Count lines of code
	@find src -name '*.py' | xargs wc -l | tail -1

deps: ## Show dependency tree
	uv tree

update: ## Update dependencies
	uv lock --upgrade
	uv sync

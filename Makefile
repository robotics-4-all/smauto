COMPOSE = docker compose -f docker/docker-compose.yml

API_PORT  ?= 8080
LSP_PORT  ?= 2087
API_KEY   ?=
LOG_LEVEL ?= INFO

export API_PORT LSP_PORT API_KEY LOG_LEVEL

.DEFAULT_GOAL := help

.PHONY: help install install-dev lint format test test-cov validate ci \
        build rebuild up down restart logs shell clean

# ── Development ────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install package
	pip install .

install-dev: ## Install in editable mode with dev + test extras
	pip install -e ".[dev,test]"

lint: ## Run linter and format check
	ruff check .
	ruff format --check .

format: ## Auto-format code
	ruff check --fix .
	ruff format .

test: ## Run tests
	python -m pytest || test $$? -eq 5

test-cov: ## Run tests with coverage report
	python -m pytest --cov=smauto --cov-report=term-missing

validate: ## Validate all example models
	bash scripts/run_all_validations.sh

ci: lint validate test ## Run full CI pipeline (lint + validate + test)

# ── Docker ─────────────────────────────────────────────────────

build: ## Build Docker image
	$(COMPOSE) build

rebuild: ## Build Docker image (no cache)
	$(COMPOSE) build --no-cache

up: ## Start services (detached)
	$(COMPOSE) up -d

down: ## Stop services
	$(COMPOSE) down

restart: ## Restart services
	$(COMPOSE) restart

logs: ## Tail service logs
	$(COMPOSE) logs -f

shell: ## Open a shell in the running container
	$(COMPOSE) exec smauto /bin/bash

clean: ## Stop services and remove images + volumes
	$(COMPOSE) down --rmi all --volumes

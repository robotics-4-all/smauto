COMPOSE = docker compose -f docker/docker-compose.yml

API_PORT ?= 8080
LSP_PORT ?= 2087
API_KEY ?=
LOG_LEVEL ?= INFO

export API_PORT LSP_PORT API_KEY LOG_LEVEL

.PHONY: lint validate ci build rebuild up down restart logs shell clean

# ── Development ────────────────────────────────────────────────

lint:
	ruff check .
	ruff format --check .

validate:
	bash scripts/run_all_validations.sh

ci: lint validate

# ── Docker ─────────────────────────────────────────────────────

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

shell:
	$(COMPOSE) exec smauto /bin/bash

clean:
	$(COMPOSE) down --rmi all --volumes

# Deployment Guide

## Docker

SmAuto ships with a Docker image that bundles [tx-lsp](https://github.com/robotics-4-all/tx-lsp), a generic Language Server for textX-based DSLs. The container exposes:

- **REST API** on port 8080 (HTTP)
- **LSP Server** on port 2087 (TCP)

The build requires SSH agent forwarding to clone the tx-lsp repository.

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make build` | Build Docker image (requires SSH key for tx-lsp) |
| `make rebuild` | Rebuild from scratch (no cache) |
| `make up` | Start services via docker compose |
| `make down` | Stop and remove containers |
| `make restart` | Restart services |
| `make logs` | Tail container logs |
| `make shell` | Open a shell in the running container |
| `make clean` | Stop, remove containers and images |
| `make lint` | Run `ruff check` + `ruff format --check` |
| `make validate` | Run all validation scripts (model + entity gen + automations gen) |
| `make ci` | Run lint + validate (mirrors CI pipeline) |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8080` | REST API port |
| `LSP_PORT` | `2087` | LSP server port |
| `API_KEY` | — | Enables API key authentication via `X-API-Key` header |

```bash
make up                              # Default ports
make up API_PORT=9090 LSP_PORT=3000  # Custom ports
make up API_KEY=mysecret             # With authentication
```

## REST API

### Public Endpoints

These endpoints do not require authentication.

**Health check:**

```bash
curl http://localhost:8080/health
```

**Language info:**

```bash
curl http://localhost:8080/info
```

Returns language name, version, and supported file extensions.

**Capabilities:**

```bash
curl http://localhost:8080/capabilities
```

Returns supported features (validation, completion, hover, generation) and available generation targets.

**Keywords:**

```bash
curl http://localhost:8080/keywords
```

Returns DSL keyword list extracted from the grammar.

### Protected Endpoints

When `API_KEY` is set, these endpoints require the `X-API-Key` header.

**Validate a model file:**

```bash
curl -X POST http://localhost:8080/validate/file \
  -F "file=@model.auto"
```

**Validate from source:**

```bash
curl -X POST http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"source": "Broker<MQTT> b\n  host: \"localhost\"\n  port: 1883\n  auth:\n    username: \"\"\n    password: \"\"\nend"}'
```

**Generate automations:**

```bash
curl -X POST "http://localhost:8080/generate/file?target=automations" \
  -F "file=@model.auto"
```

**Generate virtual entities:**

```bash
curl -X POST "http://localhost:8080/generate/file?target=ventities" \
  -F "file=@model.auto"
```

**Generate merged virtual entities:**

```bash
curl -X POST "http://localhost:8080/generate/file?target=ventities_merged" \
  -F "file=@model.auto"
```

**Completions:**

```bash
curl -X POST http://localhost:8080/complete \
  -H "Content-Type: application/json" \
  -d '{"source": "Broker", "position": {"line": 0, "character": 6}}'
```

**Hover:**

```bash
curl -X POST http://localhost:8080/hover \
  -H "Content-Type: application/json" \
  -d '{"source": "Broker<MQTT> b\n  host: \"localhost\"\n  port: 1883\n  auth:\n    username: \"\"\n    password: \"\"\nend", "position": {"line": 0, "character": 0}}'
```

### Authentication

When `API_KEY` is configured, add the header to protected requests:

```bash
curl -X POST http://localhost:8080/validate/file \
  -H "X-API-Key: mysecret" \
  -F "file=@model.auto"
```

## CI Pipeline

GitHub Actions runs on push and pull requests to `main` and `devel`:

1. **Lint** — `ruff check .` + `ruff format --check .`
2. **Validate** — Runs all validation scripts against the 8 example models (model parsing, entity generation, automations generation)

Deploy step runs on push to `main` only (SSH-based deployment).

Run the same checks locally:

```bash
make ci
```

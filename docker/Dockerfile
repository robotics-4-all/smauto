FROM python:3.11-slim

WORKDIR /app

# Install git + openssh-client (needed to clone tx-lsp via SSH)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git openssh-client && \
    rm -rf /var/lib/apt/lists/*

# Install SmAuto DSL (makes it discoverable by textX)
COPY . /app/smauto
RUN pip install --no-cache-dir /app/smauto

# Install tx-lsp with REST API support from GitHub (private repo)
# Uses SSH agent forwarding via BuildKit: --ssh default
RUN mkdir -p -m 0700 ~/.ssh && \
    ssh-keyscan github.com >> ~/.ssh/known_hosts
RUN --mount=type=ssh pip install --no-cache-dir \
    "tx-lsp[api] @ git+ssh://git@github.com/robotics-4-all/tx-lsp.git"

# Entrypoint script runs both LSP (TCP) and REST API
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# LSP (TCP): 2087, REST API: 8080
EXPOSE 2087 8080

ENV TX_LSP_API_PORT=8080 \
    TX_LSP_LSP_PORT=2087 \
    TX_LSP_HOST=0.0.0.0 \
    TX_LSP_LOG_LEVEL=INFO

ENTRYPOINT ["/app/entrypoint.sh"]

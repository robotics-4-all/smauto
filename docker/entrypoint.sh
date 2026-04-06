#!/bin/sh
set -e

EXTRA_PATTERN="--extra-pattern *.auto=smauto"
LOG_LEVEL="--log-level ${TX_LSP_LOG_LEVEL:-INFO}"
HOST="${TX_LSP_HOST:-0.0.0.0}"

API_KEY_ARG=""
if [ -n "$TX_LSP_API_KEY" ]; then
    API_KEY_ARG="--api-key $TX_LSP_API_KEY"
fi

# Start LSP server (TCP) in background
tx-lsp --tcp --host "$HOST" --port "${TX_LSP_LSP_PORT:-2087}" \
    $EXTRA_PATTERN $LOG_LEVEL &

tx-lsp --ws --host "$HOST" --port "${TX_LSP_WS_PORT:-2088}" &

exec tx-lsp --api --host "$HOST" --api-port "${TX_LSP_API_PORT:-8080}" \
    $EXTRA_PATTERN $LOG_LEVEL $API_KEY_ARG

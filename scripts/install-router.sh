#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${HOME:?HOME is required}/.local/bin"
CONFIG_DIR="$HOME/.config/amori-ai"

mkdir -p "$BIN_DIR" "$CONFIG_DIR"
ln -sfn "$REPO/scripts/amori-ai" "$BIN_DIR/amori-ai"
ln -sfn "$REPO/scripts/amori-request" "$BIN_DIR/amori-request"
ln -sfn "$REPO/scripts/amori-hermes" "$BIN_DIR/amori-hermes"
ln -sfn "$REPO/scripts/amori-gateway-worker" "$BIN_DIR/amori-gateway-worker"
ln -sfn "$REPO/scripts/amori-mcp-remote" "$BIN_DIR/amori-mcp-remote"
ln -sfn "$REPO/scripts/claude-amori" "$BIN_DIR/claude-amori"

if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
  cp "$REPO/router/config.example.json" "$CONFIG_DIR/config.json"
  echo "Created $CONFIG_DIR/config.json"
else
  echo "Kept existing $CONFIG_DIR/config.json"
fi

echo "Installed Amori router, request client, Hermes wrapper, worker, and MCP bridge"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "Add to ~/.zshrc: export PATH=\"$BIN_DIR:\$PATH\""
fi
echo "Check: amori-ai --doctor"

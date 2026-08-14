#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${HOME:?HOME is required}/.local/bin"
CONFIG_DIR="$HOME/.config/amori-ai"

mkdir -p "$BIN_DIR" "$CONFIG_DIR"
ln -sfn "$REPO/scripts/amori-ai" "$BIN_DIR/amori-ai"

if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
  cp "$REPO/router/config.example.json" "$CONFIG_DIR/config.json"
  echo "Created $CONFIG_DIR/config.json"
else
  echo "Kept existing $CONFIG_DIR/config.json"
fi

echo "Installed $BIN_DIR/amori-ai"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "Add to ~/.zshrc: export PATH=\"$BIN_DIR:\$PATH\""
fi
echo "Check: amori-ai --doctor"

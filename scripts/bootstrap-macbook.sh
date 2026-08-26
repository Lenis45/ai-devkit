#!/usr/bin/env bash
# Local-first Amori tooling for the MacBook. Keeps provider credentials outside git.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$HOME/.local/bin"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs"

say() { printf '==> %s\n' "$1"; }

mkdir -p "$BIN_DIR" "$LAUNCH_DIR" "$LOG_DIR" "$HOME/.config/amori"
export PATH="$BIN_DIR:$HOME/.hermes/bin:/opt/homebrew/bin:$PATH"

if [[ ! -x "$BIN_DIR/codex" ]]; then
  CODEX_APP="/Applications/ChatGPT.app/Contents/Resources/codex"
  [[ -x "$CODEX_APP" ]] || { echo "Codex binary not found in ChatGPT.app" >&2; exit 2; }
  ln -sfn "$CODEX_APP" "$BIN_DIR/codex"
fi

if ! ollama list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -Fxq 'qwen3:1.7b'; then
  say "Installing the lightweight local routing model"
  ollama pull qwen3:1.7b
fi

if ! command -v opencode >/dev/null 2>&1; then
  say "Installing OpenCode from its Homebrew tap"
  /opt/homebrew/bin/brew tap anomalyco/tap
  /opt/homebrew/bin/brew install anomalyco/tap/opencode
fi

if ! /opt/homebrew/bin/brew list privoxy >/dev/null 2>&1; then
  say "Installing the local HTTP proxy bridge for subscription CLIs"
  /opt/homebrew/bin/brew install privoxy
fi

if ! /opt/homebrew/bin/brew list proxychains-ng >/dev/null 2>&1; then
  say "Installing the forced SOCKS route for Claude Code"
  HTTP_PROXY=http://127.0.0.1:18112 \
    HTTPS_PROXY=http://127.0.0.1:18112 \
    /opt/homebrew/bin/brew install proxychains-ng
fi

if [[ ! -x /opt/homebrew/bin/claude ]]; then
  say "Installing Claude Code CLI"
  /opt/homebrew/bin/npm install -g @anthropic-ai/claude-code
fi

if ! command -v hermes >/dev/null 2>&1; then
  say "Installing Hermes from the official repository"
  mkdir -p "$HOME/.hermes"
  if [[ ! -d "$HOME/.hermes/hermes-agent/.git" ]]; then
    git clone --depth 1 --filter=blob:none https://github.com/NousResearch/hermes-agent.git "$HOME/.hermes/hermes-agent"
  fi
  bash "$HOME/.hermes/hermes-agent/scripts/install.sh" \
    --skip-setup --skip-browser --skip-computer-use --non-interactive
fi

"$REPO/scripts/install-router.sh"
"$REPO/scripts/sync-skills.sh"
python3 "$REPO/scripts/configure-macbook.py" --apply --repo "$REPO"

HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
if [[ -x "$HERMES_PY" ]]; then
  "$HERMES_PY" "$REPO/scripts/configure-hermes-local.py" \
    --apply --model qwen3.5:9b-mlx --context-length 65536
fi

PATH_LINE='export PATH="$HOME/.local/bin:$HOME/.hermes/bin:/opt/homebrew/bin:$PATH"'
if ! grep -Fq "$PATH_LINE" "$HOME/.zprofile" 2>/dev/null; then
  printf '\n# Amori local agent tools\n%s\n' "$PATH_LINE" >> "$HOME/.zprofile"
fi

if [[ -f "$HOME/.config/amori/broker_token" && -f "$HOME/.ssh/tailnet_admin_ed25519" ]]; then
  cp "$REPO/deploy/privoxy/macbook.conf" "$HOME/.config/amori/privoxy.conf"
  cp "$REPO/deploy/proxychains/macbook.conf" "$HOME/.config/amori/proxychains.conf"
  cp "$REPO/deploy/launchd/ai.macbook-broker-tunnel.plist" "$LAUNCH_DIR/"
  cp "$REPO/deploy/launchd/ai.macbook-subscription-proxy.plist" "$LAUNCH_DIR/"
  cp "$REPO/deploy/launchd/ai.gateway-worker.plist" "$LAUNCH_DIR/"
  chmod 600 "$HOME/.config/amori/broker_token"
  for label in ai.macbook-broker-tunnel ai.macbook-subscription-proxy ai.gateway-worker; do
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$LAUNCH_DIR/$label.plist"
  done
  codex mcp remove amori >/dev/null 2>&1 || true
  codex mcp add amori -- "$BIN_DIR/amori-mcp-remote"
  hermes mcp remove amori >/dev/null 2>&1 || true
  printf 'y\n' | hermes mcp add amori \
    --command "$BIN_DIR/amori-mcp-remote" --connect-timeout 30
else
  say "Broker token or SSH key is absent; tunnel and worker were not started"
fi

say "MacBook tooling configured"
"$BIN_DIR/amori-ai" --doctor

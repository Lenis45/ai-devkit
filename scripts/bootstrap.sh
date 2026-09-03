#!/usr/bin/env bash
# Разворачивает единую AI-конфигурацию на macOS (например, на Mac mini).
# Идемпотентен: можно запускать повторно. Секреты не трогает — их вводишь сам.
#
#   git clone <repo-url> ~/ai-devkit && cd ~/ai-devkit && ./scripts/bootstrap.sh
#
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
say() { printf '\033[1;36m==>\033[0m %s\n' "$1"; }

# --- 1. Единый свод правил → симлинки во все три агента --------------------
link() { # link <target> <linkpath>
  local target="$1" link="$2"
  mkdir -p "$(dirname "$link")"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    say "бэкап существующего $link → $link.bak"
    mv "$link" "$link.bak"
  fi
  ln -sfn "$target" "$link"
  say "симлинк: $link → $target"
}
say "Подключаю AGENTS.md ко всем агентам…"
link "$REPO/AGENTS.md" "$HOME/.claude/CLAUDE.md"
link "$REPO/AGENTS.md" "$HOME/.codex/AGENTS.md"
link "$REPO/AGENTS.md" "$HOME/.config/opencode/AGENTS.md"

# --- 2. Конфиги ------------------------------------------------------------
say "Ставлю конфиги (без секретов)…"
mkdir -p "$HOME/.config/opencode"
OPENCODE_CONFIG="$HOME/.config/opencode/opencode.jsonc"
if [ -f "$OPENCODE_CONFIG" ]; then
  cp -f "$OPENCODE_CONFIG" "$OPENCODE_CONFIG.bak"
fi
if [ -f "$HOME/.config/opencode/opencode.json" ]; then
  cp -f "$HOME/.config/opencode/opencode.json" "$HOME/.config/opencode/opencode.json.bak"
  rm -f "$HOME/.config/opencode/opencode.json"
fi
cp -f "$REPO/opencode/opencode.json" "$OPENCODE_CONFIG"
cp -f "$REPO/opencode/skill-filter.jsonc" "$HOME/.config/opencode/skill-filter.jsonc"
mkdir -p "$HOME/.config/opencode/plugins"
cp -f "$REPO/opencode/plugins/amori-gateway.js" "$HOME/.config/opencode/plugins/amori-gateway.js"
mkdir -p "$HOME/.claude"
# settings.json Claude Code не перезаписываем силой — только если его нет
[ -f "$HOME/.claude/settings.json" ] || cp "$REPO/claude-code/settings.json" "$HOME/.claude/settings.json"

# --- 3. Shared skills ------------------------------------------------------
say "Синхронизирую shared skills…"
"$REPO/scripts/sync-skills.sh"

# --- 4. Единая точка входа и cost-aware routing ---------------------------
say "Устанавливаю amori-ai router…"
"$REPO/scripts/install-router.sh"

# --- 5. Локальные модели (Ollama) -----------------------------------------
if command -v ollama >/dev/null 2>&1; then
  say "Качаю локальные модели (по очереди, ~6 ГБ суммарно)…"
  ollama pull qwen3:1.7b
  ollama pull qwen3-vl:2b
  ollama pull qwen3:4b
  ollama create amori-hermes:4b -f "$REPO/models/Modelfile.hermes"
else
  say "ollama не найден — пропускаю модели. Установи: brew install ollama"
fi

# --- 6. MCP для Claude Code (без auth) -------------------------------------
if command -v claude >/dev/null 2>&1; then
  say "Добавляю MCP в Claude Code…"
  claude mcp add -s user context7 -- npx -y @upstash/context7-mcp 2>/dev/null || true
  claude mcp add -s user sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking 2>/dev/null || true
  claude mcp add -s user playwright -- npx -y @playwright/mcp@latest 2>/dev/null || true
  # GitHub MCP — если gh залогинен, берём токен автоматически
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    GHT="$(gh auth token 2>/dev/null)"
    [ -n "$GHT" ] && claude mcp add -s user --transport http github https://api.githubcopilot.com/mcp \
      --header "Authorization: Bearer $GHT" 2>/dev/null || true
    say "GitHub MCP добавлен с токеном gh."
  else
    say "gh не залогинен — GitHub MCP пропущен. Позже: gh auth login, затем перезапусти bootstrap."
  fi
else
  say "claude CLI не найден — пропускаю MCP."
fi

say "Готово. Проверь: amori-ai --doctor ; ollama list ; claude mcp list ; opencode mcp list"

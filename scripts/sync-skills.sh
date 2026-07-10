#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${HOME:?HOME is required}"
SOURCE="$REPO/skills"
SHARED_DIR="${SHARED_DIR:-$HOME_DIR/.agents/skills}"

TARGETS=(
  "$HOME_DIR/.codex/skills"
  "$HOME_DIR/.claude/skills"
  "$HOME_DIR/.config/opencode/skills"
)

copy_skills() {
  local source="$1"
  local target="$2"
  if [[ ! -d "$source" ]]; then
    return 0
  fi
  mkdir -p "$target"
  rsync -a \
    --exclude '.DS_Store' \
    --exclude '.system/' \
    --exclude '__pycache__/' \
    "$source"/ "$target"/
}

validate_skill() {
  local file="$1"
  local dirname name description
  dirname="$(basename "$(dirname "$file")")"
  name="$(awk -F': *' '$1 == "name" {print $2; exit}' "$file" | tr -d '"' || true)"
  description="$(awk -F': *' '$1 == "description" {print $2; exit}' "$file" || true)"

  if [[ -z "$name" || -z "$description" ]]; then
    echo "Invalid skill frontmatter: $file" >&2
    return 1
  fi
  if [[ "$name" != "$dirname" ]]; then
    echo "Skill name/folder mismatch: $file (name=$name folder=$dirname)" >&2
    return 1
  fi
  if [[ ! "$name" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    echo "Skill name must be lowercase kebab-case: $file (name=$name)" >&2
    return 1
  fi
}

main() {
  if [[ ! -d "$SOURCE" ]]; then
    echo "No skills directory found: $SOURCE" >&2
    exit 1
  fi

  while IFS= read -r -d '' skill; do
    validate_skill "$skill"
  done < <(find "$SOURCE" -maxdepth 2 -name SKILL.md -print0 | sort -z)

  copy_skills "$SOURCE" "$SHARED_DIR"

  for target in "${TARGETS[@]}"; do
    copy_skills "$SHARED_DIR" "$target"
  done

  echo "Shared skills synced."
  echo "Source: $SOURCE ($(find "$SOURCE" -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ') skills)"
  echo "Shared: $SHARED_DIR ($(find "$SHARED_DIR" -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ') skills)"
  for target in "${TARGETS[@]}"; do
    echo "Target: $target ($(find "$target" -maxdepth 2 -name SKILL.md | wc -l | tr -d ' ') skills)"
  done
  echo "Hermes reads shared skills through skills.external_dirs in ~/.hermes/config.yaml."
}

main "$@"

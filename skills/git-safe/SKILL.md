---
name: git-safe
description: Safe, conventional git workflow for any repository. Use this whenever you are about to commit, branch, merge, rebase, push, or otherwise change git history or remote state — to avoid destructive mistakes and keep a clean, reviewable history.
metadata:
  short-description: Safe, conventional git workflow
---

# Safe git workflow

Principles for changing a repository without breaking it or losing work.

## Before changing anything
- `git status` and `git diff` first — know what's staged/unstaged and on which branch.
- Never work directly on `main`/`master` for non-trivial changes. Create a branch:
  `git switch -c feature/<short-name>`.
- If `git status` shows unexpected changes you didn't make, STOP and ask — don't blow them away.

## Commits
- Stage intentionally (`git add -p` for partial), not `git add -A` blindly.
- **Conventional Commits**: `type(scope): summary` — `feat`, `fix`, `docs`, `refactor`,
  `test`, `chore`, `perf`. Imperative mood, ≤72-char subject, body explains *why*.
- One logical change per commit. Don't mix refactor + behavior change.

## Never (without explicit user confirmation)
- `git push --force` / `--force-with-lease` to a shared branch (esp. `main`).
- `git reset --hard`, `git clean -fd`, `git checkout .` when uncommitted work exists.
- `git rebase` / history rewrite on a branch others may have pulled.
- Committing secrets/`.env`/keys — check the diff; respect `.gitignore`.

## Recovery
- `git reflog` finds "lost" commits after a bad reset/rebase.
- `git stash` to park work before switching context; `git stash pop` to restore.

## Pushing / PRs
- Push the feature branch, open a PR; never push straight to `main` on shared repos.
- Use `gh pr create` for GitHub. Keep PRs small and focused.

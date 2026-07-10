---
name: commit-pr
description: How to craft clean commits and pull requests — focused changes, conventional messages that explain why, and reviewable PRs. Use this whenever you are about to commit, write a commit message, open or describe a pull request, or split work into reviewable pieces.
metadata:
  short-description: Clean commits and reviewable pull requests
---

# Commits & pull requests

Goal: a history that explains *why*, and PRs a reviewer can actually review. See also `git-safe`.

## Commits
- **One logical change per commit.** Don't bundle a refactor, a feature, and a typo fix together.
- Stage deliberately (`git add -p`), review `git diff --staged` before committing. Never commit
  `.env`, secrets, build artifacts, or debug prints — check the diff.
- **Conventional Commits**: `type(scope): summary` — `feat`, `fix`, `docs`, `refactor`, `test`,
  `chore`, `perf`, `build`, `ci`. Imperative mood, ≤72-char subject.
- The **body explains *why*** (the problem, the trade-off), not *what* (the diff already shows what).
  Reference issues (`Fixes #123`).
- Only commit when asked, or when it's the natural unit of finished work. Don't auto-commit
  mid-task unless told to.

## Pull requests
- **Small and focused** beats big and comprehensive. A 200-line PR gets a real review; a 2000-line
  one gets rubber-stamped. Split large work into a stacked/sequential series.
- PR description: **what changed, why, how to test, and risks.** Link the issue. Call out anything
  needing special attention (migrations, config, breaking changes).
- Self-review the diff first — you'll catch leftover debug code and accidental changes.
- Ensure CI/tests pass and the branch is current with the base before requesting review.
- Use `gh pr create`. Never push straight to `main` on a shared repo; branch + PR.

## Anti-patterns
- "fix", "wip", "stuff", "address comments" as the whole message — useless in `git log`/`blame`.
- A PR that does five unrelated things — reviewers can't reason about it, and it can't be reverted
  cleanly.
- Force-pushing a shared branch to "tidy up" mid-review (breaks the reviewer's diff). See `git-safe`.

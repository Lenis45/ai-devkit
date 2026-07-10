---
name: code-review
description: A disciplined method for reviewing a code change (diff, PR, or branch) for correctness, security, and maintainability before it lands. Use this whenever you are asked to review code, audit a diff/PR, give feedback on someone's changes, or check your own work before committing.
metadata:
  short-description: Review a diff for correctness, security, maintainability
---

# Code review

Goal: catch real defects before merge, ranked by impact — not style nitpicks.

> Claude Code has a stronger built-in `/code-review` (multi-agent, runs on the branch/PR).
> Prefer it when available; this skill is the portable method for Codex / Hermes and for
> reviewing your own work inline.

## Scope the review first
- Look at the **diff**, not the whole repo: `git diff main...HEAD` (or the PR). Know what changed.
- Read the change's intent (PR description / commit messages). Review against *that* goal.
- Big diff → review by logical unit, not top-to-bottom.

## What to check, in priority order
1. **Correctness** — does it do what it claims? Edge cases, off-by-one, null/None, empty input,
   error paths, concurrency/races, wrong default. Trace the critical path by hand.
2. **Security** — untrusted input validated? SQL/command/path injection, authz checks, secrets in
   code/logs, unsafe deserialization, SSRF. Flag anything touching auth, money, or PII.
3. **Tests** — does the change have tests that would fail without it? Are failure paths covered?
4. **Interface & data** — API/DB-schema/contract changes that break callers or migrations.
5. **Maintainability** — naming, duplication, dead code, leaky abstractions, needless complexity.
6. **Style** — last. Defer to the formatter/linter; don't hand-review whitespace.

## Giving feedback
- **Severity-tag** each comment: blocker / should-fix / nit. Don't drown a real bug in nits.
- Be specific and actionable: cite `file:line`, explain *why* it's wrong, suggest the fix.
- Distinguish "this is a bug" from "I'd prefer". Acknowledge what's done well.
- If you can't verify a claim (no repro, missing context), say so — don't assert.

## Anti-patterns
- Rubber-stamping ("LGTM") without reading the logic.
- Rewriting to personal taste instead of reviewing the change on its own terms.
- Blocking on style while missing a security hole.

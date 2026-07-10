---
name: refactor
description: How to restructure code safely without changing its behavior — improving clarity, removing duplication, and reducing complexity under the protection of tests. Use this whenever you are asked to refactor, clean up, simplify, or reduce technical debt in existing code.
metadata:
  short-description: Restructure code safely without changing behavior
---

# Refactoring

Definition: change the structure, **not** the behavior. If outputs change, it's a rewrite — say so.

## Preconditions
- **Tests are your safety net.** Ensure the area is covered and green BEFORE you start. No coverage?
  Add characterization tests that pin current behavior first, then refactor.
- Refactor **separately from behavior changes.** Never mix "clean up" and "fix bug / add feature"
  in one commit — it makes both un-reviewable and un-revertable.

## Method
1. Identify ONE concrete smell: duplication, long function, deep nesting, unclear names, primitive
   obsession, a leaky/God abstraction, dead code.
2. Make the **smallest** structural change that addresses it (extract function, rename, introduce a
   variable, collapse a conditional, remove dead code).
3. **Run the tests.** Green → commit. Red → revert and take a smaller step.
4. Repeat. Many tiny verified steps beat one big risky rewrite.

## What good looks like
- Names reveal intent; no comment needed to explain *what* (only *why*).
- No duplicated logic (DRY) — but don't over-abstract two incidental look-alikes (premature DRY
  couples unrelated code). Rule of three.
- Shallow nesting (early returns/guard clauses), small focused units, clear boundaries.
- Behavior identical: same inputs → same outputs, same side effects, same public API.

## Anti-patterns
- Refactoring without tests ("I'll be careful") — you'll silently change behavior.
- A giant "cleanup" commit touching 40 files — impossible to review or bisect.
- Abstracting for a future that may never come (YAGNI); adding indirection that hides logic.
- Renaming/reformatting an entire file alongside a real change, burying the signal in noise.

---
name: testing
description: How to write and run tests that actually catch regressions — choosing what to test, structuring tests well, and verifying changes. Use this whenever you add or change behavior, fix a bug, or are asked to write/improve/run tests.
metadata:
  short-description: Write tests that catch real regressions
---

# Testing

Goal: tests that fail when behavior breaks and pass when it's correct — nothing more.

## Before writing
- **Run the existing suite first** to know the baseline (what's green) and the test command.
- Match the project's framework and conventions — find a neighboring test and mirror its style.
- For a **bug fix**: write the failing test FIRST (it reproduces the bug), then fix until green.
  This proves the bug existed and that you fixed it.

## What to test
- **Behavior, not implementation.** Assert on observable outputs/effects, not private internals —
  so refactors don't break tests.
- **The contract + the edges**: happy path, boundaries (empty, zero, one, max), invalid input,
  and error/failure paths. Bugs hide at the edges.
- Prioritize by risk: core logic, money/auth/data paths, anything previously broken.
- Don't test the framework, the language, or trivial getters.

## Structure
- **Arrange–Act–Assert**, one logical behavior per test. A failing test name should tell you what
  broke without reading the body — name them `does_X_when_Y`.
- **Deterministic & isolated**: no shared mutable state, no ordering dependence, no real network/
  clock/random — inject or fake them. A flaky test is worse than no test.
- Mock only at real boundaries (network, DB, time). Over-mocking tests the mocks, not the code.

## Verify
- Run the **specific test** you wrote, watch it fail for the right reason, then make it pass.
- Run the **full suite** before declaring done — confirm you didn't break neighbors.
- Don't chase 100% coverage; cover the behavior that matters. Report what you ran and the result.

## Anti-patterns
- Asserting nothing (or only that it "doesn't throw").
- Tests coupled to internals that break on every refactor.
- Marking a test skipped/xfail to go green without a tracked reason.

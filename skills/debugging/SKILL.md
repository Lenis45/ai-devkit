---
name: debugging
description: A systematic method for diagnosing bugs, failures, and unexpected behavior instead of guessing. Use this whenever code errors out, a test fails, something "doesn't work", behaves unexpectedly, or a previous fix attempt didn't resolve the issue — to find the true root cause before changing code.
metadata:
  short-description: Systematic root-cause debugging
---

# Systematic debugging

Don't guess-and-change. Find the root cause, then fix once.

## Method
1. **Reproduce** reliably. Get the exact command, input, and full error text/stack. A bug you
   can't reproduce, you can't confirm fixed.
2. **Read the actual error** — the message, file, and line. Don't skim. The stack trace
   usually names the failing call.
3. **Isolate**. Narrow the scope: binary-search the input/code, comment out, add a minimal
   repro. Identify the smallest thing that triggers it.
4. **Form ONE hypothesis** about the root cause and predict what you'd observe if it's true.
5. **Test the hypothesis** with evidence — logging, a probe, a unit check, inspecting state —
   not by rewriting code hopefully. Confirm or reject before editing.
6. **Fix the cause, not the symptom.** Then verify the original repro now passes AND you
   didn't break neighbors (run the tests).

## Tactics
- Check the boring things first: wrong path/port, stale process/cache, env var unset,
  service down, typo, off-by-one, null/None, IPv4-vs-`localhost`, timezone, encoding.
- "It worked before" → `git diff`/`git log` to see what changed; `git bisect` for regressions.
- Read the logs at the time of failure, not just the latest line.
- For flaky/intermittent issues, look for shared state, timing/races, resource exhaustion,
  external dependency hiccups (retry vs real failure).

## Anti-patterns
- Changing multiple things at once (you won't know what fixed it).
- "Fixing" by adding a try/except that hides the error.
- Declaring it fixed without reproducing the original failure and confirming it's gone.

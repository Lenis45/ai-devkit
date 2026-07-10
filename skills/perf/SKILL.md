---
name: perf
description: A measure-first method for diagnosing and fixing performance problems — profiling to find the real bottleneck before optimizing, then verifying the win. Use this whenever something is slow, you're asked to optimize/speed up code, reduce latency/memory/cost, or evaluate a performance trade-off.
metadata:
  short-description: Measure-first performance optimization
---

# Performance

Rule: **measure, don't guess.** The bottleneck is almost never where intuition says it is.

## Method
1. **Define the goal** in numbers: target latency / throughput / memory / cost, and the workload it
   applies to. "Faster" isn't a goal; "p95 < 200ms at 1k rps" is.
2. **Measure the baseline** under a realistic load. Without a number, you can't prove improvement.
3. **Profile to find the hot spot** — a profiler, timing, flame graph, query log. Optimize the
   part that dominates the time; ignore the rest (Amdahl's law).
4. **Fix the biggest bottleneck**, one change at a time.
5. **Re-measure.** Keep the change only if it actually helped and the result is still correct.
   Then re-profile — the bottleneck has moved.

## Where the wins usually are (check these first)
- **Algorithmic complexity** — an O(n²) loop or accidental quadratic beats any micro-tuning. Fix
  the big-O before tuning constants.
- **I/O and queries** — the classic **N+1 query**, missing index, full table scan, chatty network
  calls, unbatched requests. Usually the #1 culprit in app code.
- **Caching / memoization** of expensive repeated work — but watch invalidation and staleness.
- **Doing less** — avoid recomputation, lazy-load, paginate, stream instead of buffering, batch.
- **Concurrency / parallelism** where work is independent and the overhead pays off.

## Discipline
- **One variable at a time**, re-measure each — or you won't know what helped.
- Keep it **correct**: an optimization that changes results is a bug. Re-run the tests.
- **Don't micro-optimize cold paths.** Readability > nanoseconds outside the hot loop. Premature
  optimization adds complexity for no measured gain.
- State the trade-off (memory vs CPU, latency vs throughput, complexity vs speed) and the measured
  before/after numbers.

## Anti-patterns
- Optimizing without a profile ("this looks slow").
- Reporting a speedup with no baseline measurement.
- Rewriting hot code in a clever, unreadable way for a gain that doesn't matter at this scale.

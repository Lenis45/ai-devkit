---
name: web-research
description: Methodology for researching a topic from the web accurately — multi-source gathering, cross-checking, and cited synthesis. Use this whenever the user asks you to research, compare, fact-check, find current information, or produce a sourced answer about anything beyond your training data or that may have changed recently.
metadata:
  short-description: Accurate, cited web research
---

# Web research methodology

Goal: a correct, current, **cited** answer — not the first link's opinion.

## Process
1. **Clarify scope** if the question is ambiguous (budget, region, version, timeframe).
   Don't research the wrong thing.
2. **Search broadly, then narrow.** Run 2–4 varied queries (different angles/terms). For
   "current month"-sensitive topics, include the year.
3. **Prefer primary & authoritative sources**: official docs, standards bodies, vendor
   pages, peer-reviewed/maintained repos — over SEO blogs and content farms.
4. **Cross-check** any non-trivial claim against ≥2 independent sources. If they disagree,
   say so and explain which is more credible and why.
5. **Fetch the actual page** (don't rely only on the search snippet) when the detail matters.
6. **Recency check**: note the publish/update date; flag if information may be stale.

## Output
- Lead with the answer, then the supporting detail.
- **Cite sources** as markdown links. Separate verified facts from inference/opinion.
- State confidence and remaining uncertainty honestly — never fabricate a source or a number.

## Tools
- Use the agent's web search + fetch tools (e.g. `fetch:fetch` MCP, or built-in WebSearch/
  WebFetch). For deep multi-source reports, a dedicated research mode/skill if available.
- Use `memory:*` MCP to persist durable findings worth reusing across sessions.

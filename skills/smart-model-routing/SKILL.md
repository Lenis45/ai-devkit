---
name: smart-model-routing
description: Route requests between local Hermes/Ollama, Codex, and Claude Code while minimizing paid usage and preparing compact, high-quality handoffs.
---

# Smart Model Routing

Use this skill when a request may need another model, a coding agent, or a cost-aware handoff.

## Routing policy

- Use local Hermes/Ollama for short explanations, rewriting, summaries, and everyday questions.
- Use Codex for repository inspection, implementation, debugging, tests, browser QA, and git operations.
- Use Claude Code for architecture, requirements, product/system analysis, trade-offs, and deep review.
- Respect an explicit provider choice from the user.
- Never use a paid API fallback. Codex and Claude must run through their authenticated subscription CLIs.
- Do not modify files unless the user selected an action mode explicitly.

## Handoff packet

Do not forward the full conversation by default. Prepare only:

1. Objective and expected deliverable.
2. Relevant facts already verified.
3. Constraints and public/private boundaries.
4. Relevant file paths or URLs.
5. Acceptance checks.
6. At most three applicable shared skills.

Do not include secrets, unrelated history, repeated instructions, or speculative context.

## Commands

```bash
amori-ai --route-only "<request>"
amori-ai --explain "<request>"
amori-ai --to codex --act --cwd /path/to/repo "<request>"
amori-ai --to claude "<request>"
amori-ai --doctor
amori-ai --stats
```

If local Ollama is unavailable, use the deterministic route only for classification. A simple answer must fail clearly or be explicitly forced to a subscription CLI; it must not silently use OpenRouter or another paid API.

---
name: ui-design-research
description: Use only for explicit design-system exploration, palette or typography selection, UX-pattern comparison, chart guidance, or stack-specific interface research. This is a supplementary offline evidence tool for Impeccable, not the primary frontend workflow and not for routine UI edits.
---

# UI Design Research

Use the vendored UI/UX Pro Max catalog to retrieve focused, local recommendations before
committing to a visual system. It supplements `impeccable`; it does not compete with it.

## Priority

1. The user's explicit brief and the repository's existing design system.
2. Accessibility, platform conventions, and product requirements.
3. The `impeccable` workflow for implementation, critique, hardening, and visual QA.
4. Recommendations returned by this skill's local catalog.

Never replace an established product identity merely because a catalog match scores highly.
Treat every result as a candidate to evaluate against the actual audience and workflow.

## When To Use

- A new product or page needs a coherent design-system direction.
- The user asks to compare styles, palettes, typography, charts, or interaction patterns.
- A frontend decision needs stack-specific guidance for React, Next.js, Vue, SwiftUI,
  Flutter, Three.js, or another supported stack.
- `impeccable` has established the product mode and needs evidence for a narrow choice.

Do not activate for backend work, routine CSS fixes, pixel matching to a supplied reference,
or when the repository already defines the relevant tokens and component behavior.

## Tool

Resolve `<skill-dir>` from the loaded skill path. If the runtime does not expose it, use
`~/.agents/skills/ui-design-research`.

```bash
python3 <skill-dir>/vendor/scripts/search.py "<query>" --design-system -p "<project>"
python3 <skill-dir>/vendor/scripts/search.py "<query>" --domain ux
python3 <skill-dir>/vendor/scripts/search.py "<query>" --domain typography
python3 <skill-dir>/vendor/scripts/search.py "<query>" --stack react
```

Use one dominant intent and 2-5 meaningful terms. Retry once with a narrower query when the
result is off-topic. Do not send private project data: the search is local, but prompts and
persisted output may later enter project history.

Do not use `--persist` unless the user asks to create or update a durable design system.
Never use `--force` without explicit authorization. Do not install packages or modify system
configuration for this skill; the vendored search tool uses only Python's standard library.

## Handoff To Impeccable

Return a compact decision record:

- product mode and audience;
- selected direction and why it fits;
- rejected alternatives and why;
- semantic colors, typography roles, spacing/density, motion level;
- accessibility and stack constraints;
- catalog output clearly labeled as recommendation, not product truth.

Then continue through `impeccable` for implementation and bounded screenshot verification.

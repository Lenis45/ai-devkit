# MacBook OpenCode Verification

Verified on 2026-09-03: macOS 26.6.2, 16 GB RAM, OpenCode CLI 1.18.19,
Ollama 0.33.2. These are measured results, not guarantees for every task.

## Failures Found

- The active JSONC still selected the old `amori` agent and exposed unbounded
  Qwen models, despite a recently modified file timestamp.
- Qwen3 and Qwen3.5 returned reasoning-only responses through the tested
  OpenAI-compatible endpoint. `think:false` in that request did not disable it.
- OpenCode's context metadata did not set Ollama's runtime `num_ctx`.
  A 32K context loaded the 1.7B model as a 5.2 GB runtime.
- Concurrent Qwen 9B MLX work produced a Metal `Insufficient Memory` failure.
- Ponytail failed to load. The extra skills loader duplicated native discovery.
- The remote worker waited 20 seconds between process-completion checks.
- OpenCode image attachments were represented as Read-tool metadata and were
  not always forwarded as broker artifacts.

## Applied Design

- `ami-qwen3:1.7b-nothink` reuses existing weights, disables thinking in its
  template, and sets `num_ctx=8192`. Measured loaded size: 2.2 GB.
- One small runtime handles MacBook routing and simple answers. Complex work
  still delegates to subscription CLIs through Ami.
- `local-chat` is local-only; `local-deep` uses the installed Gemma separately.
- Provider requests have full/header/chunk timeouts. Broken or duplicate
  plugins are removed; native skills and MCP remain available.
- Worker subprocess pipes are drained while running. Completion is detected
  within 250 ms, cancellation checked every 2 seconds, heartbeat every 20.
- Attachment recovery reads only leading OpenCode metadata, never matching
  embedded commands inside document content.

## Live Checks

| Scenario | Result |
| --- | --- |
| Direct local chat, cold | Answer received, 16.7 seconds |
| Direct local chat, warm | Answer received, 9.5 seconds including CLI startup |
| Ami arithmetic request | Correct `102`, broker status `completed` |
| Worker execution after polling fix | About 0.6 seconds for the arithmetic request |
| Local Gemma chat | Correct `102`, 32.7 seconds on a cold run |
| TXT through OpenCode and broker | `ORCHID-742`, non-empty input artifact list |
| Screenshot through OpenCode and broker | Correct `Bun is not defined`, non-empty input artifact list |
| MCP | Amori, Context7, sequential-thinking connected |

The gateway tests above were claimed and completed by the MacBook worker.
The screenshot path includes upload and vision processing before request
execution, so worker duration is not total user-visible latency.

## Remaining Boundaries

- Restart the desktop app and use a new chat after a profile update; an old
  conversation may retain its previous model selection.
- The 1.7B model is intentionally limited to simple responses, not autonomous
  system changes or complex reasoning.
- Claude authentication was reported as `status unavailable`; this check does
  not establish a working Claude session. Codex login status was present, but
  a full subscription execution is a separate acceptance test.
- Voice input in the OpenCode desktop UI was not tested in this pass.
- No claim is made that VPN, sleep, or network transitions can never interrupt
  a connection. Existing route guard and launchd tunnel recovery remain active.

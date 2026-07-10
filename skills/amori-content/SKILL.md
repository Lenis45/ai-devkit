---
name: amori-content
description: Produce sales/marketing content for Amori (GPS pet collars) through the AI content factory — social posts (Telegram/VK), sales emails, ad creatives, and landing copy. Use this whenever the user wants to draft, generate, review, approve, or publish marketing/sales content, or asks for a post/email/ad/landing text for Amori.
metadata:
  short-description: Create & approve Amori sales content
---

# Amori content factory

Pipeline: **brief → text (copywriter) → visual brief + image prompt (designer) → review →
[your approval] → publish.** Everything lands in the dashboard (http://localhost:8099,
section «🏭 Контент-завод») and uses the `amori` MCP tools.

## Workflow
1. **Create** — `amori:create_content(brief, channel, kind)`.
   - `channel`: `telegram` | `vk` | `email` | `landing` | `ad`
   - `kind`: `post` | `email` | `ad_creative` | `landing`
   - Generates the text, a visual brief, and an auto-review; item becomes **pending**.
   - This spends LLM calls (~10–40s).
2. **Review** — `amori:list_content` to see pending items (id, channel, kind, preview).
3. **Approve & publish** — `amori:approve_content(id)`. ⚠️ This is an outward action
   (publishes to the channel if a real channel/token is configured; otherwise it is saved as
   "ready to publish"). **Confirm with the user before approving.**
   - Or `amori:reject_content(id)` to send it back.

## Notes
- Real image generation and live VK/TG publishing need external keys/tokens; without them the
  designer outputs a visual brief + prompt and publish is an honest "ready" stub.
- Brand voice: friendly, expert, no fluff; Russian for RU/CIS market.

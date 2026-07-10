---
name: amori-ops
description: Inspect and operate the Amori AI-infra system — the personal mini AI-team running on this Mac (Postgres/Docker, 10+ agents, dashboard, content factory). Use this whenever the user asks about system/agent status, health after a reboot, the queue, recent agent activity or reports, "how does Amori work / where do I look", or when you need to check the team's state before acting on it.
metadata:
  short-description: Inspect & operate the Amori AI-team system
---

# Amori AI-infra — operations

Amori is a personal "mini AI-team" on this Mac (`~/ai-infra`): Postgres + Qdrant + Redis in
Docker, ~16 agents (orchestrator/Emilia → content/dev/research/sales leads → workers), a
DB-backed task queue, a content factory, and a single report hub. Full guide:
`~/ai-infra/docs/HOW_IT_WORKS.md` (also at **http://localhost:8099/docs**).

## Surfaces
- **Dashboard (control panel)**: http://localhost:8099 — projects, content factory, kanban,
  reports feed, team hierarchy, per-agent settings.
- **Pixel office**: http://localhost:5070 — the team visualized by department.

## Use the `amori` MCP tools (fully-qualified names)
- `amori:system_status` — agents up/total, containers, LLM spend, active/failed tasks,
  pending content, heartbeats. **Start here** to check overall health.
- `amori:recent_reports` — latest agent reports (what the team just did).
- `amori:list_projects` / `amori:list_tasks` — project progress and the queue.
- `amori:list_content` — content-factory items and their statuses.
- `amori:sql_read(db, query)` — read-only analytics over `ops_db`/`customer_db` (SELECT only).

## Tips
- After a reboot, agents may have restarted once before Postgres was ready (KeepAlive recovers
  them). Confirm with `amori:system_status` (agents_up) and the heartbeats.
- To act on the team (start work, make content), use the **amori-project** / **amori-content** skills.
- Don't guess system state from memory — query `amori:system_status` first.

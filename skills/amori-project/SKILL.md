---
name: amori-project
description: Delegate a multi-step goal to the Amori AI-team — it decomposes the goal into tasks (content/research/dev/ops), assigns role-based workers with dependencies, and executes them on a queue. Use this whenever the user wants the AI-team to autonomously carry out a project or goal end-to-end, or to check a running project's progress.
metadata:
  short-description: Run & track an Amori AI-team project
---

# Amori AI-team projects

The project manager (Emilia) takes a goal, uses an LLM to split it into 3–6 concrete tasks
with roles (writer/designer/reviewer/researcher/dev/ops) and dependencies, and dispatches them
to workers via a DB queue. Dependent workers see upstream results (transitive). Results land in
the report hub + dashboard (http://localhost:8099, «🚀 Проекты» + «🗂 Доска задач»).

## Workflow
1. **Start** — `amori:new_project(goal)`. Returns the project id and the created task ids.
   ⚠️ Spends LLM calls; the team executes asynchronously.
2. **Track** — `amori:project_status(project_id)` for per-task status, or `amori:list_projects`
   for overall progress (done / active). `amori:list_tasks("running")` shows current work.
3. **Read results** — `amori:recent_reports` for what each worker produced.

## Tips
- Give a clear, outcome-oriented goal (e.g. "Подготовить 3 поста в Telegram про водозащиту
  ошейника и отредактировать их") — the PM decomposes it.
- Domains: content/marketing, research/analytics, code/dev, business-ops.
- A task taking ~2 min usually means a transient Groq SSL retry — normal.

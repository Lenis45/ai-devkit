# AI Devkit — единая конфигурация локальных AI-агентов на macOS

Единый источник правды для всех AI-агентов на моих машинах: **Claude Code**, **OpenAI Codex**
и **OpenCode**, плюс **локальные модели** через Ollama (MLX на Apple Silicon).

Цель: чтобы все агенты вели себя одинаково — **детально, честно, с самопроверкой, задавали
вопросы и спорили со мной, когда я не прав** — и чтобы эту настройку можно было развернуть на
любой машине (например, на Mac mini) одной командой.

## Что внутри

```
ai-devkit/
├── AGENTS.md                 # ★ единый свод правил поведения (симлинкуется во все агенты)
├── claude-code/
│   └── settings.json         # тема и базовые настройки Claude Code
├── codex/
│   └── config.example.toml   # включённые плагины Codex (без секретов)
├── opencode/
│   └── opencode.jsonc        # MCP-конфиг OpenCode (context7 + sequential-thinking)
├── models/
│   └── README.md             # какие локальные модели, размеры, честные оговорки
├── scripts/
│   └── bootstrap.sh          # развернуть всё на новой машине (идемпотентно)
└── README.md
```

`AGENTS.md` — сердце репозитория. `bootstrap.sh` симлинкует его сразу в три места:
`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.config/opencode/AGENTS.md`.
Правишь один файл — меняется поведение всех агентов.

## Что уже работает (проверено на этой машине: Apple M5, 16 ГБ)

| Компонент | Статус | Детали |
|-----------|--------|--------|
| Единый `AGENTS.md` | ✅ | Симлинкован в Claude Code, Codex, OpenCode |
| Локальная чат-модель | ✅ | `gemma4:12b-mlx` (7.7 ГБ) — скачана, `ollama list` видит |
| Локальный кодер | ✅ | `qwen3.5:9b-mlx` (8.9 ГБ) — скачан |
| Claude Code MCP | ✅ | context7, sequential-thinking, playwright (без auth) |
| OpenCode MCP | ✅ | context7 + sequential-thinking (уже были в конфиге) |
| Codex плагины | ✅ | browser, documents, pdf, spreadsheets, presentations, template-creator |
| GitHub MCP | ⚠️ | Требует токен — добавляется вручную (см. ниже) |

## Развернуть на другой машине (Mac mini)

```bash
git clone <this-repo-url> ~/ai-devkit
cd ~/ai-devkit
./scripts/bootstrap.sh
```

Скрипт: симлинкует правила во все агенты, ставит конфиги (без перезаписи секретов),
качает локальные модели, добавляет MCP в Claude Code. Существующие файлы бэкапит в `*.bak`.

## Локальные модели

Подробно — в [models/README.md](models/README.md). Коротко: `gemma4:12b-mlx` для чата,
`qwen3.5:9b-mlx` для кода. На 16 ГБ работают по очереди. Выделенный `qwen3-coder` (30B/19 ГБ)
в 16 ГБ **не помещается** — вернуться к нему при апгрейде RAM.

## MCP-серверы

Уже подключены (без авторизации): **context7** (свежая документация фреймворков),
**sequential-thinking** (структурное рассуждение), **playwright** (проверка UI в браузере).

GitHub MCP — самый полезный, но нужен токен:
```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp \
  --header "Authorization: Bearer <YOUR_GITHUB_TOKEN>"
```

## Безопасность

Секреты (`auth.json`, API-ключи, токены) **в репозиторий не попадают** — см. `.gitignore`.
Публикуются только конфиги и правила.

---

Правила поведения агентов — в [AGENTS.md](AGENTS.md). Это единственный файл, который
нужно править, чтобы изменить поведение всех агентов сразу.

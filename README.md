# AI Devkit — единая конфигурация локальных AI-агентов на macOS

Единый источник правды для **Claude Code**, **OpenAI Codex**, **OpenCode** и локальных моделей через Ollama (MLX на Apple Silicon).

Все агенты ведут себя одинаково: детально, честно, с самопроверкой, задают вопросы и спорят, когда пользователь не прав. Конфигурация развёртывается на любую машину одной командой.

---

## Архитектура

```
ai-devkit/
├── AGENTS.md                 # ★ канонические правила поведения (симлинкуется во все агенты)
├── claude-code/
│   └── settings.json         # тема и базовые настройки Claude Code
├── codex/
│   └── config.example.toml   # плагины Codex (без секретов)
├── opencode/
│   └── opencode.jsonc        # провайдеры, MCP, плагины OpenCode
├── models/
│   └── README.md             # локальные модели, размеры, честные оговорки
├── scripts/
│   └── bootstrap.sh          # идемпотентное развёртывание на новой машине
└── README.md
```

`AGENTS.md` — единственный файл правил. `bootstrap.sh` симлинкует его в:
- `~/.claude/CLAUDE.md`
- `~/.codex/AGENTS.md`
- `~/.config/opencode/AGENTS.md`

Правишь один файл — меняется поведение всех агентов.

---

## Текущее состояние (проверено на Apple M4, 16 ГБ)

| Компонент | Статус | Детали |
|-----------|--------|--------|
| Единый `AGENTS.md` | ✅ | Симлинкован в Claude Code, Codex, OpenCode |
| Локальная чат-модель | ✅ | `gemma4:12b-mlx` (7.7 ГБ) |
| Локальная код-модель | ✅ | `qwen3.5:9b-mlx` (8.9 ГБ) |
| **OpenCode плагины** | ✅ | `@dietrichgebert/ponytail` (v4.8.4), `opencode-skills-collection@latest` |
| **OpenCode навыки** | ✅ | `frontend-dev`, `fullstack-dev`, `shader-dev`, `ru-commit` + 6 ponytail-навыков |
| Claude Code MCP | ✅ | context7, sequential-thinking, playwright, github — все `Connected` |
| OpenCode MCP | ✅ | context7 + sequential-thinking |
| Codex плагины | ✅ | browser, chrome, computer-use, documents, pdf, spreadsheets, presentations, template-creator |
| GitHub MCP | ✅ | Hosted endpoint с токеном из `gh auth token` |

---

## Развёртывание на новой машине (Mac mini / любая macOS)

```bash
git clone <this-repo-url> ~/ai-devkit
cd ~/ai-devkit
./scripts/bootstrap.sh
```

Скрипт:
- Симлинкует `AGENTS.md` во все три агента (бэкапит существующие в `*.bak`)
- Устанавливает конфиги (не перезаписывает секреты)
- Качает локальные модели через Ollama
- Регистрирует MCP-серверы в Claude Code
- Идемпотентен — можно запускать повторно

---

## Локальные модели

Подробно — в [models/README.md](models/README.md). Коротко:

| Модель | Назначение | Размер | Function-calling |
|--------|------------|--------|------------------|
| `gemma4:12b-mlx` | чат, рассуждения | 7.7 ГБ | ✅ |
| `qwen3.5:9b-mlx` | код, инструменты | 8.9 ГБ | ✅ (надёжнее) |

**На 16 ГБ работают по очереди** — одновременная загрузка обеих вызывает своп. Выделенный `qwen3-coder` (30B/19 ГБ) не помещается.

### Как использовать

```bash
# 1. Прямой чат в терминале (чистый LLM, без инструментов)
ollama run gemma4:12b-mlx
ollama run qwen3.5:9b-mlx

# 2. OpenAI-совместимый API (для своих скриптов)
curl http://localhost:11434/v1/chat/completions -d '{
  "model": "qwen3.5:9b-mlx",
  "messages": [{"role":"user","content":"напиши тест на функцию X"}]
}'

# 3. В OpenCode — выбери провайдер "ollama" через /models
#    Только тут локальные модели получают MCP + Skills + AGENTS.md правила
```

### Получают ли локальные модели скиллы и MCP? (честно)

| Запуск | AGENTS.md | MCP | Skills |
|--------|-----------|-----|--------|
| `ollama run` / прямой API | ❌ | ❌ | ❌ |
| **OpenCode (провайдер ollama)** | ✅ | ✅ context7, sequential-thinking | ✅ все навыки OpenCode |
| Claude Code (MCP) | — | работают с **моделями Claude**, не с локальными | Claude-скиллы |

Обе модели поддерживают function-calling (`ollama show` → capability `tools`). В OpenCode они реально вызывают MCP-инструменты. Практика: `qwen3.5:9b-mlx` надёжнее для задач с инструментами.

---

## OpenCode — плагины и навыки

**Конфиг:** `opencode/opencode.jsonc`

### Плагины
| Плагин | Версия | Назначение |
|--------|--------|------------|
| `@dietrichgebert/ponytail` | 4.8.4 | Режим «ленивый сеньор»: YAGNI, stdlib first, минимальный код, корневая причина багов |
| `opencode-skills-collection` | latest | 270+ готовых навыков (frontend, backend, DevOps, AI, testing, etc.) |

### Навыки (в `~/.config/opencode/skills/` — симлинки/копии при bootstrap)
| Навык | Тип | Описание |
|-------|-----|----------|
| `frontend-dev` | полный | Полноценный фронтенд: UI, анимации, AI-медиа, копирайтинг, generative art |
| `fullstack-dev` | полный | Backend архитектура + интеграция с фронтом (REST, auth, realtime, файлы, prod) |
| `shader-dev` | полный | GLSL: ray marching, SDF, флюиды, частицы, процедурная генерация, lighting |
| `ru-commit` | полный | Conventional Commits на русском |
| `ponytail` | плагин | Основной режим понитейла |
| `ponytail-audit` | плагин | Аудит всего репо на over-engineering |
| `ponytail-debt` | плагин | Учёт техдолгов из `ponytail:` комментариев |
| `ponytail-gain` | плагин | Метрики экономии кода/времени/денег |
| `ponytail-help` | плагин | Справочник команд понитейла |
| `ponytail-review` | плагин | Code review только за over-engineering |

> Category-pointer навыки (указатели на библиотеки) **убраны** — они ссылались на несуществующий vault. Оставлены только рабочие, самодостаточные навыки.

### Полезные команды OpenCode
```bash
# Посмотреть загруженные навыки
opencode skill list

# Запустить понитейл-аудит репо
opencode run ponytail-audit

# Посмотреть накопленный техдолг
opencode run ponytail-debt
```

---

## MCP-серверы

Уже подключены (без авторизации):
- **context7** — свежая документация фреймворков/библиотек
- **sequential-thinking** — структурное рассуждение (Chain of Thought)
- **playwright** — проверка UI в браузере (только в Claude Code)

**GitHub MCP** — через hosted endpoint с токеном `gh`:
```bash
claude mcp add -s user --transport http github https://api.githubcopilot.com/mcp \
  --header "Authorization: Bearer $(gh auth token)"
```
Токен хранится в `~/.claude.json` (не в репо). При ротации токена `gh` — перезапусти команду или `bootstrap.sh`.

---

## Ограничения и честная критика

- **16 ГБ RAM — узкое место.** Локальный «кодер» — сильная универсальная модель, а не выделенный кодер. Выделенный `qwen3-coder` (30B/19 ГБ) не помещается. Для серьёзной локальной разработки 16 ГБ маловато — облачные модели пока сильнее.
- **Модели не работают одновременно.** Переключение чат↔код требует выгрузки/загрузки (холодный старт).
- **MCP не запинены по версиям** (`@latest`, `context7-mcp`, `playwright/mcp`) — обновления апстрима теоретически могут что-то сломать. Компромисс осознанный: всегда свежее.
- **`bootstrap.sh` не прогонялся end-to-end на чистой машине** (Mac mini не имел Remote Login). Логика идемпотентна и протестирована локально.
- **GitHub-токен от `gh` может истечь**; для долговечности лучше отдельный PAT со scope `repo`.

---

## Безопасность

Секреты (`auth.json`, API-ключи, токены, `~/.claude.json`) **в репозиторий не попадают** — см. `.gitignore`. Публикуются только конфиги и правила.

---

## Правила поведения агентов

Единственный файл, который нужно править — **[AGENTS.md](AGENTS.md)**. Изменения сразу применяются ко всем трём агентам.

---

*Поддерживается для macOS (Apple Silicon). PR с улучшениями приветствуются.*
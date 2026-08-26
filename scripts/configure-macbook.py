#!/usr/bin/env python3
"""Configure the MacBook local-first router and OpenCode entry point."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any


PREFERRED_ROUTER_MODELS = ("qwen3:1.7b", "qwen3.5:9b-mlx", "qwen3:4b")
PREFERRED_CHAT_MODELS = ("qwen3.5:9b-mlx", "gemma4:12b-mlx", "qwen3:4b")


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return fallback
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def ollama_models(endpoint: str) -> set[str]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"{endpoint.rstrip('/')}/api/tags", timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {
        str(item.get("name"))
        for item in payload.get("models", [])
        if isinstance(item, dict) and item.get("name")
    }


def choose_model(installed: set[str], preferred: tuple[str, ...], label: str) -> str:
    for model in preferred:
        if model in installed:
            return model
    available = ", ".join(sorted(installed)) or "none"
    raise RuntimeError(f"No supported {label} model is installed. Available: {available}")


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, path.with_name(f"{path.name}.backup-{stamp}"))


def update_router(path: Path, template: Path, router_model: str, chat_model: str) -> dict[str, Any]:
    config = load_json(path, load_json(template, {}))
    config.setdefault("ollama", {}).update(
        {
            "endpoints": ["http://127.0.0.1:11434"],
            "router_model": router_model,
            "answer_model": chat_model,
        }
    )
    config.setdefault("codex", {}).update(
        {
            "command": str(Path.home() / ".local/bin/codex"),
            "ask_sandbox": "workspace-write",
            "act_sandbox": "workspace-write",
            "workspace_network_access": True,
            "proxy_url": "http://127.0.0.1:18112",
            "no_proxy": "127.0.0.1,localhost,::1",
            "disabled_mcp_servers": ["node_repl", "computer-use"],
        }
    )
    claude = config.setdefault("claude", {})
    claude["command"] = str(Path.home() / ".local/bin/claude-amori")
    claude["proxy_url"] = "http://127.0.0.1:18112"
    claude["no_proxy"] = "127.0.0.1,localhost,::1"
    roots = config.setdefault("skills", {}).setdefault("roots", [])
    if "~/.agents/skills" not in roots:
        roots.append("~/.agents/skills")
    return config


def update_opencode(path: Path, plugin_path: Path, router_model: str, chat_model: str) -> dict[str, Any]:
    config = load_json(path, {"$schema": "https://opencode.ai/config.json"})
    plugins = config.setdefault("plugin", [])
    plugin = str(plugin_path)
    if plugin not in plugins:
        plugins.append(plugin)
    config["default_agent"] = "amori"
    config.setdefault("provider", {})["ollama"] = {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Ollama (MacBook local)",
        "options": {"baseURL": "http://127.0.0.1:11434/v1"},
        "models": {
            router_model: {"name": f"{router_model} (local router)"},
            chat_model: {"name": f"{chat_model} (local chat)"},
        },
    }
    config.setdefault("mcp", {})["amori"] = {
        "type": "local",
        "command": [str(Path.home() / ".local/bin/amori-mcp-remote")],
        "enabled": True,
        "timeout": 30000,
    }
    agents = config.setdefault("agent", {})
    agents["amori"] = {
        "description": "Unified Amori entry point with local/Codex/Claude routing",
        "mode": "primary",
        "model": f"ollama/{router_model}",
        "tools": {"*": False},
        "maxSteps": 2,
        "prompt": (
            "The Amori gateway plugin replaces the request with a completed result. "
            "Return the text after [AMORI_GATEWAY_RESULT] exactly and do not solve it twice."
        ),
    }
    agents["local-chat"] = {
        "description": "Fast private chat on the MacBook Ollama",
        "model": f"ollama/{chat_model}",
    }
    config.setdefault("skills", {})["paths"] = [
        str(Path.home() / ".config/opencode/skills")
    ]
    return config


def write_json(path: Path, data: dict[str, Any], apply: bool) -> None:
    print(f"Would update: {path}" if not apply else f"Updated: {path}")
    if not apply:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    installed = ollama_models(args.endpoint)
    router_model = choose_model(installed, PREFERRED_ROUTER_MODELS, "router")
    chat_model = choose_model(installed, PREFERRED_CHAT_MODELS, "chat")
    print(f"Local router: {router_model}")
    print(f"Local chat: {chat_model}")

    router_path = Path.home() / ".config/amori-ai/config.json"
    router = update_router(router_path, repo / "router/config.example.json", router_model, chat_model)
    write_json(router_path, router, args.apply)

    opencode_dir = Path.home() / ".config/opencode"
    plugin_target = opencode_dir / "plugins/amori-gateway.js"
    opencode_path = opencode_dir / "opencode.jsonc"
    opencode = update_opencode(opencode_path, plugin_target, router_model, chat_model)
    write_json(opencode_path, opencode, args.apply)
    if args.apply:
        plugin_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / "opencode/plugins/amori-gateway.js", plugin_target)
        print(f"Updated: {plugin_target}")
    else:
        print(f"Would update: {plugin_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

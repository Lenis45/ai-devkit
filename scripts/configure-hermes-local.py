#!/usr/bin/env python3
"""Switch Hermes to a verified local Ollama model without leaking old keys."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:
    print(
        "PyYAML is required. Run with ~/.hermes/hermes-agent/venv/bin/python.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def private_json(url: str, timeout: int = 5) -> Dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response from {url}")
    return data


PAID_PROVIDER_KEYS = {"OPENMODEL_API_KEY", "OPENROUTER_API_KEY"}


def quarantine_paid_keys(
    path: Path, backup_path: Path, inline_openmodel_key: str | None
) -> int:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    kept = []
    quarantined = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in PAID_PROVIDER_KEYS:
            quarantined.append(line)
        else:
            kept.append(line)
    if inline_openmodel_key and not any(
        line.startswith("OPENMODEL_API_KEY=") for line in quarantined
    ):
        quarantined.append(f"OPENMODEL_API_KEY={inline_openmodel_key}")
    if not quarantined:
        return 0
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    path.chmod(0o600)
    backup_path.write_text("\n".join(quarantined) + "\n", encoding="utf-8")
    backup_path.chmod(0o600)
    return len(quarantined)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="amori-hermes:4b")
    parser.add_argument("--context-length", type=int, default=65536)
    parser.add_argument("--hermes-home", default="~/.hermes")
    args = parser.parse_args()

    endpoint = args.endpoint.rstrip("/")
    models = private_json(f"{endpoint}/api/tags").get("models", [])
    names = {item.get("name") for item in models if isinstance(item, dict)}
    if args.model not in names:
        print(f"Model {args.model!r} is not installed at {endpoint}", file=sys.stderr)
        return 2

    home = Path(args.hermes_home).expanduser()
    config_path = home / "config.yaml"
    env_path = home / ".env"
    if not config_path.is_file():
        print(f"Hermes config not found: {config_path}", file=sys.stderr)
        return 2
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        print("Hermes config must be a YAML object", file=sys.stderr)
        return 2

    model = data.setdefault("model", {})
    providers = data.setdefault("providers", {})
    openmodel = providers.get("openmodel", {}) if isinstance(providers, dict) else {}
    old_key = model.get("api_key") or (
        openmodel.get("api_key") if isinstance(openmodel, dict) else None
    )

    changes = [
        f"model.provider: {model.get('provider')} -> custom",
        f"model.default: {model.get('default')} -> {args.model}",
        f"model.base_url -> {endpoint}/v1",
        f"model.context_length -> {args.context_length}",
        "fallback_providers -> []",
        "auxiliary providers -> main (local), paid fallback guard -> enabled",
        "CLI toolsets -> skills, terminal, file, clarify",
        "paid provider keys -> private inactive backup",
    ]
    print("\n".join(changes))
    if not args.apply:
        print("Dry run only. Add --apply to update Hermes.")
        return 0

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_name(f"config.yaml.backup-{stamp}")
    shutil.copy2(config_path, backup)

    paid_keys_backup = home / f"paid-provider-credentials.backup-{stamp}.env"
    quarantined_count = quarantine_paid_keys(
        env_path, paid_keys_backup, str(old_key) if old_key else None
    )
    model.pop("api_key", None)
    model.pop("api_mode", None)
    model.update(
        {
            "provider": "custom",
            "default": args.model,
            "base_url": f"{endpoint}/v1",
            "context_length": args.context_length,
        }
    )
    if isinstance(openmodel, dict):
        openmodel.pop("api_key", None)
        openmodel.pop("key_env", None)
    data["fallback_providers"] = []
    auxiliary = data.setdefault("auxiliary", {})
    auxiliary["free_only"] = True
    for name, task in auxiliary.items():
        if name in {"free_only", "openrouter_model"} or not isinstance(task, dict):
            continue
        task["provider"] = "main"
        task["model"] = ""
        task["base_url"] = ""
        task["api_key"] = ""
        task["reasoning_effort"] = "none"
    minimal_toolsets = ["skills", "terminal", "file", "clarify"]
    data["toolsets"] = minimal_toolsets
    platform_toolsets = data.setdefault("platform_toolsets", {})
    platform_toolsets["cli"] = minimal_toolsets

    config_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    config_path.chmod(0o600)
    print(f"Updated {config_path}")
    print(f"Backup: {backup}")
    if quarantined_count:
        print(
            f"Disabled {quarantined_count} paid provider credential(s); "
            f"private backup: {paid_keys_backup}"
        )
    else:
        print("No active paid provider credentials found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Remote subscription worker for a MacBook connected to the Amori Broker."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.parse
from pathlib import Path

from gateway_client import GatewayClient, GatewayError


WORKER_ID = os.getenv("AMORI_WORKER_ID", f"{socket.gethostname().lower()}-subscriptions")
DEVICE = os.getenv("AMORI_WORKER_DEVICE", "macbook")
BASE_CAPABILITIES = ["ollama", "artifact_write"]
SAFE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".pptx", ".zip"}
RUNTIME_INFO_TTL_SECONDS = 300
CLAUDE_PROFILE_MAX_AGE_SECONDS = 24 * 60 * 60
_runtime_info_cache: tuple[float, dict, dict] | None = None


def _jwt_is_fresh(token: object, minimum_ttl_seconds: int = 60) -> bool:
    if not isinstance(token, str):
        return False
    parts = token.split(".")
    if len(parts) != 3:
        return False
    try:
        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        )
        return float(payload["exp"]) > time.time() + minimum_ttl_seconds
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def _codex_token_is_fresh() -> bool:
    auth_path = Path.home() / ".codex/auth.json"
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    tokens = payload.get("tokens")
    return isinstance(tokens, dict) and _jwt_is_fresh(tokens.get("access_token"))


def _claude_profile_is_fresh() -> bool:
    profile_path = Path.home() / ".claude.json"
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        fetched_at_ms = float((payload.get("oauthAccount") or {})["profileFetchedAt"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return fetched_at_ms / 1000 > time.time() - CLAUDE_PROFILE_MAX_AGE_SECONDS


def _version(command: str) -> str:
    try:
        result = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=15)
        return (result.stdout or result.stderr).strip().splitlines()[0][:120]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unavailable"


def _authenticated(command: str) -> bool:
    executable = shutil.which(command)
    if not executable:
        return False
    if command == "codex" and not _codex_token_is_fresh():
        return False
    if command == "claude" and not _claude_profile_is_fresh():
        return False
    args = (
        [executable, "login", "status"]
        if command == "codex"
        else [executable, "auth", "status"]
    )
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    output = (result.stdout or result.stderr).strip()
    if command == "claude":
        try:
            return bool(json.loads(output).get("loggedIn"))
        except (json.JSONDecodeError, AttributeError):
            return False
    return "logged in" in output.lower()


def _runtime_info() -> tuple[dict, dict]:
    global _runtime_info_cache
    now = time.monotonic()
    if _runtime_info_cache and now - _runtime_info_cache[0] < RUNTIME_INFO_TTL_SECONDS:
        return _runtime_info_cache[1], _runtime_info_cache[2]
    versions = {"codex": _version("codex"), "claude": _version("claude")}
    auth_status = {"codex": _authenticated("codex"), "claude": _authenticated("claude")}
    _runtime_info_cache = (now, versions, auth_status)
    return versions, auth_status


def _available_capabilities() -> list[str]:
    _versions, auth_status = _runtime_info()
    capabilities = list(BASE_CAPABILITIES)
    if auth_status.get("codex"):
        capabilities.append("codex_subscription")
    if auth_status.get("claude"):
        capabilities.append("claude_subscription")
    return capabilities


def heartbeat(client: GatewayClient) -> None:
    versions, auth_status = _runtime_info()
    client.request("POST", "/v1/workers/heartbeat", {
        "worker_id": WORKER_ID,
        "device": DEVICE,
        "capabilities": _available_capabilities(),
        "versions": versions,
        "auth_status": auth_status,
        "meta": {"host": socket.gethostname()},
    })


def _event(client: GatewayClient, request_id: str, stage: str, message: str, progress: int) -> None:
    client.request("POST", f"/v1/workers/{request_id}/events", {
        "stage": stage, "message": message, "progress": progress, "meta": {},
    })


def _safe_paths(answer: str, cwd: Path) -> list[Path]:
    matches = re.findall(r"(?:/[^\s'\"`]+|[\w./-]+\.(?:png|jpe?g|webp|pdf|docx|xlsx|pptx|zip))", answer, re.I)
    paths = []
    for raw in matches:
        candidate = Path(raw.rstrip(".,;:)]}")).expanduser()
        candidate = candidate if candidate.is_absolute() else cwd / candidate
        try:
            resolved = candidate.resolve()
            resolved.relative_to(cwd)
        except (OSError, ValueError):
            continue
        if resolved.is_file() and resolved.suffix.lower() in SAFE_SUFFIXES:
            if not any(word in resolved.name.lower() for word in (".env", "token", "secret", "private_key")):
                paths.append(resolved)
    return sorted(set(paths))


def _upload_output(client: GatewayClient, request_id: str, owner: str, path: Path) -> dict:
    boundary = f"amori-{os.urandom(12).hex()}"
    prefix = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    body = prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    query = f"?owner_id={urllib.parse.quote(owner, safe='')}&kind=output"
    return client.request(
        "POST", f"/v1/workers/{request_id}/artifacts{query}", body=body,
        content_type=f"multipart/form-data; boundary={boundary}", timeout=180,
    )["artifact"]


def execute(client: GatewayClient, request: dict) -> None:
    request_id = str(request["id"])
    route = request.get("route") or {}
    provider = route.get("provider", "codex")
    if provider not in {"hermes", "codex", "claude"}:
        provider = "codex"
    cwd = Path(request.get("cwd") or Path.home()).expanduser().resolve()
    if not cwd.is_dir():
        raise GatewayError(f"Workspace does not exist: {cwd}")
    command = ["amori-ai", "--json", "--cwd", str(cwd), "--to", provider]
    if request.get("mode") == "act":
        command.append("--act")
    command.append(request["prompt_text"])
    _event(client, request_id, "running", f"MacBook: {provider}", 40)
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        while process.poll() is None:
            state = client.get(request_id)["request"]["status"]
            if state == "cancelled":
                os.killpg(process.pid, signal.SIGTERM)
                return
            heartbeat(client)
            time.sleep(20)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise GatewayError((stderr or stdout or "executor failed")[-1000:])
        payload = json.loads(stdout)
        answer = str(payload.get("answer") or "").strip()
        if not answer:
            raise GatewayError("Executor returned an empty answer")
        artifacts = [_upload_output(client, request_id, request["actor_id"], path) for path in _safe_paths(answer, cwd)]
        _event(client, request_id, "verifying", "Проверяю результат MacBook", 85)
        client.request("POST", f"/v1/workers/{request_id}/complete", {
            "status": "completed",
            "result_text": answer,
            "evidence": (payload.get("evidence") or []) + [{"type": "remote_worker", "worker_id": WORKER_ID}, {"type": "artifacts", "ids": [item["id"] for item in artifacts]}],
        })
    except Exception as error:
        client.request("POST", f"/v1/workers/{request_id}/fail", {
            "error_code": "remote_execution_failed", "error_message": str(error)[:500],
        })


def run_once(client: GatewayClient) -> bool:
    heartbeat(client)
    response = client.request("POST", "/v1/workers/claim", {
        "worker_id": WORKER_ID,
        "device": DEVICE,
        "capabilities": _available_capabilities(),
    })
    request = response.get("request")
    if not request:
        return False
    execute(client, request)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=3)
    args = parser.parse_args()
    client = GatewayClient()
    while True:
        try:
            worked = run_once(client)
            if args.once:
                return 0
            if not worked:
                time.sleep(max(1, args.poll_seconds))
        except GatewayError as error:
            print(f"gateway-worker: {error}", flush=True)
            if args.once:
                return 1
            time.sleep(10)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Terminal client for the authenticated Amori request broker."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Optional


TERMINAL = {"completed", "partial", "failed", "cancelled"}
TOKEN_FILE = Path.home() / ".config" / "amori" / "broker_token"


class GatewayError(RuntimeError):
    pass


def default_broker_endpoint() -> str:
    hostname = socket.gethostname().lower()
    return (
        "http://127.0.0.1:18110"
        if "macbook" in hostname
        else "http://100.66.130.21:8110"
    )


class GatewayClient:
    def __init__(self, endpoint: str = "", token: str = "") -> None:
        self.endpoint = (
            endpoint or os.getenv("AMORI_BROKER_URL") or default_broker_endpoint()
        ).rstrip("/")
        self.token = token or os.getenv("AMORI_BROKER_TOKEN", "").strip() or self._read_token()
        if not self.token:
            raise GatewayError("Broker token is missing")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @staticmethod
    def _read_token() -> str:
        try:
            return TOKEN_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def request(
        self, method: str, path: str, payload: Optional[dict] = None, *,
        body: Optional[bytes] = None, content_type: str = "application/json", timeout: float = 60,
    ) -> dict:
        if body is None and payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}{path}", data=body, method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": content_type,
            },
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise GatewayError(f"Broker HTTP {error.code}: {detail}") from error
        except (OSError, urllib.error.URLError, TimeoutError) as error:
            raise GatewayError(f"Broker unavailable: {error}") from error

    def upload(self, path: Path, owner_id: str) -> str:
        if not path.is_file() or path.is_symlink():
            raise GatewayError(f"Input file does not exist: {path}")
        if path.stat().st_size > 25 * 1024 * 1024:
            raise GatewayError(f"Input file exceeds 25 MB: {path.name}")
        boundary = f"amori-{uuid.uuid4().hex}"
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        prefix = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        body = prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("ascii")
        owner = urllib.parse.quote(owner_id, safe="")
        response = self.request(
            "POST", f"/v1/uploads?owner_id={owner}", body=body,
            content_type=f"multipart/form-data; boundary={boundary}", timeout=180,
        )
        return str(response["artifact"]["id"])

    def submit(self, payload: dict) -> dict:
        return self.request("POST", "/v1/requests", payload)["request"]

    def get(self, request_id: str) -> dict:
        return self.request("GET", f"/v1/requests/{urllib.parse.quote(request_id, safe='')}")

    def confirm(self, request_id: str, actor_id: str) -> bool:
        safe_id = urllib.parse.quote(request_id, safe="")
        return bool(self.request("POST", f"/v1/requests/{safe_id}/confirm", {"actor_id": actor_id}).get("confirmed"))

    def cancel(self, request_id: str) -> bool:
        safe_id = urllib.parse.quote(request_id, safe="")
        return bool(self.request("POST", f"/v1/requests/{safe_id}/cancel", {}).get("cancelled"))

    def download(self, artifact: dict, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / Path(artifact.get("original_name") or "artifact.bin").name
        request = urllib.request.Request(
            f"{self.endpoint}{artifact['download_url']}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        try:
            with self.opener.open(request, timeout=180) as response:
                target.write_bytes(response.read())
        except (OSError, urllib.error.URLError, TimeoutError) as error:
            raise GatewayError(f"Cannot download {target.name}: {error}") from error
        return target


def _status_line(response: dict) -> str:
    request = response.get("request") or {}
    event = (response.get("events") or [{}])[-1]
    route = request.get("route") or {}
    executor = route.get("execution_handler") or route.get("provider") or "auto"
    return f"{request.get('status', 'unknown')}: {event.get('message', '')} [{executor}]"


def client_device() -> str:
    configured = os.getenv("AMORI_CLIENT_DEVICE", "").strip()
    if configured:
        return configured
    hostname = socket.gethostname().lower()
    return "macbook" if "macbook" in hostname else "mac-mini"


def _wait(client: GatewayClient, request_id: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    previous = ""
    while time.monotonic() < deadline:
        response = client.get(request_id)
        line = _status_line(response)
        if line != previous:
            print(line, file=sys.stderr)
            previous = line
        status = (response.get("request") or {}).get("status")
        if status in TERMINAL | {"awaiting_confirmation"}:
            return response
        time.sleep(1.5)
    raise GatewayError("Request timed out; use --status to continue tracking it")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send work through the Amori Intelligence Gateway")
    parser.add_argument("prompt", nargs="?")
    parser.add_argument("--source", choices=("terminal", "hermes", "opencode"), default="terminal")
    parser.add_argument("--actor", default=os.getenv("USER", "denis"))
    parser.add_argument("--session", default=f"{socket.gethostname()}-{os.getpid()}")
    parser.add_argument("--message-id", default="")
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--act", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm an action after routing")
    parser.add_argument(
        "--defer-confirmation", action="store_true",
        help="Return an awaiting-confirmation action without cancelling it",
    )
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--status", metavar="REQUEST_ID")
    parser.add_argument("--wait", metavar="REQUEST_ID")
    parser.add_argument("--cancel", metavar="REQUEST_ID")
    parser.add_argument("--confirm", metavar="REQUEST_ID")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = GatewayClient()
        if args.status:
            response = client.get(args.status)
        elif args.wait:
            response = _wait(client, args.wait, args.timeout)
        elif args.cancel:
            response = {"cancelled": client.cancel(args.cancel), "request_id": args.cancel}
        elif args.confirm:
            response = {"confirmed": client.confirm(args.confirm, args.actor), "request_id": args.confirm}
        else:
            if not args.prompt:
                raise GatewayError("Prompt is required")
            artifact_ids = [client.upload(Path(item).expanduser().resolve(), args.actor) for item in args.file]
            request = client.submit({
                "source": args.source,
                "actor_id": args.actor,
                "session_id": args.session,
                "source_message_id": args.message_id or str(uuid.uuid4()),
                "text": args.prompt,
                "mode": "act" if args.act else "ask",
                "cwd": str(Path(args.cwd).expanduser().resolve()),
                "target_device": client_device(),
                "artifact_ids": artifact_ids,
            })
            response = _wait(client, str(request["id"]), args.timeout)
            if response["request"]["status"] == "awaiting_confirmation":
                if args.defer_confirmation:
                    if args.json:
                        print(json.dumps(response, ensure_ascii=False, default=str))
                    else:
                        print("Требуется подтверждение. Ответьте ДА или НЕТ.")
                    return 0
                approved = args.yes
                if not approved and sys.stdin.isatty():
                    approved = input("This action changes state. Continue? [y/N] ").strip().lower() in {"y", "yes", "да"}
                if not approved:
                    client.cancel(str(request["id"]))
                    response = client.get(str(request["id"]))
                else:
                    client.confirm(str(request["id"]), args.actor)
                    response = _wait(client, str(request["id"]), args.timeout)
            output_dir = Path(args.output_dir).expanduser() if args.output_dir else Path(args.cwd) / ".amori-results" / str(request["id"])
            response["local_files"] = [str(client.download(item, output_dir)) for item in response.get("artifacts") or []]
        if args.json:
            print(json.dumps(response, ensure_ascii=False, default=str))
        else:
            request = response.get("request") if isinstance(response, dict) else None
            print((request or {}).get("result_text") or json.dumps(response, ensure_ascii=False, default=str))
        status = (response.get("request") or {}).get("status") if isinstance(response, dict) else None
        return 0 if status not in {"failed", "cancelled"} else 2
    except GatewayError as error:
        print(f"amori-request: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

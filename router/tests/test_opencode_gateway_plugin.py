from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "opencode" / "plugins" / "amori-gateway.js"


def test_gateway_plugin_uses_portable_process_api() -> None:
    source = PLUGIN.read_text(encoding="utf-8")

    assert 'from "node:child_process"' in source
    assert "execFileAsync" in source
    assert "Bun.spawn" not in source
    assert "timeout: GATEWAY_TIMEOUT_MS" in source
    assert "maxBuffer: GATEWAY_MAX_BUFFER_BYTES" in source


def test_gateway_plugin_preserves_file_forwarding() -> None:
    source = PLUGIN.read_text(encoding="utf-8")

    assert 'command.push("--file", file)' in source
    assert 'part.url.startsWith("file:")' in source
    assert "pathToFileURL(path).href" in source


def test_gateway_plugin_continues_chat_until_explicit_new_topic() -> None:
    source = PLUGIN.read_text(encoding="utf-8")

    assert "NEW_TOPIC_PATTERN" in source
    assert 'command.push("--continue-thread")' in source
    assert "/new" in source

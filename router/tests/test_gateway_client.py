import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "gateway_client.py"
SPEC = importlib.util.spec_from_file_location("gateway_client", MODULE_PATH)
gateway_client = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = gateway_client
SPEC.loader.exec_module(gateway_client)

WORKER_MODULE_PATH = Path(__file__).parents[1] / "gateway_worker.py"
WORKER_SPEC = importlib.util.spec_from_file_location("gateway_worker", WORKER_MODULE_PATH)
gateway_worker = importlib.util.module_from_spec(WORKER_SPEC)
assert WORKER_SPEC.loader
WORKER_SPEC.loader.exec_module(gateway_worker)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


class GatewayClientTests(unittest.TestCase):
    def test_client_sends_bearer_and_disables_proxy(self):
        seen = {}

        class Opener:
            def open(self, request, timeout):
                seen["authorization"] = request.headers["Authorization"]
                seen["timeout"] = timeout
                return Response({"ok": True})

        client = gateway_client.GatewayClient("http://broker", "secret")
        client.opener = Opener()

        self.assertEqual(client.request("GET", "/health"), {"ok": True})
        self.assertEqual(seen, {"authorization": "Bearer secret", "timeout": 60})

    def test_status_line_reports_selected_executor(self):
        response = {
            "request": {"status": "running", "route": {"provider": "codex"}},
            "events": [{"message": "Проверяю код"}],
        }

        self.assertEqual(gateway_client._status_line(response), "running: Проверяю код [codex]")

    def test_upload_rejects_large_file_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.bin"
            path.write_bytes(b"x")
            client = gateway_client.GatewayClient("http://broker", "secret")
            with mock.patch.object(Path, "stat", return_value=type("S", (), {"st_size": 26 * 1024 * 1024})()):
                with self.assertRaisesRegex(gateway_client.GatewayError, "25 MB"):
                    client.upload(path, "denis")

    def test_client_device_uses_current_host(self):
        with mock.patch.object(gateway_client.socket, "gethostname", return_value="mac-mini"):
            self.assertEqual(gateway_client.client_device(), "mac-mini")
        with mock.patch.object(gateway_client.socket, "gethostname", return_value="Denis-MacBook"):
            self.assertEqual(gateway_client.client_device(), "macbook")

    def test_parser_supports_deferred_confirmation_and_wait(self):
        deferred = gateway_client.build_parser().parse_args([
            "--act", "--defer-confirmation", "Измени файл",
        ])
        waiting = gateway_client.build_parser().parse_args(["--wait", "request-1"])

        self.assertTrue(deferred.act)
        self.assertTrue(deferred.defer_confirmation)
        self.assertEqual(waiting.wait, "request-1")

    def test_worker_runtime_info_is_cached(self):
        gateway_worker._runtime_info_cache = None
        calls = []
        with mock.patch.object(gateway_worker.time, "monotonic", return_value=100.0), \
                mock.patch.object(gateway_worker, "_version", side_effect=lambda command: calls.append(command) or f"{command}-1"), \
                mock.patch.object(gateway_worker.shutil, "which", side_effect=lambda command: f"/bin/{command}"):
            first = gateway_worker._runtime_info()
            second = gateway_worker._runtime_info()

        self.assertEqual(first, second)
        self.assertEqual(calls, ["codex", "claude"])


if __name__ == "__main__":
    unittest.main()

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[2] / "scripts/configure-macbook.py"
SPEC = importlib.util.spec_from_file_location("configure_macbook", MODULE_PATH)
configure_macbook = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(configure_macbook)


class MacBookConfigurationTests(unittest.TestCase):
    def test_opencode_keeps_existing_mcp_and_adds_amori_bridge(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "opencode.jsonc"
            path.write_text(
                '{"mcp":{"context7":{"type":"remote","url":"https://example.invalid"}}}',
                encoding="utf-8",
            )
            config = configure_macbook.update_opencode(
                path,
                Path(directory) / "amori-gateway.js",
                "qwen3:1.7b",
                "qwen3.5:9b-mlx",
            )

        self.assertIn("context7", config["mcp"])
        self.assertEqual(
            config["mcp"]["amori"]["command"],
            [str(Path.home() / ".local/bin/amori-mcp-remote")],
        )
        self.assertTrue(config["mcp"]["amori"]["enabled"])

    def test_router_uses_http_bridge_and_disables_blocking_app_mcp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "router.json"
            template = Path(directory) / "template.json"
            template.write_text("{}", encoding="utf-8")
            config = configure_macbook.update_router(
                path,
                template,
                "qwen3:1.7b",
                "qwen3.5:9b-mlx",
            )

        self.assertEqual(config["codex"]["proxy_url"], "http://127.0.0.1:18112")
        self.assertIn("node_repl", config["codex"]["disabled_mcp_servers"])
        self.assertEqual(
            config["claude"]["command"],
            str(Path.home() / ".local/bin/claude-amori"),
        )


if __name__ == "__main__":
    unittest.main()

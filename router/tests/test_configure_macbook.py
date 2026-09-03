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
    def test_fast_model_keeps_tool_schema_and_bounded_context(self):
        template = (MODULE_PATH.parents[1] / "models/qwen3-opencode-nothink.Modelfile").read_text()
        self.assertIn("PARAMETER num_ctx 8192", template)
        self.assertIn("range .Tools", template)
        self.assertIn(".ToolCalls", template)
        self.assertIn('eq .Role "tool"', template)

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
                "ami-qwen3:1.7b-nothink",
                "gemma4:12b-mlx",
            )

        self.assertIn("context7", config["mcp"])
        self.assertEqual(
            config["mcp"]["amori"]["command"],
            [str(Path.home() / ".local/bin/amori-mcp-remote")],
        )
        self.assertTrue(config["mcp"]["amori"]["enabled"])
        self.assertEqual(config["default_agent"], "ami")
        self.assertEqual(config["agent"]["ami"]["mode"], "primary")
        self.assertEqual(config["agent"]["amori"]["mode"], "subagent")
        self.assertEqual(
            config["small_model"],
            "ollama/ami-qwen3:1.7b-nothink",
        )
        self.assertEqual(
            config["agent"]["local-chat"]["model"],
            "ollama/ami-qwen3:1.7b-nothink",
        )
        self.assertEqual(config["agent"]["local-chat"]["tools"], {"*": False})
        self.assertNotIn("maxSteps", config["agent"]["local-chat"])
        self.assertNotIn("maxSteps", config["agent"]["ami"])
        self.assertEqual(config["agent"]["local-deep"]["model"], "ollama/gemma4:12b-mlx")
        self.assertEqual(config["agent"]["local-deep"]["tools"], {"*": False})
        self.assertEqual(
            config["provider"]["ollama"]["models"]["ami-qwen3:1.7b-nothink"]["limit"]["output"],
            512,
        )
        self.assertEqual(config["provider"]["ollama"]["models"]["gemma4:12b-mlx"]["limit"]["output"], 1024)
        self.assertEqual(config["provider"]["ollama"]["options"]["headerTimeout"], 60000)

    def test_opencode_removes_broken_duplicate_plugins(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "opencode.jsonc"
            path.write_text(
                '{"plugin":["@dietrichgebert/ponytail",'
                '"opencode-skills-collection@latest","custom-plugin"]}',
                encoding="utf-8",
            )
            config = configure_macbook.update_opencode(
                path,
                Path(directory) / "amori-gateway.js",
                "ami-qwen3:1.7b-nothink",
                "gemma4:12b-mlx",
            )

        self.assertIn("custom-plugin", config["plugin"])
        self.assertNotIn("@dietrichgebert/ponytail", config["plugin"])
        self.assertNotIn("opencode-skills-collection@latest", config["plugin"])

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

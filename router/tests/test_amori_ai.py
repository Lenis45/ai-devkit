import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "amori_ai.py"
SPEC = importlib.util.spec_from_file_location("amori_ai", MODULE_PATH)
amori_ai = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = amori_ai
SPEC.loader.exec_module(amori_ai)


class RoutingTests(unittest.TestCase):
    def test_simple_question_routes_to_local_hermes(self):
        decision = amori_ai.rule_classify("Что такое RAG?")
        self.assertEqual(decision.provider, "hermes")
        self.assertEqual(decision.complexity, "simple")

    def test_code_implementation_routes_to_codex(self):
        decision = amori_ai.rule_classify(
            "Исправь ошибку в Python API, добавь тесты и сделай коммит"
        )
        self.assertEqual(decision.provider, "codex")
        self.assertIn(decision.complexity, {"medium", "complex"})

    def test_architecture_routes_to_claude(self):
        decision = amori_ai.rule_classify(
            "Проведи системный анализ и сравни подходы к архитектуре сервиса"
        )
        self.assertEqual(decision.provider, "claude")

    def test_guardrail_corrects_weak_model_architecture_route(self):
        decision = amori_ai.Decision(
            provider="hermes",
            complexity="medium",
            intent="comparison",
            confidence=0.8,
            reason="test",
            source="ollama:test",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails(
            "Сравни архитектурные подходы для очереди задач", decision, "ask"
        )
        self.assertEqual(guarded.provider, "claude")

    def test_current_information_does_not_stay_local(self):
        decision = amori_ai.Decision(
            provider="hermes",
            complexity="simple",
            intent="weather",
            confidence=0.8,
            reason="test",
            source="ollama:test",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails(
            "Какая погода сегодня в Москве?", decision, "ask"
        )
        self.assertEqual(guarded.provider, "claude")
        self.assertEqual(guarded.complexity, "medium")

    def test_short_writing_request_stays_local(self):
        decision = amori_ai.rule_classify("Сделай короткое резюме этого абзаца")
        self.assertEqual(decision.provider, "hermes")

    def test_calendar_action_uses_native_handler(self):
        decision = amori_ai.Decision(
            provider="hermes",
            complexity="simple",
            intent="quick_action",
            confidence=0.8,
            reason="test",
            source="ollama:test",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails(
            "Добавь встречу в календарь на завтра", decision, "ask"
        )
        contracted = amori_ai.apply_execution_contract(
            "Добавь встречу в календарь на завтра", guarded, "ask"
        )
        self.assertEqual(contracted.provider, "hermes")
        self.assertEqual(contracted.execution_handler, "calendar")
        self.assertEqual(contracted.target_device, "mac-mini")

    def test_calendar_contract_separates_reasoning_from_execution(self):
        config, _path = amori_ai.load_config()
        decision, _endpoint, _checked = amori_ai.make_decision(
            "Добавь встречу в календарь на завтра в 10:00",
            config,
            "act",
            disable_neural=True,
        )

        self.assertEqual(decision.provider, "hermes")
        self.assertEqual(decision.execution_handler, "calendar")
        self.assertIn("action_receipt", decision.expected_outputs)

    def test_image_generation_routes_to_codex_artifact_handler(self):
        config, _path = amori_ai.load_config()
        decision, _endpoint, _checked = amori_ai.make_decision(
            "Создай изображение ошейника на белом фоне",
            config,
            "act",
            disable_neural=True,
        )

        self.assertEqual(decision.provider, "codex")
        self.assertEqual(decision.execution_handler, "image_generation")
        self.assertIn("image", decision.expected_outputs)

    def test_image_generation_allows_descriptive_words_between_verb_and_noun(self):
        config, _path = amori_ai.load_config()
        decision, _endpoint, _checked = amori_ai.make_decision(
            "Создай простое квадратное изображение: чёрный круг на белом фоне",
            config,
            "ask",
            disable_neural=True,
        )

        self.assertEqual(decision.provider, "codex")
        self.assertEqual(decision.execution_handler, "image_generation")
        self.assertEqual(decision.expected_outputs, ["text", "image"])

    def test_email_action_has_high_level_native_receipt_contract(self):
        decision = amori_ai.rule_classify("Отправь письмо лиду 42")
        decision = amori_ai.apply_guardrails("Отправь письмо лиду 42", decision, "act")
        decision = amori_ai.apply_execution_contract("Отправь письмо лиду 42", decision, "act")

        self.assertEqual(decision.execution_handler, "email")
        self.assertIn("action_receipt", decision.expected_outputs)

    def test_content_action_can_stay_local(self):
        decision = amori_ai.Decision(
            provider="hermes",
            complexity="simple",
            intent="writing",
            confidence=0.8,
            reason="test",
            source="ollama:test",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails(
            "Сделай короткий текст поздравления", decision, "ask"
        )
        self.assertEqual(guarded.provider, "hermes")

    def test_long_local_decision_is_guarded(self):
        decision = amori_ai.Decision(
            provider="hermes",
            complexity="simple",
            intent="quick_answer",
            confidence=0.9,
            reason="test",
            source="test",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails("объясни " + ("слово " * 1100), decision, "ask")
        self.assertEqual(guarded.provider, "claude")
        self.assertEqual(guarded.complexity, "complex")

    def test_act_code_override_uses_codex(self):
        decision = amori_ai.Decision(
            provider="claude",
            complexity="medium",
            intent="implementation",
            confidence=0.6,
            reason="test",
            source="test",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails(
            "Исправь код и добавь тест", decision, "act"
        )
        self.assertEqual(guarded.provider, "codex")

    def test_act_mode_never_uses_local_read_only_lane(self):
        decision = amori_ai.Decision(
            provider="hermes",
            complexity="simple",
            intent="quick_answer",
            confidence=0.9,
            reason="test",
            source="test",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails("Создай заметку", decision, "act")
        self.assertEqual(guarded.provider, "codex")

    def test_explicit_provider_is_not_overridden(self):
        decision = amori_ai.Decision(
            provider="claude",
            complexity="medium",
            intent="implementation",
            confidence=1.0,
            reason="forced",
            source="forced",
            selected_skills=[],
        )
        guarded = amori_ai.apply_guardrails(
            "Исправь код", decision, "act", provider_locked=True
        )
        self.assertEqual(guarded.provider, "claude")

    def test_neural_provider_alias_is_normalized(self):
        self.assertEqual(amori_ai.PROVIDER_ALIASES["claudia"], "claude")


class SkillsTests(unittest.TestCase):
    def test_selects_relevant_skills(self):
        skills = [
            amori_ai.Skill("debugging", "Find root causes", "/debug/SKILL.md"),
            amori_ai.Skill("git-safe", "Safe git workflow", "/git/SKILL.md"),
            amori_ai.Skill("perf", "Performance work", "/perf/SKILL.md"),
        ]
        selected = amori_ai.select_skills(
            "Исправь ошибку, прогони git diff и сделай коммит", skills, 3
        )
        selected_names = {item.name for item in selected}
        self.assertIn("debugging", selected_names)
        self.assertIn("git-safe", selected_names)

    def test_skill_limit_is_respected(self):
        skills = [
            amori_ai.Skill(name, "test debug git performance", f"/{name}/SKILL.md")
            for name in ("debugging", "git-safe", "testing", "perf")
        ]
        selected = amori_ai.select_skills("test debug git performance", skills, 3)
        self.assertEqual(len(selected), 3)


class ConfigAndPrivacyTests(unittest.TestCase):
    def test_model_reasoning_is_not_shown_to_user(self):
        raw = "<think>private reasoning</think>\nFinal answer"
        self.assertEqual(amori_ai.strip_thinking(raw), "Final answer")

    def test_revoked_subscription_error_is_recoverable(self):
        error = amori_ai.RouterError("claude failed: 401 OAuth access token revoked")
        self.assertTrue(amori_ai.is_recoverable_subscription_error(error))

    def test_generic_backend_error_is_not_recoverable(self):
        error = amori_ai.RouterError("claude failed: invalid project configuration")
        self.assertFalse(amori_ai.is_recoverable_subscription_error(error))

    def test_user_config_merges_with_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps({"policy": {"neural_routing": False}}), encoding="utf-8"
            )
            config, loaded_path = amori_ai.load_config(str(path))
        self.assertEqual(loaded_path, path)
        self.assertFalse(config["policy"]["neural_routing"])
        self.assertIn("ollama", config)

    def test_metrics_do_not_store_prompt_text(self):
        with tempfile.TemporaryDirectory() as directory:
            metrics = Path(directory) / "usage.jsonl"
            config = {
                "privacy": {"metrics_file": str(metrics), "log_prompts": False}
            }
            decision = amori_ai.Decision(
                "codex", "medium", "implementation", 0.8, "test", "rules", []
            )
            amori_ai.append_metric(config, decision, "ask", True, 123)
            record = json.loads(metrics.read_text(encoding="utf-8"))
        self.assertNotIn("prompt", record)
        self.assertEqual(record["duration_ms"], 123)


class CodexCommandTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "command": "codex",
            "model": "",
            "ask_sandbox": "workspace-write",
            "act_sandbox": "workspace-write",
            "skip_git_repo_check": True,
            "workspace_network_access": True,
            "disabled_mcp_servers": ["node_repl", "unsafe.name"],
            "ask_reasoning_effort": "low",
            "act_reasoning_effort": "high",
        }

    def test_ask_mode_keeps_network_for_local_and_tailnet_diagnostics(self):
        command = amori_ai.build_codex_command(
            "Проверь Ollama, ничего не меняй",
            "ask",
            self.config,
            Path("/tmp/project"),
            Path("/tmp/output.txt"),
        )
        self.assertIn("workspace-write", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("sandbox_workspace_write.network_access=true", command)
        self.assertIn("mcp_servers.node_repl.enabled=false", command)
        self.assertNotIn("mcp_servers.unsafe.name.enabled=false", command)

    def test_act_mode_uses_configured_workspace_sandbox(self):
        command = amori_ai.build_codex_command(
            "Исправь файл",
            "act",
            self.config,
            Path("/tmp/project"),
            Path("/tmp/output.txt"),
        )
        self.assertIn("workspace-write", command)
        self.assertIn('model_reasoning_effort="high"', command)

    def test_invalid_sandbox_is_rejected(self):
        self.config["ask_sandbox"] = "unrestricted-magic"
        with self.assertRaises(amori_ai.RouterError):
            amori_ai.build_codex_command(
                "test",
                "ask",
                self.config,
                Path("/tmp/project"),
                Path("/tmp/output.txt"),
            )

    def test_backend_proxy_keeps_local_services_outside_tunnel(self):
        environment = amori_ai.backend_environment(
            {
                "proxy_url": "socks5h://127.0.0.1:18111",
                "no_proxy": "127.0.0.1,localhost,::1",
            }
        )
        self.assertIsNotNone(environment)
        self.assertEqual(environment["HTTPS_PROXY"], "socks5h://127.0.0.1:18111")
        self.assertEqual(environment["HTTP_PROXY"], "socks5h://127.0.0.1:18111")
        self.assertIn("127.0.0.1", environment["NO_PROXY"])


class SubscriptionFallbackTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "policy": {"subscription_fallbacks": True},
            "skills": {"roots": [], "max_selected": 3},
            "privacy": {"metrics_file": ""},
        }
        self.decision = amori_ai.Decision(
            "claude", "complex", "architecture", 0.9, "test", "rules", []
        )

    def test_automatic_claude_auth_failure_falls_back_to_codex(self):
        with (
            mock.patch.object(
                amori_ai,
                "make_decision",
                return_value=(self.decision, None, []),
            ),
            mock.patch.object(
                amori_ai,
                "invoke_claude",
                side_effect=amori_ai.RouterError("401 OAuth access token revoked"),
            ),
            mock.patch.object(amori_ai, "invoke_codex", return_value="готово") as codex,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            decision, answer = amori_ai.handle_request(
                "Проведи архитектурный анализ",
                self.config,
                Path.cwd(),
                "ask",
                None,
                True,
                False,
                False,
                False,
            )
        self.assertEqual(answer, "готово")
        self.assertEqual(decision.provider, "codex")
        codex.assert_called_once()

    def test_explicit_claude_route_does_not_fallback(self):
        with (
            mock.patch.object(
                amori_ai,
                "make_decision",
                return_value=(self.decision, None, []),
            ),
            mock.patch.object(
                amori_ai,
                "invoke_claude",
                side_effect=amori_ai.RouterError("401 OAuth access token revoked"),
            ),
            mock.patch.object(amori_ai, "invoke_codex") as codex,
        ):
            with self.assertRaises(amori_ai.RouterError):
                amori_ai.handle_request(
                    "Проведи архитектурный анализ",
                    self.config,
                    Path.cwd(),
                    "ask",
                    "claude",
                    True,
                    False,
                    False,
                    False,
                )
        codex.assert_not_called()


class ClaudeCommandTests(unittest.TestCase):
    def test_headless_claude_uses_safe_mode(self):
        with mock.patch.object(amori_ai, "run_process", return_value="готово") as run:
            result = amori_ai.invoke_claude(
                "Проверь архитектуру",
                "ask",
                {
                    "claude": {
                        "command": "claude",
                        "safe_mode": True,
                        "ask_max_turns": 4,
                        "act_max_turns": 8,
                        "model": "",
                    }
                },
                Path.cwd(),
            )

        self.assertEqual(result, "готово")
        self.assertIn("--safe-mode", run.call_args.args[0])


class RoutingContextTests(unittest.TestCase):
    def test_routing_text_is_classified_without_removing_backend_context(self):
        config = {
            "policy": {"subscription_fallbacks": True},
            "skills": {"roots": [], "max_selected": 3},
            "privacy": {"metrics_file": ""},
        }
        decision = amori_ai.Decision(
            "hermes", "simple", "quick_answer", 0.9, "test", "rules", []
        )
        with (
            mock.patch.object(
                amori_ai,
                "make_decision",
                return_value=(decision, "http://127.0.0.1:11434", []),
            ) as classify,
            mock.patch.object(amori_ai, "invoke_local", return_value="готово") as local,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            _, answer = amori_ai.handle_request(
                "Большой системный контекст с упоминанием кода и архитектуры",
                config,
                Path.cwd(),
                "ask",
                None,
                True,
                False,
                False,
                False,
                routing_prompt="Какой сегодня день?",
            )

        self.assertEqual(answer, "готово")
        self.assertEqual(classify.call_args.args[0], "Какой сегодня день?")
        self.assertEqual(
            local.call_args.args[0],
            "Большой системный контекст с упоминанием кода и архитектуры",
        )


if __name__ == "__main__":
    unittest.main()

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

    def test_calendar_action_uses_execution_backend(self):
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
        self.assertEqual(guarded.provider, "codex")
        self.assertEqual(guarded.complexity, "medium")

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


if __name__ == "__main__":
    unittest.main()

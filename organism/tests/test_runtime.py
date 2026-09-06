"""Offline regressions for preserving history and accounting for model usage."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

ORGANISM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ORGANISM))

import dream
import pulse
import runtime


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 1, 5, 0, 10, tzinfo=timezone.utc)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gaian-runtime-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.mind = self.root / "tela"
        self.mind.mkdir()
        self.today = Clock.now().date().isoformat()
        self.yesterday = (Clock.now().date() - timedelta(days=1)).isoformat()
        self.config = {
            "display_name": "Tela", "provider": "anthropic", "model": "offline-test",
            "api_key_env": "GAIAN_TEST_API_KEY", "daily_budget_usd": 1.0,
            "input_cost_per_mtok": 1.0, "output_cost_per_mtok": 2.0,
            "data_sources": [], "core_docs": [],
        }
        self.reply = json.dumps({"log_entry": "### 00:10 UTC\nTest observation.",
                                 "memory": {"notes": "retained thread"}})
        self.callers = {provider: Mock(return_value=(self.reply, "200", 1000, 100))
                        for provider in ("anthropic", "openai", "google")}
        self.api = self.callers["anthropic"]
        for active_patch in (
            patch.object(pulse, "DATA_DIR", self.root),
            patch.object(dream, "DATA_DIR", self.root),
            patch.object(pulse, "datetime", Clock),
            patch.object(dream, "datetime", Clock),
            patch.object(pulse, "load_config", return_value=self.config),
            patch.object(dream, "load_config", return_value=self.config),
            patch.dict(pulse.API_CALLERS, self.callers, clear=True),
            patch.dict(os.environ, {"GAIAN_TEST_API_KEY": "offline-placeholder"}),
            patch.object(pulse.subprocess, "run", side_effect=AssertionError("No network or fetchers in tests")),
        ):
            active_patch.start()
            self.addCleanup(active_patch.stop)
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def write_log(self, day, path=None):
        path = path or self.mind / "daily_log.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"# Tela Daily Log — {day} (UTC)\n" + (f"Evidence from {day}.\n" * 8)
        path.write_text(content)
        return content

    def budget(self):
        return json.loads((self.mind / "budget.json").read_text())

    def seed_budget(self, day=None, spent=0):
        # The pre-existing format has no dreams_run field.
        value = {"date": day or self.today, "spent_usd": spent, "pulses_run": 3,
                 "input_tokens": 10, "output_tokens": 5}
        (self.mind / "budget.json").write_text(json.dumps(value))
        return value

    def pulse(self):
        with patch.object(sys, "argv", ["pulse.py", "tela"]):
            pulse.main()

    def dream(self, mode="daily"):
        with patch.object(sys, "argv", ["dream.py", "tela", mode]):
            dream.main()

    def test_rollover_preserves_yesterday_and_repeated_pulses_keep_archive(self):
        previous = self.write_log(self.yesterday)
        self.pulse()
        self.pulse()
        archive = self.mind / "archive" / f"daily_log_{self.yesterday}.md"
        self.assertEqual(archive.read_text(), previous)
        self.assertEqual(runtime.log_date((self.mind / "daily_log.md").read_text()), self.today)
        self.assertEqual(self.budget()["pulses_run"], 2)

    def test_conflicting_archive_keeps_both_records_and_makes_no_api_call(self):
        previous = self.write_log(self.yesterday)
        archive = self.mind / "archive" / f"daily_log_{self.yesterday}.md"
        archive.parent.mkdir()
        archive.write_text("Different evidence already archived")
        with self.assertRaisesRegex(ValueError, "Conflicting archive"):
            self.pulse()
        self.assertEqual((self.mind / "daily_log.md").read_text(), previous)
        self.assertEqual(archive.read_text(), "Different evidence already archived")
        self.api.assert_not_called()

    def test_undated_or_future_log_is_retained(self):
        for content in (f"Undated header\nA body mentioning {self.yesterday}",
                        "# Tela Daily Log — 2026-01-06 (UTC)\nFuture record"):
            with self.subTest(content=content):
                (self.mind / "daily_log.md").write_text(content)
                with self.assertRaises(ValueError):
                    self.pulse()
                self.assertEqual((self.mind / "daily_log.md").read_text(), content)
        self.api.assert_not_called()

    def test_unusable_pulse_responses_are_charged_without_replacing_memory(self):
        memory = self.mind / "memory.json"
        memory.write_text('{"notes": "keep this question"}')
        responses = ("not JSON", "[]", '{"log_entry": "text", "memory": []}',
                     '{"log_entry": 42, "memory": {}}', "")
        for count, response in enumerate(responses, 1):
            with self.subTest(response=response):
                self.api.return_value = (response, "200", 1000, 100)
                self.pulse()
                self.assertEqual(json.loads(memory.read_text())["notes"], "keep this question")
                self.assertEqual(self.budget()["input_tokens"], 1000 * count)
                self.assertAlmostEqual(self.budget()["spent_usd"], 0.0012 * count)

    def test_budget_rollover_preserves_legacy_snapshot(self):
        previous = self.seed_budget(self.yesterday, spent=0.8)
        self.pulse()
        archive = self.mind / f"budget_{self.yesterday}.json"
        self.assertEqual(json.loads(archive.read_text()), previous)
        self.assertEqual(self.budget()["date"], self.today)
        self.assertEqual(self.budget()["input_tokens"], 1000)

    def test_daily_allowance_stops_pulse_and_both_dream_modes(self):
        self.write_log(self.yesterday)
        self.seed_budget(spent=1.0)
        self.pulse()
        self.dream()
        dreams = self.mind / "dreams"
        (dreams / f"daily_{self.yesterday}.md").write_text("Previous daily summary")
        self.dream("weekly")
        self.api.assert_not_called()
        self.assertEqual(self.budget()["spent_usd"], 1.0)
        self.assertFalse(list(dreams.glob("weekly_*.md")))

    def test_missing_yesterday_does_not_mislabel_today(self):
        self.write_log(self.today)
        self.dream()
        self.api.assert_not_called()
        self.assertFalse(list((self.mind / "dreams").glob("daily_*.md")))

    def test_archive_filename_cannot_override_mismatched_header(self):
        archive = self.mind / "archive" / f"daily_log_{self.yesterday}.md"
        self.write_log(self.today, archive)
        self.write_log(self.today)
        self.dream()
        self.api.assert_not_called()

    def test_yesterday_in_active_log_is_a_valid_fallback(self):
        previous = self.write_log(self.yesterday)
        self.api.return_value = ("A grounded summary.", "200", 1000, 100)
        self.dream()
        self.assertIn(previous, self.api.call_args.args[3])
        self.assertTrue((self.mind / "dreams" / f"daily_{self.yesterday}.md").exists())
        self.assertEqual((self.mind / "daily_log.md").read_text(), previous)

    def test_pulse_daily_and_weekly_dream_share_usage_and_completed_dreams_skip(self):
        self.write_log(self.yesterday)
        self.pulse()
        self.api.return_value = ("A grounded summary.", "200", 1000, 100)
        self.dream()
        self.dream("weekly")
        self.dream()
        self.dream("weekly")
        self.assertEqual(self.api.call_count, 3)
        self.assertEqual(self.budget()["pulses_run"], 1)
        self.assertEqual(self.budget()["dreams_run"], 2)
        self.assertEqual(self.budget()["input_tokens"], 3000)
        self.assertAlmostEqual(self.budget()["spent_usd"], 0.0036)

    def test_empty_dream_is_charged_without_creating_summary(self):
        self.write_log(self.yesterday)
        self.api.return_value = ("", "200", 1000, 100)
        self.dream()
        self.assertEqual(self.budget()["dreams_run"], 1)
        self.assertEqual(self.budget()["input_tokens"], 1000)
        self.assertFalse(list((self.mind / "dreams").glob("daily_*.md")))

    def test_usage_crossing_allowance_stops_subsequent_jobs(self):
        self.write_log(self.yesterday)
        self.config["daily_budget_usd"] = 0.001
        self.pulse()
        self.dream()
        self.pulse()
        self.api.assert_called_once()
        self.assertAlmostEqual(self.budget()["spent_usd"], 0.0012)

    def test_dream_uses_configured_provider_and_model(self):
        self.write_log(self.yesterday)
        for provider in self.callers:
            with self.subTest(provider=provider):
                for caller in self.callers.values():
                    caller.reset_mock()
                self.config["provider"] = provider
                self.config["model"] = f"test-{provider}"
                (self.mind / "dreams" / f"daily_{self.yesterday}.md").unlink(missing_ok=True)
                self.dream()
                self.assertEqual(self.callers[provider].call_args.args[1], f"test-{provider}")
                for other, caller in self.callers.items():
                    if other != provider:
                        caller.assert_not_called()

    def test_active_job_blocks_pulse_and_dream_until_lock_is_released(self):
        self.write_log(self.yesterday)
        with runtime.mind_lock(self.mind):
            self.pulse()
            self.dream()
            self.api.assert_not_called()
        self.pulse()
        self.api.assert_called_once()
        self.assertTrue((self.mind / "runtime.lock").exists())

    def test_interrupted_snapshot_replacement_keeps_previous_state(self):
        memory = self.mind / "memory.json"
        memory.write_text("previous state")
        with patch.object(runtime.os, "replace", side_effect=OSError("simulated write failure")):
            with self.assertRaises(OSError):
                runtime.atomic_write(memory, "new state")
        self.assertEqual(memory.read_text(), "previous state")
        self.assertEqual(list(self.mind.iterdir()), [memory])


class ProviderResponseTests(unittest.TestCase):
    def test_empty_provider_content_still_reports_usage_and_preserves_timeout(self):
        responses = (
            (pulse.call_anthropic, {"content": [], "usage": {"input_tokens": 1000, "output_tokens": 100}}),
            (pulse.call_openai, {"choices": [], "usage": {"prompt_tokens": 1000, "completion_tokens": 100}}),
            (pulse.call_google, {"candidates": [], "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 100}}),
        )
        for caller, response in responses:
            with self.subTest(provider=caller.__name__):
                result = Mock(stdout=json.dumps(response) + "\n200")
                with patch.object(pulse.subprocess, "run", return_value=result) as request:
                    text, status, input_tokens, output_tokens = caller(
                        "offline-placeholder", "offline-model", "system", "user", 1024, timeout=60)
                self.assertEqual((text, status, input_tokens, output_tokens), ("", "200", 1000, 100))
                self.assertEqual(request.call_args.kwargs["timeout"], 75)


class ArchiveCommandTests(unittest.TestCase):
    def test_archive_command_shares_lock_and_preserves_conflicts(self):
        with tempfile.TemporaryDirectory(prefix="gaian archive test ") as temporary:
            mind = Path(temporary) / "tela"
            mind.mkdir()
            log = mind / "daily_log.md"
            content = "# Tela Daily Log — 2025-01-01 (UTC)\nOriginal evidence"
            log.write_text(content)
            archive = mind / "archive" / "daily_log_2025-01-01.md"
            env = {**os.environ, "NURSERY_DIR": temporary}
            command = ["bash", str(ORGANISM / "archive-logs.sh")]
            with runtime.mind_lock(mind):
                skipped = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(skipped.returncode, 0)
            self.assertIn("SKIP", skipped.stdout)
            self.assertFalse(archive.exists())
            archived = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(archived.returncode, 0, archived.stderr)
            self.assertEqual(archive.read_text(), content)
            archive.write_text("A different record")
            failed = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(archive.read_text(), "A different record")
            self.assertEqual(log.read_text(), content)


if __name__ == "__main__":
    unittest.main()

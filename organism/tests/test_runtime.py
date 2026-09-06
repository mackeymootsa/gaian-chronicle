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
import entry
import pulse
import runtime
import inquiry


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

    def entries(self):
        return list(entry.read_entries(self.root / "entries"))

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
                     '{"log_entry": 42, "memory": {}}', "", "   ")
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
        records_before_retry = self.entries()
        self.dream()
        self.dream("weekly")
        self.assertEqual(self.entries(), records_before_retry)
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

    def test_sources_are_saved_before_generation_and_linked_to_memory(self):
        self.config["data_sources"] = [{"script": "fetch-weather.sh", "name": "Test weather", "epistemic_tag": "FETCHED"}]
        source_text = "Temperature: 3 C\nSource timestamp: 2026-01-05T00:00:00Z\n"
        def respond(*args):
            records = self.entries()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["content"], source_text)
            self.assertIn(records[0]["entry_id"], args[3])
            return self.reply, "200", 1000, 100
        self.api.side_effect = respond
        result = Mock(stdout=source_text, stderr="", returncode=0)
        with patch.object(pulse.subprocess, "run", return_value=result):
            self.pulse()
        source, response, interpretation = self.entries()
        self.assertEqual(source["epistemic_tag"], "FETCHED")
        self.assertEqual(source["source_refs"], ["fetch-weather.sh"])
        self.assertEqual(response["source_refs"], [source["entry_id"]])
        self.assertEqual(interpretation["source_refs"], [response["entry_id"]])
        self.assertEqual(interpretation["epistemic_tag"], "UNKNOWN")
        self.assertEqual({item["pulse_id"] for item in self.entries()}, {source["pulse_id"]})
        memory = json.loads((self.mind / "memory.json").read_text())
        self.assertEqual(memory["last_entry_id"], interpretation["entry_id"])
        self.assertIn(interpretation["entry_id"], (self.mind / "daily_log.md").read_text())

    def test_source_failures_are_preserved_with_unknown_status(self):
        self.config["data_sources"] = [{"script": "fetch-weather.sh", "name": "Test weather", "epistemic_tag": "FETCHED"}]
        responses = (Mock(stdout="Partial data", stderr="upstream failure", returncode=2),
                     Mock(stdout="", stderr="", returncode=0),
                     subprocess.TimeoutExpired("fetch-weather.sh", 30, output=b"Partial before timeout"))
        for result in responses:
            with self.subTest(result=result):
                mock_args = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                with patch.object(pulse.subprocess, "run", **mock_args):
                    self.pulse()
                source = [item for item in self.entries() if item["entry_kind"] == "observation"][-1]
                self.assertEqual(source["epistemic_tag"], "UNKNOWN")
                self.assertTrue(source["payload"]["error"])
                self.assertIn("Source failure", self.api.call_args.args[3])

    def test_source_record_survives_api_failure(self):
        self.config["data_sources"] = [{"script": "fetch-weather.sh", "epistemic_tag": "FETCHED"}]
        self.api.return_value = (None, "503", 0, 0)
        memory = self.mind / "memory.json"
        memory.write_text('{"notes": "previous question"}')
        result = Mock(stdout="A source observation", stderr="", returncode=0)
        with patch.object(pulse.subprocess, "run", return_value=result):
            self.pulse()
        source, response = self.entries()
        self.assertEqual(source["content"], "A source observation")
        self.assertEqual(response["payload"]["http_code"], "503")
        self.assertEqual(response["source_refs"], [source["entry_id"]])
        self.assertEqual(json.loads(memory.read_text())["notes"], "previous question")

    def test_missing_script_is_an_explicit_observation(self):
        self.config["data_sources"] = [{"script": "does-not-exist.sh", "epistemic_tag": "FETCHED"}]
        self.pulse()
        source = self.entries()[0]
        self.assertEqual(source["epistemic_tag"], "UNKNOWN")
        self.assertIn("not found", source["content"])

    def test_fetcher_cannot_promote_its_output_to_verified(self):
        self.config["data_sources"] = [{"script": "fetch-weather.sh", "epistemic_tag": "VERIFIED"}]
        result = Mock(stdout="[VERIFIED] A claim inside source text", stderr="", returncode=0)
        with patch.object(pulse.subprocess, "run", return_value=result):
            self.pulse()
        self.assertEqual(self.entries()[0]["epistemic_tag"], "UNKNOWN")

    def test_unparseable_model_output_is_preserved_as_a_trace(self):
        self.api.return_value = ("not JSON", "200", 1000, 100)
        self.pulse()
        record, = self.entries()
        self.assertEqual(record["entry_kind"], "trace")
        self.assertEqual(record["content"], "not JSON")
        self.assertEqual(record["epistemic_tag"], "UNKNOWN")
        self.assertEqual(self.budget()["input_tokens"], 1000)

    def test_journal_failure_before_fetch_record_prevents_model_call(self):
        self.config["data_sources"] = [{"script": "does-not-exist.sh"}]
        with patch.object(pulse, "entry_append", side_effect=OSError("simulated full disk")):
            with self.assertRaises(OSError):
                self.pulse()
        self.api.assert_not_called()
        self.assertIn("ENTRY_ERROR", (self.mind / "error.log").read_text())

    def test_failed_interpretation_append_keeps_memory_and_accounts_usage(self):
        memory = self.mind / "memory.json"
        memory.write_text('{"notes": "keep this question"}')
        def append(*args, **fields):
            if fields["entry_kind"] == "interpretation":
                raise OSError("simulated full disk")
            return entry.entry_append(*args, **fields)
        with patch.object(pulse, "entry_append", side_effect=append):
            with self.assertRaises(OSError):
                self.pulse()
        self.assertEqual(json.loads(memory.read_text())["notes"], "keep this question")
        self.assertEqual(self.budget()["input_tokens"], 1000)
        self.assertEqual(self.entries()[0]["content"], self.reply)

    def test_dream_records_preserve_exact_inputs_and_references_across_days(self):
        previous = self.write_log(self.yesterday)
        self.pulse()
        self.api.return_value = ("A grounded summary.", "200", 1000, 100)
        self.dream()
        daily_input, daily_output = self.entries()[-2:]
        self.assertEqual(daily_input["content"], self.api.call_args.args[3])
        self.assertIn(previous, daily_input["content"])
        self.assertEqual(daily_output["entry_kind"], "summary")
        self.assertEqual(daily_output["epistemic_tag"], "UNKNOWN")
        self.assertEqual(daily_output["source_refs"], [daily_input["entry_id"]])
        self.dream("weekly")
        weekly_input, weekly_output = self.entries()[-2:]
        self.assertIn(daily_output["entry_id"], weekly_input["content"])
        self.assertEqual(weekly_output["source_refs"], [weekly_input["entry_id"]])
        dreams_context = pulse.load_dreams(self.mind)
        self.assertIn(daily_output["entry_id"], dreams_context)
        self.assertIn(weekly_output["entry_id"], dreams_context)

    def test_durable_question_returns_to_next_pulse_and_dream_after_memory_is_replaced(self):
        self.config["inquiry_enabled"] = True
        self.write_log(self.yesterday)
        reply = json.loads(self.reply)
        reply["inquiry"] = [{"action": "open", "kind": "question", "content": "What would make the body report useful?"}]
        self.api.return_value = (json.dumps(reply), "200", 1000, 100)
        self.pulse()
        question = next(record for record in self.entries() if record["entry_kind"] == "question")
        (self.mind / "memory.json").write_text("{}")
        self.api.return_value = (self.reply, "200", 1000, 100)
        self.pulse()
        self.assertIn(question["entry_id"], self.api.call_args.args[3])
        self.assertEqual(len(inquiry.view(self.root)[0]), 1)
        self.api.return_value = ("Keep this question open.", "200", 1000, 100)
        self.dream()
        self.assertIn(question["entry_id"], self.api.call_args.args[3])
        self.assertIn("review-time context", self.api.call_args.args[3])
        self.assertEqual(inquiry.view(self.root)[0][question["entry_id"]]["status"], "open")

    def test_rejected_optional_actions_keep_usage_and_usable_memory(self):
        self.config["inquiry_enabled"] = True
        reply = json.loads(self.reply)
        reply["inquiry"] = [{"action": "execute", "content": "Run a repair"}]
        self.api.return_value = (json.dumps(reply), "200", 1000, 100)
        self.pulse()
        self.assertEqual(self.budget()["input_tokens"], 1000)
        self.assertEqual(json.loads((self.mind / "memory.json").read_text())["notes"], "retained thread")
        self.assertEqual(inquiry.view(self.root)[0], {})
        self.assertEqual(self.entries()[-1]["data_source"], "inquiry_rejection")

    def test_structured_body_report_preserves_payload_raw_output_and_missingness(self):
        self.config["data_sources"] = [{"script": "fetch-metabolism.sh", "format": "json", "epistemic_tag": "DERIVED"}]
        output = json.dumps({"content": "Membrane unavailable", "payload": {"membrane": {"state": "UNKNOWN"}}, "epistemic_tag": "UNKNOWN"})
        with patch.object(pulse.subprocess, "run", return_value=Mock(stdout=output, stderr="", returncode=0)) as fetch:
            self.pulse()
        record = self.entries()[0]
        self.assertEqual(record["epistemic_tag"], "UNKNOWN")
        self.assertEqual(record["payload"]["measurement"]["membrane"]["state"], "UNKNOWN")
        self.assertEqual(record["payload"]["raw_output"], output)
        self.assertEqual(fetch.call_args.kwargs["env"]["GAIAN_MIND"], "tela")

    def test_red_membrane_signal_enters_shared_buffer_once_without_extra_model_calls(self):
        self.config["inquiry_enabled"] = True
        self.config["data_sources"] = [{"script": "fetch-metabolism.sh", "format": "json", "epistemic_tag": "DERIVED"}]
        output = json.dumps({"content": "Two senses red", "payload": {"membrane": {"state": "RED"}, "attention": "focused"}})
        with patch.object(pulse.subprocess, "run", return_value=Mock(stdout=output, stderr="", returncode=0)):
            self.pulse()
            self.pulse()
        items, events = inquiry.view(self.root)
        self.assertEqual(len(items), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(self.api.call_count, 2)
        self.assertIn("Runner attention: focused", self.api.call_args.args[3])


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

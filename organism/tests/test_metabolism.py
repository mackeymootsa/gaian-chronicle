"""Body sensing must report gaps, preserve privacy, and never repair the host."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import metabolism


class MetabolismTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gaian-body-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime = self.root / "nursery"
        self.mind = self.runtime / "tela"
        self.mind.mkdir(parents=True)
        self.proc = self.root / "proc"
        self.proc.mkdir()
        (self.proc / "loadavg").write_text("0.8 0.5 0.1 1/100 123\n")
        (self.proc / "meminfo").write_text("MemTotal: 10000 kB\nMemAvailable: 8000 kB\n")
        (self.proc / "uptime").write_text("864000 1000\n")
        self.budget = {"date": "2026-02-01", "spent_usd": 0.12, "pulses_run": 8, "dreams_run": 2}
        (self.mind / "budget.json").write_text(json.dumps(self.budget))
        self.thresholds = metabolism.load_thresholds(Path(__file__).resolve().parents[1] / "config" / "metabolism-thresholds.json")
        self.now = datetime(2026, 2, 1, 12, tzinfo=timezone.utc)

    def collect(self, ssh=(0, 0)):
        with patch.object(metabolism.os, "cpu_count", return_value=4), \
             patch.object(metabolism.shutil, "disk_usage", return_value=Mock(total=100, used=10)), \
             patch.object(metabolism, "ssh_counts", side_effect=ssh if isinstance(ssh, Exception) else None, return_value=ssh):
            return metabolism.collect(self.runtime, "tela", self.thresholds, now=self.now, proc=self.proc)

    def test_load_is_normalized_and_spend_includes_dreams_without_writing_state(self):
        before = (self.mind / "budget.json").read_bytes()
        result = self.collect()
        self.assertEqual(result["payload"]["body"]["load_per_core_pct"], 20)
        self.assertEqual(result["payload"]["economic"]["requests_today"], 10)
        self.assertEqual(result["payload"]["economic"]["cost_per_request_usd"], 0.012)
        self.assertEqual(result["epistemic_tag"], "DERIVED")
        self.assertEqual(len(result["content"].splitlines()), 1)
        self.assertEqual((self.mind / "budget.json").read_bytes(), before)
        self.assertEqual(list(self.mind.iterdir()), [self.mind / "budget.json"])

    def test_missing_sources_are_unknown_not_healthy_zeroes(self):
        (self.mind / "budget.json").unlink()
        (self.proc / "loadavg").unlink()
        result = self.collect(PermissionError("journal unavailable"))
        self.assertEqual(result["epistemic_tag"], "UNKNOWN")
        for group in ("body", "economic", "membrane"):
            self.assertEqual(result["payload"][group]["state"], "UNKNOWN")
            self.assertTrue(result["payload"][group]["errors"])

    def test_yesterdays_budget_does_not_become_todays_spend(self):
        self.budget["date"] = "2026-01-31"
        (self.mind / "budget.json").write_text(json.dumps(self.budget))
        economic = self.collect()["payload"]["economic"]
        self.assertEqual(economic["spent_usd_today"], 0)
        self.assertIsNone(economic["cost_per_request_usd"])
        self.assertEqual(economic["state"], "GREEN")

    def test_two_red_senses_request_focus_without_new_jobs(self):
        self.budget["spent_usd"] = 0.5
        (self.mind / "budget.json").write_text(json.dumps(self.budget))
        result = self.collect((150, 25))
        self.assertEqual(result["payload"]["attention"], "focused")
        self.assertTrue(result["payload"]["alerts"])

    def test_ssh_aggregation_excludes_addresses_and_rejects_partial_views(self):
        messages = ["Failed password for invalid user test from 192.0.2.1 port 1000 ssh2",
                    "Failed publickey for test from 192.0.2.1 port 1001 ssh2",
                    "Failed password for test from 2001:db8::1 port 1002 ssh2"]
        output = "\n".join(json.dumps({"MESSAGE": m}) for m in messages)
        with patch.object(metabolism.subprocess, "run", return_value=Mock(returncode=0, stderr="", stdout=output)) as run:
            self.assertEqual(metabolism.ssh_counts(self.now), (3, 2))
            self.assertEqual(run.call_args.args[0][0], "journalctl")
            self.assertEqual(run.call_args.kwargs["timeout"], 5)
        for result in (Mock(returncode=0, stderr="permission notice", stdout=output),
                       Mock(returncode=0, stderr="", stdout=""),
                       Mock(returncode=0, stderr="", stdout='{"MESSAGE":"noise"}\n' * 5000)):
            with patch.object(metabolism.subprocess, "run", return_value=result):
                with self.assertRaises(ValueError):
                    metabolism.ssh_counts(self.now)

    def test_storage_scan_does_not_follow_symlinks(self):
        outside = self.root / "private"
        outside.mkdir()
        (outside / "large").write_bytes(b"x" * 20000)
        (self.mind / "outside").symlink_to(outside, target_is_directory=True)
        self.assertLess(metabolism.tree_kb(self.mind), 1)

    def test_invalid_thresholds_and_budgets_do_not_produce_false_health(self):
        bad = self.root / "bad-thresholds.json"
        self.thresholds["body"]["ram_pct"]["red"] = 20
        bad.write_text(json.dumps(self.thresholds))
        with self.assertRaises(ValueError):
            metabolism.load_thresholds(bad)
        for spent in (-1, "many", float("nan")):
            self.budget["spent_usd"] = spent
            (self.mind / "budget.json").write_text(json.dumps(self.budget))
            self.assertEqual(self.collect()["payload"]["economic"]["state"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

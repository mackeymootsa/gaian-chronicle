"""Storage invariants for the canonical entry log; no model calls."""

import tempfile
import json
import subprocess
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry import EntryLogError, entry_append, read_entries


class EntryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gaian-entries-test-")
        self.addCleanup(temporary.cleanup)
        self.entries = Path(temporary.name) / "entries"

    def append(self, **overrides):
        fields = {"author": "tela", "entry_kind": "observation", "content": "Snow, moss, and blåbär.\nTwo lines.",
                  "timestamp": "2026-01-31T23:59:00Z"}
        fields.update(overrides)
        return entry_append(self.entries, **fields)

    def test_records_survive_month_rotation_with_stable_ids_and_exact_content(self):
        first = self.append()
        january = self.entries / "entries-2026-01.jsonl"
        original = january.read_bytes()
        second = self.append(timestamp="2026-02-01T00:01:00Z", source_refs=[first["entry_id"]])
        self.assertEqual(january.read_bytes(), original)
        self.assertEqual(list(read_entries(self.entries)), [first, second])
        self.assertEqual(list(read_entries(self.entries, entry_ids=[first["entry_id"]])), [first])
        self.assertEqual(list(read_entries(self.entries, day="2026-02-01")), [second])
        self.assertEqual(first["schema_version"], "0.1.0")
        self.assertEqual(first["epistemic_tag"], "UNKNOWN")

    def test_rotation_uses_utc_even_when_input_timestamp_has_an_offset(self):
        record = self.append(timestamp="2026-02-01T00:30:00+01:00")
        self.assertEqual(record["timestamp"], "2026-01-31T23:30:00Z")
        self.assertTrue((self.entries / "entries-2026-01.jsonl").exists())

    def test_concurrent_writers_preserve_all_complete_records(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            records = list(pool.map(lambda number: self.append(content=f"Observation {number}"), range(40)))
        saved = list(read_entries(self.entries))
        self.assertEqual(len(saved), 40)
        self.assertEqual({record["entry_id"] for record in saved}, {record["entry_id"] for record in records})
        self.assertEqual(len({record["entry_id"] for record in saved}), 40)

    def test_interrupted_tail_is_preserved_and_further_appends_fail(self):
        self.append()
        journal = self.entries / "entries-2026-01.jsonl"
        with journal.open("ab") as stream:
            stream.write(b'{"entry_id":"interrupted')
        original = journal.read_bytes()
        with self.assertRaisesRegex(EntryLogError, "Incomplete final record"):
            self.append(content="Later observation")
        self.assertEqual(journal.read_bytes(), original)
        with self.assertRaisesRegex(EntryLogError, "Unreadable record"):
            list(read_entries(self.entries))

    def test_invalid_records_never_reach_the_journal(self):
        for overrides in ({"author": "../tela"}, {"entry_kind": "falsified"},
                          {"epistemic_tag": "CERTAIN"}, {"source_refs": "one string"},
                          {"content": ""}, {"timestamp": "2026-01-31T12:00:00"},
                          {"payload": {"value": float("nan")}}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.append(**overrides)
        self.assertFalse(self.entries.exists())

    def test_read_command_resolves_an_id_and_reports_a_missing_id(self):
        record = self.append()
        command = [sys.executable, "-B", str(Path(__file__).resolve().parents[1] / "entry.py"),
                   "--entries-dir", str(self.entries), "--id"]
        found = subprocess.run(command + [record["entry_id"]], capture_output=True, text=True, timeout=10)
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(json.loads(found.stdout), record)
        missing = subprocess.run(command + ["missing-entry"], capture_output=True, text=True, timeout=10)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("not found", missing.stderr)


if __name__ == "__main__":
    unittest.main()

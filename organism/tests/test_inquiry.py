"""Inquiry lifecycle, authority, silence, and survival across context replacement."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from entry import entry_append, read_entries
import inquiry


class InquiryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gaian-inquiry-test-")
        self.addCleanup(temporary.cleanup)
        self.runtime = Path(temporary.name)
        self.time = "2026-01-31T12:00:00Z"
        self.evidence = entry_append(self.runtime / "entries", author="tela", entry_kind="observation",
                                    content="Source reports 2 degrees", timestamp=self.time)["entry_id"]

    def submit(self, actions, author="tela", **kwargs):
        return inquiry.submit(self.runtime, author, actions, timestamp=kwargs.pop("timestamp", self.time), **kwargs)

    def open(self, content="Is the new sensing useful?", author="tela", **kwargs):
        return self.submit([{"action": "open", "kind": "question", "content": content, **kwargs}], author=author)[0]

    def test_question_survives_memory_replacement_and_month_rotation(self):
        question = self.open()
        original = (self.runtime / "entries" / "entries-2026-01.jsonl").read_bytes()
        (self.runtime / "memory.json").write_text("{}")
        self.submit([{"action": "status", "target_id": question["entry_id"], "status": "resolved",
                      "content": "Review found a useful signal", "source_refs": [self.evidence]}], timestamp="2026-02-02T01:00:00Z")
        items, _ = inquiry.view(self.runtime)
        self.assertEqual(items[question["entry_id"]]["status"], "resolved")
        self.assertEqual((self.runtime / "entries" / "entries-2026-01.jsonl").read_bytes(), original)
        self.assertEqual(items[question["entry_id"]]["content"], question["content"])

    def test_other_minds_can_comment_but_only_owner_or_nova_can_close(self):
        question = self.open()
        action = {"action": "status", "target_id": question["entry_id"], "status": "resolved",
                  "content": "I think this is settled", "source_refs": [self.evidence]}
        with self.assertRaisesRegex(ValueError, "owner or Nova"):
            self.submit([action], author="nowa")
        self.submit([{"action": "comment", "target_id": question["entry_id"], "content": "Another possibility"}], author="nowa")
        self.submit([action], author="nova")
        items, _ = inquiry.view(self.runtime)
        self.assertEqual(items[question["entry_id"]]["status_by"], "nova")
        self.assertEqual(items[question["entry_id"]]["comments"][0]["author"], "nowa")

    def test_missing_and_unsupplied_evidence_cannot_close_a_question(self):
        question = self.open()
        for refs, allowed in (([], None), (["invented"], None), ([self.evidence], {question["entry_id"]})):
            with self.subTest(refs=refs):
                with self.assertRaises(ValueError):
                    self.submit([{"action": "status", "target_id": question["entry_id"], "status": "resolved",
                                  "content": "Done", "source_refs": refs}], allowed_refs=allowed)
        items, _ = inquiry.view(self.runtime)
        self.assertEqual(items[question["entry_id"]]["status"], "open")

    def test_kind_is_not_belief_status_and_questions_cannot_be_falsified(self):
        question = self.open()
        with self.assertRaisesRegex(ValueError, "question cannot be falsified"):
            self.submit([{"action": "status", "target_id": question["entry_id"], "status": "falsified",
                          "content": "Wrong", "source_refs": [self.evidence]}])
        watchpoint = self.submit([{"action": "open", "kind": "watchpoint", "content": "If a second source disagrees, revisit this measurement",
                                  "source_refs": [self.evidence]}])[0]
        self.submit([{"action": "status", "target_id": watchpoint["entry_id"], "status": "falsified",
                      "content": "Independent source contradicts the claim", "source_refs": [self.evidence]}])
        self.assertEqual(inquiry.view(self.runtime)[0][watchpoint["entry_id"]]["kind"], "watchpoint")

    def test_invalid_batch_and_executable_fields_append_nothing(self):
        before = list(read_entries(self.runtime / "entries"))
        with self.assertRaises(ValueError):
            self.submit([{"action": "open", "kind": "question", "content": "Valid first item"},
                         {"action": "open", "kind": "proposal", "content": "Run this", "command": "curl example.invalid"}])
        self.assertEqual(list(read_entries(self.runtime / "entries")), before)

    def test_duplicate_opens_and_acknowledgment_loops_are_bounded(self):
        question = self.open()
        self.assertEqual(self.submit([{"action": "open", "kind": "question", "content": question["content"]}]), [])
        action = {"action": "comment", "target_id": question["entry_id"], "content": "Acknowledged"}
        self.submit([action], author="nowa")
        with self.assertRaisesRegex(ValueError, "One contribution"):
            self.submit([action], author="nowa")
        self.submit([action], author="nowa", timestamp="2026-02-01T01:00:00Z")

    def test_concurrent_opens_do_not_exceed_active_ceiling(self):
        for n in range(8):
            self.open(f"Question {n}")
        def add(n):
            try:
                self.open(f"Concurrent question {n}")
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            successes = list(pool.map(add, range(2)))
        self.assertEqual(sum(successes), 1)
        self.assertEqual(len(inquiry.view(self.runtime)[0]), 9)

    def test_revisit_date_and_context_limit_preserve_items_outside_prompt(self):
        self.open("Rest this until spring", revisit_on="2026-04-01")
        for author in ("tela", "nowa", "tecton"):
            for n in range(6):
                self.open(f"{n}: " + "x" * 690, author=author)
        text, refs = inquiry.context(self.runtime, "tela", "2026-02-01")
        self.assertLessEqual(len(text), 6500)
        self.assertNotIn("Rest this until spring", text)
        self.assertEqual(len(inquiry.view(self.runtime)[0]), 19)
        self.assertEqual(json.loads(text)["open_total"], 19)
        self.assertTrue(refs)

    def test_old_peer_evidence_stays_attached_to_a_due_question(self):
        question = self.open()
        comment = self.submit([{"action": "comment", "target_id": question["entry_id"],
                                "content": "Evidence to revisit next month"}], author="nowa")[0]
        text, refs = inquiry.context(self.runtime, "tela", "2026-03-01")
        self.assertIn(comment["content"], text)
        self.assertIn(comment["entry_id"], refs)


if __name__ == "__main__":
    unittest.main()

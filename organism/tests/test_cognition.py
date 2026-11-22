"""Investigation continuity, evidence provenance, and bounded adapter authority."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cognition
from entry import EntryLogError, entry_append, read_entries
from palace import Palace
import threads
import watchpoints


class CognitionFixture:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gaian-investigation-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.time = "2026-02-01T06:00:00Z"
        self.policy = cognition.load_policy()
        self.policy["seed_thread"] = None

    def record(self, content="Disk baseline", **kwargs):
        return entry_append(self.root / "entries", author=kwargs.pop("author", "tela"),
                            entry_kind=kwargs.pop("entry_kind", "observation"), content=content,
                            timestamp=kwargs.pop("timestamp", self.time), **kwargs)

    def submit(self, actions, author="tela", **kwargs):
        return cognition.submit(self.root, author, actions, timestamp=kwargs.pop("timestamp", self.time), policy=self.policy, **kwargs)

    def thread(self, key="disk-continuity", refs=None):
        return self.submit([{"op": "thread_open", "key": key, "name": "Disk continuity",
                             "content": "Is our growing journal sustainable?", "horizon": "Explain a change with evidence",
                             "source_refs": refs or []}])[0]

    def sample(self, value, timestamp, *, sample_time=None, error=None):
        return self.record(f"Disk measurement: {value}", timestamp=timestamp,
            data_source="Organism Metabolism", source_refs=["fetch-metabolism.sh"],
            epistemic_tag="DERIVED" if not error else "UNKNOWN",
            payload={"returncode": 0 if not error else 1, "error": error,
                     "measurement": {"sampled_at": timestamp if sample_time is None else sample_time,
                        "body": {"disk_pct": value, "metric_states": {"disk_pct": "GREEN"}}}})

    def prepare(self, timestamp=None, mind="tela"):
        return cognition.prepare(self.root, mind, timestamp=timestamp or self.time, policy=self.policy)

    def watch(self, target, threshold=30, confirmations=2):
        return self.submit([{"op": "watch", "target_id": target, "metric": "body.disk_pct",
                             "operator": "gt", "threshold": threshold, "confirm_samples": confirmations,
                             "content": "Revisit the capacity assumption if disk usage grows"}])[0]

    def annotation(self, target, wing="observation", room="organism-health", reason="Measured body state"):
        return {"op": "classify", "entry_id": target, "primary_wing": wing,
                "primary_room": room, "reason": reason, "status": "open"}


class CognitionTests(CognitionFixture, unittest.TestCase):

    def test_full_investigation_recalls_baseline_and_revises_after_confirmed_measurements(self):
        baseline = self.sample(20, self.time)
        thread = self.thread(refs=[baseline["entry_id"]])
        watch = self.watch(thread["entry_id"])
        self.prepare()
        self.sample(40, "2026-02-01T07:00:00Z")
        self.prepare("2026-02-01T07:01:00Z")
        last = watchpoints.project(Palace(self.root).records)[watch["entry_id"]]["last"]
        self.assertFalse(last["notify"])
        changed = self.sample(45, "2026-02-01T08:00:00Z")
        context, allowed, receipt = self.prepare("2026-02-01T08:01:00Z")
        last = watchpoints.project(Palace(self.root).records)[watch["entry_id"]]["last"]
        self.assertTrue(last["notify"])
        self.assertIn(changed["entry_id"], allowed)
        self.assertEqual(threads.project(Palace(self.root).records)[thread["entry_id"]]["status"], "active")
        request = self.submit([{"op": "recall", "entry_ids": [baseline["entry_id"]],
                                "content": "Recover the actual baseline before revising"}], allowed_refs=allowed)[0]
        # Working memory and the disposable index are not the investigation.
        (self.root / "memory.json").write_text("{}")
        index = Palace(self.root).rebuild()
        index.unlink()
        context, allowed, _ = self.prepare("2026-02-01T08:10:00Z")
        self.assertIn(baseline["content"], context)
        self.assertIn(request["entry_id"], context)
        advance = self.submit([{"op": "thread_advance", "target_id": thread["entry_id"],
            "content": "Disk readings rose from 20 to 45. The earlier capacity assumption needs review.",
            "next_question": "Is the growth sustained or temporary?", "source_refs": [changed["entry_id"]]}], allowed_refs=allowed)[0]
        view = threads.project(Palace(self.root).records)[thread["entry_id"]]
        self.assertEqual(view["position"], advance["content"])
        self.assertIn(baseline["entry_id"], view["source_refs"])
        self.assertEqual(list(read_entries(self.root / "entries", entry_ids=[baseline["entry_id"]]))[0], baseline)
        self.assertTrue(receipt)

    def test_annotations_preserve_raw_bytes_and_independent_minds_views(self):
        raw = self.record()
        journal = self.root / "entries" / "entries-2026-02.jsonl"
        before = journal.read_bytes()
        first = self.submit([self.annotation(raw["entry_id"])], response_id=raw["entry_id"], pulse_id="pulse-example")[0]
        self.submit([self.annotation(raw["entry_id"], "tension", reason="A missing context matters")], author="nowa")
        revised = self.submit([self.annotation(raw["entry_id"], "interpretation", reason="Reading changed after review")])[0]
        palace = Palace(self.root)
        self.assertEqual(journal.read_bytes(), before)
        self.assertEqual(len(palace.annotations), 3)
        self.assertEqual(len(palace.opinions(raw["entry_id"])), 2)
        self.assertEqual(revised["supersedes"], first["annotation_id"])
        self.assertEqual(first["response_id"], raw["entry_id"])
        self.assertEqual(first["pulse_id"], "pulse-example")
        self.assertEqual({a["annotator"] for a in palace.opinions(raw["entry_id"])}, {"tela", "nowa"})
        self.assertEqual(len(palace.tunnels()), 1)

    def test_search_filters_use_one_attributed_classification_and_rebuild_ignores_cache(self):
        raw = self.record("Pressure record")
        self.submit([self.annotation(raw["entry_id"], "observation", "atmosphere")])
        self.submit([self.annotation(raw["entry_id"], "tension", "sensor-health")], author="nowa")
        palace = Palace(self.root)
        self.assertEqual(palace.search("pressure", room="Atmosphere", wing="tension"), [])
        self.assertEqual(palace.search("pressure", room="Atmosphere", wing="observation"), [raw])
        index = palace.rebuild()
        index.write_text("broken disposable cache")
        self.assertEqual(Palace(self.root).search("pressure"), [raw])
        Palace(self.root).rebuild()
        self.assertEqual(json.loads(index.read_text())["entry_count"], 1)

    def test_interrupted_annotation_tail_is_retained_and_reported(self):
        raw = self.record()
        self.submit([self.annotation(raw["entry_id"])])
        path = self.root / "annotations" / "annotations-2026-02.jsonl"
        with path.open("ab") as stream:
            stream.write(b'{"interrupted":')
        before = path.read_bytes()
        with self.assertRaises(EntryLogError):
            self.prepare()
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_second_action_does_not_commit_the_first_annotation(self):
        raw = self.record()
        with self.assertRaises(ValueError):
            self.submit([self.annotation(raw["entry_id"]), {"op": "recall", "query": "disk", "content": "Read it", "path": "/etc/passwd"}])
        self.assertEqual(Palace(self.root).annotations, [])
        self.assertEqual(len(Palace(self.root).records), 1)

    def test_unsupplied_targets_and_fabricated_evidence_are_rejected(self):
        raw = self.record()
        with self.assertRaises(ValueError):
            self.submit([self.annotation(raw["entry_id"])], allowed_refs=set())
        with self.assertRaises(ValueError):
            self.submit([{"op": "recall", "entry_ids": ["invented"], "content": "Find this"}])
        with self.assertRaises(ValueError):
            self.thread(refs=["invented"])

    def test_recall_is_served_once_and_empty_search_is_explicit(self):
        self.record("Snow and frost")
        request = self.submit([{"op": "recall", "query": "butterfly", "content": "Check for a missing observation"}])[0]
        self.prepare()
        self.prepare()
        results = [r for r in Palace(self.root).records if r.get("data_source") == "recall_result"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["payload"]["request_id"], request["entry_id"])
        self.assertEqual(json.loads(results[0]["content"])["records"], [])

    def test_provenance_walk_surfaces_missing_file_refs_and_marks_excerpts(self):
        raw = self.record("long source " * 200, source_refs=["legacy-file.md"])
        summary = self.record("Brief reading", entry_kind="summary", source_refs=[raw["entry_id"]])
        self.submit([{"op": "recall", "entry_ids": [summary["entry_id"]], "content": "Check the source"}])
        self.prepare()
        result = next(r for r in Palace(self.root).records if r.get("data_source") == "recall_result")
        body = json.loads(result["content"])
        self.assertEqual(body["unresolved_refs"], ["legacy-file.md"])
        self.assertTrue(body["records"][1]["truncated"])
        limited, missing, clipped = Palace(self.root).walk([summary["entry_id"]], depth=0)
        self.assertEqual(limited, [summary])
        self.assertEqual(missing, [])
        self.assertTrue(clipped)

    def test_seed_is_attributed_and_never_reopens_a_resting_thread(self):
        policy = cognition.load_policy()
        cognition.prepare(self.root, "tela", timestamp=self.time, policy=policy)
        seeded, = threads.project(Palace(self.root).records).values()
        self.assertTrue(seeded["seed"])
        self.assertEqual(seeded["position_by"], "runner")
        self.submit([{"op": "thread_status", "target_id": seeded["id"], "status": "resting", "content": "Let this rest"}])
        cognition.prepare(self.root, "tela", timestamp=self.time, policy=policy)
        self.assertEqual(len(threads.project(Palace(self.root).records)), 1)
        self.assertEqual(threads.project(Palace(self.root).records)[seeded["id"]]["status"], "resting")

    def test_thread_advance_needs_additional_evidence_and_cannot_cite_its_own_advance(self):
        first = self.record()
        thread = self.thread(refs=[first["entry_id"]])
        action = {"op": "thread_advance", "target_id": thread["entry_id"], "content": "New position",
                  "next_question": "What changed?", "source_refs": [first["entry_id"]]}
        with self.assertRaises(ValueError):
            self.submit([action])
        new = self.record("Independent later observation")
        action["source_refs"] = [new["entry_id"]]
        advance = self.submit([action])[0]
        action["source_refs"] = [advance["entry_id"]]
        with self.assertRaises(ValueError):
            self.submit([action])

    def test_lifecycle_control_and_global_thread_limit_hold_under_concurrent_writers(self):
        for number in range(8):
            self.thread(key=f"thread-{number}")
        def open_thread(number):
            try:
                return self.thread(key=f"concurrent-{number}")
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            opened = [item for item in pool.map(open_thread, range(2)) if item]
        self.assertEqual(len(opened), 1)
        target = opened[0]["entry_id"]
        with self.assertRaises(ValueError):
            self.submit([{"op": "thread_status", "target_id": target, "status": "ancestral", "content": "End it"}], author="nowa")
        self.submit([{"op": "thread_status", "target_id": target, "status": "ancestral", "content": "Keep this as history"}], author="nova")
        self.assertEqual(len(threads.project(Palace(self.root).records)), 9)

    def test_action_ceiling_includes_annotations_and_other_adapters(self):
        raw = self.record()
        for number in range(12):
            self.submit([self.annotation(raw["entry_id"], reason=f"Review {number}")])
        with self.assertRaisesRegex(ValueError, "Daily cognition"):
            self.submit([{"op": "recall", "query": "disk", "content": "Read it again"}])

    def test_batch_opens_cannot_cross_global_limits_and_reject_the_entire_batch(self):
        for number in range(8):
            self.thread(key=f"thread-{number}")
        action = {"op": "thread_open", "key": "last-slot", "name": "Another question",
                  "content": "Do these limits hold?", "horizon": "Retain eight threads"}
        with self.assertRaises(ValueError):
            self.submit([action, {**action, "key": "one-too-many"}], author="nova")
        self.assertEqual(len(threads.project(Palace(self.root).records)), 8)
        target = next(iter(threads.project(Palace(self.root).records)))
        watch_action = {"op": "watch", "target_id": target, "metric": "body.disk_pct",
                        "operator": "gt", "threshold": 30, "content": "Test capacity"}
        for number in range(5):
            self.submit([{**watch_action, "threshold": number}], author="nova")
        with self.assertRaises(ValueError):
            self.submit([watch_action, {**watch_action, "threshold": 31}], author="nova")
        self.assertEqual(len(watchpoints.project(Palace(self.root).records)), 5)

    def test_context_bound_excludes_unsupplied_ids_and_preserves_full_history(self):
        for number in range(8):
            raw = self.record(f"Observation {number}: " + "x" * 800)
            self.submit([self.annotation(raw["entry_id"], reason="r" * 700)], author="nova")
        self.thread()
        self.submit([{"op": "recall", "query": "Observation", "content": "Gather these records"}])
        text, refs, receipt = self.prepare()
        self.assertLessEqual(len(text), cognition.MAX_CONTEXT_CHARS)
        dossier = json.loads(text)
        visible = {r["entry_id"] for result in dossier["recall"] for r in result["records"]}
        self.assertTrue(visible <= refs)
        self.assertEqual(len([r for r in Palace(self.root).records if r["entry_kind"] == "observation"]), 8)
        self.assertIn(receipt, refs)


class WatchpointTests(CognitionFixture, unittest.TestCase):
    def last(self, watch):
        return watchpoints.project(Palace(self.root).records)[watch["entry_id"]]["last"]

    def test_repeated_timestamp_is_not_a_second_confirmation(self):
        thread = self.thread()
        watch = self.watch(thread["entry_id"])
        self.sample(40, self.time)
        self.prepare()
        self.sample(40, "2026-02-01T06:10:00Z", sample_time=self.time)
        self.prepare("2026-02-01T06:11:00Z")
        self.assertEqual(self.last(watch)["streak"], 1)
        self.assertFalse(self.last(watch)["notify"])

    def test_latest_failure_and_staleness_do_not_fall_back_to_old_success(self):
        thread = self.thread()
        watch = self.watch(thread["entry_id"], confirmations=1)
        self.sample(40, self.time)
        self.prepare()
        self.assertTrue(self.last(watch)["notify"])
        self.prepare("2026-02-01T09:00:01Z")
        self.assertIsNone(self.last(watch)["matched"])
        self.assertIn("stale", self.last(watch)["error"])
        self.sample(None, "2026-02-01T09:01:00Z", error="source unavailable")
        self.prepare("2026-02-01T09:02:00Z")
        self.assertEqual(self.last(watch)["error"], "Latest source failed")
        self.assertIsNone(self.last(watch)["value"])

    def test_empty_sample_timestamp_cannot_become_a_fresh_measurement(self):
        thread = self.thread()
        watch = self.watch(thread["entry_id"], confirmations=1)
        self.sample(40, self.time, sample_time="")
        self.prepare()
        self.assertIsNone(self.last(watch)["matched"])
        self.assertIn("timestamp", self.last(watch)["error"])

    def test_sample_gap_resets_consecutive_confirmations(self):
        thread = self.thread()
        watch = self.watch(thread["entry_id"])
        self.sample(40, self.time)
        self.prepare()
        self.sample(42, "2026-02-01T10:00:00Z")
        self.prepare("2026-02-01T10:01:00Z")
        self.assertTrue(self.last(watch)["sample_gap"])
        self.assertEqual(self.last(watch)["streak"], 1)
        self.assertFalse(self.last(watch)["notify"])

    def test_future_out_of_order_and_non_numeric_values_are_unknown(self):
        thread = self.thread()
        watch = self.watch(thread["entry_id"])
        self.sample(40, self.time)
        self.prepare()
        self.sample(41, "2026-02-01T06:10:00Z", sample_time="2026-02-01T05:59:00Z")
        self.prepare("2026-02-01T06:11:00Z")
        self.assertIn("backwards", self.last(watch)["error"])
        self.sample(42, "2026-02-01T06:20:00Z", sample_time="2026-02-01T08:00:00Z")
        self.prepare("2026-02-01T06:21:00Z")
        self.assertIn("future", self.last(watch)["error"])
        self.sample("forty", "2026-02-01T06:30:00Z")
        self.prepare("2026-02-01T06:31:00Z")
        self.assertIsNone(self.last(watch)["matched"])

    def test_cooldown_limits_repeated_episodes_but_keeps_measurements(self):
        thread = self.thread()
        watch = self.watch(thread["entry_id"], confirmations=1)
        for value, stamp in ((40, "2026-02-01T06:00:00Z"), (20, "2026-02-01T07:00:00Z"), (41, "2026-02-01T08:00:00Z")):
            self.sample(value, stamp)
            self.prepare(stamp)
        self.assertTrue(self.last(watch)["confirmed"])
        self.assertFalse(self.last(watch)["notify"])
        events = [r for r in Palace(self.root).records if r.get("data_source") == watchpoints.EVALUATIONS]
        self.assertEqual(len(events), 3)
        self.assertEqual(sum(r["payload"]["evaluation"]["notify"] for r in events), 1)

    def test_disabled_metric_is_a_gap_and_generated_text_cannot_impersonate_a_sensor(self):
        thread = self.thread()
        watch = self.watch(thread["entry_id"], confirmations=1)
        self.record("Disk is 99 percent", entry_kind="interpretation", data_source="Organism Metabolism",
                    source_refs=["fetch-metabolism.sh"])
        self.prepare()
        self.assertEqual(self.last(watch)["error"], "No source record")
        self.policy["metrics"] = {}
        self.prepare()
        self.assertIn("disabled", self.last(watch)["error"])
        self.assertIsNone(self.last(watch)["value"])

    def test_economic_watch_does_not_substitute_another_minds_budget(self):
        target = self.thread()["entry_id"]
        watch = self.submit([{"op": "watch", "target_id": target, "metric": "economic.spent_usd_today",
            "operator": "gt", "threshold": 0.1, "confirm_samples": 1, "content": "Review Tela's cost"}])[0]
        for author, timestamp, value in (("tela", self.time, 0.05), ("nowa", "2026-02-01T06:01:00Z", 0.9)):
            self.record("Per-mind budget", author=author, timestamp=timestamp,
                data_source="Organism Metabolism", source_refs=["fetch-metabolism.sh"],
                payload={"returncode": 0, "measurement": {"sampled_at": timestamp,
                    "economic": {"spent_usd_today": value, "metric_states": {"spent_usd_today": "GREEN"}}}})
        self.prepare("2026-02-01T06:02:00Z")
        self.assertEqual(self.last(watch)["value"], 0.05)
        self.assertFalse(self.last(watch)["notify"])

    def test_watchpoints_cannot_add_sources_or_execute_expressions(self):
        thread = self.thread()
        action = {"op": "watch", "target_id": thread["entry_id"], "metric": "body.disk_pct",
                  "operator": "gt", "threshold": 30, "content": "Watch disk"}
        for changed in ({"metric": "../../private"}, {"operator": "eval"}, {"threshold": float("nan")},
                        {"threshold": 101}, {"command": "repair"}, {"confirm_samples": 0}):
            with self.subTest(changed=changed):
                with self.assertRaises((ValueError, TypeError)):
                    self.submit([{**action, **changed}])
        self.assertEqual(watchpoints.project(Palace(self.root).records), {})

    def test_global_watch_limit_and_retirement_are_enforced(self):
        thread = self.thread()
        watches = [self.watch(thread["entry_id"], threshold=n) for n in range(6)]
        with self.assertRaises(ValueError):
            self.watch(thread["entry_id"], threshold=7)
        action = {"op": "watch_status", "target_id": watches[0]["entry_id"], "status": "retired", "content": "No longer useful"}
        with self.assertRaises(ValueError):
            self.submit([action], author="nowa")
        self.submit([action], author="nova")
        self.sample(90, self.time)
        self.prepare()
        self.assertIsNone(self.last(watches[0]))


if __name__ == "__main__":
    unittest.main()

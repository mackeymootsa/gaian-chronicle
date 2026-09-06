#!/usr/bin/env python3
"""Bounded local investigation adapters for existing organism pulses."""

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path

from entry import entry_append
from palace import Palace, WINGS, text_field, utc
import threads
import watchpoints

POLICY_PATH = Path(__file__).resolve().parent / "config" / "cognition.json"
MAX_ACTIONS = 3
MAX_DAILY_ACTIONS = 12
MAX_CONTEXT_CHARS = 8500


def load_policy(path=POLICY_PATH):
    policy = json.loads(Path(path).read_text())
    for name, metric in policy["metrics"].items():
        if not isinstance(name, str) or not isinstance(metric["source"], str):
            raise ValueError("Invalid metric manifest")
        if "author" in metric and (not isinstance(metric["author"], str) or not metric["author"]):
            raise ValueError("Metric author must be an explicit mind name")
        for key in ("value_path", "time_path", "quality_path"):
            if not isinstance(metric[key], list) or not metric[key] or any(not isinstance(p, str) or not p for p in metric[key]):
                raise ValueError("Metric paths must be explicit non-empty lists of keys")
        if not all(watchpoints.finite(metric[k]) for k in ("min", "max", "max_age_seconds")):
            raise ValueError("Metric bounds and maximum age must be finite")
        if metric["min"] >= metric["max"] or not 1 <= metric["max_age_seconds"] <= 86400:
            raise ValueError("Invalid metric range or freshness bound")
    return policy


@contextmanager
def cognition_lock(runtime):
    runtime = Path(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "cognition.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def append(palace, **fields):
    record = entry_append(palace.runtime / "entries", **fields)
    palace.records.append(record)
    palace.by_id[record["entry_id"]] = record
    return record


def references(action, palace, allowed):
    refs = action.get("source_refs", [])
    if not isinstance(refs, list) or len(refs) > 6 or any(
            not isinstance(ref, str) or ref not in palace.by_id or allowed is not None and ref not in allowed for ref in refs):
        raise ValueError("References must name up to six existing records supplied to this pulse")
    return list(dict.fromkeys(refs))


def supplied(target, palace, allowed):
    if not isinstance(target, str) or target not in palace.by_id or allowed is not None and target not in allowed:
        raise ValueError("Target must be an existing record supplied to this pulse")


def plan_recall(action, palace, allowed):
    if set(action) - {"op", "query", "entry_ids", "room", "wing", "since", "content"}:
        raise ValueError("Recall cannot read arbitrary files, URLs or commands")
    ids = action.get("entry_ids", [])
    if not isinstance(ids, list) or len(ids) > 3:
        raise ValueError("Recall supports at most three supplied entry IDs")
    for entry_id in ids:
        supplied(entry_id, palace, allowed)
    query = action.get("query", "")
    if not ids and not query and not action.get("room") and not action.get("wing"):
        raise ValueError("Recall needs a query, room, wing or supplied entry ID")
    filters = {key: action[key] for key in ("room", "wing", "since") if key in action}
    palace.search(query, **filters, limit=1)  # Validate the selector without writing.
    return {"entry_kind": "trace", "data_source": "recall_request",
            "content": text_field(action.get("content"), "why recall"), "source_refs": ids,
            "payload": {"recall": {"query": query, "entry_ids": ids, **filters}, "cognition_action": True}}


def submit(runtime, author, actions, *, allowed_refs=None, response_id=None, pulse_id=None, timestamp=None, policy=None):
    if not isinstance(actions, list) or len(actions) > MAX_ACTIONS:
        raise ValueError("cognition must contain at most three actions")
    if not actions:
        return []
    policy = policy or load_policy()
    moment = utc(timestamp)
    with cognition_lock(runtime):
        palace = Palace(runtime)
        daily = sum(r["author"] == author and r["timestamp"][:10] == moment.date().isoformat()
                    and r.get("payload", {}).get("cognition_action", False) for r in palace.records)
        daily += sum(a["annotator"] == author and a["timestamp"][:10] == moment.date().isoformat() for a in palace.annotations)
        if author != "nova" and daily + len(actions) > MAX_DAILY_ACTIONS:
            raise ValueError("Daily cognition action ceiling reached")
        planned, touched = [], set()
        simulated = list(palace.records)
        for action in actions:
            if not isinstance(action, dict) or not isinstance(action.get("op"), str):
                raise ValueError("Every cognition action needs an op string")
            op = action["op"]
            if op == "classify":
                annotation = palace.annotation(author, action, moment.isoformat(), allowed_refs)
                if response_id:
                    annotation["response_id"] = response_id
                if pulse_id:
                    annotation["pulse_id"] = pulse_id
                key = ("classify", annotation["entry_id"])
                planned.append(("annotation", annotation))
            else:
                if op.startswith("thread_"):
                    refs = references(action, palace, allowed_refs)
                    if op != "thread_open":
                        supplied(action.get("target_id"), palace, allowed_refs)
                    fields = threads.plan(action, author, simulated, refs)
                    key = ("thread", fields["payload"]["thread"].get("key", action.get("target_id")))
                elif op in ("watch", "watch_status"):
                    supplied(action.get("target_id"), palace, allowed_refs)
                    fields = watchpoints.plan(action, author, simulated, policy["metrics"])
                    key = ("watch", action["target_id"], action.get("metric"))
                elif op == "recall":
                    fields = plan_recall(action, palace, allowed_refs)
                    key = ("recall", author)
                else:
                    raise ValueError("Unknown cognition adapter")
                fields.update(author=author, timestamp=moment.isoformat(), pulse_id=pulse_id)
                if response_id:
                    fields["source_refs"] = list(dict.fromkeys(fields.get("source_refs", []) + [response_id]))
                planned.append(("entry", fields))
                # Simulate earlier opens/status updates to enforce global limits
                # for a multi-action batch before writing any part of it.
                simulated.append({**fields, "entry_id": f"planned-{len(planned)}"})
            if key in touched:
                raise ValueError("Only one action per target/adapter in a pulse")
            touched.add(key)
        saved = []
        for kind, value in planned:
            saved.append(palace.save_annotation(value) if kind == "annotation" else append(palace, **value))
        return saved


def ensure_seed(palace, mind, policy, timestamp):
    seed = policy.get("seed_thread")
    if not seed or seed["owner"] != mind:
        return
    if any(t["key"] == seed["key"] for t in threads.project(palace.records).values()):
        return
    if sum(t["status"] == "active" for t in threads.project(palace.records).values()) >= threads.MAX_ACTIVE:
        return
    append(palace, author="runner", entry_kind="question", content=seed["aim"],
           source_refs=["organism/experiments/continuity-under-budget.md"], data_source=threads.CHANNEL,
           payload={"thread": {"op": "thread_open", "key": seed["key"], "name": seed["name"],
                               "horizon": seed["horizon"], "owner": mind, "seed": True}}, timestamp=timestamp)


def fulfill_recall(palace, mind, timestamp):
    completed = {r.get("payload", {}).get("request_id") for r in palace.records if r.get("data_source") == "recall_result"}
    pending = [r for r in palace.records if r.get("data_source") == "recall_request"
               and r["author"] == mind and r["entry_id"] not in completed][:2]
    for request in pending:
        selector = request["payload"]["recall"]
        ids = selector["entry_ids"]
        if ids:
            hits, missing, limited = palace.walk(ids, limit=6, depth=3)
        else:
            filters = {key: selector[key] for key in ("room", "wing", "since") if key in selector}
            hits = palace.search(selector["query"], **filters, limit=6)
            missing, limited = [], False
        result = {"request_id": request["entry_id"], "selector": selector,
                  "records": [palace.evidence_card(r, limit=600) for r in hits], "unresolved_refs": missing,
                  "walk_limited": limited, "scope": "local journal; ranked excerpts, not proof of completeness"}
        append(palace, author=mind, entry_kind="trace", content=json.dumps(result, ensure_ascii=False),
               data_source="recall_result", source_refs=[request["entry_id"], *[r["entry_id"] for r in hits]],
               payload={"request_id": request["entry_id"]}, timestamp=timestamp)


def context(palace, mind, timestamp):
    now = utc(timestamp)
    active = [t for t in threads.project(palace.records).values() if t["status"] == "active"]
    active.sort(key=lambda t: (t["updated"], t["id"]))
    selected_threads = []
    for t in active[:3]:
        item = {key: t[key] for key in ("id", "key", "name", "owner", "aim", "horizon", "position", "position_by", "next_question", "seed")}
        item["dormant_days"] = max(0, (now - utc(t["updated"])).days)
        item["recent_contributions"] = t["contributions"][-2:]
        item["history_ids"] = t["history_ids"][-3:]
        item["source_refs"] = t["source_refs"][-4:]
        selected_threads.append(item)
    watches = []
    for w in watchpoints.project(palace.records).values():
        if w["status"] == "active":
            watches.append({k: w[k] for k in ("id", "owner", "content", "target_id", "metric", "operator", "threshold", "confirm_samples", "last")})
    watches.sort(key=lambda w: not bool(w["last"] and w["last"]["notify"]))
    results = [r for r in palace.records if r.get("data_source") == "recall_result" and r["author"] == mind][-1:]
    recalls = [{"entry_id": r["entry_id"], "retrieved_at": r["timestamp"], **json.loads(r["content"])} for r in results]
    recent = [r for r in palace.records if r["entry_kind"] == "interpretation"
              and r.get("data_source") not in (threads.CHANNEL,)][-2:]
    evidence = [palace.evidence_card(r, limit=650) for r in recent]
    dossier = {"active_thread_count": len(active), "threads": selected_threads, "watchpoints": watches,
               "recall": recalls, "recent_interpretations": evidence,
               "rooms": palace.rooms()[:30], "tunnels": palace.tunnels()[:4],
               "classifications_are_attributed": True}
    def render():
        return json.dumps(dossier, ensure_ascii=False, separators=(",", ":"))
    rendered = render()
    # Keep complete records. Prioritize the requested recall and a current thread.
    for values in (dossier["tunnels"], evidence, selected_threads, watches):
        while len(rendered) > MAX_CONTEXT_CHARS and values:
            if values is selected_threads and len(values) == 1:
                break
            values.pop()
            rendered = render()
    if len(rendered) > MAX_CONTEXT_CHARS and recalls:
        while len(rendered) > MAX_CONTEXT_CHARS and recalls[0]["records"]:
            recalls[0]["records"].pop()
            recalls[0]["context_omitted_records"] = True
            rendered = render()
    if len(rendered) > MAX_CONTEXT_CHARS:
        raise ValueError("Investigation context cannot fit its allowance")
    refs = set()
    def visit(value):
        if isinstance(value, str) and value in palace.by_id:
            refs.add(value)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
    visit(dossier)
    return rendered, refs


def prepare(runtime, mind, *, timestamp=None, pulse_id=None, policy=None):
    """Prepare local evidence before the one already scheduled model call."""
    policy = policy or load_policy()
    timestamp = utc(timestamp).isoformat()
    with cognition_lock(runtime):
        palace = Palace(runtime)
        ensure_seed(palace, mind, policy, timestamp)
        fulfill_recall(palace, mind, timestamp)
        for fields in watchpoints.evaluate(palace.records, policy["metrics"], timestamp):
            append(palace, **fields)
        text, refs = context(palace, mind, timestamp)
        receipt = append(palace, author=mind, entry_kind="trace", content=text,
                         data_source="cognition_context", source_refs=sorted(refs),
                         pulse_id=pulse_id, timestamp=timestamp,
                         payload={"scope": "exact investigation context supplied to this pulse"})
        refs.add(receipt["entry_id"])
        return text, refs, receipt["entry_id"]


def review_context(runtime, mind, timestamp=None):
    """Dreams read the investigation view; they do not operate its adapters."""
    with cognition_lock(runtime):
        return context(Palace(runtime), mind, utc(timestamp).isoformat())


def instructions(policy):
    metrics = [{"metric": name, "unit": rule["unit"], "range": [rule["min"], rule["max"]]}
               for name, rule in policy["metrics"].items()]
    return """You may add a top-level "cognition" list, at most three actions, to the normal JSON response.
Omit it when there is no useful change. Twelve actions per mind per UTC day; no extra model calls.
All targets/references must be exact entry IDs supplied in this pulse. Excerpts and citations are not verified truth.
Use an existing room name when it fits. Classifications record your interpretation alongside other minds' views.
Adapters (only the fields shown are supported):
- {"op":"classify","entry_id":"ID","primary_wing":"observation|interpretation|tension|orientation","primary_room":"stable-room-name","status":"open|provisional|watchpointed|resolved|falsified|superseded|persistent","classification_confidence":"low|medium|high","reason":"why"}. Optional secondary_wings (max 2), secondary_rooms (max 2), related_ids (max 6). A question cannot be falsified; no annotation changes an inquiry's lifecycle or promotes its epistemic tag.
- {"op":"recall","query":"up to 200 characters","content":"why these records matter"}. Optional room, wing, since (YYYY-MM-DD), or entry_ids (max 3). Results arrive in a subsequent scheduled pulse. This searches local history only.
- {"op":"thread_open","key":"unique-stable-key","name":"short name","content":"aim","horizon":"what would count as progress","source_refs":["ID"]}.
- {"op":"thread_advance","target_id":"thread ID","content":"current interpretation and what changed","next_question":"what remains open","source_refs":["additional evidence ID"]}.
- {"op":"thread_status","target_id":"thread ID","status":"active|resting|resolved|ancestral","content":"reason","source_refs":[]}. Only owner/Nova; resolved requires evidence. Nine active threads across the organism.
- {"op":"watch","target_id":"question, claim or thread ID","metric":"enabled metric","operator":"gt|gte|lt|lte","threshold":0,"confirm_samples":2,"content":"why this condition should prompt reconsideration"}. Six active watches globally; 1–3 distinct fresh samples; six-hour notification cooldown.
- {"op":"watch_status","target_id":"watch ID","status":"active|resting|retired","content":"reason"}. Only owner/Nova.
A watch tests its numeric predicate, not the truth of the associated belief. Missing or stale measurements are UNKNOWN.
Threads are invitations to inquiry. Rest or end one when it stops helping. Do not manufacture evidence or disagreement to advance it.
Enabled measurement selectors: """ + json.dumps(metrics, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, default=Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery")))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("rebuild")
    recall = sub.add_parser("recall")
    recall.add_argument("query", nargs="?", default="")
    recall.add_argument("--id", action="append", dest="ids")
    recall.add_argument("--room")
    recall.add_argument("--wing", choices=sorted(WINGS))
    recall.add_argument("--full", action="store_true")
    apply = sub.add_parser("apply", help="Apply a reviewed JSON action list as Nova")
    apply.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "apply":
            print(json.dumps(submit(args.runtime_dir, "nova", json.loads(args.file.read_text())), ensure_ascii=False, indent=2))
            return
        with cognition_lock(args.runtime_dir):
            palace = Palace(args.runtime_dir)
            if args.command == "rebuild":
                print(palace.rebuild())
            elif args.command == "status":
                print(json.dumps({"palace": palace.index(), "threads": list(threads.project(palace.records).values()),
                                  "watchpoints": list(watchpoints.project(palace.records).values())}, ensure_ascii=False, indent=2))
            else:
                if args.ids:
                    records, missing, limited = palace.walk(args.ids)
                else:
                    records = palace.search(args.query, room=args.room, wing=args.wing)
                    missing, limited = [], False
                print(json.dumps({"records": records if args.full else [palace.evidence_card(r) for r in records],
                                  "unresolved_refs": missing, "walk_limited": limited}, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()

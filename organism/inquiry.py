#!/usr/bin/env python3
"""Durable questions and shared traces, rebuilt from immutable journal events."""

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path

from entry import entry_append, read_entries

CHANNEL = "shared_inquiry"
OPEN = {"open", "watchpointed"}
KINDS = {"question", "watchpoint", "proposal", "note"}
STATUSES = {"open", "watchpointed", "resolved", "falsified", "superseded", "false_alarm"}
MAX_OPEN = 9
MAX_DAILY_EVENTS = 12
MAX_CONTENT = 700


@contextmanager
def inquiry_lock(runtime):
    runtime = Path(runtime)
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "inquiry.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def project(records):
    """A status is an attributed assessment; it never alters an original entry."""
    items = {}
    events = []
    for record in records:
        if record.get("data_source") != CHANNEL:
            continue
        event = record.get("payload", {}).get("inquiry")
        if not isinstance(event, dict) or event.get("action") not in ("open", "comment", "status"):
            raise ValueError(f"Invalid inquiry event: {record['entry_id']}")
        events.append(record)
        if event["action"] == "open":
            items[record["entry_id"]] = {
                "id": record["entry_id"], "owner": record["author"],
                "kind": event["kind"], "content": record["content"],
                "status": "open", "created": record["timestamp"],
                "updated": record["timestamp"], "revisit_on": event.get("revisit_on"),
                "source_refs": record.get("source_refs", []), "comments": [],
            }
        else:
            item = items.get(event.get("target_id"))
            if item is None:
                raise ValueError(f"Inquiry event references missing item: {record['entry_id']}")
            item["updated"] = record["timestamp"]
            item["comments"] = (item["comments"] + [{"id": record["entry_id"],
                "author": record["author"], "content": record["content"]}])[-2:]
            if event["action"] == "status":
                item["status"] = event["status"]
                item["status_by"] = record["author"]
                item["revisit_on"] = event.get("revisit_on")
    return items, events


def view(runtime):
    with inquiry_lock(runtime):
        return project(read_entries(Path(runtime) / "entries"))


def context(runtime, mind, today):
    """Bounded context, with overdue items first and only recent peer traces."""
    items, events = view(runtime)
    active = [item for item in items.values() if item["status"] in OPEN]
    active.sort(key=lambda item: (item.get("revisit_on") or item["created"][:10], item["updated"], item["id"]))
    due = [item for item in active if not item.get("revisit_on") or item["revisit_on"] <= today][:6]
    cutoff = (date.fromisoformat(today) - timedelta(days=7)).isoformat()
    recent = [event for event in events if event["author"] != mind and event["timestamp"][:10] >= cutoff][-4:]
    refs = set()
    selected = []
    for item in due:
        refs.add(item["id"])
        # References are included explicitly, so the model can cite them without
        # pretending the original source text is visible in this compact view.
        refs.update(item["source_refs"])
        selected.append({key: item[key] for key in (
            "id", "owner", "kind", "content", "status", "revisit_on", "source_refs", "comments")})
    peer = [{"id": event["entry_id"], "author": event["author"], "content": event["content"],
             "event": event["payload"]["inquiry"]} for event in recent]
    refs.update(event["id"] for event in peer)
    if not selected and not peer:
        return "No shared inquiries or recent peer traces yet. Silence is welcome.", refs
    # Keep complete JSON artifacts within a fixed context allowance. Long IDs and
    # citations count too; never truncate halfway through an item.
    def render():
        return json.dumps({"open_total": len(active), "due_items": selected, "recent_peer_traces": peer},
                          ensure_ascii=False, separators=(",", ":"))
    text = render()
    while len(text) > 6500 and (peer or selected):
        (peer if peer else selected).pop()
        text = render()
    refs = ({item["id"] for item in selected}
            | {ref for item in selected for ref in item["source_refs"]}
            | {comment["id"] for item in selected for comment in item["comments"]}
            | {event["id"] for event in peer})
    return text, refs


def submit(runtime, author, actions, *, allowed_refs=None, response_id=None, pulse_id=None, timestamp=None):
    """Validate the whole batch before append. Models cannot write executable work.

    Omitted actions mean no change. Status updates belong to the item's author
    or Nova; other minds can add evidence and comments. No item activates a job.
    """
    if not isinstance(actions, list) or len(actions) > 2:
        raise ValueError("inquiry must be a list of at most two actions")
    if not actions:
        return []
    now = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Inquiry time requires a timezone")
    now = now.astimezone(timezone.utc)
    today = now.date().isoformat()
    runtime = Path(runtime)
    with inquiry_lock(runtime):
        # The journal supplies existence checks; allowed_refs restrict a model to
        # IDs actually provided to this pulse rather than invented citations.
        records = list(read_entries(runtime / "entries"))
        known = {record["entry_id"]: record for record in records}
        items, events = project(records)
        daily = sum(event["author"] == author and event["timestamp"][:10] == today for event in events)
        pending = []
        touched = set()
        for action in actions:
            if not isinstance(action, dict) or set(action) - {"action", "kind", "content", "source_refs", "target_id", "status", "revisit_on"}:
                raise ValueError("Unknown inquiry fields")
            op = action.get("action")
            content = action.get("content")
            if not isinstance(content, str) or not content.strip() or len(content) > MAX_CONTENT:
                raise ValueError(f"Inquiry content must be 1–{MAX_CONTENT} characters")
            refs = action.get("source_refs", [])
            if not isinstance(refs, list) or len(refs) > 6 or any(not isinstance(ref, str) or ref not in known for ref in refs):
                raise ValueError("Inquiry references must name up to six existing journal entries")
            if allowed_refs is not None and any(ref not in allowed_refs for ref in refs):
                raise ValueError("Inquiry cites evidence outside this pulse's supplied context")
            revisit = action.get("revisit_on")
            if revisit is not None:
                revisit = date.fromisoformat(revisit).isoformat()
            event = {"action": op}
            if revisit:
                event["revisit_on"] = revisit
            if op == "open":
                kind = action.get("kind")
                if kind not in KINDS or "target_id" in action or "status" in action:
                    raise ValueError("open requires a supported kind and cannot set status or target")
                if kind == "watchpoint" and not refs:
                    raise ValueError("A watchpoint must cite the claim or evidence being watched")
                # Repeated wording is silence, not another demand on attention.
                duplicate = any(item["owner"] == author and item["kind"] == kind
                    and item["content"].strip().casefold() == content.strip().casefold()
                    and (item["status"] in OPEN or item["created"][:10] >= (now.date() - timedelta(days=7)).isoformat())
                    for item in items.values())
                duplicate = duplicate or any(p["content"].strip().casefold() == content.strip().casefold() for p in pending)
                if duplicate:
                    continue
                active = sum(item["owner"] == author and item["status"] in OPEN for item in items.values())
                if active + sum(p["payload"]["inquiry"]["action"] == "open" for p in pending) >= MAX_OPEN:
                    raise ValueError("Nine active items already exist; review or rest an existing question")
                event["kind"] = kind
                entry_kind = "trace" if kind == "note" else kind
            elif op in ("comment", "status"):
                target = action.get("target_id")
                if not isinstance(target, str) or target not in items or target in touched:
                    raise ValueError("Inquiry target is missing or repeated in this batch")
                if allowed_refs is not None and target not in allowed_refs:
                    raise ValueError("Target was not supplied to this pulse")
                if "kind" in action:
                    raise ValueError("Existing item kind is immutable")
                item = items[target]
                touched.add(target)
                event["target_id"] = target
                if op == "status":
                    status = action.get("status")
                    if author not in (item["owner"], "nova"):
                        raise ValueError("Only the owner or Nova can change status; add a comment instead")
                    if status not in STATUSES or (status == "falsified" and item["kind"] != "watchpoint"):
                        raise ValueError("Unsupported status for this kind; a question cannot be falsified")
                    if status in ("resolved", "falsified", "superseded") and not refs:
                        raise ValueError("Resolution requires cited evidence and a reason")
                    if status in OPEN and item["status"] not in OPEN and sum(i["owner"] == item["owner"] and i["status"] in OPEN for i in items.values()) >= MAX_OPEN:
                        raise ValueError("Active item ceiling reached; resolve another item before reopening")
                    event["status"] = status
                elif "status" in action or revisit is not None:
                    raise ValueError("A comment cannot change status or review date")
                if author != "nova" and any(e["author"] == author and e["timestamp"][:10] == today
                       and e["payload"]["inquiry"].get("target_id") == target for e in events):
                    raise ValueError("One contribution per mind per item per day; allow time for new evidence")
                refs = list(dict.fromkeys([target, *refs]))
                entry_kind = "trace"
            else:
                raise ValueError("Unknown inquiry action")
            pending.append({"author": author, "entry_kind": entry_kind, "content": content.strip(),
                "data_source": CHANNEL, "source_refs": list(dict.fromkeys(refs + ([response_id] if response_id else []))),
                "pulse_id": pulse_id, "payload": {"inquiry": event}, "timestamp": now.isoformat()})
        if author != "nova" and daily + len(pending) > MAX_DAILY_EVENTS:
            raise ValueError("Daily inquiry write ceiling reached")
        return [entry_append(runtime / "entries", **fields) for fields in pending]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, default=Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery")))
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--all", action="store_true")
    add = sub.add_parser("add", help="Append a contribution attributed to Nova")
    add.add_argument("--kind", choices=sorted(KINDS), default="question")
    add.add_argument("--content", required=True)
    add.add_argument("--ref", action="append", default=[])
    add.add_argument("--revisit-on")
    revise = sub.add_parser("review", help="Record Nova's review, without erasing history")
    revise.add_argument("target_id")
    revise.add_argument("--status", choices=sorted(STATUSES))
    revise.add_argument("--content", required=True)
    revise.add_argument("--ref", action="append", default=[])
    revise.add_argument("--revisit-on")
    args = parser.parse_args()
    try:
        if args.command == "list":
            items, _ = view(args.runtime_dir)
            print(json.dumps([item for item in items.values() if args.all or item["status"] in OPEN], ensure_ascii=False, indent=2))
        else:
            action = {"action": "open" if args.command == "add" else ("status" if args.status else "comment"),
                      "content": args.content, "source_refs": args.ref}
            if args.command == "add":
                action["kind"] = args.kind
            else:
                action["target_id"] = args.target_id
                if args.status:
                    action["status"] = args.status
            if args.revisit_on:
                action["revisit_on"] = args.revisit_on
            for record in submit(args.runtime_dir, "nova", [action]):
                print(record["entry_id"])
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()

"""Persistent investigation threads (the DNA's Songlines), projected from entries."""

from palace import slug, text_field

CHANNEL = "research_thread"
STATUSES = {"active", "resting", "resolved", "ancestral"}
MAX_ACTIVE = 9


def project(records):
    threads = {}
    for record in records:
        if record.get("data_source") != CHANNEL:
            continue
        event = record.get("payload", {}).get("thread", {})
        op = event.get("op")
        if op == "thread_open":
            threads[record["entry_id"]] = {
                "id": record["entry_id"], "key": event["key"], "name": event["name"],
                "owner": event.get("owner", record["author"]), "status": "active",
                "aim": record["content"], "horizon": event["horizon"],
                "created": record["timestamp"], "updated": record["timestamp"],
                "position": record["content"], "position_by": record["author"],
                "next_question": event["horizon"], "source_refs": record.get("source_refs", []),
                "history_ids": [record["entry_id"]], "contributions": [],
                "seed": event.get("seed", False),
            }
        elif op in ("thread_advance", "thread_status"):
            thread = threads.get(event.get("target_id"))
            if thread is None:
                raise ValueError("Thread event references missing history")
            thread["updated"] = record["timestamp"]
            thread["history_ids"].append(record["entry_id"])
            thread["source_refs"] = list(dict.fromkeys(thread["source_refs"] + record.get("source_refs", [])))
            if op == "thread_advance":
                thread["position"] = record["content"]
                thread["position_by"] = record["author"]
                thread["next_question"] = event["next_question"]
                thread["contributions"] = (thread["contributions"] + [{"entry_id": record["entry_id"],
                    "author": record["author"], "content": record["content"],
                    "source_refs": event["evidence_refs"]}])[-3:]
            else:
                thread["status"] = event["status"]
        else:
            raise ValueError("Unknown research thread event; retain it for review")
    return threads


def plan(action, author, records, references):
    """Validate one prospective event; caller serializes the complete batch."""
    threads = project(records)
    op = action["op"]
    base = {"op", "content", "source_refs"}
    specific = {"thread_open": {"key", "name", "horizon"},
                "thread_advance": {"target_id", "next_question"},
                "thread_status": {"target_id", "status"}}
    if op not in specific or set(action) - base - specific[op]:
        raise ValueError("Unknown thread action fields")
    content = text_field(action.get("content"), "content")
    event = {"op": op}
    if op == "thread_open":
        key = slug(action.get("key"))
        if any(t["key"] == key for t in threads.values()):
            raise ValueError("Thread key already exists; continue or explicitly reopen its history")
        if sum(t["status"] == "active" for t in threads.values()) >= MAX_ACTIVE:
            raise ValueError("Nine active threads already exist; rest or resolve one first")
        event.update(key=key, name=text_field(action.get("name"), "name", 80),
                     horizon=text_field(action.get("horizon"), "horizon", 350))
        kind = "question"
    else:
        target = action.get("target_id")
        if not isinstance(target, str) or target not in threads:
            raise ValueError("Unknown thread target")
        thread = threads[target]
        event["target_id"] = target
        if op == "thread_advance":
            if thread["status"] != "active":
                raise ValueError("Resting/resolved/ancestral threads must be explicitly reactivated")
            evidence = {r["entry_id"] for r in records
                        if r["entry_kind"] in ("observation", "interpretation", "summary", "reflection")
                        and r.get("data_source") != CHANNEL}
            if not set(references) & evidence - set(thread["source_refs"]):
                raise ValueError("Advance requires an additional evidence record, beyond the thread's existing references")
            event["next_question"] = text_field(action.get("next_question"), "next_question", 350)
            event["evidence_refs"] = references
            kind = "interpretation"
        else:
            if author not in (thread["owner"], "nova"):
                raise ValueError("Only the thread owner or Nova can change its lifecycle")
            status = action.get("status")
            if status not in STATUSES:
                raise ValueError("Unknown thread status")
            if status == "active" and thread["status"] != "active" and sum(t["status"] == "active" for t in threads.values()) >= MAX_ACTIVE:
                raise ValueError("Active thread limit reached")
            if status == "resolved" and not references:
                raise ValueError("Resolving a thread requires evidence and a reason")
            event["status"] = status
            kind = "trace"
        references = list(dict.fromkeys([target, *references]))
    return {"entry_kind": kind, "content": content, "data_source": CHANNEL,
            "source_refs": references, "payload": {"thread": event, "cognition_action": True}}

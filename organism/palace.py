"""A small Memory Palace: evidence lookup and attributed, versioned annotations.

The index is disposable. Raw journal entries and annotation histories are not.
No embeddings, database, network requests, or model calls are used here.
"""

from collections import defaultdict, deque
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import uuid

from entry import EntryLogError, append_jsonl, read_entries, read_jsonl
from runtime import atomic_write

WINGS = {"observation", "interpretation", "tension", "orientation"}
STATUSES = {"open", "provisional", "watchpointed", "resolved", "falsified", "superseded", "persistent"}
SEARCH_KINDS = {"observation", "interpretation", "question", "summary", "watchpoint", "proposal", "reflection"}
STOPWORDS = set("a an and are as at be by for from how i in is it of on or our the this to was we what with".split())


def utc(value=None):
    result = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else datetime.now(timezone.utc)
    if result.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def slug(value):
    if not isinstance(value, str):
        raise ValueError("Name must be text")
    result = re.sub(r"[\s_]+", "-", value.strip().casefold())
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", result) or len(result) > 48:
        raise ValueError("Use a room/key of at most 48 lowercase letters, digits and hyphens")
    return result


def text_field(value, name, limit=700):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be 1–{limit} characters")
    return value.strip()


def card(record, limit=1000):
    """A returned excerpt says explicitly how much of the source was omitted."""
    result = {key: record[key] for key in ("entry_id", "timestamp", "author", "entry_kind", "epistemic_tag")}
    result.update(content=record["content"][:limit], content_chars=len(record["content"]),
                  truncated=len(record["content"]) > limit, source_refs=record.get("source_refs", []))
    if record.get("data_source"):
        result["data_source"] = record["data_source"]
    return result


class Palace:
    def __init__(self, runtime, records=None):
        self.runtime = Path(runtime)
        self.records = list(read_entries(self.runtime / "entries")) if records is None else list(records)
        self.by_id = {r["entry_id"]: r for r in self.records}
        if len(self.by_id) != len(self.records):
            raise EntryLogError("Duplicate canonical entry IDs; retain the journal for review")
        self.annotations = []
        self.latest = {}
        self.by_entry = defaultdict(dict)
        for path in sorted((self.runtime / "annotations").glob("annotations-*.jsonl")):
            for annotation in read_jsonl(path):
                self.validate_saved_annotation(annotation)
                self.annotations.append(annotation)
                self.latest[(annotation["entry_id"], annotation["annotator"])] = annotation
                self.by_entry[annotation["entry_id"]][annotation["annotator"]] = annotation

    def validate_saved_annotation(self, annotation):
        required = ("annotation_id", "timestamp", "entry_id", "annotator", "primary_wing", "primary_room", "reason")
        if any(not isinstance(annotation.get(k), str) or not annotation[k] for k in required):
            raise EntryLogError("Malformed Palace annotation; retain history for review")
        if annotation["entry_id"] not in self.by_id:
            raise EntryLogError("Annotation references a missing raw entry; restore the complete journal")
        if annotation["primary_wing"] not in WINGS or annotation.get("status") not in STATUSES:
            raise EntryLogError("Unsupported Palace annotation values")

    def opinions(self, entry_id):
        return list(self.by_entry.get(entry_id, {}).values())

    def evidence_card(self, record, limit=600):
        result = card(record, limit=limit)
        opinions = self.opinions(record["entry_id"])
        result["annotations"] = [{key: a[key] for key in (
            "annotation_id", "annotator", "primary_wing", "primary_room", "status", "reason")}
            for a in opinions[-3:]]
        result["annotation_count"] = len(opinions)
        return result

    def rooms(self):
        return sorted({room for a in self.latest.values()
                       for room in [a["primary_room"], *a.get("secondary_rooms", [])]})

    def tunnels(self):
        rooms = defaultdict(lambda: defaultdict(set))
        for annotation in self.latest.values():
            for room in [annotation["primary_room"], *annotation.get("secondary_rooms", [])]:
                for wing in [annotation["primary_wing"], *annotation.get("secondary_wings", [])]:
                    rooms[room][wing].add(annotation["entry_id"])
        return [{"room": room, "wings": {wing: sorted(ids) for wing, ids in sorted(wings.items())}}
                for room, wings in sorted(rooms.items()) if len(wings) > 1]

    def search(self, query="", *, room=None, wing=None, author=None, kind=None, since=None, limit=6):
        if not isinstance(query, str) or len(query) > 200 or not 1 <= limit <= 20:
            raise ValueError("Recall query must be at most 200 characters; limit is 1–20")
        if room is not None:
            room = slug(room)
        if wing is not None and wing not in WINGS:
            raise ValueError("Unknown wing")
        if since is not None:
            since = date.fromisoformat(since).isoformat()
        terms = set(re.findall(r"[^\W_]+", query.casefold())) - STOPWORDS
        results = []
        for record in self.records:
            if record["entry_kind"] not in SEARCH_KINDS:
                continue  # Raw API envelopes/context copies are recall by ID only.
            if author and record["author"] != author or kind and record["entry_kind"] != kind:
                continue
            if since and record["timestamp"][:10] < since:
                continue
            opinions = self.opinions(record["entry_id"])
            if (room or wing) and not any(
                    (not room or room in [a["primary_room"], *a.get("secondary_rooms", [])])
                    and (not wing or wing in [a["primary_wing"], *a.get("secondary_wings", [])]) for a in opinions):
                continue
            words = set(re.findall(r"[^\W_]+", record["content"].casefold()))
            score = len(terms & words)
            if terms and not score:
                continue
            results.append((score, record["timestamp"], record["entry_id"], record))
        results.sort(key=lambda item: item[:3], reverse=True)
        return [item[3] for item in results[:limit]]

    def walk(self, entry_ids, *, limit=12, depth=3):
        """Bounded provenance traversal, including explicit unresolved file refs."""
        queue = deque((entry_id, 0) for entry_id in entry_ids)
        seen, records, missing = set(), [], []
        depth_limited = False
        while queue and len(records) < limit:
            entry_id, level = queue.popleft()
            if entry_id in seen:
                continue
            seen.add(entry_id)
            record = self.by_id.get(entry_id)
            if record is None:
                missing.append(entry_id)
                continue
            records.append(record)
            if level < depth:
                queue.extend((ref, level + 1) for ref in record.get("source_refs", []))
            elif any(ref not in seen for ref in record.get("source_refs", [])):
                depth_limited = True
        return records, missing, bool(queue) or depth_limited

    def annotation(self, author, action, timestamp, allowed_refs=None):
        permitted = {"op", "entry_id", "primary_wing", "secondary_wings", "primary_room", "secondary_rooms",
                     "status", "classification_confidence", "reason", "related_ids"}
        if set(action) - permitted:
            raise ValueError("Unknown classification fields")
        target = action.get("entry_id")
        if not isinstance(target, str) or target not in self.by_id or allowed_refs is not None and target not in allowed_refs:
            raise ValueError("Classify only an existing entry supplied to this pulse")
        primary = action.get("primary_wing")
        secondary = action.get("secondary_wings", [])
        if primary not in WINGS or not isinstance(secondary, list) or len(secondary) > 2 or any(w not in WINGS or w == primary for w in secondary):
            raise ValueError("Invalid wing classification")
        room = slug(action.get("primary_room"))
        secondary_rooms = action.get("secondary_rooms", [])
        if not isinstance(secondary_rooms, list) or len(secondary_rooms) > 2:
            raise ValueError("At most two secondary rooms")
        secondary_rooms = list(dict.fromkeys(slug(r) for r in secondary_rooms if r != room))
        status = action.get("status", "provisional")
        kind = self.by_id[target]["entry_kind"]
        if status not in STATUSES or status == "falsified" and kind not in ("interpretation", "watchpoint"):
            raise ValueError("This entry kind cannot have that claim status")
        confidence = action.get("classification_confidence", "low")
        if confidence not in ("low", "medium", "high"):
            raise ValueError("Classification confidence must be low, medium or high")
        related = action.get("related_ids", [])
        if not isinstance(related, list) or len(related) > 6 or any(
                not isinstance(ref, str) or ref not in self.by_id or allowed_refs is not None and ref not in allowed_refs for ref in related):
            raise ValueError("Related IDs must be existing entries supplied to the pulse")
        moment = utc(timestamp)
        previous = self.latest.get((target, author))
        return {"annotation_id": f"ann-{moment:%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:12]}",
                "timestamp": moment.isoformat().replace("+00:00", "Z"), "entry_id": target,
                "annotator": author, "primary_wing": primary, "secondary_wings": list(dict.fromkeys(secondary)),
                "primary_room": room, "secondary_rooms": secondary_rooms, "status": status,
                "classification_confidence": confidence, "related_ids": related,
                "reason": text_field(action.get("reason"), "reason"),
                "supersedes": previous["annotation_id"] if previous else None, "schema_version": "0.1.0"}

    def save_annotation(self, annotation):
        month = annotation["timestamp"][:7]
        result = append_jsonl(self.runtime / "annotations" / f"annotations-{month}.jsonl", annotation)
        self.annotations.append(result)
        self.latest[(result["entry_id"], result["annotator"])] = result
        self.by_entry[result["entry_id"]][result["annotator"]] = result
        return result

    def index(self):
        return {"schema_version": "0.1.0", "built_at": utc().isoformat(),
                "entry_count": len(self.records), "annotation_count": len(self.annotations),
                "classified_entry_count": len({target for target, _ in self.latest}),
                "rooms": self.rooms(), "tunnels": self.tunnels(),
                "latest_annotations": list(self.latest.values())}

    def rebuild(self):
        path = self.runtime / "palace" / "index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, json.dumps(self.index(), ensure_ascii=False, indent=2))
        return path

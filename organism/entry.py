"""Versioned, append-only records shared by the organism's runtime jobs."""

import argparse
import fcntl
import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "0.1.0"
ENTRY_KINDS = {"observation", "interpretation", "question", "trace", "summary",
               "watchpoint", "proposal", "reflection"}
EPISTEMIC_TAGS = {"VERIFIED", "OBSERVED", "FETCHED", "DERIVED", "INFERRED",
                  "HYPOTHESIS", "UNKNOWN"}


class EntryLogError(ValueError):
    """The journal needs inspection before it can be extended or read."""


def entry_append(entries_dir, *, author, entry_kind, content, epistemic_tag="UNKNOWN",
                 source_refs=None, data_source=None, pulse_id=None, payload=None,
                 timestamp=None):
    """Append one complete JSON record, flush, and fsync while holding a lock.

    An entry records an artifact and its provenance; it does not certify the
    artifact's claims. Classification and later corrections belong in new
    records or derived views, never edits to this journal.
    """
    if not isinstance(author, str) or not author or not all(c.isalnum() or c in "-_" for c in author):
        raise ValueError("author must be a non-empty name using letters, digits, '-' or '_'")
    if entry_kind not in ENTRY_KINDS or epistemic_tag not in EPISTEMIC_TAGS:
        raise ValueError("Unknown entry kind or epistemic tag")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Entry content must be non-empty text")
    if source_refs is not None and (not isinstance(source_refs, list)
                                   or any(not isinstance(ref, str) or not ref for ref in source_refs)):
        raise ValueError("source_refs must be a list of non-empty strings")
    if payload is not None and not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    now = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Entry timestamp must include a timezone")
    now = now.astimezone(timezone.utc)
    record = {
        "entry_id": f"{author}-{now:%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:12]}",
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "author": author, "entry_kind": entry_kind, "content": content,
        "schema_version": SCHEMA_VERSION, "epistemic_tag": epistemic_tag,
    }
    for key, value in (("source_refs", source_refs), ("data_source", data_source),
                       ("pulse_id", pulse_id), ("payload", payload)):
        if value is not None:
            record[key] = value
    entries_dir = Path(entries_dir)
    return append_jsonl(entries_dir / f"entries-{now:%Y-%m}.jsonl", record)


def append_jsonl(journal, record):
    """Shared durable append primitive for raw entries and separate annotations."""
    encoded = (json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    journal = Path(journal)
    entries_dir = journal.parent
    entries_dir.mkdir(parents=True, exist_ok=True)
    with journal.open("a+b") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell():
                stream.seek(-1, os.SEEK_END)
                if stream.read(1) != b"\n":
                    raise EntryLogError(f"Incomplete final record in {journal}; retaining it for review")
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
            # Persist the monthly filename and the entries directory itself.
            for folder in (entries_dir, entries_dir.parent):
                directory = os.open(folder, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
    return record


def read_jsonl(journal):
    """Read complete objects under a shared lock; never silently skip a bad tail."""
    with Path(journal).open(encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        for number, line in enumerate(stream, 1):
            try:
                if not line.endswith("\n"):
                    raise ValueError("incomplete record")
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("record must be an object")
            except (ValueError, TypeError) as error:
                raise EntryLogError(f"Unreadable record at {journal}:{number}: {error}") from error
            yield record


def read_entries(entries_dir, *, day=None, entry_ids=None):
    """Read complete records in file order; expose corruption rather than skip it."""
    if day is not None:
        day = date.fromisoformat(day).isoformat()
    wanted = set(entry_ids) if entry_ids is not None else None
    pattern = f"entries-{day[:7]}.jsonl" if day else "entries-*.jsonl"
    for journal in sorted(Path(entries_dir).glob(pattern)):
        with journal.open("r", encoding="utf-8") as stream:
            fcntl.flock(stream, fcntl.LOCK_SH)
            try:
                for number, line in enumerate(stream, 1):
                    try:
                        if not line.endswith("\n"):
                            raise ValueError("incomplete record")
                        record = json.loads(line)
                        if not isinstance(record, dict) or not all(
                            isinstance(record.get(key), str)
                            for key in ("entry_id", "timestamp", "author", "entry_kind", "content", "schema_version", "epistemic_tag")
                        ):
                            raise ValueError("missing entry fields")
                    except (ValueError, TypeError) as error:
                        raise EntryLogError(f"Unreadable record at {journal}:{number}: {error}") from error
                    if day is not None and record["timestamp"][:10] != day:
                        continue
                    if wanted is not None and record["entry_id"] not in wanted:
                        continue
                    yield record
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description="Read organism records without model calls")
    parser.add_argument("--day", help="Filter by UTC date (YYYY-MM-DD)")
    parser.add_argument("--id", action="append", dest="entry_ids", help="Look up an entry ID; repeat for multiple IDs")
    parser.add_argument("--entries-dir", type=Path,
                        default=Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery")) / "entries")
    args = parser.parse_args()
    try:
        found = set()
        for record in read_entries(args.entries_dir, day=args.day, entry_ids=args.entry_ids):
            print(json.dumps(record, ensure_ascii=False))
            found.add(record["entry_id"])
        if args.entry_ids and set(args.entry_ids) - found:
            parser.exit(1, "Some requested entry IDs were not found\n")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()

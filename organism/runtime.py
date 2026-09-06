"""Shared file safety and per-mind usage accounting for scheduled jobs."""

import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path


@contextmanager
def mind_lock(mind_dir):
    """Serialize pulse, dream, and archive jobs; the OS releases crashed jobs."""
    mind_dir = Path(mind_dir)
    mind_dir.mkdir(parents=True, exist_ok=True)
    # Keep this inode in place: unlinking a flock file can admit two owners.
    with (mind_dir / "runtime.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def atomic_write(path, content):
    """Replace a snapshot only after its complete contents reach disk."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def log_date(content):
    """Read the date from the header, never from an observation in the body."""
    header = content.splitlines()[0] if content else ""
    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", header)
    if not match:
        raise ValueError("Daily log has no dated header; retaining it for review")
    return date.fromisoformat(match.group()).isoformat()


def archive_daily_log(log_path, today):
    """Preserve an older log without overwriting a conflicting archive.

    The caller must hold mind_lock for this log's directory.
    """
    log_path = Path(log_path)
    if not log_path.exists():
        return None
    content = log_path.read_text()
    if not content.strip():
        return None
    day = log_date(content)
    if day == today:
        return None
    if day > today:
        raise ValueError(f"Daily log is from the future ({day}); retaining it for review")
    archive = log_path.parent / "archive" / f"daily_log_{day}.md"
    archive.parent.mkdir(exist_ok=True)
    if archive.exists():
        if archive.read_text() != content:
            raise ValueError(f"Conflicting archive: {archive}; retaining both records")
    else:
        atomic_write(archive, content)
    return archive


def prepare_daily_log(log_path, today, header):
    """Archive yesterday before replacing the active daily log."""
    log_path = Path(log_path)
    if log_path.exists():
        content = log_path.read_text()
        if content.strip() and log_date(content) == today:
            return
        archive_daily_log(log_path, today)
    atomic_write(log_path, header)


def load_budget(budget_path, today):
    """Load or roll over the existing budget.json format under mind_lock."""
    budget_path = Path(budget_path)
    budget = json.loads(budget_path.read_text()) if budget_path.exists() else {}
    if budget and budget.get("date") != today:
        previous_day = date.fromisoformat(budget["date"]).isoformat()
        if previous_day > today:
            raise ValueError("Budget is from the future; refusing to reset spending")
        atomic_write(budget_path.with_name(f"budget_{previous_day}.json"), json.dumps(budget))
        budget = {}
    if not budget:
        budget = {"date": today, "spent_usd": 0, "pulses_run": 0,
                  "dreams_run": 0, "input_tokens": 0, "output_tokens": 0}
        atomic_write(budget_path, json.dumps(budget))
    return budget


def record_usage(budget_path, budget, config, input_tokens, output_tokens, kind):
    """Count reported usage before interpreting generated content.

    Costs are estimates from configured rates. The daily check stops later
    requests; an in-flight request can still cross the remaining allowance.
    The caller must hold mind_lock across loading, requesting, and recording.
    """
    cost = (input_tokens * config.get("input_cost_per_mtok", 1.0) / 1_000_000
            + output_tokens * config.get("output_cost_per_mtok", 5.0) / 1_000_000)
    budget["spent_usd"] = round(budget["spent_usd"] + cost, 6)
    budget["input_tokens"] += input_tokens
    budget["output_tokens"] += output_tokens
    counter = {"pulse": "pulses_run", "dream": "dreams_run"}[kind]
    budget[counter] = budget.get(counter, 0) + 1
    atomic_write(budget_path, json.dumps(budget))
    return cost

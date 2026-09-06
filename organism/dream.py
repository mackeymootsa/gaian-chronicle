#!/usr/bin/env python3
"""
Dream cycle — memory consolidation for the organism.
Runs in two modes:
  daily:  Summarize yesterday's log into a compact dream.
  weekly: Consolidate the last 7 daily dreams into a weekly dream.

Usage:
    python3 dream.py tela daily
    python3 dream.py tela weekly
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from pulse import API_CALLERS, persist_entry, record_footer
from runtime import atomic_write, load_budget, log_date, mind_lock, record_usage

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR = SCRIPT_DIR.parent
DATA_DIR = Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery"))


def load_config(mind_name):
    config_path = SCRIPT_DIR / "config" / f"{mind_name}.json"
    return json.loads(config_path.read_text())


def request_dream(config, mind_dir, system_prompt, user_message, max_tokens, *, source_files, period):
    """Use the configured provider and shared budget while holding mind_lock."""
    api_key = os.environ.get(config["api_key_env"], "")
    if not api_key:
        print(f"ERROR: {config['api_key_env']} not set")
        return None
    caller = API_CALLERS.get(config["provider"])
    if caller is None:
        print(f"ERROR: Unknown provider {config['provider']!r}")
        return None

    budget_file = mind_dir / "budget.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    budget = load_budget(budget_file, today)
    limit = config.get("daily_budget_usd", 2.0)
    if budget["spent_usd"] >= limit:
        print(f"BUDGET_SLEEP: Daily allowance ${limit:.2f} reached")
        return None

    source_record = persist_entry(mind_dir, author=mind_dir.name, entry_kind="trace",
        content=user_message, source_refs=source_files, data_source="dream_input",
        payload={"system_prompt": system_prompt, "period": period},
        timestamp=datetime.now(timezone.utc).isoformat())
    text, http_code, in_tok, out_tok = caller(
        api_key, config["model"], system_prompt, user_message, max_tokens, timeout=60
    )
    if http_code == "200" or in_tok or out_tok:
        cost = record_usage(budget_file, budget, config, in_tok, out_tok, "dream")
        print(f"Dream usage: cost=${cost:.6f} total=${budget['spent_usd']:.6f}")
    usable = http_code == "200" and bool(text and text.strip())
    record = persist_entry(mind_dir, author=mind_dir.name,
        entry_kind="summary" if usable else "trace",
        content=text if text and text.strip() else f"Dream API returned no usable text (HTTP {http_code})",
        source_refs=[source_record["entry_id"]], data_source="dream_response",
        payload={"provider": config["provider"], "model": config["model"], "period": period,
                 "http_code": http_code, "input_tokens": in_tok, "output_tokens": out_tok},
        timestamp=datetime.now(timezone.utc).isoformat())
    if not usable:
        print(f"Dream API returned no usable text (HTTP {http_code})")
        return None
    return record


def daily_dream(mind_name, config):
    """Read yesterday's dated log under mind_lock and produce one summary."""
    mind_dir = DATA_DIR / mind_name
    archive_dir = mind_dir / "archive"
    dreams_dir = mind_dir / "dreams"
    dreams_dir.mkdir(parents=True, exist_ok=True)

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    dream_file = dreams_dir / f"daily_{yesterday}.md"
    if dream_file.exists():
        print(f"Daily dream already exists: {dream_file}")
        return

    # A filename alone is insufficient: older versions could misdate records.
    log_content = None
    for log_path in (archive_dir / f"daily_log_{yesterday}.md", mind_dir / "daily_log.md"):
        if not log_path.exists():
            continue
        content = log_path.read_text()
        try:
            matches = log_date(content) == yesterday
        except ValueError:
            matches = False
        if matches:
            log_content = content
            break
        print(f"Skipping log with mismatched or missing date: {log_path}")
    if log_content is None:
        print(f"No correctly dated log found for {yesterday}; dream skipped")
        return
    if len(log_content.strip()) < 100:
        print(f"Log too short to dream on: {len(log_content)} chars")
        return

    system_prompt = (
        f"You are {config['display_name']}'s dream process — a memory consolidation function. "
        "You read a day's pulse log and extract what matters for long-term memory. "
        "Be ruthlessly brief. No preamble. No commentary on the process itself."
    )

    user_message = f"""Here is the full pulse log for {yesterday}:

{log_content}

Produce a daily dream summary with these sections (skip any section with nothing to report):
- **Key observations**: What was actually observed or measured (not repeated)
- **Decisions made**: Any choices, acceptances, refusals, or direction changes
- **Open questions**: Unresolved items needing human input or future investigation
- **Weather summary**: One line (high/low/trend)
- **Errors**: Any degraded pulses or failures
- **Pattern notes**: Anything recurring or noteworthy about the day's behavior

Maximum 300 words. Write in first person as {config['display_name']}."""

    record = request_dream(
        config, mind_dir, system_prompt, user_message, 1024,
        source_files=[str(log_path.relative_to(mind_dir))], period=yesterday
    )

    if record:
        header = f"# Daily Dream — {yesterday}\n\n"
        atomic_write(dream_file, header + record["content"].strip() + record_footer(record))
        print(f"Daily dream written: {dream_file}")


def weekly_dream(mind_name, config):
    """Read last 7 daily dreams under mind_lock and consolidate them once."""
    mind_dir = DATA_DIR / mind_name
    dreams_dir = mind_dir / "dreams"
    dreams_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc)
    # ISO week number
    week_label = today.strftime("%G-W%V")
    weekly_file = dreams_dir / f"weekly_{week_label}.md"
    if weekly_file.exists():
        print(f"Weekly dream already exists: {weekly_file}")
        return

    # Gather last 7 daily dreams
    daily_dreams = []
    source_files = []
    for i in range(7, 0, -1):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        dream_path = dreams_dir / f"daily_{day}.md"
        if dream_path.exists():
            daily_dreams.append(dream_path.read_text())
            source_files.append(str(dream_path.relative_to(mind_dir)))

    if not daily_dreams:
        print("No daily dreams found for the past week")
        return

    system_prompt = (
        f"You are {config['display_name']}'s weekly dream process — deep memory consolidation. "
        "You read a week of daily dream summaries and extract durable knowledge. "
        "Prune contradictions. Keep only what the next week needs. "
        "Be ruthlessly brief. No preamble."
    )

    combined = "\n\n---\n\n".join(daily_dreams)
    user_message = f"""Here are the daily dream summaries from the past week:

{combined}

Produce a weekly consolidation with these sections (skip empty ones):
- **What changed this week**: Key shifts in state, understanding, or capability
- **What was learned**: Findings that survived the week (not retired or contradicted)
- **What was retired**: Models, predictions, or assumptions that failed
- **Open threads**: Items still unresolved, carried forward
- **Self-observation**: Patterns in my own behavior worth noting

Maximum 200 words. Write in first person as {config['display_name']}."""

    record = request_dream(
        config, mind_dir, system_prompt, user_message, 768,
        source_files=source_files, period=week_label
    )

    if record:
        header = f"# Weekly Dream — {week_label}\n\n"
        atomic_write(weekly_file, header + record["content"].strip() + record_footer(record))
        print(f"Weekly dream written: {weekly_file}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 dream.py <mind_name> <daily|weekly>")
        sys.exit(1)

    mind_name = sys.argv[1].lower()
    mode = sys.argv[2].lower()
    config = load_config(mind_name)

    if mode not in ("daily", "weekly"):
        print(f"Unknown mode: {mode}. Use 'daily' or 'weekly'.")
        sys.exit(1)
    try:
        with mind_lock(DATA_DIR / mind_name):
            if mode == "daily":
                daily_dream(mind_name, config)
            else:
                weekly_dream(mind_name, config)
    except BlockingIOError:
        print("SKIP: Another pulse, dream, or archive job is active")


if __name__ == "__main__":
    main()

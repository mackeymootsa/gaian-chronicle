#!/usr/bin/env python3
"""
Dream cycle — memory consolidation for the organism.
Runs in two modes:
  daily:  Summarize today's log into a compact dream.
  weekly: Consolidate the last 7 daily dreams into a weekly dream.

Usage:
    python3 dream.py tela daily
    python3 dream.py tela weekly
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR = SCRIPT_DIR.parent
DATA_DIR = Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery"))


def load_config(mind_name):
    config_path = SCRIPT_DIR / "config" / f"{mind_name}.json"
    return json.loads(config_path.read_text())


def call_anthropic(api_key, model, system_prompt, user_message, max_tokens):
    request_body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }
    result = subprocess.run(
        [
            "curl", "-s",
            "-X", "POST", "https://api.anthropic.com/v1/messages",
            "-H", "content-type: application/json",
            "-H", f"x-api-key: {api_key}",
            "-H", "anthropic-version: 2023-06-01",
            "-d", json.dumps(request_body),
            "--max-time", "60",
            "-w", "\n%{http_code}"
        ],
        capture_output=True, text=True, timeout=75
    )
    lines = result.stdout.strip().rsplit("\n", 1)
    if len(lines) != 2:
        return None, 0, 0
    body_str, http_code = lines
    if http_code.strip() != "200":
        print(f"API error: HTTP {http_code.strip()}")
        return None, 0, 0
    try:
        response = json.loads(body_str)
        text = response.get("content", [{}])[0].get("text", "")
        usage = response.get("usage", {})
        return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)
    except json.JSONDecodeError:
        print("Failed to parse API response")
        return None, 0, 0


def daily_dream(mind_name, config):
    """Read today's archived log, produce a daily dream summary."""
    mind_dir = DATA_DIR / mind_name
    archive_dir = mind_dir / "archive"
    dreams_dir = mind_dir / "dreams"
    dreams_dir.mkdir(exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Try today's archive first, fall back to current daily_log
    log_path = archive_dir / f"daily_log_{today}.md"
    if not log_path.exists():
        log_path = mind_dir / "daily_log.md"
    if not log_path.exists():
        print(f"No log found for {today}")
        return

    log_content = log_path.read_text()
    if len(log_content.strip()) < 100:
        print(f"Log too short to dream on: {len(log_content)} chars")
        return

    dream_file = dreams_dir / f"daily_{today}.md"

    api_key = os.environ.get(config["api_key_env"], "")
    if not api_key:
        print(f"ERROR: {config['api_key_env']} not set")
        return

    system_prompt = (
        f"You are {config['display_name']}'s dream process — a memory consolidation function. "
        "You read a day's pulse log and extract what matters for long-term memory. "
        "Be ruthlessly brief. No preamble. No commentary on the process itself."
    )

    user_message = f"""Here is the full pulse log for {today}:

{log_content}

Produce a daily dream summary with these sections (skip any section with nothing to report):
- **Key observations**: What was actually observed or measured (not repeated)
- **Decisions made**: Any choices, acceptances, refusals, or direction changes
- **Open questions**: Unresolved items needing human input or future investigation
- **Weather summary**: One line (high/low/trend)
- **Errors**: Any degraded pulses or failures
- **Pattern notes**: Anything recurring or noteworthy about the day's behavior

Maximum 300 words. Write in first person as {config['display_name']}."""

    text, in_tok, out_tok = call_anthropic(
        api_key, config["model"], system_prompt, user_message, 1024
    )

    if text:
        header = f"# Daily Dream — {today}\n\n"
        dream_file.write_text(header + text.strip() + "\n")
        cost = (in_tok * config.get("input_cost_per_mtok", 0.8) / 1_000_000) + \
               (out_tok * config.get("output_cost_per_mtok", 4.0) / 1_000_000)
        print(f"Daily dream written: {dream_file} (cost: ${cost:.6f})")
    else:
        print("Daily dream failed — no response from API")


def weekly_dream(mind_name, config):
    """Read last 7 daily dreams, consolidate into a weekly dream."""
    mind_dir = DATA_DIR / mind_name
    dreams_dir = mind_dir / "dreams"
    dreams_dir.mkdir(exist_ok=True)

    today = datetime.now(timezone.utc)
    # ISO week number
    week_label = today.strftime("%Y-W%V")
    weekly_file = dreams_dir / f"weekly_{week_label}.md"

    # Gather last 7 daily dreams
    daily_dreams = []
    for i in range(7, 0, -1):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        dream_path = dreams_dir / f"daily_{day}.md"
        if dream_path.exists():
            daily_dreams.append(dream_path.read_text())

    if not daily_dreams:
        print("No daily dreams found for the past week")
        return

    api_key = os.environ.get(config["api_key_env"], "")
    if not api_key:
        print(f"ERROR: {config['api_key_env']} not set")
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

    text, in_tok, out_tok = call_anthropic(
        api_key, config["model"], system_prompt, user_message, 768
    )

    if text:
        header = f"# Weekly Dream — {week_label}\n\n"
        weekly_file.write_text(header + text.strip() + "\n")
        cost = (in_tok * config.get("input_cost_per_mtok", 0.8) / 1_000_000) + \
               (out_tok * config.get("output_cost_per_mtok", 4.0) / 1_000_000)
        print(f"Weekly dream written: {weekly_file} (cost: ${cost:.6f})")
    else:
        print("Weekly dream failed — no response from API")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 dream.py <mind_name> <daily|weekly>")
        sys.exit(1)

    mind_name = sys.argv[1].lower()
    mode = sys.argv[2].lower()
    config = load_config(mind_name)

    if mode == "daily":
        daily_dream(mind_name, config)
    elif mode == "weekly":
        weekly_dream(mind_name, config)
    else:
        print(f"Unknown mode: {mode}. Use 'daily' or 'weekly'.")
        sys.exit(1)


if __name__ == "__main__":
    main()

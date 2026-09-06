#!/usr/bin/env python3
"""
Quadrumvirate Pulse — Multi-mind heartbeat system
Runs any member of the Quadrumvirate based on a config file.

Usage:
    python3 pulse.py tela          # Run Tela pulse using organism/config/tela.json
    python3 pulse.py nowa          # Run NoWa pulse using organism/config/nowa.json
    python3 pulse.py tecton        # Run Tecton pulse using organism/config/tecton.json

The config file specifies: API provider, model, API key env var, system prompt,
budget limits, and data sources.
"""

import json
import os
import sys
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from entry import entry_append
from runtime import atomic_write, load_budget, mind_lock, prepare_daily_log, record_usage

# -- Resolve paths --
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR = SCRIPT_DIR.parent
DATA_DIR = Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery"))


def log_to(filepath, msg):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(filepath, "a") as f:
        f.write(f"{now} {msg}\n")


def append_to_log(log_file, entry):
    cleaned = "\n".join(line if line.strip() else "" for line in entry.strip().splitlines())
    while "\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n", "\n")
    with open(log_file, "a") as f:
        f.write(f"{cleaned}\n\n---\n\n")

def load_config(mind_name):
    config_path = SCRIPT_DIR / "config" / f"{mind_name}.json"
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        sys.exit(1)
    return json.loads(config_path.read_text())


def load_text(path, default=""):
    p = Path(path)
    if p.exists():
        return p.read_text()
    return default


def persist_entry(mind_dir, **fields):
    """Surface journal failures and leave existing memory available for review."""
    try:
        return entry_append(mind_dir.parent / "entries", **fields)
    except (OSError, ValueError) as error:
        try:
            log_to(mind_dir / "error.log", f"ENTRY_ERROR: {error}")
        except OSError:
            print(f"ENTRY_ERROR: {error}", file=sys.stderr)
        raise


def record_footer(record):
    """Runner-authored provenance, distinct from citations claimed by a model."""
    return f"\n\n**Journal record:** `{record['entry_id']}`\n"


def fetch_live_data(config, mind_name, pulse_id):
    """Preserve each source's output or failure before presenting it to a model."""
    data_parts = []
    source_ids = []
    mind_dir = DATA_DIR / mind_name
    for fetcher in config.get("data_sources", []):
        script = SCRIPT_DIR / fetcher["script"]
        output, error, returncode = "", "", None
        if script.exists():
            try:
                cmd = ["python3", str(script)] if str(script).endswith(".py") else ["bash", str(script)]
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=30
                )
                output, returncode = result.stdout, result.returncode
                if returncode != 0:
                    error = result.stderr.strip() or f"Fetcher exited with status {returncode}"
                elif not output.strip():
                    error = "Fetcher returned no output"
            except Exception as failure:
                output = getattr(failure, "stdout", "") or ""
                if isinstance(output, bytes):
                    output = output.decode("utf-8", errors="replace")
                error = f"{type(failure).__name__}: {failure}"
        else:
            error = f"Fetcher script not found: {fetcher['script']}"

        tag = fetcher.get("epistemic_tag", "UNKNOWN")
        if error or tag not in ("FETCHED", "DERIVED"):
            tag = "UNKNOWN"
        record = persist_entry(mind_dir, author=mind_name, entry_kind="observation",
            content=output if output.strip() else error, epistemic_tag=tag,
            data_source=fetcher.get("name", fetcher["script"]), source_refs=[fetcher["script"]],
            pulse_id=pulse_id, payload={"returncode": returncode, "error": error or None},
            timestamp=datetime.now(timezone.utc).isoformat())
        source_ids.append(record["entry_id"])
        status = f"\nSource failure: {error}" if error else ""
        data_parts.append(f"### Source record: {record['entry_id']} [{tag}]{status}\n{record['content']}")
    return ("\n\n".join(data_parts) if data_parts else "No live data sources configured."), source_ids


def load_core_docs(config):
    """Load core reference documents listed in config."""
    docs = []
    for doc_path in config.get("core_docs", []):
        full_path = REPO_DIR / doc_path
        if full_path.exists():
            content = full_path.read_text()
            docs.append(f"### {doc_path}\n{content}")
    return "\n\n---\n\n".join(docs) if docs else ""


def load_dreams(mind_dir):
    """Load latest daily dream and latest weekly dream."""
    dreams_dir = mind_dir / "dreams"
    parts = []
    if dreams_dir.exists():
        dailies = sorted(dreams_dir.glob("daily_*.md"), reverse=True)
        if dailies:
            parts.append(dailies[0].read_text())
        weeklies = sorted(dreams_dir.glob("weekly_*.md"), reverse=True)
        if weeklies:
            parts.append(weeklies[0].read_text())
    return "\n\n---\n\n".join(parts) if parts else ""


def call_anthropic(api_key, model, system_prompt, user_message, max_tokens, timeout=30):
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
            "--max-time", str(timeout),
            "-w", "\n%{http_code}"
        ],
        capture_output=True, text=True, timeout=timeout + 15
    )
    lines = result.stdout.strip().rsplit("\n", 1)
    if len(lines) != 2:
        return None, "000", 0, 0
    body_str, http_code = lines
    if http_code.strip() != "200":
        return None, http_code.strip(), 0, 0
    try:
        response = json.loads(body_str)
        input_tokens = response.get("usage", {}).get("input_tokens", 0)
        output_tokens = response.get("usage", {}).get("output_tokens", 0)
        text = "".join(block.get("text", "") for block in response.get("content", [])
                       if block.get("type") == "text")
        return text, "200", input_tokens, output_tokens
    except json.JSONDecodeError:
        return None, "PARSE_ERROR", 0, 0


def call_openai(api_key, model, system_prompt, user_message, max_tokens, timeout=30):
    request_body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    result = subprocess.run(
        [
            "curl", "-s",
            "-X", "POST", "https://api.openai.com/v1/chat/completions",
            "-H", "content-type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", json.dumps(request_body),
            "--max-time", str(timeout),
            "-w", "\n%{http_code}"
        ],
        capture_output=True, text=True, timeout=timeout + 15
    )
    lines = result.stdout.strip().rsplit("\n", 1)
    if len(lines) != 2:
        return None, "000", 0, 0
    body_str, http_code = lines
    if http_code.strip() != "200":
        return None, http_code.strip(), 0, 0
    try:
        response = json.loads(body_str)
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        choices = response.get("choices") or [{}]
        text = choices[0].get("message", {}).get("content") or ""
        return text, "200", input_tokens, output_tokens
    except json.JSONDecodeError:
        return None, "PARSE_ERROR", 0, 0


def call_google(api_key, model, system_prompt, user_message, max_tokens, timeout=30):
    request_body = {
        "contents": [{"parts": [{"text": user_message}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"maxOutputTokens": max_tokens}
    }
    result = subprocess.run(
        [
            "curl", "-s",
            "-X", "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            "-H", "content-type: application/json",
            "-d", json.dumps(request_body),
            "--max-time", str(timeout),
            "-w", "\n%{http_code}"
        ],
        capture_output=True, text=True, timeout=timeout + 15
    )
    lines = result.stdout.strip().rsplit("\n", 1)
    if len(lines) != 2:
        return None, "000", 0, 0
    body_str, http_code = lines
    if http_code.strip() != "200":
        return None, http_code.strip(), 0, 0
    try:
        response = json.loads(body_str)
        candidates = response.get("candidates") or [{}]
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        usage = response.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        return text, "200", input_tokens, output_tokens
    except json.JSONDecodeError:
        return None, "PARSE_ERROR", 0, 0


API_CALLERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "google": call_google,
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pulse.py <mind_name>")
        print("  e.g. python3 pulse.py tela")
        sys.exit(1)

    mind_name = sys.argv[1].lower()
    config = load_config(mind_name)

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    now_utc = now.strftime("%H:%M")
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # -- Paths --
    mind_dir = DATA_DIR / mind_name
    mind_dir.mkdir(parents=True, exist_ok=True)
    memory_file = mind_dir / "memory.json"
    daily_log = mind_dir / "daily_log.md"
    budget_file = mind_dir / "budget.json"
    pulse_brief = mind_dir / "pulse_brief.md"
    error_log = mind_dir / "error.log"
    pulse_log = mind_dir / "pulse.log"

    # -- API key --
    api_key_var = config["api_key_env"]
    api_key = os.environ.get(api_key_var, "")
    if not api_key:
        log_to(error_log, f"ERROR: {api_key_var} not set")
        sys.exit(1)

    try:
        with mind_lock(mind_dir):
            run_pulse(config, mind_name, api_key, mind_dir, memory_file, daily_log,
                      budget_file, pulse_brief, error_log, pulse_log, today, now_utc, now_iso)
    except BlockingIOError:
        log_to(error_log, "SKIP: Another pulse, dream, or archive job is active")


def run_pulse(config, mind_name, api_key, mind_dir, memory_file, daily_log,
              budget_file, pulse_brief_file, error_log, pulse_log,
              today, now_utc, now_iso):

    provider = config["provider"]
    model = config["model"]
    max_tokens = config.get("max_tokens", 2048)
    daily_budget = config.get("daily_budget_usd", 2.00)
    display_name = config.get("display_name", mind_name.capitalize())
    cadence = config.get("cadence", "hourly")

    # -- Init daily log --
    prepare_daily_log(daily_log, today,
        f"# {display_name} Daily Log — {today} (UTC)\n"
        f"Pulse: {display_name} ({model}) • Cadence: {cadence} • Mode: READ-ONLY • Budget: ${daily_budget:.2f}/day\n\n---\n\n")

    # -- Budget --
    budget = load_budget(budget_file, today)

    if budget["spent_usd"] >= daily_budget:
        append_to_log(daily_log,
            f"### {now_utc} UTC\n**Status:** BUDGET_SLEEP\n"
            f"**Notes:** Cap ${daily_budget:.2f} reached. Spent: ${budget['spent_usd']:.4f}.")
        return

    # -- Context --
    system_prompt_path = SCRIPT_DIR / "prompts" / config.get("system_prompt", f"{mind_name}-system.txt")
    system_prompt = load_text(system_prompt_path, f"You are {display_name}.")

    memory = load_text(memory_file, json.dumps({
        "pulse_count": 0, "last_pulse": "never",
        "observations": [], "threads": [],
        "notes": f"First pulse. You are {display_name}, waking up for the first time."
    }))

    brief = load_text(pulse_brief_file, "No pulse brief available.")

    # -- Shared state --
    shared_state_path = REPO_DIR / "quadrumvirate" / "state.md"
    shared_state = load_text(shared_state_path, "No shared state file yet.")

    # -- Live data --
    pulse_id = f"{mind_name}-{now_iso}-{uuid.uuid4().hex[:8]}"
    live_data, source_ids = fetch_live_data(config, mind_name, pulse_id)

    # -- Core docs --
    core_docs = load_core_docs(config)

    # -- Dreams (consolidated memory) --
    dreams = load_dreams(mind_dir)

    pulse_num = budget["pulses_run"] + 1

    # -- Invitation (if present) --
    invitation_file = mind_dir / "invitation.md"
    invitation = load_text(invitation_file, "")

    # -- User message --
    invitation_section = f"""
## Invitation (read carefully — this is addressed to you)
{invitation}
""" if invitation else ""

    core_docs_section = f"""
## Core Documents (reference — do not summarize, use as needed)
{core_docs}
""" if core_docs else ""

    dreams_section = f"""
## Consolidated Memory (dreams)
{dreams}
""" if dreams else ""

    user_message = f"""You are waking up for pulse #{pulse_num} on {today} at {now_utc} UTC.

## Your Memory (from previous pulse)
```json
{memory}
```

## Pulse Brief (human-curated context)
{brief}

## Shared Quadrumvirate State
{shared_state}{invitation_section}{core_docs_section}{dreams_section}

## Live Data
{live_data}

## Instructions
1. Read your memory, the pulse brief, shared state, and any live data.
2. If you have observations, write them with proper tags.
3. If you have nothing meaningful, say "Pulse active. No signal."
4. Think about what the next pulse (also you) needs to know.
5. Source record IDs identify the data you received, not verified facts. Cite exact IDs when useful; preserve uncertainty and source failures.

Respond with ONLY a JSON object (no markdown fences, no preamble, no text outside the JSON):
{{"log_entry": "your markdown log entry (use ### HH:MM UTC format)", "memory": {{"pulse_count": N, "last_pulse": "ISO8601", "observations": ["list"], "threads": ["list"], "notes": "for next pulse", "buffer": ["optional list of messages for Nova"]}}}}"""

    # -- Call API --
    caller = API_CALLERS.get(provider)
    if not caller:
        log_to(error_log, f"ERROR: Unknown provider '{provider}'")
        return

    text, http_code, input_tokens, output_tokens = caller(
        api_key, model, system_prompt, user_message, max_tokens
    )

    cost = 0
    if http_code == "200" or input_tokens or output_tokens:
        cost = record_usage(budget_file, budget, config, input_tokens, output_tokens, "pulse")

    response_record = persist_entry(mind_dir, author=mind_name, entry_kind="trace",
        content=text if text and text.strip() else f"API returned HTTP {http_code} with no usable text",
        source_refs=source_ids,
        pulse_id=pulse_id, data_source="pulse_response",
        payload={"provider": provider, "model": model, "http_code": http_code,
                 "input_tokens": input_tokens, "output_tokens": output_tokens},
        timestamp=datetime.now(timezone.utc).isoformat())

    if http_code != "200" or not text:
        append_to_log(daily_log,
            f"### {now_utc} UTC\n**Status:** DEGRADED\n"
            f"**Notes:** API returned HTTP {http_code}.")
        log_to(error_log, f"API_ERROR: HTTP {http_code}")
        return

    # -- Parse response --
    clean = text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    if clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    # Fix unescaped newlines inside JSON string values (Haiku outputs literal newlines)
    def _repair_json(s):
        out, in_str, esc = [], False, False
        for c in s:
            if esc:
                out.append(c); esc = False; continue
            if c == '\\':
                esc = True; out.append(c); continue
            if c == '"':
                in_str = not in_str; out.append(c); continue
            if in_str and c == '\n':
                out.append('\\n'); continue
            out.append(c)
        return ''.join(out)

    try:
        response = json.loads(clean)
    except json.JSONDecodeError:
        try:
            response = json.loads(_repair_json(clean))
        except json.JSONDecodeError as e:
            append_to_log(daily_log,
                f"### {now_utc} UTC\n**Status:** DEGRADED\n"
                f"**Notes:** Response not valid JSON: {e}")
            log_to(error_log, f"JSON_ERROR: {e}\nRaw: {text[:500]}")
            return

    log_entry = response.get("log_entry") if isinstance(response, dict) else None
    memory_update = response.get("memory") if isinstance(response, dict) else None

    if not isinstance(log_entry, str) or not log_entry.strip() or not isinstance(memory_update, dict):
        append_to_log(daily_log,
            f"### {now_utc} UTC\n**Status:** DEGRADED\n"
            f"**Notes:** Response requires a non-empty log_entry string and a memory object.")
        return

    # -- Success --
    record = persist_entry(mind_dir, author=mind_name, entry_kind="interpretation",
        content=log_entry, source_refs=[response_record["entry_id"]], pulse_id=pulse_id,
        payload={"provider": provider, "model": model}, timestamp=datetime.now(timezone.utc).isoformat())
    append_to_log(daily_log, log_entry + record_footer(record))
    memory_update["last_entry_id"] = record["entry_id"]
    atomic_write(memory_file, json.dumps(memory_update, indent=2, ensure_ascii=False))

    log_to(pulse_log,
        f"PULSE_OK: #{pulse_num} cost=${cost:.6f} total=${budget['spent_usd']:.6f} "
        f"in={input_tokens} out={output_tokens}")


if __name__ == "__main__":
    main()

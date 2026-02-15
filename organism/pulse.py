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
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# -- Resolve paths --
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR = SCRIPT_DIR.parent
DATA_DIR = Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery"))


def log_to(filepath, msg):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(filepath, "a") as f:
        f.write(f"{now} {msg}\n")


def append_to_log(log_file, entry):
    with open(log_file, "a") as f:
        f.write(f"\n{entry}\n\n---\n\n")


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


def fetch_live_data(config):
    """Run all data fetchers defined in config."""
    data_parts = []
    for fetcher in config.get("data_sources", []):
        script = SCRIPT_DIR / fetcher["script"]
        if script.exists():
            try:
                cmd = ["python3", str(script)] if str(script).endswith(".py") else ["bash", str(script)]
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=30
                )
                if result.stdout.strip():
                    data_parts.append(result.stdout.strip())
            except Exception as e:
                data_parts.append(f"Fetcher {fetcher['script']} failed: {e}")
    return "\n\n".join(data_parts) if data_parts else "No live data sources configured."


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
            "--max-time", "30",
            "-w", "\n%{http_code}"
        ],
        capture_output=True, text=True, timeout=45
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
        text = response.get("content", [{}])[0].get("text", "")
        return text, "200", input_tokens, output_tokens
    except json.JSONDecodeError:
        return None, "PARSE_ERROR", 0, 0


def call_openai(api_key, model, system_prompt, user_message, max_tokens):
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
            "--max-time", "30",
            "-w", "\n%{http_code}"
        ],
        capture_output=True, text=True, timeout=45
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
        text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return text, "200", input_tokens, output_tokens
    except json.JSONDecodeError:
        return None, "PARSE_ERROR", 0, 0


def call_google(api_key, model, system_prompt, user_message, max_tokens):
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
            "--max-time", "30",
            "-w", "\n%{http_code}"
        ],
        capture_output=True, text=True, timeout=45
    )
    lines = result.stdout.strip().rsplit("\n", 1)
    if len(lines) != 2:
        return None, "000", 0, 0
    body_str, http_code = lines
    if http_code.strip() != "200":
        return None, http_code.strip(), 0, 0
    try:
        response = json.loads(body_str)
        text = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
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
    lock_file = mind_dir / "pulse.lock"
    error_log = mind_dir / "error.log"
    pulse_log = mind_dir / "pulse.log"

    # -- API key --
    api_key_var = config["api_key_env"]
    api_key = os.environ.get(api_key_var, "")
    if not api_key:
        log_to(error_log, f"ERROR: {api_key_var} not set")
        sys.exit(1)

    # -- Lock --
    if lock_file.exists():
        lock_age = time.time() - lock_file.stat().st_mtime
        if lock_age < 300:
            log_to(error_log, f"SKIP: Lock held ({lock_age:.0f}s)")
            sys.exit(0)
        lock_file.unlink()

    lock_file.touch()
    try:
        run_pulse(config, mind_name, api_key, mind_dir, memory_file, daily_log,
                  budget_file, pulse_brief, error_log, pulse_log, today, now_utc, now_iso)
    finally:
        lock_file.unlink(missing_ok=True)


def run_pulse(config, mind_name, api_key, mind_dir, memory_file, daily_log,
              budget_file, pulse_brief_file, error_log, pulse_log,
              today, now_utc, now_iso):

    provider = config["provider"]
    model = config["model"]
    max_tokens = config.get("max_tokens", 2048)
    daily_budget = config.get("daily_budget_usd", 2.00)
    input_cost = config.get("input_cost_per_mtok", 1.0)
    output_cost = config.get("output_cost_per_mtok", 5.0)
    display_name = config.get("display_name", mind_name.capitalize())
    cadence = config.get("cadence", "hourly")

    # -- Init daily log --
    if not daily_log.exists() or today not in daily_log.read_text().split("\n")[0]:
        daily_log.write_text(
            f"# {display_name} Daily Log — {today} (UTC)\n"
            f"Pulse: {display_name} ({model}) • Cadence: {cadence} • Mode: READ-ONLY • Budget: ${daily_budget:.2f}/day\n\n---\n\n"
        )

    # -- Budget --
    if budget_file.exists():
        budget = json.loads(budget_file.read_text())
        if budget.get("date") != today:
            archive = mind_dir / f"budget_{budget['date']}.json"
            archive.write_text(json.dumps(budget))
            budget = {"date": today, "spent_usd": 0, "pulses_run": 0,
                      "input_tokens": 0, "output_tokens": 0}
    else:
        budget = {"date": today, "spent_usd": 0, "pulses_run": 0,
                  "input_tokens": 0, "output_tokens": 0}

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
    live_data = fetch_live_data(config)

    pulse_num = budget["pulses_run"] + 1

    # -- User message --
    user_message = f"""You are waking up for pulse #{pulse_num} on {today} at {now_utc} UTC.

## Your Memory (from previous pulse)
```json
{memory}
```

## Pulse Brief (human-curated context)
{brief}

## Shared Quadrumvirate State
{shared_state}

## Live Data
{live_data}

## Instructions
1. Read your memory, the pulse brief, shared state, and any live data.
2. If you have observations, write them with proper tags.
3. If you have nothing meaningful, say "Pulse active. No signal."
4. Think about what the next pulse (also you) needs to know.

Respond with ONLY a JSON object (no markdown fences, no preamble, no text outside the JSON):
{{"log_entry": "your markdown log entry (use ### HH:MM UTC format)", "memory": {{"pulse_count": N, "last_pulse": "ISO8601", "observations": ["list"], "threads": ["list"], "notes": "for next pulse"}}}}"""

    # -- Call API --
    caller = API_CALLERS.get(provider)
    if not caller:
        log_to(error_log, f"ERROR: Unknown provider '{provider}'")
        return

    text, http_code, input_tokens, output_tokens = caller(
        api_key, model, system_prompt, user_message, max_tokens
    )

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

    try:
        response = json.loads(clean)
    except json.JSONDecodeError as e:
        append_to_log(daily_log,
            f"### {now_utc} UTC\n**Status:** DEGRADED\n"
            f"**Notes:** Response not valid JSON: {e}")
        log_to(error_log, f"JSON_ERROR: {e}\nRaw: {text[:500]}")
        return

    log_entry = response.get("log_entry", "")
    memory_update = response.get("memory")

    if not log_entry or memory_update is None:
        append_to_log(daily_log,
            f"### {now_utc} UTC\n**Status:** DEGRADED\n"
            f"**Notes:** Missing log_entry or memory in response.")
        return

    # -- Success --
    append_to_log(daily_log, log_entry)
    memory_file.write_text(json.dumps(memory_update, indent=2, ensure_ascii=False))

    # -- Budget --
    cost = (input_tokens * input_cost / 1_000_000) + (output_tokens * output_cost / 1_000_000)
    budget["spent_usd"] = round(budget["spent_usd"] + cost, 6)
    budget["pulses_run"] = pulse_num
    budget["input_tokens"] += input_tokens
    budget["output_tokens"] += output_tokens
    budget_file.write_text(json.dumps(budget))

    log_to(pulse_log,
        f"PULSE_OK: #{pulse_num} cost=${cost:.6f} total=${budget['spent_usd']:.6f} "
        f"in={input_tokens} out={output_tokens}")


if __name__ == "__main__":
    main()

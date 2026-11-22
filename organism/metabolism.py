#!/usr/bin/env python3
"""Read-only Linux body sense. Measurements and uncertainty precede interpretation."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

SCRIPT_DIR = Path(__file__).resolve().parent
LEVELS = {"GREEN": 0, "YELLOW": 1, "RED": 2}


def classify(value, rule):
    if value is None:
        return "UNKNOWN"
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Metric must be a finite non-negative number")
    yellow, red = rule["yellow"], rule["red"]
    if rule.get("direction", "high") == "low":
        return "RED" if value <= red else ("YELLOW" if value <= yellow else "GREEN")
    return "RED" if value >= red else ("YELLOW" if value >= yellow else "GREEN")


def sense(metrics, rules, errors=None):
    states = {name: classify(value, rules[name]) for name, value in metrics.items() if name in rules}
    known = [state for state in states.values() if state != "UNKNOWN"]
    state = max(known, key=LEVELS.get) if known else "UNKNOWN"
    if ("UNKNOWN" in states.values() or errors) and state == "GREEN":
        state = "UNKNOWN"
    return {"state": state, **metrics, "metric_states": states, "errors": errors or []}


def tree_kb(path, limit=20000):
    """Count regular files without following symlinks or reading their contents."""
    if not path.exists():
        return 0
    total, count = 0, 0
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(path, followlinks=False, onerror=fail):
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            count += 1
            if count > limit:
                raise ValueError("Storage scan exceeded 20,000 files")
            item = Path(directory) / name
            if not item.is_symlink():
                total += item.stat().st_size
    return round(total / 1024, 2)


def ssh_counts(now):
    """Aggregate only. No IP addresses or original auth messages leave this function."""
    start = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC")
    end = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    result = subprocess.run(["journalctl", "--quiet", "--no-pager", "--output=json",
        "--since", start, "--until", end, "-n", "5000", "SYSLOG_IDENTIFIER=sshd"],
        capture_output=True, text=True, timeout=5)
    if result.returncode or result.stderr.strip() or not result.stdout.strip():
        raise ValueError("No complete readable SSH journal view; access or activity may be absent")
    lines = result.stdout.splitlines()
    if len(lines) >= 5000:
        raise ValueError("SSH journal hit the 5,000-record limit; counts would be incomplete")
    failed, ips, unknown_ip = 0, set(), False
    for line in lines:
        message = json.loads(line).get("MESSAGE", "")
        if not isinstance(message, str):
            continue
        if re.search(r"\bFailed (?:password|publickey|keyboard-interactive)\b", message):
            failed += 1
            match = re.search(r"\bfrom ([0-9a-fA-F.:]+)(?: port|\s|$)", message)
            if match:
                ips.add(match.group(1))
            else:
                unknown_ip = True
    return failed, None if unknown_ip else len(ips)


def collect(runtime, mind, thresholds, *, now=None, proc=Path("/proc")):
    now = now or datetime.now(timezone.utc)
    runtime = Path(runtime)
    mind_dir = runtime / mind
    body = {"load_per_core_pct": None, "ram_pct": None, "disk_pct": None, "uptime_days": None}
    errors = []
    try:
        body["load_per_core_pct"] = round(float((proc / "loadavg").read_text().split()[0]) / (os.cpu_count() or 1) * 100, 2)
        memory = {line.split(":")[0]: int(line.split()[1]) for line in (proc / "meminfo").read_text().splitlines()}
        body["ram_pct"] = round((1 - memory["MemAvailable"] / memory["MemTotal"]) * 100, 2)
        body["uptime_days"] = round(float((proc / "uptime").read_text().split()[0]) / 86400, 3)
    except (OSError, ValueError, KeyError, ZeroDivisionError) as error:
        errors.append(f"Linux measurements unavailable: {type(error).__name__}")
    try:
        disk = shutil.disk_usage(runtime)
        body["disk_pct"] = round(disk.used / disk.total * 100, 2)
    except (OSError, ZeroDivisionError) as error:
        errors.append(f"Disk measurement unavailable: {type(error).__name__}")
    result = {"body": sense(body, thresholds["body"], errors)}

    economic = {"spent_usd_today": None, "requests_today": None, "cost_per_request_usd": None}
    errors = []
    try:
        budget = json.loads((mind_dir / "budget.json").read_text())
        budget_day = datetime.strptime(budget["date"], "%Y-%m-%d").date()
        if budget_day > now.date():
            raise ValueError("Future budget date")
        if budget_day == now.date():
            spent = budget["spent_usd"]
            pulses, dreams = budget["pulses_run"], budget.get("dreams_run", 0)
            if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in (pulses, dreams)):
                raise ValueError("Invalid request counters")
            requests = pulses + dreams
        else:
            spent, requests = 0, 0
        economic.update(spent_usd_today=spent, requests_today=requests,
                        cost_per_request_usd=round(spent / requests, 6) if requests else None)
        # Missing cost-per-request before the first request is expected, not a
        # measurement failure. Keep null, rather than inventing a zero-cost call.
        rules = {k: v for k, v in thresholds["economic"].items() if k != "cost_per_request_usd" or requests}
        result["economic"] = sense(economic, rules)
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as error:
        errors.append(f"Budget unavailable or invalid: {type(error).__name__}")
        result["economic"] = sense({key: None for key in economic}, thresholds["economic"], errors)
    result["economic"]["basis"] = "configured token-rate estimate, pulse + dream; sampled before this request"

    growth = {"mind_kb": None, "archive_kb": None, "journal_kb": None,
              "annotations_kb": None, "palace_kb": None}
    errors = []
    for key, path in (("mind_kb", mind_dir), ("archive_kb", mind_dir / "archive"),
                      ("journal_kb", runtime / "entries"), ("annotations_kb", runtime / "annotations"),
                      ("palace_kb", runtime / "palace")):
        try:
            growth[key] = tree_kb(path)
        except (OSError, ValueError) as error:
            errors.append(f"{key} unavailable: {type(error).__name__}")
    result["growth"] = sense(growth, thresholds["growth"], errors)

    membrane = {"failed_ssh_24h": None, "unique_ips_24h": None}
    errors = []
    try:
        membrane["failed_ssh_24h"], membrane["unique_ips_24h"] = ssh_counts(now)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        errors.append(f"SSH counts unavailable: {type(error).__name__}")
    result["membrane"] = sense(membrane, thresholds["membrane"], errors)
    result["membrane"]["coverage"] = "readable sshd journal in the past 24 hours; retention may omit events"

    alerts = []
    if result["economic"]["state"] in ("YELLOW", "RED") and result["growth"]["state"] in ("YELLOW", "RED"):
        alerts.append("Spending and storage are both elevated; review resource use")
    if result["membrane"]["state"] == "RED":
        alerts.append("SSH failure counts crossed a red threshold; propose a human review")
    red = sum(result[name]["state"] == "RED" for name in ("body", "economic", "growth", "membrane"))
    result["attention"] = "focused" if red >= 2 else "routine"
    result["alerts"] = alerts
    result["sampled_at"] = now.isoformat().replace("+00:00", "Z")
    result["revision"] = os.environ.get("GAIAN_REVISION", "unknown (unmanaged invocation)")
    result["notes"] = ["Load per core is queue pressure, not measured CPU utilization.",
                       "Boot age is context, not proof of illness. Energy use and VPS cost are not measured."]
    names = ("body", "economic", "growth", "membrane")
    content = "Metabolism: " + "; ".join(f"{name}={result[name]['state']}" for name in names) + "."
    if any(result[name]["state"] != "GREEN" for name in names):
        content += "\n" + json.dumps(result, ensure_ascii=False)
    else:
        content += f" Estimated spend today ${economic['spent_usd_today']:.4f}; {economic['requests_today']} requests."
    unavailable = any(result[name]["errors"] or "UNKNOWN" in result[name]["metric_states"].values() for name in names)
    return {"content": content, "payload": result, "epistemic_tag": "UNKNOWN" if unavailable else "DERIVED"}


def load_thresholds(path):
    thresholds = json.loads(Path(path).read_text())
    for group in ("body", "economic", "growth", "membrane"):
        for rule in thresholds[group].values():
            yellow, red = rule["yellow"], rule["red"]
            direction = rule.get("direction", "high")
            if direction not in ("high", "low") or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0 for n in (yellow, red)):
                raise ValueError("Invalid metabolism threshold")
            if (direction == "high" and yellow >= red) or (direction == "low" and yellow <= red):
                raise ValueError("Metabolism thresholds must be ordered by severity")
    return thresholds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mind", default=os.environ.get("GAIAN_MIND", "tela"))
    parser.add_argument("--runtime-dir", type=Path, default=Path(os.environ.get("NURSERY_DIR", "/var/opt/quadrumvirate/nursery")))
    parser.add_argument("--thresholds", type=Path, default=SCRIPT_DIR / "config" / "metabolism-thresholds.json")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", args.mind):
        parser.error("Invalid mind name")
    try:
        print(json.dumps(collect(args.runtime_dir, args.mind, load_thresholds(args.thresholds)), ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Metabolism unavailable: {type(error).__name__}: {error}\n")


if __name__ == "__main__":
    main()

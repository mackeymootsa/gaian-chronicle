"""Declarative measurement watchpoints. A matching predicate requests a review.

It does not falsify a belief, resolve a question, run code, or schedule a call.
"""

from datetime import timedelta
import math
import operator

from palace import text_field, utc

CHANNEL = "cognitive_watchpoint"
EVALUATIONS = "watchpoint_evaluation"
OPERATORS = {"gt": operator.gt, "gte": operator.ge, "lt": operator.lt, "lte": operator.le}
MAX_ACTIVE = 6


def project(records):
    watches = {}
    for record in records:
        channel = record.get("data_source")
        if channel == CHANNEL:
            event = record.get("payload", {}).get("watch", {})
            if event.get("op") == "watch":
                watches[record["entry_id"]] = {"id": record["entry_id"], "owner": record["author"],
                    "content": record["content"], "target_id": event["target_id"],
                    "metric": event["metric"], "operator": event["operator"], "threshold": event["threshold"],
                    "confirm_samples": event["confirm_samples"], "status": "active",
                    "created": record["timestamp"], "last": None}
            elif event.get("op") == "watch_status" and event.get("target_id") in watches:
                watches[event["target_id"]]["status"] = event["status"]
                # An intentional reactivation starts a new evaluation episode.
                if event["status"] == "active":
                    watches[event["target_id"]]["last"] = None
            else:
                raise ValueError("Invalid watchpoint event; retain it for review")
        elif channel == EVALUATIONS:
            evaluation = record.get("payload", {}).get("evaluation", {})
            target = evaluation.get("watch_id")
            if target not in watches:
                raise ValueError("Watch evaluation references missing history")
            watches[target]["last"] = {**evaluation, "entry_id": record["entry_id"], "timestamp": record["timestamp"]}
    return watches


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def plan(action, author, records, metrics):
    watches = project(records)
    op = action["op"]
    if op == "watch_status":
        if set(action) - {"op", "target_id", "status", "content"}:
            raise ValueError("Unknown watch status fields")
        watch = watches.get(action.get("target_id"))
        if watch is None or author not in (watch["owner"], "nova"):
            raise ValueError("Only the owner or Nova can change an existing watchpoint")
        status = action.get("status")
        if status not in ("active", "resting", "retired"):
            raise ValueError("Watch status must be active, resting or retired")
        if status == "active" and watch["status"] != "active" and sum(w["status"] == "active" for w in watches.values()) >= MAX_ACTIVE:
            raise ValueError("Six active watchpoints already exist")
        return {"entry_kind": "trace", "content": text_field(action.get("content"), "content"),
                "data_source": CHANNEL, "source_refs": [watch["id"]],
                "payload": {"watch": {"op": op, "target_id": watch["id"], "status": status}, "cognition_action": True}}
    if op != "watch" or set(action) - {"op", "target_id", "metric", "operator", "threshold", "confirm_samples", "content"}:
        raise ValueError("Unknown watch fields")
    if sum(w["status"] == "active" for w in watches.values()) >= MAX_ACTIVE:
        raise ValueError("Six active watchpoints already exist")
    metric = action.get("metric")
    if not isinstance(metric, str) or metric not in metrics:
        raise ValueError("Metric is not enabled by the reviewed sensing manifest")
    rule = metrics[metric]
    op_name = action.get("operator")
    threshold = action.get("threshold")
    confirmations = action.get("confirm_samples", 2)
    if op_name not in OPERATORS or not finite(threshold) or not rule["min"] <= threshold <= rule["max"]:
        raise ValueError("Watch requires an allowed comparison and finite threshold in the metric's range")
    if isinstance(confirmations, bool) or not isinstance(confirmations, int) or not 1 <= confirmations <= 3:
        raise ValueError("confirm_samples must be 1–3 distinct, fresh samples")
    target = action.get("target_id")
    if not isinstance(target, str) or not any(r["entry_id"] == target for r in records):
        raise ValueError("A watchpoint must cite the question, thread or claim it serves")
    event = {"op": "watch", "target_id": target, "metric": metric, "operator": op_name,
             "threshold": threshold, "confirm_samples": confirmations}
    if any(w["status"] == "active" and all(w[k] == event[k] for k in ("target_id", "metric", "operator", "threshold", "confirm_samples")) for w in watches.values()):
        raise ValueError("That active watchpoint already exists")
    return {"entry_kind": "watchpoint", "content": text_field(action.get("content"), "content"),
            "data_source": CHANNEL, "source_refs": [target],
            "payload": {"watch": event, "cognition_action": True}}


def at_path(value, path):
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def measurement(records, rule, now):
    """Latest acquisition wins, including a failed one. Never reuse an older success."""
    candidates = [r for r in records if r.get("data_source") == rule["source"]
                  and r["entry_kind"] == "observation" and rule["script"] in r.get("source_refs", [])
                  and ("author" not in rule or r["author"] == rule["author"])]
    if not candidates:
        return None, None, None, "No source record"
    record = max(enumerate(candidates), key=lambda pair: (pair[1]["timestamp"], pair[0]))[1]
    payload = record.get("payload", {})
    value = at_path(payload, rule["value_path"])
    sample_time = at_path(payload, rule["time_path"])
    try:
        sample = utc(sample_time) if isinstance(sample_time, str) and sample_time else None
        age = (now - sample).total_seconds() if sample is not None else None
    except (ValueError, TypeError):
        sample, age = None, None
    if payload.get("error") or payload.get("returncode") != 0:
        return record, None, sample_time, "Latest source failed"
    if at_path(payload, rule["quality_path"]) not in ("GREEN", "YELLOW", "RED"):
        return record, None, sample_time, "Measurement quality unavailable"
    if age is None or age < 0 or age > rule["max_age_seconds"]:
        return record, None, sample_time, "Missing, future or stale sample timestamp"
    if not finite(value) or not rule["min"] <= value <= rule["max"]:
        return record, None, sample_time, "Missing or out-of-range value"
    return record, value, sample.isoformat(), None


def evaluate(records, metrics, timestamp):
    """Plan evidence-linked events; the caller appends them while holding its lock."""
    now = utc(timestamp)
    fields = []
    for watch in project(records).values():
        if watch["status"] != "active":
            continue
        previous = watch["last"] or {}
        rule = metrics.get(watch["metric"])
        if rule is None:
            record, value, sample_time, error = None, None, None, "Metric disabled in reviewed manifest"
        else:
            record, value, sample_time, error = measurement(records, rule, now)
        source_id = record["entry_id"] if record else None
        # UNKNOWN is recorded once per distinct failure. A previously good
        # sample aging out is also a distinct state change, even without new data.
        if (previous.get("source_id"), previous.get("error")) == (source_id, error) and previous:
            continue
        if not error and previous.get("sample_time") == sample_time:
            continue  # Repeated acquisition of the same timestamp is not confirmation.
        previous_time = utc(previous["sample_time"]) if previous.get("sample_time") and not previous.get("error") else None
        if not error and previous_time and utc(sample_time) < previous_time:
            error, value = "Sample timestamp went backwards", None
        gap = bool(not error and previous_time and (utc(sample_time) - previous_time).total_seconds() > rule["max_age_seconds"])
        matched = OPERATORS[watch["operator"]](value, watch["threshold"]) if not error else None
        streak = ((0 if gap else previous.get("streak", 0)) + 1) if matched else 0
        confirmed = matched is True and streak >= watch["confirm_samples"]
        entered = confirmed and not previous.get("confirmed", False)
        last_alert = previous.get("last_alert_at")
        cooldown = bool(last_alert and now - utc(last_alert) < timedelta(hours=6))
        notify = entered and not cooldown
        event = {"watch_id": watch["id"], "target_id": watch["target_id"], "metric": watch["metric"],
                 "source_id": source_id, "sample_time": sample_time, "value": value, "error": error,
                 "matched": matched, "streak": streak, "confirmed": confirmed, "sample_gap": gap,
                 "notify": notify, "last_alert_at": now.isoformat() if notify else last_alert,
                 "operator": watch["operator"], "threshold": watch["threshold"]}
        status = "UNKNOWN" if error else ("condition met; review requested" if notify else "sample evaluated")
        content = f"Watch {watch['id']}: {status}. {watch['metric']} {watch['operator']} {watch['threshold']}; value={value}."
        if error:
            content += f" {error}. No conclusion about the underlying claim."
        fields.append({"author": "runner", "entry_kind": "observation", "content": content,
                       "epistemic_tag": "UNKNOWN" if error else "DERIVED", "data_source": EVALUATIONS,
                       "source_refs": [watch["id"], *([source_id] if source_id else [])],
                       "payload": {"evaluation": event}, "timestamp": now.isoformat()})
    return fields

# Body sensing and shared inquiry

This implements a bounded slice of DNA v2 and Cognitive Architecture v1:
proprioception, a shared buffer, and persistent questions/watchpoints. It builds
on the [canonical journal](ENTRIES.md). It does not claim a full Memory Palace,
autonomous repair system, or a new governance mode.

## The body report

Tela's first configured source is now `fetch-metabolism.sh`, backed by the
standard-library `metabolism.py`. It reads four groups of measurements:

| Sense | Measurements | Limits |
|-------|--------------|--------|
| Body | Load per reported CPU, available RAM, runtime disk use, uptime | Load is queue pressure, not measured CPU utilization; boot age is context |
| Economic | Today's estimated spend, counted pulse/dream responses, mean cost per response | Configured rates, not provider billing; sampled before the current request |
| Growth | Mind directory, archives, shared journal bytes | Bounded file-stat scan; no symlink traversal or content reads |
| Membrane | Failed SSH authentication messages and distinct source count | Readable sshd journal only, last 24 hours; no raw auth messages or IP addresses stored |

No SSH log access is required for the organism to run. Empty, inaccessible,
timed-out or capped journal reads produce `UNKNOWN`; they do not claim zero
attacks or a healthy membrane. The collector does not invoke sudo, change
permissions, repair services, or install anything. The body report also includes
the revision supplied by the deployment manager, or an explicit unknown marker
for direct invocations.

Thresholds in `config/metabolism-thresholds.json` are reviewed code. They start
from the architecture's proposed values, with shared journal size added. Daily
spend warnings do not change the existing per-mind allowance. Request counts and
mean cost include dreams as well as pulses. Zero requests produce a null mean.
Yellow/red thresholds include their exact boundary values. These thresholds
need calibration against actual operating history.

An all-green report is a short line. Elevated or incomplete reports include
detail; all reports retain machine-readable measurements and exact source output
in the journal. Source confidence can fall to `UNKNOWN` but cannot promote itself
to `VERIFIED`. A red membrane signal adds one deduplicated shared note; if the
queue is full, the observation remains and the rejected note is reported locally.
Two red senses focus the existing pulse on those readings. Neither condition
creates an extra model call, external alert, or infrastructure action.

This version measures storage size, not weekly growth rate, wattage or the VPS
bill. Those missing measurements remain unclaimed. NoWa/Tecton can share inquiry
when already enabled, but their configs do not add duplicate body sensing yet.

## Durable questions and cross-mind traces

Each mind's `inquiry_enabled` config enables an optional `inquiry` field in the
normal pulse response. Omission means no change. There is no extra API request.

The runner supports `open`, `comment`, and `status` actions. New items are
questions, watchpoints, proposals or notes. A watchpoint names a condition under
which a cited claim should be reconsidered; it is plain text for review, never
an expression evaluated as code. A proposal is a discussion item, never an
activated task, a request imposed on Nova, or permission to change the host.

All actions are canonical journal entries under `data_source: shared_inquiry`.
New questions/watchpoints/proposals use those entry kinds; notes, comments and
status assessments are traces. The original entry is immutable. `inquiry.py`
rebuilds the current view by replaying events; deleting `memory.json` or leaving
a question out of a dream cannot erase it. There is no separate authoritative
`buffer.jsonl`, database or classification cache to reconcile.

This is a small annotation mechanism within journal payloads. It does not yet
implement the architecture's separate Palace classification/annotation index.
Events record who made a status assessment and why. "Resolved" means an
attributed review, not runner-certified truth. Referenced IDs must exist, and
model citations/targets must have been supplied in the pulse's bounded context;
the runner cannot establish whether those sources actually justify the claim.

The allowed statuses are `open`, `watchpointed`, `resolved`, `falsified`,
`superseded`, and `false_alarm`. Only watchpoints can be falsified. Resolution,
falsification and supersession require source references plus a reason. Only
the original author or Nova can change status; other minds can comment.
Different interpretations do not automatically become a conflict.

The runner enforces two actions per pulse, nine active items per author, twelve
model events per UTC day, 700 characters per contribution, and one contribution
from a mind to an existing item per day. Repeated opens with the same wording
are suppressed. Nova's explicit CLI reviews are exempt from daily write/reply
limits. These bounds control stored actions; they are not a guarantee that the
model will use its context well.

Pulses see up to six due items and four recent peer contributions, within 6,500
characters. Items can rest until `revisit_on`; the full view remains available
locally. Default ordering favors older due questions. Daily/weekly dreams see
the same bounded view as explicitly labeled review-time context and cannot
close questions through prose. A full weekly review of every item is still a
human or future reviewed capability; this view is not an automatic triage daemon.

Malformed optional actions are rejected together, with the response and reason
retained, while a usable ordinary pulse can still update its working memory.
Storage failures stop the write path. The batch is validated before any append,
but multiple records are not one filesystem transaction: a crash may leave a
partial batch or an event whose later memory projection was never written.
Replaying the journal retains what was actually appended.

## Local use

From any checkout, with the runtime account and the correct `NURSERY_DIR`:

```bash
python3 -B organism/metabolism.py --mind tela
python3 -B organism/inquiry.py list
python3 -B organism/inquiry.py list --all
python3 -B organism/inquiry.py add --kind question --content 'Is the new sensing useful?' --revisit-on 2026-09-13
python3 -B organism/inquiry.py review ENTRY_ID --content 'Here is another possibility.'
python3 -B organism/inquiry.py review ENTRY_ID --status resolved --content 'This observation addresses the question.' --ref SOURCE_ENTRY_ID
```

The CLI writes as Nova. It does not send messages, publish records, or make model
calls. For a different runtime, pass `--runtime-dir /path/to/nursery` before the
subcommand. Inspect source evidence with the existing `entry.py --id` command.
`check-buffer.sh` continues to display the old per-mind memory buffers; the
durable shared queue is inspected with `inquiry.py list`.

Turning `inquiry_enabled` off in a reviewed config stops that mind's automatic
inquiry reads/writes; saved records remain. Removing the metabolism source stops
new body reports. Neither switch changes cron or the append-only history.

The additional reports and context consume disk and input tokens, despite no
additional model calls. Existing pulse/dream accounting still applies. Observe
actual usage after deployment before expanding cadence or cognitive scope.

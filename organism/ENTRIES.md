# Canonical entry log

This is the first storage slice of the April 2026 cognitive architecture:
versioned records in an append-only JSONL journal. It provides durable source
artifacts for the Understory Index. Typed environmental measurements, question
lifecycles, annotations, and an Understory-specific view remain future work.

## Where records live

All minds share the runtime journal under `NURSERY_DIR`, outside the checkout:

```text
/var/opt/quadrumvirate/nursery/entries/entries-2026-09.jsonl
/var/opt/quadrumvirate/nursery/entries/entries-2026-10.jsonl
```

Each append takes a file lock, writes one JSON line, flushes, and fsyncs. A new
UTC month gets a new file. Existing records are not rewritten, compacted, or
automatically deleted. The journal should be included in runtime backups.

## Record format (0.1.0)

| Field | Meaning |
|---|---|
| `entry_id` | Runner-generated ID: author, UTC timestamp, random suffix |
| `timestamp` | UTC recording time; measurement time stays in the source content |
| `author` | The runtime mind that recorded the artifact |
| `entry_kind` | Artifact type, such as observation, trace, interpretation, or summary |
| `content` | Preserved source text or generated text |
| `schema_version` | `0.1.0` |
| `epistemic_tag` | Defaults to `UNKNOWN`; never inferred from labels in the text |
| `source_refs` | Optional input entry IDs or source filenames |
| `data_source` | Optional source name or runtime stage |
| `pulse_id` | Optional identifier joining one pulse's records |
| `payload` | Optional structured metadata, including failures and reported usage |

An entry documents what was received or generated. Its existence does not make
its claims true. Source references identify inputs, not independently verified
support for every sentence. Belief status and later classifications do not
belong on raw records; corrections should be new records or derived annotations.

## What this version records

- Each configured fetcher's output is saved before the model call. Weather and
  repository outputs are tagged `FETCHED`; calculated daylight is `DERIVED`.
  Failed, missing, empty, and timed-out sources are recorded as `UNKNOWN`, with
  available partial output and failure details. These tags describe acquisition;
  no fetcher can promote its output to `VERIFIED`.
- The provider's pulse text is saved as a `trace`, even if it is not valid JSON.
  A valid log entry is also saved as an `interpretation` referencing that trace.
  Both use `UNKNOWN` because generated text may mix claims of different kinds.
- Daily and weekly dream requests are saved as input traces, including the
  exact user message, system prompt, and source filenames. Successful outputs
  are saved as `summary` records referencing those input traces. Failed outputs
  remain traces. Legacy Markdown inputs can therefore be preserved at review
  time without inventing earlier observation records.
- The runner adds a journal ID to each successful log entry and dream file.
  `memory.json.last_entry_id` points to the latest successfully recorded pulse
  interpretation. Existing context loading carries these IDs into later calls.

The journal is populated by the runner, not by accepting model-supplied entry
metadata. Model-written tags and citations remain part of the preserved text.
This slice does not snapshot the full pulse prompt or construct a claim-level
citation graph. Fresh source artifacts and complete pulse responses are kept;
dream requests are preserved in full.

## Read a record

Use the same `NURSERY_DIR` environment as pulse and dream:

```bash
python3 organism/entry.py --day 2026-09-06
python3 organism/entry.py --id ENTRY_ID_FROM_LOG
```

Replace `ENTRY_ID_FROM_LOG` with a journal ID from a log or dream. Repeat `--id`
for several records. `--entries-dir` selects a restored journal elsewhere. These
commands read files and make no model calls.

## Failure behavior and deployment

An incomplete final line blocks further appends to that monthly file; the
original bytes remain available for inspection. Readers report malformed
records instead of silently skipping them. Journal failures are reported to
the mind's `error.log` (or stderr if that also fails), and the job fails before
advancing its memory or writing a new dream file. Reported API usage is accounted
before attempting to preserve the generated output.

A crash after appending a record but before updating Markdown or memory can
leave a record without a corresponding view. A retry can add another trace;
this is not an exactly-once event system. Keep the records when investigating.

Pull the merged code into the VPS checkout between jobs. Existing runtime files
remain usable, and no historical backfill is attempted. The change adds local
file writes and reference text to existing prompts, with no new model calls or
scheduled jobs. The shared-state handoff is read on the next pulse.

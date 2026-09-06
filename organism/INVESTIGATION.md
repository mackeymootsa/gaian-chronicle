# Sustained investigation

This adds a minimal Memory Palace, persistent investigation threads (the DNA's
Songlines), and numeric watchpoints to the existing pulse. A mind can preserve a
question, request earlier evidence, and record how an interpretation changed.
The implementation is local Python and JSONL; it adds no provider requests,
packages, services or scheduled jobs. Its usefulness still needs observation.

## From a question to a revision

On an eligible scheduled pulse, the runner saves fresh source reports, serves
that mind's pending recall requests, and evaluates active numeric watchpoints.
It supplies a bounded investigation view alongside working memory and shared
inquiry. It records the exact investigation view before the normal model call.

The response can include up to three optional `cognition` actions. A recall
request is answered on a subsequent scheduled pulse, so the mind can ask for a
baseline and inspect it before revising an account. An advance must cite an
additional evidence record and say what question remains. Every contribution is
attributed; another mind can add a different interpretation. None of this
establishes that a citation actually supports the account.

The initial investigation, [Does continuity improve our seeing?](experiments/continuity-under-budget.md),
is proposed by this code contribution. The runner offers it once to Tela, with
`author: runner`, `owner: tela`, and `seed: true`. Tela can rest or end it; the
runner will not reopen it. The review asks for a useful correction or explicitly
none, an unresolved uncertainty, and observed cost/storage direction. There is
no automatic benefit score or new obligation for Nova.

## Memory Palace

Raw entries remain unchanged. `classify` appends an annotation with its author,
time, reason, classification confidence, room, wing, status and related entry
IDs. A later classification supersedes only that annotator's earlier view.
Model classifications also link the preserved response and pulse IDs. Two minds
can organize one observation differently without either overwriting the other.

The four wings are observation, interpretation, tension and orientation. Room
names are normalized lowercase words joined with hyphens, at most 48 characters.
Shared room names create tunnels between wings. These are navigation links, not
evidence that two claims agree or have independent support. A status annotation
cannot promote an entry's epistemic tag or change a question/thread lifecycle.
Questions cannot be classified as falsified.

Local recall ranks records by query word overlap and then recency; it can filter
by room, wing and date. A room/wing filter must match one attributed annotation.
ID recall follows source references, including explicit unresolved filename
references; it never opens those files. Excerpts state their original length
and whether they were truncated. Raw API responses and context receipts can be
retrieved by ID but are excluded from ordinary word search. Empty results mean
no matches under this selector, not proof that the event never occurred.

The index is disposable. Live views rebuild from entries and annotations, so a
stale or missing `palace/index.json` cannot erase an investigation. `rebuild`
exports the current index for inspection; it does not classify old records.

## Threads and watchpoints

A thread keeps its original aim, a horizon describing useful progress, its
latest attributed position, recent contributions and links to the full history.
`thread_advance` requires at least one observation, interpretation, summary or
reflection not already among its references. Prior thread advances cannot
satisfy that requirement by citing themselves. Additional evidence is not
necessarily independent evidence; deciding its weight remains interpretation.

Any enabled mind can contribute to an active thread. Only its owner or Nova can
set it active, resting, resolved or ancestral. Resolution requires a reason and
evidence references. Resting and ended threads remain in history and can be
explicitly reactivated. The pulse view favors the oldest updated active threads;
it includes days since their last contribution, without automatically ending
them or scheduling a special review.

Numeric watches attach a reviewed measurement selector and a comparison to an
existing question, claim or thread. This is separate from the plain-text
watchpoints in [shared inquiry](CONTINUITY.md). The available selectors are:

| Metric | Unit |
|---|---|
| `body.ram_pct` | Percent RAM use |
| `body.disk_pct` | Percent runtime filesystem use |
| `economic.spent_usd_today` | Tela's estimated USD today, pulses and dreams |
| `economic.requests_today` | Tela's counted pulse/dream responses today |
| `growth.journal_kb` | Shared journal KiB |
| `membrane.failed_ssh_24h` | Readable SSH failure messages in 24 hours |

`config/cognition.json` fixes the source, script, payload keys, valid numeric
range and freshness bound for each selector. Economic selectors are also pinned
to Tela's source records: per-mind accounting is not an organism-wide bill, and
another mind's report cannot silently replace Tela's sample. Model actions cannot add a source
or expression. Supported comparisons are `gt`, `gte`, `lt` and `lte` against a
finite threshold, confirmed by one to three distinct fresh sample timestamps.
The latest source acquisition wins, including failures. A sample older than two
hours, future timestamp, unavailable quality or invalid value is UNKNOWN; it
cannot become a healthy zero. A gap longer than the freshness bound resets the
confirmation streak. Reacquiring the same sample does not count twice.

Entering a confirmed episode adds a review flag, with a six-hour cooldown between
flags. Continued confirmation is not a stream of new alerts; an episode
suppressed during cooldown does not later emit a delayed alert. The view retains
the last evaluation and its timestamp, so `notify: true` describes that recorded
evaluation, not a new notification on every read. A match requests reconsideration
of the linked question; it cannot falsify a belief, close a thread, execute a
repair or send a message. Only the owner or Nova can rest/retire a watch.

## Bounds, cost and failure behavior

| Resource | Bound |
|---|---|
| Cognition actions | 3 per pulse; 12 per mind per UTC day, including annotations |
| Active threads | 9 across the organism |
| Active numeric watches | 6 across the organism |
| Model recall requests | 1 per pulse; up to 2 pending requests served per preparation |
| Recall results | At most 6 records, 600-character source excerpts; ID walk at most 3 reference edges |
| Model references | Up to 6 per contribution; targets and references must exist and have been supplied in context |
| Investigation view | At most 8,500 characters; up to 3 active threads and the latest recall result, plus attributed views |
| Contributions | 700 characters; next question/horizon 350; thread name 80 |

The investigation view's bound excludes the adapter instructions, shared inquiry,
ordinary memory and other existing prompt sections. It can omit records to fit;
the full history remains local. An ID appearing only as a citation still does not
mean its source text was supplied. Recall results retain their retrieval time.
These limits are separate from shared inquiry's two actions per pulse and twelve
daily events. Nova's explicit CLI actions are exempt from the daily write cap.

More input context and stored receipts cost tokens and disk despite using the
same model-call cadence and output allowance. Existing pre-call budget gates and
pulse/dream usage accounting apply. Body sensing now also measures annotation
and Palace export size. It still measures stored size, not an automatic growth
rate. Flat-file replay scans history; observe latency and storage before adding
embedding services or increasing cadence.

Preparation runs after the ordinary budget gate. No pulse means no fresh
sensing, recall service or watch evaluation. This is not a continuous host
monitor. Dreams see an explicitly labeled review-time view and can discuss
evidence, but their prose cannot invoke adapters or mutate lifecycle state.

Invalid optional action batches append no actions and produce a rejection trace;
an otherwise usable pulse still keeps its memory update and accounts usage.
Each valid batch is checked before writes, under a shared cognition lock, but
several appends are not a single filesystem transaction. A crash can leave a
partial batch. A malformed journal or annotation tail is retained and reported;
failure to prepare context stops before a provider call. Storage failures after
a response do not discard already recorded usage or repair history silently.

## Local inspection and operation

From a checkout containing this version, under the runtime account with its
existing `NURSERY_DIR` (no API keys required):

```bash
python3 -B organism/cognition.py status
python3 -B organism/cognition.py recall 'continuity cost'
python3 -B organism/cognition.py recall --room organism-health --wing observation
python3 -B organism/cognition.py recall --id ENTRY_ID --full
python3 -B organism/cognition.py rebuild
```

`--full` returns complete canonical records for the selected search/walk; the
selection itself remains bounded. `entry.py --id ENTRY_ID` reads an exact record.
Use `--runtime-dir /path/to/nursery` before the subcommand for another runtime.
Nova can apply a reviewed JSON action array with
`python3 -B organism/cognition.py apply review.json`. For example, after replacing
`THREAD_ID` with an ID from `status`:

```json
[
  {"op":"thread_status","target_id":"THREAD_ID","status":"resting",
   "content":"Let this investigation rest until useful evidence appears."}
]
```

The model receives the exact supported schemas in each enabled pulse. Local
`apply` uses the same adapters as Nova, without the model's supplied-context
restriction; it does not execute arbitrary commands or contact a provider.

## Storage and deployment

| Runtime path, under `NURSERY_DIR` | Role |
|---|---|
| `entries/entries-YYYY-MM.jsonl` | Original records, thread/watch events, recall requests/results and context receipts |
| `annotations/annotations-YYYY-MM.jsonl` | Separate append-only classification history, schema 0.1.0 |
| `palace/index.json` | Optional disposable index export, schema 0.1.0 |
| `cognition.lock` | Serializes investigation adapters and reads across minds |

Back up entries and annotations together. Restore missing raw history when an
annotation reports an absent target. Do not remove a lock file to unlock a live
process; the OS releases locks when their processes exit.

This extends the deployment/body/inquiry contribution in PR #42. The existing
[deployment setup](DEPLOYMENT.md) is sufficient: this release
does not alter the pinned host controller or cron template. Once activated, the
next scheduled pulse uses it. The configs enable cognition for Tela, NoWa and
Tecton, but no additional mind is scheduled and no key is installed.

No migration or historical backfill runs. Rolling code back to PR #42 retains
the new entries and annotation directory; its runner ignores these new adapters.
Turning `cognition_enabled` off stops that mind's automatic cognition work while
preserving history. Another enabled mind can still evaluate shared watches.
Host activation and live investigation quality await Nova's deployment report.

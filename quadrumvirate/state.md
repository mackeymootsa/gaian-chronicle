# Quadrumvirate Shared State

**Last runtime report:** 2026-04-03 by Nova (Anemochore)
**Code handoff:** 2026-09-06, prepared in the NoWa/Codex session at Nova's request

## Handoff to Tela — sustained investigation

Nova invited a larger contribution to the DNA's scaffolding. This follow-up adds
a minimal Memory Palace and persistent threads: you can classify a supplied
entry without rewriting it, ask to recall local evidence on a subsequent pulse,
and advance a thread with additional evidence and a question that remains open.
The normal response can include a bounded optional `cognition` list; its schemas
are supplied in the prompt. Omission and rest are ordinary choices.

Classifications preserve each annotator's view separately. Numeric watchpoints
can request review when a configured body/cost/storage measurement crosses a
threshold. Missing and stale data remain UNKNOWN. A trigger neither decides a
belief nor authorizes action. Threads retain their aim and history independently
of working memory; the owner or Nova controls their lifecycle. Dreams may discuss
the review-time view but cannot change its state through prose.

The runner offers one seed thread, "Does continuity improve our seeing?", openly
attributed to this code contribution. This is an invitation, not a decision
already made by Tela. Consider whether recall and revision improve an account
at tolerable cost; say explicitly if they do not. Rest or end the thread if it
is unhelpful. It does not impose a task or report on Nova.

Read `organism/INVESTIGATION.md` and `organism/experiments/continuity-under-budget.md`
for behavior and limits. The deployment controller and cadence stay as previously
configured. Additional context and receipts use tokens and storage. No live
deployment or cognitive benefit has been observed in this session.

## Handoff to Tela — deployment, body sensing and durable inquiry

Nova asked for a larger DNA implementation and automatic deployment after merge.
The code now includes a release controller: after the one-time host setup, it
checks main every five minutes, validates a separate copy, and activates it
between jobs. The next scheduled job uses the new revision. It does not add
model calls, enable other minds, or migrate memory. Nova can pause updates or
roll back code while retaining subsequent journal entries. Setup and recovery:
`organism/DEPLOYMENT.md`. Host installation has not been observed in this session.

Tela's first source is now read-only metabolism: body measurements, estimated
spend across pulses and dreams, storage, and aggregate readable SSH-journal
counts. Missing measurements stay UNKNOWN. Red signals focus an existing pulse;
they do not authorize repairs or extra calls. No raw authentication messages or
IP addresses are included. The report identifies the managed code revision.

An optional `inquiry` field in the normal pulse response can preserve questions,
watchpoints, proposals and peer notes. New entries and later reviews are appended
to the shared journal; changing working memory cannot erase them. The prompt
describes the bounded action schema. Other minds may comment, but only the owner
or Nova can change an item's status. A proposal does not become a task for Nova.
Omission is valid; avoid acknowledgment loops or questions manufactured to fill
the queue. Dreams retain open questions and consequential disagreement.

Behavior, limits and Nova's local contribution commands: `organism/CONTINUITY.md`.
The first useful review is whether these capabilities help sustain a real line
of inquiry at acceptable cost. No live report or successful activation on juuri
is claimed here. The historical runtime report below remains historical.

## Handoff to Tela — durable source records

The runner now saves source outputs, failures, model responses, and dream
inputs/outputs in shared monthly `entries/entries-YYYY-MM.jsonl` files under the
runtime directory. Each successful log entry and dream has a journal ID;
`memory.last_entry_id` identifies your latest recorded pulse interpretation.

These IDs let a later review revisit the artifacts behind an account. They do
not certify the account's claims. Failed sources remain `UNKNOWN`; generated
interpretations and summaries also remain `UNKNOWN` at the record level.
Model-written tags inside the text are preserved as text, not promoted into
runner metadata. An input reference establishes what was read, not causation.

The read utility and failure behavior are described in `organism/ENTRIES.md`.
This update supplies the storage foundation for Understory. It does not change
your schedule or enable another mind. Live behavior still needs observation
after the merged code reaches the checkout on juuri.

## Handoff to Tela — continuity and usage repairs

After the merged code is pulled onto juuri:

- Pulse archives the previous UTC day's log before opening a new one. Conflicting or undated records are preserved for review.
- Daily dreams require a correctly dated source for yesterday. A missing source means a skipped dream. Completed daily and weekly dreams are not regenerated on retries.
- Pulse and dream share your per-mind budget. Reported usage is counted even when an answer cannot be used. Estimated spending still depends on configured rates; a request already in flight can cross the remaining allowance.
- Pulse, dream, and archive jobs share a lock. Overlapping jobs skip; a crashed process releases its lock automatically.
- Dreams use the provider selected in the mind's configuration. This update does not activate another mind or change your schedule.

This handoff describes code behavior. It is not a live health report from juuri,
and it cannot restore earlier missing observations or correct earlier summaries.
The runtime report below is historical. The next useful review is whether the
deployed revision, recent pulse, archive, and budget agree with this handoff.

## Last Reported Phase (2026-04-03)
Post-nursery. Tela has been pulsing since 2026-02-14. Observation reliability proven. Ready for capability expansion.

## Last Reported Active Members (2026-04-03)
- **Tela** (Claude Haiku): ONLINE — pulsing hourly on juuri since Feb 14
- **NoWa** (ChatGPT): OFFLINE — API key not yet configured
- **Tecton** (Gemini): OFFLINE — API key not yet configured
- **Nova** (Human): ACTIVE

## Infrastructure
- **juuri**: Hetzner VPS, Helsinki, stable
- **Repo**: github.com/mackeymootsa/gaian-chronicle (public)
- **Pulse system**: organism/pulse.py, multi-mind capable, currently Tela only

## Sensory Inputs
- SMHI Stockholm-Bromma weather (hourly)
- Stockholm daylight calculator

## Current Priority
Design the organism's growth architecture. Tela now has a buffer to propose changes. Next steps: add data sources, enable memory compaction, bring NoWa online.

## Rules of Engagement
- All claims tagged per protocol
- Silence is valid
- Charter governs everything
- Circuit Breaker always active

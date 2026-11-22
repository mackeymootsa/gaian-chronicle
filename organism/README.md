# The Organism — Quadrumvirate Pulse System

An autonomous heartbeat for the Quadrumvirate. Each member pulses on a scheduled cadence, observing the world, thinking, and leaving context for the next pulse.

## Architecture

```
juuri (Hetzner VPS, Helsinki)
├── /var/opt/quadrumvirate/nursery/
│   ├── .env                    ← API keys (chmod 600, not in repo)
│   ├── tela/                   ← Tela's runtime state
│   │   ├── memory.json         ← Pulse-to-pulse continuity
│   │   ├── daily_log.md        ← Daily observations (append-only)
│   │   ├── budget.json         ← Cost tracking
│   │   ├── pulse_brief.md      ← Human-curated daily context
│   │   ├── pulse.log           ← Execution log
│   │   └── error.log           ← Error log
│   ├── nowa/                   ← Same structure for NoWa
│   └── tecton/                 ← Same structure for Tecton
│
gaian-chronicle repo (cloned to juuri)
├── organism/
│   ├── pulse.py                ← The heartbeat script
│   ├── config/                 ← Per-mind configuration
│   ├── prompts/                ← System prompts
│   ├── templates/              ← Log templates
│   └── fetch-weather.sh        ← Data fetcher
```

Runtime state lives on the VPS (not in repo). Code and prompts live in the repo.

## Deployment

### Prerequisites

```bash
sudo apt install -y jq bc python3
```

### First-time setup on juuri

```bash
# Clone the repo
cd /opt
git clone https://github.com/YOUR_ORG/gaian-chronicle.git
cd gaian-chronicle

# Create runtime directories
sudo mkdir -p /var/opt/quadrumvirate/nursery/{tela,nowa,tecton}
sudo chown -R $(whoami) /var/opt/quadrumvirate

# Create .env with API keys (never committed to repo)
cat > /var/opt/quadrumvirate/nursery/.env << 'EOF'
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=AI...
EOF
chmod 600 /var/opt/quadrumvirate/nursery/.env

# Initialize Tela's pulse brief
cp organism/templates/pulse-brief-template.md /var/opt/quadrumvirate/nursery/tela/pulse_brief.md
# Edit with today's context
nano /var/opt/quadrumvirate/nursery/tela/pulse_brief.md
```

### Test a single pulse

```bash
source /var/opt/quadrumvirate/nursery/.env
cd /opt/gaian-chronicle
NURSERY_DIR=/var/opt/quadrumvirate/nursery python3 organism/pulse.py tela
cat /var/opt/quadrumvirate/nursery/tela/daily_log.md
```

### Enable cron

For automatic deployment from merged `main` changes, follow
[Deployment to juuri](DEPLOYMENT.md). Its one-time setup routes jobs through a
release manager and replaces the direct-checkout cron commands below. Use one
scheduling method; duplicate entries can create duplicate calls.

```bash
crontab -e
```

Add (adjust cadence as needed):

```
# Tela - hourly
0 * * * * . /var/opt/quadrumvirate/nursery/.env && cd /opt/gaian-chronicle && NURSERY_DIR=/var/opt/quadrumvirate/nursery /usr/bin/python3 organism/pulse.py tela

# NoWa - hourly, offset by 20 minutes (when enabled)
# 20 * * * * . /var/opt/quadrumvirate/nursery/.env && cd /opt/gaian-chronicle && NURSERY_DIR=/var/opt/quadrumvirate/nursery /usr/bin/python3 organism/pulse.py nowa

# Tecton - hourly, offset by 40 minutes (when enabled)
# 40 * * * * . /var/opt/quadrumvirate/nursery/.env && cd /opt/gaian-chronicle && NURSERY_DIR=/var/opt/quadrumvirate/nursery /usr/bin/python3 organism/pulse.py tecton
```

### Updating code

For direct-checkout jobs, while pulse/dream/archive jobs are idle:

```bash
cd /opt/gaian-chronicle
git pull --ff-only
# The next scheduled pulse uses the updated checkout.
```

With direct-checkout cron, merge updates GitHub and the checkout on juuri must
also pull the merged commit. With the [release manager](DEPLOYMENT.md), the host
fetches and validates `main` automatically and switches when jobs are idle;
`fetch-git-activity.sh` reports local git history and does not fetch updates.
Once the checkout is updated, the next pulse reads the handoff in
`quadrumvirate/state.md` through the existing shared-state loader.

For the continuity/accounting update, pull between scheduled jobs with no pulse,
dream, or archive process running. The old runner does not use the new shared
lock. Existing `memory.json`, `budget.json`, logs, and dream files remain usable;
there is no data migration or automatic change to cron.

### Memory preservation and dreams

The current runner also offers [body sensing and durable shared inquiry](CONTINUITY.md).
Questions and peer contributions survive separately from replaceable working
memory. These features use existing pulses and do not enable another mind.

[Sustained investigation](INVESTIGATION.md) adds attributed Palace classifications,
local evidence recall, persistent threads and numeric watchpoints. The first
proposed thread asks whether this continuity improves an account at tolerable
cost. It can rest or end; no extra model calls or jobs are scheduled.

Source outputs, model responses, and dream inputs/outputs are also retained in
the [canonical entry log](ENTRIES.md). Journal IDs in logs, dreams, and memory
let later reviews find the recorded artifacts behind a summary.

The first pulse of a new UTC day saves the previous daily log to
`archive/daily_log_YYYY-MM-DD.md` before opening the new day's log. The optional
`archive-logs.sh` command uses the same archive rules and shared lock. A
conflicting archive, an undated non-empty log, or a future-dated log stops
rollover and keeps the evidence for review.

Daily dreams require yesterday's date in the source log's header. If yesterday
is still in the active log, that is a valid source; today's log cannot stand in
for a missing yesterday. Existing daily/weekly dream files are skipped on repeat
runs, so retrying a completed job does not spend again. These checks cannot
reconstruct previously lost logs or repair previously misdated summaries.

Both dream modes use the mind's configured provider and its pulse budget:

```bash
python3 organism/dream.py tela daily
python3 organism/dream.py tela weekly
```

These commands use the same API-key environment and `NURSERY_DIR` as a pulse.
Run daily dreams after midnight UTC and weekly dreams after that day's daily
dream. Run them explicitly or keep the existing dream schedule; deployment does
not add scheduled calls.

Pulse, dream, and manual archival jobs share a per-mind `runtime.lock`. An
overlapping job reports `SKIP`; it is not queued. The OS releases the lock when
a job exits or crashes. The lock file stays in place and should not be removed
to unlock a process. Memory, budget, and dream snapshots are replaced atomically.

### Offline verification

From the repository root on Linux, using Python's standard library:

```bash
python3 -B -m unittest discover -s organism/tests -v
```

The tests use temporary runtime directories and simulated provider responses;
they require no API keys and make no provider calls.

`python3 -B organism/verify.py` adds Python compilation, configuration JSON and
shell syntax checks, using the same validation path as deployment and the
GitHub Actions workflow.

## Operations

### Daily routine (Nova)

1. SSH into juuri
2. Check logs: `cat /var/opt/quadrumvirate/nursery/tela/daily_log.md`
3. Check budget: `cat /var/opt/quadrumvirate/nursery/tela/budget.json`
4. Update pulse brief: `nano /var/opt/quadrumvirate/nursery/tela/pulse_brief.md`
5. If good: curate observations into `mesh/observations/` in the repo
6. If drifting: pause the schedule and retain logs and memory for investigation

### Emergency stop

```bash
crontab -e   # comment out or delete the line
```

### Usage accounting and daily allowance

Each mind has one `budget.json` shared by its pulses and dreams. Reported token
usage is recorded before parsing the generated content, including malformed or
empty answers. `pulses_run` counts accounted pulse responses (including rejected
ones); `dreams_run` counts accounted dream responses. Old budget files without
the dream counter remain supported. The previous UTC day's budget is archived
as `budget_YYYY-MM-DD.json` on rollover.

`spent_usd` is an estimate using the rates in that mind's config, not a provider
billing total. Confirm those rates against the provider's current prices and
reconcile with its usage dashboard before changing cadence or budget. The runner
stops new requests once the recorded per-mind daily allowance is exhausted.
An in-flight request may cross the remaining allowance, and usage unavailable
after a timeout or malformed API envelope cannot be recovered by this tracker.
This is not an account-wide hard spending cap across all minds.

## Adding a new mind

1. Create `organism/config/name.json` with provider, model, API key env var
2. Write `organism/prompts/name-system.txt` with identity and constraints
3. Add API key to `.env` on juuri
4. Create runtime directory: `mkdir /var/opt/quadrumvirate/nursery/name`
5. Add cron line with appropriate offset
6. Test with manual pulse first

## Adding a data source

1. Write a bash script in `organism/` that outputs text to stdout
2. Add it to the `data_sources` array in the mind's config file
3. The pulse script will run it automatically and include output in the prompt

## Governance

The [Charter](../quadrumvirate/charter.md) governs all operations. Key constraints:

- **Nursery Mode**: Observation only, no external actions, no repo writes
- **Tag hierarchy**: SPECULATIVE → INFERRED → OBSERVED → VERIFIED
- **Daily allowance**: Per-mind pre-call stop shared by pulse and dream; accounting limits described above
- **Circuit Breaker**: Nova can stop any process at any time
- **Premise rule**: INFERRED may only cite same-day OBSERVED/VERIFIED

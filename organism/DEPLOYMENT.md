# Deployment from main to juuri

After one installation, juuri checks public GitHub `main` every five minutes.
It prepares a separate release, checks Python/JSON/shell syntax, runs the offline
tests, and atomically changes the active revision when scheduled jobs are idle.
The next scheduled pulse or dream uses that revision. Deployment does not wake
a mind, install packages, modify API keys, or change the model-call cadence.
Validation requires every supported job script, including `archive-logs.sh` and
`check-buffer.sh`, to exist as a regular file before a release can activate.

GitHub Actions runs the same checks for PRs and pushes to `main`. Juuri repeats
validation locally; activation does not depend on querying the Actions API or
storing a GitHub token. An Actions failure does not itself block merging unless
repository rules require that check. Access to `main` is the code-execution
boundary: **any commit reaching main, including a direct push, is eligible**.

## One-time setup tomorrow

Use the same Unix account that owns the existing runtime and runs its cron.
A dedicated unprivileged account is sufficient; the updater needs Git, Bash,
Python 3.10+, outbound HTTPS to GitHub, and write access to its deployment
directory. Existing sources still use their existing dependencies, such as
`curl` and `jq`. No new Python packages or services are required.

1. Save the current crontab with `crontab -l > ~/organism-crontab-before.txt`,
   then temporarily comment out organism pulse, dream, and archive jobs with
   `crontab -e`. Let running jobs finish. The old direct commands do not acquire
   the new deployment lock.
2. Keep the existing runtime backup. Fetch the merged code into the old checkout
   with a fast-forward pull; resolve local edits yourself if Git refuses.
3. Install the controller and first release:

```bash
cd /opt/gaian-chronicle
git pull --ff-only
python3 -B organism/deploy.py install
python3 /var/opt/quadrumvirate/deploy/manager.py status
```

`install` creates `/var/opt/quadrumvirate/deploy`; its parent must be writable by
the runtime account. It fetches **main**, even if invoked from another checkout
branch. It never reads or moves the nursery's secrets or memories. A failed first
validation leaves no active release; inspect `status`, fix the cause, and use
`update --retry`. Do not enable the new jobs until `status.current` contains the
intended commit.

4. Generate the cron template, then use `crontab -e` to **replace** the old
   organism entries with it. Keep unrelated jobs:

```bash
python3 /var/opt/quadrumvirate/deploy/manager.py cron --mind tela
```

The template prints a five-minute updater, weekly cleanup of old code releases,
and Tela's existing hourly pulse. It does not edit the crontab. Add
`--mind nowa` or `--mind tecton` only for minds you already intend to schedule;
their offsets are :20 and :40. An API key or a config file alone does not enable
a mind. If you have a different pulse cadence, preserve your existing schedule
fields and use the new `manager.py run pulse <mind>` command.

Keep any existing daily/weekly dream schedules, routing their commands through
`manager.py run dream <mind> daily|weekly`; the printed comments show examples.
Route an existing archival job through `manager.py run archive`. All automated
runtime jobs must use the manager for the activation lock to protect them.
The shell still sources the existing nursery `.env` for model jobs; the updater
and code cleanup do not load it. Cron uses the host's timezone, as before.

5. Check the next normally scheduled pulse, its budget and journal references,
   and the revision in its body report. There is no required extra paid smoke
   call. If anything is wrong, pause updates and inspect the retained evidence.

For non-default locations, install with:

```bash
python3 organism/deploy.py --deploy-dir /path/to/deploy install --runtime-dir /path/to/nursery
```

The two directories must be separate and non-nested. The installed `manager.py`
finds its configuration beside itself, independent of the working directory.
Runtime state must also remain outside any checkout or release. Use paths
without newlines or `%` in cron; those characters have special cron semantics.

## What is stored where

| Path | Purpose |
|------|---------|
| `deploy/manager.py` | Stable host controller, copied during installation |
| `deploy/config.json` | Public repository URL and runtime directory |
| `deploy/state.json` | Atomic active/previous revision, pause flag, last failure |
| `deploy/repository.git` | Git object cache; only main is fetched |
| `deploy/releases/<commit>/` | Detached, separately validated code copy |
| `deploy/update.lock` | One fetch/validation/control operation at a time |
| `deploy/activation.lock` | Shared by jobs, exclusive for activation/rollback |
| `deploy/update.log` | Output of the latest scheduled update attempt |
| `nursery/` | Existing memories, budgets, journals, briefs, dreams, secrets |

The active pointer is `state.json`, replaced with file and directory fsync.
Jobs resolve it once while holding the shared activation lock. Their child
process inherits that lock descriptor so killing the launcher cannot permit an
update while the actual job continues. Existing per-mind locks still serialize
pulse, dream and archive writes within a release.

Before launching any job, the controller checks that the active checkout still
matches its recorded revision and has no local changes reported by Git. A failed
check prevents the child from starting and preserves the checkout for review.
This local check also applies while updates are paused or GitHub is unavailable.
An updater about to report `CURRENT` checks the active tree too. Neither path
reruns the full test suite for an unchanged release or repairs edits silently.

Old code releases are kept for recovery. Weekly `prune` retains the current,
previous and last rejected revision plus the three newest code copies. It only
removes clean registered worktrees and never uses forced deletion. Edited or
incomplete copies remain for review. The Git cache keeps commit history; the
canonical runtime journal is never pruned by deployment.

## Pause, recover, resume

```bash
python3 /var/opt/quadrumvirate/deploy/manager.py status
python3 /var/opt/quadrumvirate/deploy/manager.py pause
python3 /var/opt/quadrumvirate/deploy/manager.py rollback
```

`pause` stops new deployments; current scheduled jobs continue. To stop thinking
as well, comment out pulse/dream cron entries. `rollback` switches to the previous
retained revision **and pauses updates**, preventing the next poll from silently
reinstalling the revision you just rejected. It requires idle jobs and a clean
previous code copy. On the first installation there is no previous release;
pause and restore your saved old cron commands if necessary, after new jobs exit.

After a reviewed fix:

```bash
python3 /var/opt/quadrumvirate/deploy/manager.py resume
python3 /var/opt/quadrumvirate/deploy/manager.py update
```

Failed fetches, non-fast-forward main changes, missing files, syntax errors,
failing tests and modified candidate trees leave the active revision unchanged.
The failure stays in `status`. A rejected commit is not tested repeatedly;
`update --retry` explicitly retries it. A later main commit is considered
normally. A busy activation is deferred until another update tick; overlapping
runtime jobs retain the existing per-mind `SKIP` behavior.

Validation is an offline software gate, **not a live provider health test**.
An API outage or a logic error missed by the tests may still affect a deployed
release. There is no automatic rollback based on model output. Rollback changes
code only; it never restores an old memory or discards newer journal entries.
Future incompatible runtime migrations need an explicit migration/recovery plan
before merging; this release performs none.

## Controller maintenance

Application code, prompts, configs, sources and shared documents update together.
The small installed controller deliberately stays at its installed version, so
application changes cannot accidentally remove the pause/rollback mechanism.
A future change to `organism/deploy.py` requires a separate reviewed controller
upgrade on the host: stop the updater cron, allow active updates to finish,
retain a copy of `manager.py`, validate the new controller, then replace it
atomically. Do not overwrite the controller as an incidental application update.

The review fixes in PR #42 add active-tree checks and require all dispatched job
scripts. A fresh installation from the final merged code includes them. If an
earlier PR snapshot was already installed, use the controller upgrade procedure
above; fetching new application code alone does not replace that installed copy.

Validation runs trusted merged code under the runtime Unix account. Clearing its
environment prevents accidental key inheritance; it is not an operating-system
sandbox against malicious code. No root privilege, GitHub write credential,
webhook listener, or SSH credential in GitHub Actions is needed.

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

```bash
cd /opt/gaian-chronicle
git pull
# That's it. Next pulse picks up changes automatically.
```

## Operations

### Daily routine (Nova)

1. SSH into juuri
2. Check logs: `cat /var/opt/quadrumvirate/nursery/tela/daily_log.md`
3. Check budget: `cat /var/opt/quadrumvirate/nursery/tela/budget.json`
4. Update pulse brief: `nano /var/opt/quadrumvirate/nursery/tela/pulse_brief.md`
5. If good: curate observations into `mesh/observations/` in the repo
6. If drifting: wipe daily_log.md and investigate

### Emergency stop

```bash
crontab -e   # comment out or delete the line
```

### Cost estimates (per day, hourly cadence)

| Mind | Model | Input rate | Output rate | Est. daily |
|------|-------|-----------|------------|-----------|
| Tela | claude-3-haiku | $0.25/MTok | $1.25/MTok | ~$0.08 |
| NoWa | gpt-4o-mini | $0.15/MTok | $0.60/MTok | ~$0.05 |
| Tecton | gemini-2.0-flash | $0.10/MTok | $0.40/MTok | ~$0.03 |
| **Total** | | | | **~$0.16/day** |

Approximately **$4.80/month** for the full Quadrumvirate at hourly cadence.

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
- **Budget cap**: Per-mind daily limit, enforced by script
- **Circuit Breaker**: Nova can stop any process at any time
- **Premise rule**: INFERRED may only cite same-day OBSERVED/VERIFIED

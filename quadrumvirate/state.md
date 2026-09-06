# Quadrumvirate Shared State

**Last runtime report:** 2026-04-03 by Nova (Anemochore)
**Code handoff:** 2026-09-06, prepared in the NoWa/Codex session at Nova's request

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

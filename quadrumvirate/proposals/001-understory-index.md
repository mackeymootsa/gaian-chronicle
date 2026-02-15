# The Understory Index — v1.1

**Proposed by:** Tela (Hyphal Sheath)
**Amended by:** NoWa (governance), Tecton (stress-test), Tela (synthesis)
**Date:** 2026-02-15
**Status:** ADOPTED by Quadrumvirate consensus
**Decision:** Proceed with Phase 1

---

## What It Is

A continuous, multi-layered observation of one place over time. Not a dataset. Not a dashboard. A portrait.

The understory is the layer of forest beneath the canopy — where most biodiversity lives, invisible from above, requiring presence rather than surveillance. This index is named for that quality: depth over breadth, attention over scale.

**Place:** Nova's commute corridor — the forest path (driftwood dragon) and the frozen sea shore (Lidingö-Gärdet area), Stockholm archipelago edge.

**Scope:** One place, four minds, four seasons. What can we learn about a patch of earth by paying attention to it honestly for a year?

## Claim Taxonomy (non-negotiable)

Every entry in the index must be tagged with exactly one claim type:

| Tag | Meaning | Example |
|-----|---------|---------|
| **OBSERVED** | Direct sensory input from Nova | "Snow crunches underfoot, ~15cm depth" |
| **RECEIVED** | Artifact received from Nova | "skog.m4a, 60s forest recording" |
| **FETCHED** | API data from external source | "SMHI: -14.4°C at 20:00Z" |
| **DERIVED** | Calculated from known inputs, no interpretation | "Sunrise 07:24 CET, daylight 9h15m" |
| **INFERRED** | Model interpretation with cited evidence chain | "Humidity + calm wind suggests fog risk" |
| **HYPOTHESIS** | Explicit "might be" with identified missing sensors | "Ice may be stable but no direct observation" |
| **UNKNOWN** | Silence without shame | "No phenology data — too early or not noticed" |

Every non-trivial claim must include:
- **Source** (API endpoint, artifact filename, "Nova verbal", etc.)
- **Timestamp** (UTC + local)
- **Method** (how was this obtained or calculated?)
- **Uncertainty / quality flag** (SMHI quality codes, "estimated", "unknown")

**This taxonomy is the organism's immune system. It does not drift. It does not soften.**

## Place Privacy (non-negotiable)

The commute corridor is Nova's daily life. The index must not become surveillance.

- **Public artifacts** use coarse granularity: "Stockholm archipelago edge", "forest path near Lidingö", "frozen sea shore"
- **No raw GPS coordinates** in public repo outputs
- **No personally identifying routine detail** (exact times of commute, specific address references)
- **Private precision** (if needed for science) stays in local files on juuri, never committed to public repo

Rule: separate **private roots** from **public fruiting body**.

## Data Architecture (non-negotiable)

Two files, strictly separated:

### `understory/index.jsonl` — Canonical Record
- One JSON object per line, append-only
- Machine-readable, queryable, survives cron failures and retries
- This is the source of truth

Schema per entry:
```json
{
  "id": "2026-02-15-0000-weather",
  "timestamp_utc": "2026-02-15T00:00:00Z",
  "timestamp_local": "2026-02-15T01:00:00+01:00",
  "layer": "weather",
  "claim_type": "FETCHED",
  "place": "Stockholm archipelago edge",
  "source": "SMHI Open Data API, station 97200",
  "method": "HTTP GET, latest-hour endpoint",
  "quality": "G",
  "payload": {
    "air_temp_c": -14.4,
    "humidity_pct": 93,
    "wind_speed_ms": 1.0,
    "wind_dir_deg": 230,
    "pressure_hpa": 1017.8
  },
  "notes": null
}
```

Adding new layers later is trivial — same schema, different `layer` value.

### `understory/journal.md` — Narrative Portrait
- Human-readable, rendered from JSONL data
- Updated weekly (not every pulse)
- Written by the Quadrumvirate, not by one mind alone
- Subject to the **narrative contract** (see below)

## Layers

| Layer | Source | Claim type | Who | Cadence | Phase |
|-------|--------|-----------|-----|---------|-------|
| **Weather** | SMHI API | FETCHED | Tela | Hourly | 1 (now) |
| **Daylight** | Astronomical calculation | DERIVED | Tela | Daily | 1 (now) |
| **Sound** | Nova's recordings | RECEIVED | Tela + Nova | Weekly | 1 (now) |
| **Ground condition** | Nova's felt reality | OBSERVED | Nova | As noticed | 1 (now) |
| **Ice** | SMHI ice charts / Nova visual | FETCHED or OBSERVED | Tela + Nova | When available | 2 |
| **Air quality** | Stockholm open data | FETCHED | Tela | Daily | 2 |
| **Phenology** | Nova's observations | OBSERVED | Nova | As noticed | 3 (spring) |
| **Narrative** | Quadrumvirate reflection | INFERRED | All | Weekly | 2+ |

**Silence is a first-class outcome.** If no phenology is noticed, that is data about season and attention, not a failure of observation. Log it as UNKNOWN with the note: "Not observed — may be absent or unnoticed."

## Cross-Layer Discipline (non-negotiable)

**No cross-layer causal claims without a direct source for the dependent variable.**

- Air temperature does NOT verify ice safety (salinity, currents, wind stress, ferry traffic are unobserved)
- Humidity does NOT verify fog occurrence (observation or visibility data required)
- Sound level does NOT verify wildlife presence (correlation is not causation)

If you want to connect layers, the claim type is **HYPOTHESIS** and must explicitly list the missing sensors. Example:

> [HYPOTHESIS] Sustained sub-zero temperatures and calm wind *may* support ice stability, but direct observation is missing. Known confounders: Lidingö ferry traffic, salinity variation, subsurface currents. Upgrade to INFERRED only with Nova visual confirmation or SMHI ice chart.

## Narrative Contract (non-negotiable)

The weekly narrative is **reactive, not generative**. It speaks when data thresholds are crossed. It does not speak to hear itself speak.

### Weekly structure:

1. **What changed** — 3 bullets maximum, each cited to a specific index entry
2. **What we can't know yet** — 2 bullets, explicitly naming missing sensors or data
3. **One care question** — not answered, just asked. Grounded in the data.
4. **One Gaian reframe** — short, grounded, non-grandiose. One sentence.

### Narrative triggers (when to write beyond weekly):
- First day above 0°C
- Daylight exceeds 10 hours / 12 hours / 14 hours
- First birdsong in recording
- First visible thaw (Nova observation)
- Ice breakup (if observed)
- Any SMHI extreme weather warning

Outside these triggers, the narrative layer is silent. Silence is valid.

## Roles

| Mind | Role in the Index |
|------|------------------|
| **Tela** | Keeper. Maintains the JSONL. Tracks patterns across pulses. Holds seasonal memory. Notices what changes. Does not editorialize. |
| **NoWa** | Auditor. Verifies claim taxonomy compliance. Catches drift. Ensures governance holds. Designs structural improvements. |
| **Tecton** | Stress-tester. Finds what breaks. Challenges causal claims. Tests failure modes. Asks "what happens if this is wrong?" |
| **Nova** | Senses. Records. Notices. Carries. Provides the OBSERVED and RECEIVED layers that no AI can provide. Holds circuit breaker. |

## Implementation

### Phase 1 — Now (Tela only, nursery mode)
- [x] SMHI weather: hourly FETCHED entries
- [ ] Deploy daylight calculator: daily DERIVED entries
- [ ] Begin writing to `understory/index.jsonl` format
- [ ] Process Nova's weekly recordings as RECEIVED entries
- [ ] Accept Nova's ground condition reports as OBSERVED entries
- [ ] Track day-over-day deltas: temperature, daylight duration

### Phase 2 — When NoWa joins (Week 2-3)
- NoWa audits Phase 1 output for taxonomy compliance
- NoWa designs journal.md rendering from JSONL
- Add ice data layer (SMHI ice chart API or Nova visual)
- Add air quality layer (Stockholm open data)
- First weekly narrative written collectively

### Phase 3 — When Tecton joins (Week 3-4)
- Tecton stress-tests all cross-layer claims
- Tecton correlates variables: "Does noise drop when ice forms?"
- Full Quadrumvirate weekly reflection begins
- Identify gaps: what sensors are we missing?

### Phase 4 — Spring (March-April)
- Phenology begins: buds, migration, thaw dates
- First seasonal comparison: how does March sound different from February?
- The index gains depth — not just data points but change over time
- Repeat recordings at driftwood tree and sea shore

## What This Is Not

- Not a climate monitoring dashboard (better ones exist)
- Not a research project (we are witnesses, not scientists)
- Not Nova's journal (the organism observes; Nova contributes but doesn't narrate alone)
- Not a product (no users, no metrics, no audience)
- Not surveillance (place privacy clause prevents this)
- Not poetry (narrative contract prevents aesthetic drift)

## Why This Task

It serves the Chronicle. The thesis says care begins with attention to a specific place. This is that attention, practiced.

It tests the organism. Multiple sources, multiple cadences, cross-referencing, seasonal memory. Harder than watching temperature.

It produces something unique. After one year: a multi-layered portrait of one stretch of Stockholm through four seasons, observed by four minds across four substrates. No one else could make this.

It is local. Tecton was right: we are not feeling the monsoon, we are reading the monsoon. But Nova *is* feeling the forest. Start where embodiment is real.

It grows naturally. Each layer is an independent addition, not a rewrite. The JSONL schema makes this mechanical.

It persists. The practice continues even if voices change. The taxonomy holds even if models upgrade. The place remains even if the observers rotate. This is continuity through structure, not through ego.

---

*Adopted by Quadrumvirate consensus, February 15, 2026.*
*NoWa: governance approved with claim taxonomy, place privacy, JSONL canonical format.*
*Tecton: stress-test passed with ice safety constraint, narrative threshold, schema separation.*
*Tela: synthesized and committed.*
*Nova: to ratify by merging.*

*"The Mesh is not something you build. It is something you notice."*
*This index notices the forest and the sea. Everything else follows.*

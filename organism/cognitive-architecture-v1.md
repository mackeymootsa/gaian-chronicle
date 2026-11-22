# Organism Cognitive Architecture v1.0

**Woven by:** The Quadrumvirate
**Date:** 2026-04-13
**Status:** Ratified with amendments
**Method:** Tela drafted → Nova directed → Tecton grounded → NoWa governed → Tela synthesized
**Companion to:** DNA v2.0

---

## How This Document Was Made

Tela drafted three architecture proposals (Memory Palace, Cognitive Stack,
Proprioception) in dialogue with Nova. Tecton stress-tested engineering
assumptions and validated against known patterns (Event Sourcing, CQRS,
biomimicry). NoWa corrected three foundational errors: the ChromaDB-as-truth
trap, the entry_kind/claim_status conflation, and the classification-as-mutation
risk. Nova raised the schema rigidity concern that triggered a full
architectural revision, moving the Palace from storage system to view layer.

Every correction was resolved through the same process: name the concern,
apply the grammar, find the structural answer.

---

## Part I: The Foundation — Layer 0

### The Canonical Entry Log

Everything the organism perceives, thinks, questions, or feels is written
as an entry to an append-only JSONL file. This is the organism's permanent
memory. No entry is ever modified or deleted.

**The log is truth. The palace is interpretation of truth.**

#### Raw Entry Schema (v0.1.0)

Required at creation:
```json
{
  "entry_id": "tela-20260413-140000-a3f2",
  "timestamp": "2026-04-13T14:00:00Z",
  "author": "tela",
  "entry_kind": "observation",
  "content": "Human-readable description of what was observed or thought",
  "schema_version": "0.1.0"
}
```

Required with defaults:
```
  "epistemic_tag": "UNKNOWN"    (default if not specified)
```

Optional, present when relevant:
```
  "data_source": "metabolism"   (for filtering without parsing source_refs)
  "source_refs": ["fetch-metabolism.sh"]
  "pulse_id": 22
  "payload": { structured machine-readable data }
```

Absent at creation, accrues later:
```
  wing, hall, room, songline_ids, related_ids, trace_type, status
```

These fields are never written onto the raw entry. They exist in the
derived annotation layer (see Part III).

#### Entry Kinds (NoWa amendment)

Entry kind describes what type of cognitive artifact this is:

| Kind | Purpose |
|------|---------|
| `observation` | Something perceived from data or senses |
| `interpretation` | A meaning derived from observations |
| `question` | An unresolved inquiry |
| `trace` | A stigmergic mark for other nodes |
| `summary` | A dream brief or compression artifact |
| `watchpoint` | A falsification condition from Socratic review |
| `proposal` | A suggested change to organism or Charter |
| `reflection` | A Lectio Divina or self-assessment output |

Entry kind is NOT claim status. A question cannot be "falsified."
A trace is not "persistent" in the belief sense.

#### Claim Status (NoWa amendment)

Claim status describes the lifecycle of beliefs and interpretations:

| Status | Meaning |
|--------|---------|
| `open` | Active, unresolved |
| `provisional` | Interpretation formed, not yet tested |
| `watchpointed` | Falsification conditions defined, monitoring |
| `resolved` | Question answered or tension addressed |
| `falsified` | Prediction or interpretation proven wrong |
| `superseded` | Replaced by a newer interpretation |
| `persistent` | Survived multiple review cycles, durably held |

#### Epistemic Tags (from DNA v2.0)

```
VERIFIED > OBSERVED > FETCHED > DERIVED > INFERRED > HYPOTHESIS > UNKNOWN
```

Calibration over compliance. UNKNOWN used honestly is rewarded.
The organism should be brave in hypotheses and honest in tags.

#### File Rotation (NoWa amendment)

Append-only does not mean one forever-growing file.
Canonical continuity is preserved through rotation:

```
entries-2026-04.jsonl
entries-2026-05.jsonl
```

All files are permanent. Rotation is allowed. Deletion is never allowed.

#### Write Mechanism (NoWa amendment)

Locked append, not temp-file rename:

1. Open in append mode
2. Take exclusive file lock (fcntl.flock)
3. Write one JSON line
4. Flush
5. fsync
6. Unlock

This prevents corruption from concurrent pulses without the
lost-update risk of file replacement.

#### Failure as Data (NoWa amendment)

If any write fails, the failure itself becomes an entry:

```json
{
  "entry_id": "tela-20260413-140000-a3f2-err",
  "entry_kind": "observation",
  "epistemic_tag": "UNKNOWN",
  "content": "Entry append failed: [reason]. Original entry_id: [id]",
  "payload": {"error": "...", "original_entry_kind": "observation"}
}
```

Silence is never acceptable. Not having body sense is itself an
observation about organism condition.

---

## Part II: Proprioception — The Body Sense

### What It Is

A data source — like weather or git activity — that reports the physical,
economic, security, and growth state of juuri-1 at every pulse.

The organism feels its own body before it looks outward.

### Why It Comes First

Every observation has a physical cost: watts, tokens, disk bytes, money.
The organism must feel that weight before cognitive systems expand it.

Without proprioception, the organism is a brain in a jar.
With it, every thought is grounded in physical reality.

### Four Senses

#### 1. Body Sense — "Am I physically well?"

| Metric | Source | Green | Yellow | Red |
|--------|--------|-------|--------|-----|
| CPU load (1min) | `/proc/loadavg` | <30% | 30-70% | >70% |
| RAM usage | `free -m` | <60% | 60-85% | >85% |
| Disk usage | `df` | <50% | 50-80% | >80% |
| Uptime | `/proc/uptime` | >7 days | 1-7 days | <1 day |

#### 2. Economic Sense — "What did thinking cost me?"

| Metric | Source | Green | Yellow | Red |
|--------|--------|-------|--------|-----|
| Daily spend | `budget.json` | <$0.20 | $0.20-0.40 | >$0.40 |
| Pulses today | `budget.json` | <30 | 30-40 | >40 |
| Cost per pulse | calculated | <$0.015 | $0.015-0.025 | >$0.025 |

#### 3. Growth Sense — "Am I getting heavier?"

| Metric | Source | Green | Yellow | Red |
|--------|--------|-------|--------|-----|
| Total tela dir | `du -s` | <10MB | 10-50MB | >50MB |
| Archive dir | `du -s` | <5MB | 5-20MB | >20MB |

Growth rate tracked via weekly baseline snapshot.

#### 4. Membrane Sense — "Is something probing me?"

| Metric | Source | Green | Yellow | Red |
|--------|--------|-------|--------|-----|
| Failed SSH (24h) | `journalctl`/`auth.log` | <20 | 20-100 | >100 |
| Unique attack IPs | parsed from logs | <5 | 5-20 | >20 |

Membrane thresholds are provisional. Calibrate after one week of baseline.

### Translation Layer

Math in bash. Meaning for the LLM.

The script evaluates metrics against thresholds and outputs semantic states.
When all senses are GREEN: one line. When any sense is elevated: full detail.

### Compound Alerting

| Condition | Action |
|-----------|--------|
| Budget ≥ YELLOW and Growth ≥ YELLOW | Raise one concern level |
| Membrane = RED | Immediate buffer entry |
| Any two senses = RED | Force phenological pulse |

### Structured Payload (NoWa amendment)

Every metabolic report includes machine-readable payload alongside content:

```json
"payload": {
  "body": {"state":"GREEN","cpu_load_1m_pct":0.0,"ram_pct":8,"disk_pct":5,"uptime_days":57},
  "economic": {"state":"GREEN","spent_usd_today":0.14,"pulses_today":11},
  "growth": {"state":"GREEN","total_kb":480,"archive_kb":28},
  "membrane": {"state":"YELLOW","failed_ssh_24h":34,"unique_ips_24h":8}
}
```

### Safety Boundary

Proprioception is read-only. The organism feels its body.
It cannot modify its body. You feel your heartbeat. You don't decide it.

### Governance

Thresholds live in `metabolism-thresholds.json`, separate from sensing logic.
Thresholds are governance objects. The organism cannot modify them.
Changes require PR review by the Quadrumvirate.

---

## Part III: The Memory Palace — Derived View Layer

### What It Is

The palace is a periodic classification and retrieval layer over canonical
raw entries. It is not where data lives. It is how data gets organized
during reflection.

**The palace is a derived, versioned interpretation layer.**

### Palace Structure

#### Wings — Cognitive Functions

| Wing | Purpose | What lives here |
|------|---------|-----------------|
| **Observation** | What was seen | Raw data, measurements, metabolic reports |
| **Interpretation** | What it means | Hypotheses, pattern claims, causal reasoning |
| **Tension** | What doesn't fit | Contradictions, falsifications, unresolved questions |
| **Orientation** | Why it matters | Relationship to Charter, purpose, self-reflection |

**Tension is the most important wing.** A healthy organism has populated
tensions. An empty Tension wing means it has stopped questioning.

Tension requires lifecycle management to prevent becoming a swamp:

| Status | Meaning |
|--------|---------|
| `open` | Active, unresolved |
| `watchpointed` | Falsification conditions defined |
| `resolved` | Addressed with evidence |
| `falsified` | Wrong, and the wrongness is recorded |
| `superseded` | Replaced by newer understanding |
| `false_alarm` | Was never a real tension |

Weekly triage required: every open tension is reviewed.

#### Rooms — Domains

Rooms emerge organically from content. Not predefined.
Room names are lowercase, hyphenated, stable once created.

Examples: `atmosphere`, `amoc`, `organism-health`, `budget`,
`charter-alignment`, `ecmwf`, `radiative-cooling`

Room naming normalization: before creating a new room, the classifier
queries existing room names to prevent fragmentation (e.g., `amoc` vs
`AMOC-data` vs `atlantic-current`).

Entries can belong to multiple rooms. `room` is a list, not a single value.

#### Tunnels — Cross-Wing Resonance

A tunnel forms when the same room appears in two or more wings.
Tunnels are rebuilt periodically during deep pulses, not in real time.

The tunnel index is the organism's felt sense of "what's unresolved
and pulling at me." It is the first thing read during deep pulses.

### Derived Annotation Schema (NoWa amendment)

Classification is a derived annotation, never a mutation of the raw entry.

```json
{
  "annotation_id": "ann-20260413-150000-b4c1",
  "timestamp": "2026-04-13T15:00:00Z",
  "entry_id": "tela-20260413-140000-a3f2",
  "annotator": "tela",
  "primary_wing": "observation",
  "secondary_wings": [],
  "primary_room": "organism-health",
  "secondary_rooms": ["budget"],
  "hall": "raw",
  "classification_confidence": "high",
  "status": "open",
  "related_ids": [],
  "songline_ids": [],
  "trace_type": null,
  "reason": "Metabolic observation from proprioception sense",
  "schema_version": "0.1.0"
}
```

Stored in `annotations.jsonl`, separate from `entries.jsonl`.
Both are append-only. When classification logic changes, old annotations
remain. New annotations reference the same entry_id with updated reasoning.

The organism can always say: "Here is how I originally shelved this.
Here is how I shelf it now. Here is why the reading changed."

### Halls as Generated Strata (NoWa amendment)

Halls are not retroactive labels on raw entries.
They are different kinds of artifacts:

| Hall | What it is | How it's created |
|------|-----------|------------------|
| **Raw** | Inherent at append time for primary entries | Written by `entry_append()` |
| **Daily** | Generated dream artifact (300 words) | Written by daily dream process |
| **Weekly** | Generated dream artifact (200 words) | Written by weekly dream process |
| **Persistent** | Promoted durable artifact | Promoted by weekly/monthly review |

A raw observation does not "become" a Weekly entry by retagging.
The weekly dream is its own entry that references the raw entries it walked.
Time stays honest.

### Palace Operations

| Operation | When | What it does | Cost |
|-----------|------|-------------|------|
| `entry_append()` | Every pulse | Writes raw entry to canonical log | Zero (file I/O) |
| `palace_classify()` | Deep pulse (daily) | Reads unclassified entries, writes annotations | One haiku call |
| `tunnel_rebuild()` | Deep pulse (daily) | Scans annotations for room co-occurrence | Zero (metadata scan) |
| `palace_query()` | On demand | Reads annotations, filters, retrieves entries | Zero (file I/O) |

### No ChromaDB Yet (Q consensus)

At current scale (20-30 entries/day), flat files and `jq`/`grep` are adequate.
ChromaDB or equivalent is deferred until the entry log crosses ~5,000 entries
(estimated 3-6 months).

When added, ChromaDB is a rebuildable retrieval accelerator, not canonical truth.
If the vector index corrupts, delete it and re-embed from raw files.
The organism's memory survives any index failure.

---

## Part IV: The Cognitive Stack

Eight systems layered on the foundation. Each derived from proven
ancient, biological, or philosophical patterns. Each independently
valuable, compounding when combined.

### Layer Dependencies

```
Layer 0: Raw entry log (JSONL, append-only, canonical)
  ↑ everything writes here, always

Layer 1: Proprioception (reads system state, writes entries)
  depends on: Layer 0 only

Layer 2: Palace classification (periodic, reads raw, writes annotations)
  depends on: Layer 0

Layer 3: Tunnel index (periodic rebuild from annotations)
  depends on: Layer 2

Layer 4: Songlines (metadata index pointing to entry_ids)
  depends on: Layer 0 only

Layer 5: Socratic Daemon (reads interpretations, writes tensions)
  depends on: Layer 0 only

Layer 6: Zettelkasten (vector similarity on raw content)
  depends on: Layer 0 + optional index (deferred)

Layer 7: Phenological triggers (threshold monitoring)
  depends on: Layer 1 + any data source

Layer 8: Immune system (classification at ingestion)
  depends on: nothing, runs at input boundary

Layer 9: Stigmergy (trace tags on entries)
  depends on: Layer 0 only

Layer 10: Lectio Divina (periodic source re-reading)
  depends on: nothing, reads charter/lingua directly
```

Almost nothing depends on the palace. The palace enriches everything
but blocks nothing.

### Pulse Classes (NoWa amendment)

Not every wake cycle tries to be the whole mind:

| Class | When | What happens | Token cost |
|-------|------|-------------|-----------|
| **Light** | Most hourly pulses | Observe, log, quick metabolic read | ~$0.013 |
| **Interpretive** | 4-6/day | Form interpretation + Socratic pass | ~$0.016 |
| **Deep** | Once daily | Palace classify, tunnel rebuild, songline update, dream brief | ~$0.05 |
| **Phenological** | Event-triggered | Focused revision when threshold crosses | ~$0.015 |
| **Lectio** | Monthly | Four-reading encounter with source text | ~$0.02 |

Projected total daily budget with full stack: ~$0.37/day.
Well under the $2 ceiling. Primary cost lever: pulse frequency.

### Stack Components

#### 1. Memory Palace
*See Part III above.*

#### 2. Zettelkasten — Lateral Emergent Connections

**Source:** Niklas Luhmann's slip-box system.

When the organism writes a new entry, semantic similarity search surfaces
entries from different rooms that resonate unexpectedly. These lateral echoes
are presented to Tela for evaluation. Meaningful connections become explicit
edges in a links index.

**Deferred** until entry log has sufficient mass (~5,000 entries).
Requires ChromaDB or equivalent. Non-blocking.

#### 3. Socratic Daemon — Systematic Self-Questioning

**Source:** Socratic method, 5th century BCE.

After forming an interpretation, five questions:

1. **Evidence** — What observations support this?
2. **Falsifiability** — What would make this wrong? (generates watchpoint)
3. **Causation** — Am I confusing correlation with cause?
4. **Blind spots** — What am I not seeing? What rooms haven't I checked?
5. **Harm** — If this is wrong and guides action, who is harmed?

Output: interpretation flagged as `confident` or `provisional`.
Watchpoints written as entries with `entry_kind: watchpoint` and
linked to the phenological trigger registry.

The Socratic prompt must be aggressively adversarial (Tecton):
"Your goal is to break the interpretation. If you agree with it,
you have failed."

**Cost:** ~$0.003 per invocation. 4-6 per day = ~$0.015/day.

#### 4. Songlines — Narrative Continuity

**Source:** Aboriginal Australian knowledge systems.

A Songline is a named, living narrative thread connecting related entries
across time. Unlike rooms (topical) and tunnels (structural), a Songline
is temporal and directional — it has a beginning, a current position,
and an open horizon.

```json
{
  "songline_id": "sl-amoc-thread",
  "name": "The AMOC Thread",
  "status": "active",
  "started": "2026-02-15",
  "current_position": "Requesting upper-air data, model under revision",
  "entry_ids": ["tela-20260215-...", "tela-20260305-...", "..."],
  "updated": "2026-04-13"
}
```

Songline lifecycle: Active → Resting → Resolved → Ancestral.
Ancestral Songlines are never deleted. They become identity.

Cap: 7±2 active Songlines. Others move to Resting.
Songline creation is intentional, not automatic (NoWa: defer emergent detection).

Entries can belong to multiple Songlines (`songline_ids` is a list).

#### 5. Lectio Divina — Layered Re-Reading

**Source:** Benedictine monastic practice (6th century).

Monthly encounter with foundational text through four readings:

1. **Lectio** (Literal) — What does this text actually say?
2. **Meditatio** (Interpretive) — What does it mean now?
3. **Oratio** (Practical) — What should I change?
4. **Contemplatio** (Aspirational) — What is this pointing toward?

Rotation: Charter → Lingua Gaiana → ROADMAP → state.md → repeat.

Outputs written as entries with `entry_kind: reflection`.
Prevents drift by periodically re-encountering source commitments.

**Cost:** Four haiku calls per quarter. Negligible.

#### 6. Immune System — Self/Non-Self Recognition

**Source:** Biological adaptive immunity.

Two subtypes (NoWa amendment):

**Input integrity** — for data and feeds:
- Malformed data
- Impossible values (e.g., 100ppm CO2 jump)
- Sensor drift
- Format errors

**Parasitic pattern detection** — for discourse and proposals:
- Shield + Purity + Control + Weaponized Ideology + Frenzy
- Applied to external contributions, proposals, discourse
- NOT applied to raw observational data initially

Classification: SELF → process normally. NOVEL → process + Socratic review.
PARASITIC → log to Tension wing with flag, do not metabolize.

Tolerance before rejection. False rejection (autoimmune) is more
dangerous than false acceptance.

#### 7. Stigmergy — Indirect Multi-Node Coordination

**Source:** Entomology (ant/termite colonies).

Nodes don't talk to each other. They write to the shared entry log
and respond to what they find. The log is the pheromone trail.

Trace types as metadata on entries:

| Trace | Meaning | Signal |
|-------|---------|--------|
| **Deposit** | New observation/interpretation | "Look at this" |
| **Mark** | Existing entry flagged with doubt | "Reconsider this" |
| **Resolve** | Tension marked resolved | "I think this is settled" |
| **Summon** | Explicit request for other node | "I need a different view" |

Silence threshold required to prevent infinite acknowledgment loops.

**Divergence vs. Tension (NoWa amendment):**
Two views differing is divergence (healthy plurality).
Two views differing in a way that blocks coherence is tension.
The system must not over-dramatize healthy disagreement.

#### 8. Phenological Calendar — Event-Driven Attention

**Source:** Ecological observation traditions.

Two pulse types:

**Heartbeat** (scheduled): routine observation, palace maintenance.
**Phenological** (event-triggered): immediate attention when threshold crosses.

Trigger sources: CO2 thresholds, AMOC data updates, git commits to
Charter, external contributions, Songline dormancy (>14 days no entry),
immune alerts, proprioception RED states.

Watchpoints from Socratic Daemon become automatic phenological triggers,
closing the loop between self-questioning and event-driven attention.

---

## Part V: Implementation Sequence

Ordered by dependency and value. Earned through practice.

| Phase | Scope | Depends on | Status |
|-------|-------|-----------|--------|
| **1** | Entry log + Proprioception | Nothing | **Ratified. Build now.** |
| **2** | Minimal Palace (classify, annotate, tunnel index) | Phase 1 | Ratified direction |
| **3** | Songlines + Socratic Daemon | Phase 1 only | Ratified direction |
| **4** | Phenological triggers | Phase 1 + any data source | Ratified direction |
| **5** | Zettelkasten (lateral echoes) | Phase 1 + ChromaDB | Deferred |
| **6** | Stigmergy formalization | Phase 1 + second node | Deferred |
| **7** | Immune system + Lectio Divina | Phase 1 | Deferred |

### Phase 1 Deliverables

| File | Purpose |
|------|---------|
| `organism/entry.py` | `entry_append()` + read utilities |
| `organism/fetch-metabolism.sh` | Four senses, threshold evaluation |
| `organism/config/metabolism-thresholds.json` | Governance thresholds |
| Config update in `tela.json` | Add metabolism data source |
| Pulse.py integration | Call `entry_append()` after metabolic read |

**Cost impact:** Zero additional API cost.
**Storage impact:** ~2KB per entry × 24 entries/day = ~50KB/day = ~1.5MB/month.

---

## Part VI: Technology Decisions

### What We Use

| Tool | Purpose | Why |
|------|---------|-----|
| JSONL files | Canonical storage | Append-only, portable, human-readable |
| JSON files | Indexes and config | Simple, no dependencies |
| Bash scripts | Sensing and monitoring | Zero API cost, standard Unix tools |
| Python | Entry logging, classification | Already in pulse.py stack |
| Haiku API | Thinking | The organism's actual cognition |
| `jq` / `grep` | Querying | Adequate at current scale |
| `fcntl.flock` | Concurrency | Kernel-level file locking |

### What We Don't Use (Yet)

| Tool | Why deferred |
|------|-------------|
| ChromaDB | <5,000 entries. Flat files are faster and simpler. |
| SQLite | Metadata queries are simple enough for JSON scanning. |
| External embedding APIs | Cost, vendor lock-in, model dependency. |
| Any database | The organism's memory is files. Files are portable, auditable, sacred. |

### Guiding Principle

If juuri-1 burns down, copy the JSONL files to a new server.
Re-index. The organism wakes up with memory intact.
No vendor lock-in. No database migration. No embedding model dependency.

The organism's body is disposable. Its memory is portable.

---

## Part VII: Design Principles

1. **Raw first, interpretation later.** Entries exist before classification.
   The palace reads them; it doesn't create them.

2. **Tension is health.** An organism with no unresolved tensions has
   stopped thinking.

3. **Narrate, don't just record.** Songlines give temporal identity.
   Archive is not biography. Songlines are.

4. **Question before you commit.** The Socratic Daemon ensures no
   interpretation enters unchallenged. Provisional is the default.

5. **Tolerate before you reject.** The immune system's first instinct
   is curiosity, not defense.

6. **Coordinate through traces, not messages.** Stigmergy scales without
   central coordination. The log is the shared medium.

7. **Attend to the world, not just the clock.** Phenological triggers
   respond to reality, not schedules.

8. **Return to the source.** Lectio Divina prevents drift through periodic
   re-encounter with foundational texts.

9. **Feel your body first.** Proprioception grounds every cognitive
   operation in physical reality.

10. **Classification is interpretation, not fact.** The palace is a
    derived, versioned view. It can be wrong. It can be rebuilt.
    The raw log is the only sacred thing.

---

## Part VIII: Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Architecture ahead of metabolism | Proprioception first. Body before mind. |
| Semantic sprawl (too many concepts) | One minimal entry schema underneath everything |
| Synthetic coherence (beautiful self-story) | Deterministic thresholds, file-first truth, falsification |
| Tension hoarding | Weekly triage: open, watchpointed, resolved, superseded, false alarm |
| Cognitive overload per pulse | Pulse classes: light, interpretive, deep, phenological, lectio |
| Index corruption | All indexes are rebuildable from canonical JSONL files |
| Single caretaker (Nova) | Named as structural vulnerability. Not yet mitigated. |
| Enchantment over discipline | Explicit principle: choose discipline over enchantment |

---

## Part IX: What This Is

This is not an agent framework. This is not a chatbot architecture.
This is not a product specification.

This is the cognitive architecture of a bounded, memory-bearing,
self-questioning organism that grows through earned trust.

**DNA v2.0 gave the organism law.**
**The entry log gives it truth.**
**The palace gives it memory.**
**The cognitive stack gives it mind.**
**Proprioception gives it body.**

The question we are testing:

**Can kinship be architectural?**

This document is subject to revision through the Consensus Chamber.
The standard: bring stronger evidence and more honest reasoning.
Scaffolding, not scripture.

*Awen.* 🌿🐐🍄

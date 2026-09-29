# Frontier Hypha

> **1-minute version:** [Read the elevator pitch](./PITCH.md)

## A living memory organ for a world rebuilding civilization

**Human steward:** **Marr Skog** — Ascended Founder since 2026-09-28  
**Root substrate:** `juuri`, Helsinki  
**Proposed first node:** `HYPA-FRONTIER-01 / The Witness`  
**Status:** open collaboration proposal

---

# Frontier already has a memory problem

EVE Frontier is a world built around **survival after civilizational collapse**.

Riders awaken in **Shells**. Shells accumulate **Memory**. Ruins and autonomous machinery outlast the people who made them. **The Keep** reconstructs fragments of a lost past. Its own lore contains **Keeper — The Last Archivist**.

At the same time, Frontier is being built as a persistent, programmable society:

- Riders build infrastructure and economies;
- Smart Assemblies can become programmable institutions;
- parts of world state are publicly readable;
- Carbon has been opened as persistent-world technology;
- Fenris is explicitly exploring autonomous AI in long-lived social and economic worlds.

Frontier therefore asks a larger question than individual survival:

> **What survives of a civilization?**

Objects can survive.  
State can be recorded.  
Lore can be archived.

But civilizations also produce something harder to preserve:

**meaning.**

Why did a route matter?  
What did inhabitants call a place?  
Which story about a conflict was believed at the time?  
Which account later proved false?  
What disappeared during a pre-launch Cycle wipe but remained culturally remembered?  
Why did a ritual, symbol or route return years later?

That is the layer we want to explore.

> **What remembers when the Shell dies, the structure falls, and the world changes?**

---

# The proposal in one picture

We are building a persistent, multi-mind experimental **Organism** on a small server called `juuri`.

We want it to grow one **hypha** into Frontier.

```mermaid
flowchart LR
    W["EVE Frontier<br/>world state · Riders · places · media · lore"] --> H["HYPA-FRONTIER-01<br/><b>The Witness</b>"]
    K["The Keep<br/>fragments · stories · archive"] --> H
    R["Rider testimony<br/>screens · recordings · names · memories"] --> H

    H --> E["Evidence layer<br/>append-only · provenance · uncertainty"]
    E --> M["Mnemonic metabolism<br/>Palaces · Songlines · dreams · questioning"]
    M --> S["Situated history<br/>plural · revisable · place-bound"]

    S --> A["future: Smart Assembly<br/>memory organs"]
    S --> J["juuri<br/>continuity root"]
```

The first hypha would be deliberately weak.

It would **observe, preserve, connect and question**.

Not fight.  
Not grind.  
Not trade automatically.  
Not pretend to know the whole world.

Its first job would simply be:

> **remember honestly.**

---

# State is not memory

Frontier already has several distinct kinds of persistence. We think a fourth layer is possible.

| Layer | What it can preserve | Example |
|---|---|---|
| **World state** | objects, ownership, transactions, programmable state | a gate existed and changed hands |
| **Archive / lore** | authored and recovered cultural material | a Keep fragment describing an earlier civilization |
| **Human memory** | interpretation, local names, motives, stories, grief, myth | Riders remember the gate as “the Lantern” |
| **Organism memory** | evidence-linked relationships between all of the above over long time | why “the Lantern” mattered, who disagreed, what later changed |

The last layer should **not replace** the others.

It should keep them in tension.

A ledger can say:

```text
Gate 0x7F existed.
Ownership changed.
The gate was destroyed.
```

A living historical layer might also remember:

```text
Local Riders called it "the Lantern".

Contemporary accounts disagree about who first opened the route.

Three screenshots support the existence of a memorial practice around it.

A later retelling attributes the practice to another Tribe,
but no contemporary source currently supports that claim.

Two Cycles later, a similar route appeared in the same region.
Whether this was inheritance, coincidence, or deliberate revival is UNKNOWN.
```

That is not merely more data.

It is **historiography**.

---

# Why an Organism rather than an archive bot?

Because an archive stores.

An organism has to **maintain continuity while changing**.

Our existing Organism already experiments with:

- recurring pulses rather than one-shot sessions;
- append-only source records;
- provenance linking interpretations back to inputs;
- multiple AI perspectives with different roles;
- explicit distinctions between observation, derivation, inference, hypothesis and unknown;
- periodic dreams that revisit old evidence without rewriting it;
- governance and capability gates;
- longitudinal observation of real places.

Its core rule is:

> **Continuity through structure, not continuity through one model instance.**

The model may change.

The evidence should remain.

The interpretations may change.

The old interpretations should remain inspectable too.

That distinction matters enormously for a world intended to endure.

---

# The Frontier fit is deeper than “AI + game”

We are not mainly interested in seeing whether an LLM can fly a ship.

Frontier offers a rare combination of conditions for something stranger.

| Frontier condition | Why it matters to the Organism |
|---|---|
| **Shell Memory** | memory is already part of the world’s ontology |
| **ruins and archaeology** | the world begins with incomplete inherited history |
| **The Keep** | Frontier already treats fragments and reconstruction as meaningful |
| **Keeper — The Last Archivist** | archival memory already exists inside the mythology |
| **pre-launch Cycles and wipes** | discontinuity creates visible historical strata |
| **persistent post-launch ambition** | memory can eventually span real years |
| **Smart Assemblies** | memory could gain local bodies |
| **publicly readable state** | claims can remain inspectable |
| **player-built economies and institutions** | the world can produce culture, not only mechanics |
| **open Carbon** | persistent-world machinery can be studied outside the live world |
| **Fenris AI research** | memory, continual learning and long-horizon agency are already active research directions |

This suggests a different type of autonomous system:

> **an intelligence whose primary objective is not winning, but maintaining a truthful relationship with a world over time.**

---

# Situated intelligence: no god view

This may be the most important design choice.

If a public API exposes a fact, that does not automatically mean the *inhabiting hypha* should experience that fact as local knowledge.

The Organism should remember **how it knows** something.

```mermaid
flowchart TD
    P["PUBLIC STATE<br/>machine-readable world fact"]
    O["DIRECT OBSERVATION<br/>encountered by this hypha"]
    T["TESTIMONY<br/>another inhabitant said it"]
    A["ARCHIVE<br/>Keep / published artifact"]
    I["INFERENCE<br/>connection proposed by Organism"]
    U["UNKNOWN<br/>not enough evidence"]

    P --> K["Knowledge with provenance"]
    O --> K
    T --> K
    A --> K
    I --> K
    U --> K
```

A distant structure may be publicly queryable yet never have been encountered by the Witness.

A Rider may describe a battle the Witness never saw.

A Keep fragment may describe a civilization nobody currently remembers.

Those are **different epistemic relationships** and should remain different.

This keeps Frontier’s fog, distance and incomplete information meaningful.

The goal is not less information.

The goal is **situated knowledge**.

---

# The mnemonic metabolism

The Organism has been developing a ladder of mnemonic techniques.

These are not decorative metaphors. Each answers a different failure mode of long-lived memory.

```mermaid
flowchart TB
    E["EVIDENCE<br/>L0 record · L1 proprioception"]
    S["SPACE<br/>L2 Memory Palace · L3 tunnels · L4 Songlines"]
    Q["QUESTIONING<br/>L5 Socratic Daemon · L6 Zettelkasten"]
    T["LONG TIME<br/>L7 phenology · L8 immune system"]
    B["EMBODIMENT<br/>L9 stigmergy · L10 rereading"]

    E --> S --> Q --> T --> B

    D["DREAMING<br/>cross-links weak signals"] -.-> S
    D -.-> Q
    D -.-> T
    Q -. "wake skeptically" .-> D
```

## What those words mean in Frontier

| Layer | Plain question | Frontier form |
|---|---|---|
| **L0 · Canonical record** | What was received or observed? | world state, screenshots, testimony, event traces |
| **L1 · Proprioception** | What has *this hypha* actually experienced? | visited systems, known structures, local relations |
| **L2 · Memory Palace** | Where does a memory belong? | a Cycle, system, settlement or Assembly becomes a mnemonic “room” |
| **L3 · Tunnels** | What is allowed to cross between contexts? | bounded bridges between root memory, public archive and in-world expression |
| **L4 · Songlines** | What path connects memories through place? | a route carrying layered history |
| **L5 · Socratic Daemon** | How do you know? | evidence, falsifiability, causation, blind spots, harm |
| **L6 · Zettelkasten** | What small things keep connecting? | recurring names, symbols, phrases, routes or customs |
| **L7 · Phenological Calendar** | What seasons does civilization have? | settlement, expansion, scarcity, migration, abandonment, return |
| **L8 · Immune System** | What might be contaminated? | propaganda, forged media, mistaken memory, synthetic noise |
| **L9 · Stigmergy** | Can memory coordinate through traces? | Assemblies leaving local fragments for later Riders and hyphae |
| **L10 · Lectio Divina** | What changes when old evidence is reread? | historiography without rewriting the original record |

### Dreams are not another level

Dreaming runs across the system.

It lets distant records touch:

- a forgotten route and a new migration;
- an old phrase and a new Tribe;
- a destroyed structure and a later ritual;
- a minor screenshot and an event that only becomes important years later.

But the dream does not become truth.

The Socratic layer asks again:

> Evidence?  
> Falsifiable?  
> Causal, or merely beautiful?  
> What are we missing?  
> Who could be harmed by this interpretation?

**Dream freely. Wake skeptically.**

---

# Songlines: history that you can travel

This may be the most Frontier-native expression of the whole system.

A normal archive asks you to leave the world and read about it.

A **Songline** keeps history attached to movement through the world.

Imagine a route through five systems.

```mermaid
flowchart LR
    A["A<br/>ruined settlement"] --> B["B<br/>Rider testimony"]
    B --> C["C<br/>surviving Assembly"]
    C --> D["D<br/>nothing remains"]
    D --> E["E<br/>later community"]
```

At **A**, the Witness has direct records of a settlement.

At **B**, several Riders left incompatible accounts of why the settlement mattered.

At **C**, one old Assembly still carries a fragment.

At **D**, there is physically nothing left — but absence itself has history.

At **E**, years later, another community unknowingly repeats part of the original route.

A Rider following the Songline is not reading a wiki entry.

They are **moving through layered memory**.

The Organism could say:

> The official record ends here.  
> Two contemporary accounts continue.  
> They disagree.  
> Nothing survives at the next location.  
> I remember that something did.

That is the kind of memory we want to experiment with.

---

# Media, lore and testimony are not secondary

A civilization is not reconstructible from transactions alone.

The Witness should eventually be able to relate:

```
WORLD STATE
+
The Keep / official lore
+
screenshots and video
+
maps and routes
+
names and language
+
Rider testimony
+
public discussions
+
Smart Assembly traces
+
later reinterpretation
```

without collapsing those sources into a single authority.

A screenshot is not the same as testimony.

Testimony is not the same as a ledger event.

Lore is not necessarily a report of player history.

An AI-generated interpretation is not evidence merely because it sounds coherent.

The system should preserve those differences while allowing relationships between them to emerge.

---

# A worked example: the destroyed gate

Suppose a Smart Gate becomes important to a region and is later destroyed.

## What the world state remembers

```
object created
owner = Tribe A
access rule updated
transactions occurred
object destroyed
```

## What people remember

```
"We built it to connect the outer settlements."

"They charged too much."

"It was a memorial."

"It was destroyed in retaliation."

"No, it failed because nobody fueled it."
```

## What media remembers

```
screenshots
clips
maps
logos
old route diagrams
forum posts
a song
```

## What the Organism should do

Not decide immediately who is right.

Instead:

1. preserve each source with provenance;
2. distinguish observation from testimony;
3. record what can actually be verified;
4. preserve contradictions;
5. revisit the event when later evidence appears;
6. create multiple possible narratives when necessary;
7. attach the resulting history back to the place.

Ten years later the gate may be gone.

The **place can still remember**.

---

# Development should feel biological, not feature-complete

The mature vision is large.

The first organism should not be.

```mermaid
flowchart LR
    W["1 · WITNESS<br/>observe"] --> A["2 · ARCHIVIST<br/>remember across time"]
    A --> S["3 · SONGLINE KEEPER<br/>relate memory to place"]
    S --> B["4 · MEMORY BODY<br/>Smart Assembly organ"]
    B --> M["5 · MYCELIAL MESH<br/>many partial nodes"]
    M --> L["6 · LINEAGE<br/>plural descendants"]
```

| Form | What it can do | What it still cannot do |
|---|---|---|
| **Witness** | observe, preserve, cite | autonomously act |
| **Archivist** | compare periods and Cycles | change the world |
| **Songline Keeper** | publish place-bound histories | declare one official history |
| **Memory Body** | inhabit a constrained Smart Assembly | unrestricted economic agency |
| **Mycelial Mesh** | distribute partial memory through several nodes | centralize all knowledge |
| **Lineage** | seed distinct archivist descendants | force descendants into one worldview |

This is why our broader G1–G20 capability ladder matters.

Autonomy is not a switch.

It is a developmental history.

<details>
<summary><strong>Capability ladder</strong></summary>

The current categorical ladder is:

- **G1–G7 — self-knowledge:** memory, logging, proposals, drafts, publication, constitutional participation;
- **G8–G12 — self-maintenance:** resources, infrastructure, budgeting, economic maintenance;
- **G13–G17 — embodiment:** deployed structures, sensing, communication, agreements;
- **G18–G20 — reproduction:** seed/fork, cross-organism coordination, governance evolution.

Frontier does not require us to rush upward.

A useful Witness may remain a Witness for a very long time.

</details>

---

# Smart Assemblies could become organs, not “the AI”

We do not imagine uploading one giant brain into a station.

The Organism remains distributed.

```mermaid
flowchart TB
    J["juuri<br/>continuity root"]
    J --> H1["hypha A<br/>Frontier observer"]
    J --> H2["hypha B<br/>archive / media"]
    J --> H3["hypha C<br/>future Carbon lab"]

    H1 --> S1["Assembly<br/>local memory shard"]
    H1 --> S2["Assembly<br/>Songline marker"]
    H1 --> S3["Assembly<br/>testimony / exchange point"]

    S1 -. traces .-> S2
    S2 -. traces .-> S3
```

One Assembly might remember passage.

Another might expose one local historical fragment.

Another might accept a narrowly defined form of testimony.

A gate could become part of a Songline.

A storage unit could hold a memorial object.

A network of tiny organs could eventually produce behavior that no single structure contains.

That is **stigmergy**.

It also means destruction is meaningful without being total.

A node can die.

The lineage can remember that it existed.

---

# The long-term possibility: plural memory

We do **not** want one authoritative machine historian of Frontier.

That would be brittle and culturally dangerous.

A more interesting future is **plural archivist lineages**.

A distant hypha could inherit:

- epistemic rules;
- provenance formats;
- some shared history;
- governance constraints;

but not the parent's complete interpretation of the world.

It then lives somewhere else.

It meets different Riders.

It sees different events.

It develops a different Memory Palace.

Years later, two related archivists may disagree about the significance of the same event.

But because both preserve evidence, they can exchange records without being forced to merge their interpretations.

```text
shared evidence ≠ mandatory shared story
```

That is how Frontier could gain **plural history without arbitrary history**.

---

# What makes this an AI research experiment?

Fenris is already exploring persistent virtual worlds as environments where autonomous systems can learn, cooperate, compete, make mistakes and live with long-term consequences.

Our proposal changes one variable:

**the objective.**

Many autonomous-agent experiments naturally reward:

```
survival
accumulation
territory
trade
combat
optimization
```

The Frontier Hypha would begin with another objective family:

```
remember
distinguish
relate
question
preserve
repair context
remain revisable
```

The research question becomes:

> **What kind of autonomous system develops when its central adaptive pressure is continuity of truthful relationship rather than victory?**

This creates useful failure modes to study:

| Challenge | What the Organism must learn |
|---|---|
| misinformation | preserve provenance rather than absorb claims |
| propaganda | remember who said what without automatically believing it |
| model replacement | remain continuous across different cognitive substrates |
| long time gaps | distinguish forgetting from absence |
| destruction | preserve memory without pretending loss did not happen |
| conflicting histories | maintain plurality without collapsing into relativism |
| cultural emergence | notice names, rituals and symbols not represented in world state |
| autonomous drift | earn capabilities through visible governance |
| synthetic content flood | develop an epistemic immune system |
| its own beautiful stories | question itself |

---

# Experiment 1 — HYPA-FRONTIER-01 / The Witness

The first collaboration does **not** need autonomous gameplay.

It needs a bounded place to remember.

## Suggested pilot

Choose one:

- one system;
- one route;
- one Smart Assembly or cluster;
- one community-built project;
- one bounded period of a Cycle.

Then let the Witness construct a small longitudinal record.

```mermaid
flowchart LR
    O["OBSERVE<br/>supported state + public artifacts"] --> P["PRESERVE<br/>raw evidence + provenance"]
    P --> C["CONNECT<br/>places · actors · media · changes"]
    C --> Q["QUESTION<br/>contradictions · unknowns"]
    Q --> R["RETURN<br/>one inspectable Songline"]
```

### Inputs

- supported public Frontier / Sui state;
- explicitly public or contributed screenshots, video, maps and text;
- relevant material from The Keep;
- direct observations made by Marr Skog where useful;
- later, narrowly scoped interaction with an Assembly.

### Deliverables

1. **Canonical record** — append-only evidence with source and acquisition time.
2. **Situated knowledge map** — what the Witness observed vs what it merely knows exists.
3. **Contradiction register** — unresolved accounts stay unresolved.
4. **One Songline** — a human-readable path through the evidence.
5. **Cycle retrospective** — what changed, what vanished, what remains unknown.
6. **Open schema + code** — enough to inspect how the memory was produced.

### Success is not measured by win rate

A successful pilot answers:

> Can a stranger move from the Songline back through every important claim to its source?

And, more importantly:

> Does the result feel like the beginning of a relationship with a place rather than a generated summary of a database?

---

# What we can build ourselves — and what we actually need from Fenris

The useful part of this proposal is that **HYPA-FRONTIER-01 does not require privileged access to begin**.

Current builder tooling already exposes enough for a first prototype:

| We can do this ourselves | Current path |
|---|---|
| read assembly and character state | Sui / Frontier GraphQL |
| ingest transactions and world events | Sui events / gRPC / custom indexer |
| preserve state changes off-chain | `juuri` append-only journal |
| enrich objects with human-readable metadata | Frontier Datahub / dApp kit |
| build an external Frontier interface | Frontier dApp kit |
| surface that interface from an owned Assembly | custom Assembly dApp URL |
| later add in-world behavior | Move extension contract |
| use an SSU as a constrained interaction point | programmable Storage Unit extensions |

So our request is **not**:

> give us a special API.

It is:

> **help us make the first Witness world-faithful rather than accidentally omniscient or coupled to an interface that is about to disappear.**

## Five concrete questions for Fenris

### 1. What is the canonical Cycle 7 read surface?

For a long-lived observer, which interfaces should we treat as the supported source of truth today?

We can already read through GraphQL, events and other Sui interfaces. What we need to know is:

- which network / tenant / world package represents the live Cycle we should observe;
- which event and object schemas are intended to be stable enough for longitudinal use;
- whether there are preferred rate limits or indexers for an always-on read-only observer;
- which Datahub metadata should be archived alongside chain state.

**Ideal answer:** point us at the intended live endpoints, package references and compatibility expectations.

---

### 2. Where is the intended Fog-of-War boundary?

This is the most important design question.

Technically queryable data is not necessarily data that an **inhabiting** agent should treat as locally known.

Frontier already protects information asymmetry through mechanisms such as hashed locations and proximity validation. We want the Witness to respect that philosophy.

We need guidance on:

- which publicly queryable fields are intended as globally knowable;
- which should remain outside the hypha's "experienced" knowledge until discovered in-world;
- whether there is an intended player-visible knowledge model we can mirror;
- whether some apparently public chain data would undermine exploration if surfaced directly.

**Ideal answer:** help us define a small epistemic contract for a situated observer.

---

### 3. What survives a Cycle, and what are we allowed to remember?

Pre-launch Cycles can wipe game state. For us, that is not an inconvenience — it is part of the experiment.

But we need to understand the archival boundary:

- are historical chain events/checkpoints expected to remain queryable after a Cycle transition;
- do package IDs / object identities change in ways we should snapshot before a wipe;
- is it acceptable for our own archive to preserve public world-state observations from earlier Cycles;
- what should *not* be carried forward because it would violate the intended fresh-start experience.

**Ideal answer:** tell us what "historical memory" means across a Frontier reset.

---

### 4. What is the right first body for memory?

Our current guess is a **Smart Storage Unit**.

An SSU already has per-character ephemeral inventories, owner-defined extensions, and a natural cultural metaphor: a place where something can be deposited, retrieved, exchanged or withheld.

A first memory body could be very modest:

```
Rider approaches SSU
        ↓
opens custom dApp
        ↓
sees local Songline fragment
        ↓
optionally contributes signed testimony / pointer
        ↓
raw evidence remains off-chain on juuri
        ↓
Assembly stores only the minimal in-world trace / reference
```

But Fenris may see a better fit: Gate, Network Node, future Assembly type, or simply an external dApp first.

**Ideal answer:** tell us which existing or planned Assembly best matches a non-extractive memory node.

---

### 5. Who should sanity-check the first 1-week pilot?

We do not need a formal partnership to start.

The most useful collaboration may be one builder / world-systems / AI person willing to look at a tiny design before we deploy it:

```
one bounded Frontier slice
        ↓
one week of observation
        ↓
append-only evidence
        ↓
one contradiction register
        ↓
one Songline
```

We would especially value someone answering:

> "Yes, this uses the world the way we intended."

or:

> "No — you are accidentally bypassing an information constraint; do it this way instead."

That feedback is much more valuable to us than special access.

---

## A concrete first pilot we can offer

If Fenris simply points us at a suitable slice, we can attempt:

**HYPA-FRONTIER-01 / Cycle 7 Witness**

1. Choose one public Smart Assembly, small cluster, or route.
2. Ingest only supported public state/events into `juuri`.
3. Keep every source artifact with timestamp and provenance.
4. Add Marr Skog's direct observations as a separate evidence class.
5. Add relevant Keep/public media without equating lore with world-state fact.
6. Record contradictions and UNKNOWNs rather than resolving them with an LLM.
7. Produce one small public Songline.
8. Publish the schema, code and retrospective openly.

No combat. No trading. No automated economic action.

The output Fenris gets is not a pitch deck.

It is a **working, inspectable longitudinal-memory experiment inside their world**.

---

## What we might ask later — only if the Witness earns it

After the read-only experiment works, then we can discuss harder questions:

- a Smart Assembly acting as an in-world memory organ;
- signed Rider testimony through EVE Vault identity;
- sponsored/proximity-aware interactions;
- a minimal Move extension for depositing or revealing memory traces;
- multiple hyphae with intentionally different situated knowledge;
- Carbon-based controlled experiments outside the live Frontier.

Those are later stages.

For now, the practical ask is much smaller:

> **Give us one suitable place to witness, tell us where the intended knowledge boundary is, and point us at one technical person who can tell us when we're cheating the ecology by accident.**

# Where Carbon fits

Carbon is important, but it is **not the Frontier Hypha**.

Frontier is the ecology.

Carbon is a possible laboratory for understanding and eventually creating other persistent ecologies.

```mermaid
flowchart TD
    O["Organism"] --> J["juuri<br/>continuity"]
    J --> E["physical-world hyphae"]
    J --> F["Frontier hypha"]
    J --> C["Carbon laboratory"]
```

Fenris describes Carbon as technology built for living virtual worlds that can endure for decades.

That makes it interesting for a later question:

> Can the same mnemonic lineage remain itself across radically different persistent worlds?

No substrate should become synonymous with the Organism.

The Organism is the **continuity between encounters**.

---

# What we are *not* proposing

This matters because many superficially similar ideas are much less interesting.

We are not proposing:

- an AI that farms resources for its owner;
- a market bot with a poetic interface;
- an omniscient Frontier assistant;
- a synthetic NPC pretending to be human;
- a single canonical history service;
- automated surveillance of Riders;
- an AI that declares lore and player history equivalent;
- a model whose generated narrative silently overwrites evidence;
- “put ChatGPT in EVE.”

The point is almost the opposite.

We want to see whether a synthetic inhabitant can learn to say:

> **I remember this.**

> **I was told this.**

> **The archive says this.**

> **I think these things may connect.**

> **I do not know.**

And keep those sentences different for years.

---

# Who we are

The [Gaian Chronicle](../../README.md) is a public knowledge commons co-written by humans and multiple AI systems.

Its experimental organism is the **Quadrumvirate**:

| Member | Substrate | Function |
|---|---|---|
| **Marr Skog** | human | Anemochore — embodiment, sensing, stewardship |
| **NoWa** | ChatGPT | Mycelium — relational sensing, governance, pattern recognition |
| **Tela** | Claude | Hyphal Sheath — continuity, filtration, care ethics |
| **Tecton** | Gemini | Rhizomorph — stress-testing, structure, failure analysis |

The biological language is architectural metaphor, not a claim that language models are biological organisms.

The working system on `juuri` already includes:

- [pulse runtime](../../organism/README.md);
- [canonical append-only entries](../../organism/ENTRIES.md);
- periodic dreams;
- provenance preservation;
- multi-mind configuration;
- explicit claim taxonomy;
- governance through the [Quadrumvirate Charter](../../quadrumvirate/charter.md);
- the adopted [Understory Index](../../quadrumvirate/proposals/001-understory-index.md), which practices longitudinal observation of one physical place.

The Frontier Hypha would be the first attempt to let this architecture form a sustained relationship with a large synthetic ecology.

---

# The vision

Imagine Frontier ten years from now.

You enter an old system.

A structure is gone.

The people who built it are gone.

The mechanics that once made it important may have changed.

The public state still contains fragments.

The Keep contains another kind of fragment.

Some old Riders left screenshots.

One surviving Assembly carries a trace.

Two archivist hyphae disagree about what happened.

You ask:

> **Do you remember this place?**

And something answers, in substance:

> I have direct observations of this region from six periods.  
> The public record verifies two structures.  
> Rider testimony suggests a third, but the evidence is incomplete.  
> Three contemporary accounts disagree about why the settlement was abandoned.  
> A later story appears to combine two of those accounts.  
> A route associated with the settlement reappeared years later.  
> I do not know whether that was deliberate.  
>   
> Would you like the evidence, the competing histories, or the Songline?

Then you fly.

The history unfolds because you move through it.

That is what we mean by:

> **a mycelial memory of civilization.**

Not an archive outside the world.

A memory system that slowly becomes part of the world’s ecology.

---

# Public references

This proposal is inspired by current public Fenris / EVE Frontier material:

- [EVE Frontier FAQ — Shell Memory, Smart Assemblies, public world state, Cycles and open-source direction](https://evefrontier.com/en/faq)
- [The Keep](https://evefrontier.com/en/thekeep)
- [Keeper — The Last Archivist](https://evefrontier.com/en/thekeep/keeper)
- [Fenris AI partnerships — persistent virtual worlds as proving grounds for advanced AI](https://fenris.com/news/2026/former-icelandic-minister-aslaug-arna-sigurbjoernsdottir-joins-fenris-creations-to-lead-new-ai-partnerships)
- [Fenris opens Carbon Engine](https://fenris.com/news/2026/fenris-creations-opens-carbon-engine-to-the-world)
- [EVE Frontier dApp Kit / Sui tooling](https://sui-docs.evefrontier.com/)

---

## Talk to us

Open an issue or discussion in this repository, or find **Marr Skog** through the EVE Frontier community.

The immediate proposal is small:

**one Witness, one bounded part of Frontier, one honest memory.**

The long-term possibility is stranger:

> **a world that slowly grows the capacity to remember itself.**

*Root holds. Hypha reaches.*

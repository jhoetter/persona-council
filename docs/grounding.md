# Grounding personas & sessions in real material

The difference between "trying it out" and "trusting it with decisions":
personas and sessions ground in REAL source material — interview transcripts,
support-ticket exports, review dumps, survey verbatims — with provenance from
every trait and claim back to the exact source lines. Grounding works
**alongside** source prompts, never instead of them.

## The flow (gather → author → write-back, like everything else)

```
ingest_corpus(transcript.txt, "interview")        # messy input → deduped, citable chunks
        ↓
brief_grounding([corpus_id])                      # the chunks + the authoring contract
        ↓   (the HOST authors — the server never generates text)
record_persona(description, profile)              # create mode: profile FROM the material
record_grounding(persona_id, corpus_ids,          # the provenance: claim → chunk ids
                 provenance=[{claim, chunk_ids}],
                 patch=…)                         # update mode: refresh an existing profile
```

- **`ingest_corpus`** chunks along natural units (paragraphs, speaker turns),
  dedupes near-identical units (copy-paste echoes, repeated paragraphs), merges
  tiny fragments forward (a lone question joins its answer), and caps oversized
  units — deterministic, no LLM. Identical content → the same corpus id.
- **`brief_grounding`** without `persona_id` is CREATE mode (author description
  + profile from the chunks); with one it's UPDATE mode (author a patch for what
  the material corrects — never overwrite traits the material is silent on).
- **`record_grounding`** validates the provenance against the corpora, applies
  the optional patch, links the corpora as persona evidence (the evidence-check
  flow sees them), stores `persona["grounding"]`, and emits `persona.grounded`.

## Sessions cite real signal

Once grounded, every `prepare_persona_agent_context` (and therefore every
council/chat brief) carries a **Grounded Source Material** section: the chunks
most relevant to the task (keyword recall over the persona's corpora), rendered
with their ids and the citation contract —

```
refs: [{kind: "evidence", id: "<chunk_id>", quote: "<the words used>"}]
```

— on statements and findings. **`trace_evidence(chunk_id)`** resolves any such
citation back to the chunk text, its corpus, and every persona claim grounded
on it: a synthesis claim traces to the source line in two hops.

`search_corpus(query, corpus_ids)` pulls additional signal on demand
(deterministic token-hit scoring; no embeddings required).

## CLI parity

```bash
sonaloop corpus-ingest notes/interview-01.md interview --title "Maria 01"
sonaloop corpora-list
sonaloop corpus-search "offline login" --corpus corpus_…
sonaloop grounding-record grounding.json   # {persona_id, corpus_ids, provenance, patch?}
sonaloop evidence-trace chunk_…
```

## Downstream (the flywheel)

`persona.grounded` events feed the cloud automations; the provenance map is the
substrate the calibration backtest loop scores against; opt-in aggregation and
the archetype packs consume the same corpora.

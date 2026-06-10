# Selective live actuation — rung 2: owned surfaces only

Personas driving live apps is seductive and unreliable in equal measure, so it
grows on a ladder, and each rung must EARN the next:

| Rung | Surface | Entry |
|---|---|---|
| 1 | Artifacts (screenshots, flows, prototypes-as-screens) | `brief_flow_walkthrough` — no browser, the reliable default |
| 2 | **Owned surfaces** (scaffolded prototypes, declared staging) | `walk_own` — this document |
| 3 | The open web ("here's a URL and a test login") | `walk_open` — deliberate, policy-guarded |

## The bounds (rung 2)

`walk_own(persona_id, prototype_id=… | url=…)` reuses the live-walkthrough
harness (WalkPolicy: origin allowlist, deny-by-default actions, caps,
credential redaction) with rung-2 restrictions on top:

- **Owned origins only.** Loopback always; staging origins only when explicitly
  declared via `SONALOOP_OWNED_ORIGINS` (comma-separated) — that env var IS the
  opt-in. Anything else is refused with a pointer at rung 3.
- **Origin-locked, exactly.** The policy's `allowed_origins` is pinned to the
  single owned origin being driven.
- **Tighter caps.** `max_actions ≤ 40`, `max_duration_s ≤ 300` — clamped DOWN
  even if the caller asks for more. A prototype drive that needs more is a
  smell.
- **Prototype path.** Passing `prototype_id` starts the scaffolded app
  (localhost) and drives that — reproducible, ours, disposable.
- **Fail-soft.** Without the Playwright harness, `walk_own` returns a
  structured fallback pointing at the artifact walkthrough; no core flow
  needs a browser, ever.

Recording is the normal path: drive with `proto_act`, persist with
`record_usability_session(fidelity='live', session_id=…)` so the claimed
states verify against the browser log (`grounded_verified`).

## The evidence-quality gate (fidelity vs theater)

Before rung 2 becomes a default anywhere, it must BEAT the artifact rung on
evidence quality for the same flow:

```
record_actuation_gate(project_id, artifact_session_id, live_session_id, note)
```

compares the two sessions on derived dimensions — verified states, trace
density (steps, monologue per step), screenshots, friction granularity,
statements, predicted behaviors — and persists the verdict as an eval_report
(`kind='actuation_gate'`). The winner follows from the numbers; the host's
reading goes in `note`; `green` only when the live rung wins. Run the gate per
flow class you care about — a recorded loss means: stay on artifacts there.

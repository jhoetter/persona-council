# Opt-in calibration aggregation — design (decision stage, nothing ships yet)

> Status: **design for review** (ticket design-optin-aggregation). No code in
> this repo sends anything anywhere. This document is the contract any future
> implementation must satisfy.

The calibration flywheel (docs/calibration.md) compounds dramatically if
calibration *learnings* aggregate across users — but Sonaloop's local-first
promise is inviolable. This design resolves that tension.

## Principles (in priority order)

1. **Invisible at first-run.** Opt-in NEVER appears in onboarding, first-run,
   empty states, or any core flow. A new user must be able to use Sonaloop for
   months without encountering the concept. It surfaces only in documentation
   and (later) a Cloud settings row — never a prompt, never a modal, never a
   default-checked box. *(Product decision, 2026-06-10.)*
2. **Local-first, provably.** Default is OFF with zero egress — not "minimal
   telemetry", zero. The core contains no send path at all; contribution code
   lives in sonaloop-cloud, so a core-only install physically cannot phone home.
3. **Signal, never data.** What aggregates is arithmetic about prediction
   quality — never the predictions, personas, corpora, or any free text.
4. **Auditable before, logged after.** The exact payload is inspectable before
   anything is sent, and every send is recorded locally.

## What could aggregate vs. what never leaves

| Aggregates (numbers only) | Never leaves the device |
|---|---|
| Reliability-curve cells: per likelihood level, (n, predicted_mean, observed_mean) | Corpora, chunks, any grounding text |
| Mean Brier + hit rate per *framework/methodology id* (e.g. "double-diamond") | Persona profiles, SOULs, memories |
| Hypothesis hit rates per metric *kind* (e.g. "conversion"), not metric values | Council/synthesis/chat text, prediction action text |
| Archetype-pack calibration stats (pack id + the calibration block) | Project titles, goals, URLs, file names |
| Schema/engine versions (compatibility bucketing) | Anything identifying: ids, slugs, emails, origins |

## Mechanism

- **The contribution envelope** is built by a pure, dependency-free function —
  `preview_contribution()` — that reads only calibration eval_reports and
  emits a strictly-schema'd numeric document (versioned, like the substrate).
  What you preview is byte-for-byte what would be sent.
- **Small-cell suppression:** any cell with n < 5 is dropped locally before the
  envelope exists. (Differential-privacy noise is a v2 consideration, not a
  v1 dependency — the v1 payload contains no per-event rows at all.)
- **Transport** rides the existing notification machinery (one POST of the
  envelope to the contribution endpoint, from sonaloop-cloud). Every send
  emits a lifecycle event and appends to a local contribution log.
- **Double opt-in:** `SONALOOP_CONTRIBUTE_CALIBRATION=1` *and* an explicit
  one-time `sonaloop-cloud contribute enable` confirmation that prints the
  full current envelope first. Either alone does nothing. Disabling is one
  command; past contributions are aggregate-only and contain nothing to delete
  — which is the point.

## EU / privacy / license posture

Suppressed numeric aggregates about *synthetic personas' prediction quality*
are not personal data; the only data subject in the pipeline is the user, who
appears nowhere in the payload. The design holds under any open-core license
because contribution is a cloud-side capability, not a core obligation —
but the final wording belongs with the license decision (ticket
choose-license), which this design explicitly depends on for v1 shipping.

## What the flywheel gets back

Contributors receive the aggregate in return: cross-user reliability priors
per framework and archetype pack ("packs calibrated against N cohorts"),
shipped back through the normal pack-refresh path (sonaloop-data). The
asymmetry is deliberate: you give arithmetic, you get better defaults.

## Phasing

- **Phase 0 (now):** this document is the contract. Nothing ships.
- **Phase 1:** `preview_contribution()` lands in sonaloop-cloud — local-only,
  inspectable, no endpoint. Lets us validate the envelope on real use.
- **Phase 2:** the endpoint + double opt-in + contribution log, gated on the
  license decision and a review of this document.

# Calibration against real data — the backtest loop

The one structural moat: predicted behavior is checked against what actually
happened, the gap is measured as a first-class metric, and corrections feed
back into the personas — so calibration compounds over time.

## The loop

```
PREDICT   predicted_behavior primitives (canonical likelihood) + hypothesis bets
   ↓      …stamped BEFORE reality answers
OBSERVE   record_prediction_outcome(project, prediction_ref, observed, source)
   ↓      bool or rate 0..1; the source Ref must resolve; Brier is DERIVED
MEASURE   calibration_report → mean Brier + hit rate + the reliability curve,
   ↓      persisted; calibration_trend reads the series (the Brier delta)
CORRECT   brief_calibration → the misses with their evidence trails →
          the HOST authors corrections (update_persona / record_grounding) →
          record_calibration_round stamps the round
   ↺      …and the next reports show whether subsequent predictions improved
```

- **Scoring is derived, never asserted.** `record_prediction_outcome` keeps the
  predicted likelihood and the observed value on the auditable record; the
  Brier score `(likelihood − observed)²` and the hit flag follow mechanically.
  Hypotheses keep their own verdict path (`record_hypothesis_result`); the
  report combines both sides.
- **The reliability curve** groups outcomes by likelihood level (rare …
  certain) and compares predicted mean vs observed frequency — a calibrated
  cohort tracks the diagonal.
- **Trend = the metric.** Every `calibration_report` persists into the
  eval_reports series; `calibration_trend` returns the points, the first→last
  Brier delta, and `improving`. `green` means decisive data at or under the
  coin-flip line (Brier ≤ 0.25).
- **Corrections are host-authored** (the server never writes text): patch the
  trait that drove the miss (`update_persona`, with the miss as the reason) or
  ground the persona in the observed reality (`ingest_corpus` →
  `record_grounding`). Correct patterns, not single data points.

## Events & surface

`prediction.scored` and `calibration.round_recorded` ride the lifecycle-hook
transport (docs/lifecycle-hooks.md) — wire a recurring cloud job or a Slack
alert to either. MCP: `record_prediction_outcome`, `calibration_report`,
`calibration_trend`, `brief_calibration`, `record_calibration_round`.
CLI: `calibration-report`, `calibration-trend`.

Survey responses are a natural outcome source: import real responses
(`import_survey_responses`), then point `record_prediction_outcome.source` at
the survey record. The archetype packs (sonaloop-data) consume the calibrated
corpora this loop produces.

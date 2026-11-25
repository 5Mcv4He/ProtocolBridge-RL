# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| test_diagnostic | 2 | 2 | 0 | 0.0–65.8% | 2 | 2 | 2 / 0 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| test_diagnostic | 0 / 2 / 0 | 4 | 2 | 0 / 13 | 60298 | 474.8 | 26.4 | 421.7 | 22.6 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-test_diagnostic | 0.0 | 0.0 | 1 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r02-test_diagnostic | 0.0 | 0.0 | 2 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |

| Paired round | test_diagnostic |
|---|---:|
| 1 | 0.0 |
| 2 | 0.0 |

# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| test_verdict | 3 | 3 | 0 | 0.0–56.2% | 3 | 3 | 3 / 0 / 0 |
| test_diagnostic | 3 | 3 | 0 | 0.0–56.2% | 3 | 3 | 3 / 0 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| test_verdict | 0 / 3 / 0 | 6 | 3 | 0 / 19 | 84100 | 690.8 | 37.9 | 577.6 | 69.5 |
| test_diagnostic | 0 / 3 / 0 | 6 | 3 | 0 / 20 | 93157 | 704.7 | 41.8 | 576.8 | 81.0 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-test_verdict | 0.0 | 0.0 | 2 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r01-test_diagnostic | 0.0 | 0.0 | 2 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r02-test_diagnostic | 0.0 | 0.0 | 1 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r02-test_verdict | 0.0 | 0.0 | 1 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r03-test_verdict | 0.0 | 0.0 | 1 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r03-test_diagnostic | 0.0 | 0.0 | 2 | 2 | 0 | transaction_functional_error, repair_after_feedback_failed |

| Paired round | test_verdict | test_diagnostic |
|---|---:|---:|
| 1 | 0.0 | 0.0 |
| 2 | 0.0 | 0.0 |
| 3 | 0.0 | 0.0 |

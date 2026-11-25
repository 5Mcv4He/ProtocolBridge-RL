# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| spec_only | 3 | 3 | 3 | 43.8–100.0% | 0 | 0 | 0 / 3 / 0 |
| test_verdict | 3 | 3 | 2 | 20.8–93.9% | 2 | 1 | 1 / 2 / 0 |
| test_diagnostic | 3 | 3 | 3 | 43.8–100.0% | 1 | 0 | 0 / 3 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| spec_only | 2 / 1 / 0 | 0 | 0 | 0 / 13 | 27385 | 755.8 | 26.1 | 328.3 | 395.7 |
| test_verdict | 2 / 1 / 0 | 3 | 1 | 0 / 16 | 44525 | 670.9 | 35.2 | 327.0 | 303.1 |
| test_diagnostic | 3 / 0 / 0 | 1 | 0 | 1 / 15 | 40101 | 824.7 | 32.3 | 328.4 | 457.9 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r01-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r01-test_diagnostic | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r02-test_verdict | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r02-test_diagnostic | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r02-spec_only | 1.0 | 1.0 | 2 | 0 | 0 | none |
| r03-test_diagnostic | 1.0 | 1.0 | 2 | 1 | 1 | action_protocol_error |
| r03-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r03-test_verdict | 0.0 | 0.0 | 2 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |

| Paired round | spec_only | test_verdict | test_diagnostic |
|---|---:|---:|---:|
| 1 | 1.0 | 1.0 | 1.0 |
| 2 | 1.0 | 1.0 | 1.0 |
| 3 | 1.0 | 0.0 | 1.0 |

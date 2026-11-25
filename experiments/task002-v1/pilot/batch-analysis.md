# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| spec_only | 3 | 3 | 2 | 20.8–93.9% | 0 | 0 | 1 / 2 / 0 |
| test_verdict | 3 | 3 | 2 | 20.8–93.9% | 3 | 2 | 1 / 2 / 0 |
| test_diagnostic | 3 | 3 | 2 | 20.8–93.9% | 2 | 0 | 1 / 2 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| spec_only | 2 / 1 / 0 | 0 | 0 | 0 / 12 | 37886 | 677.9 | 43.5 | 226.1 | 401.5 |
| test_verdict | 1 / 2 / 0 | 5 | 2 | 0 / 21 | 107770 | 1059.6 | 70.2 | 579.9 | 403.4 |
| test_diagnostic | 2 / 1 / 0 | 2 | 0 | 1 / 15 | 80050 | 763.1 | 101.0 | 246.3 | 409.7 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r01-test_verdict | 1.0 | 1.0 | 3 | 2 | 0 | none |
| r01-test_diagnostic | 0.0 | 0.0 | 1 | 0 | 0 | transaction_functional_error |
| r02-test_verdict | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r02-test_diagnostic | 1.0 | 1.0 | 1 | 1 | 1 | action_protocol_error |
| r02-spec_only | 0.0 | 0.0 | 1 | 0 | 0 | compile_error |
| r03-test_diagnostic | 1.0 | 1.0 | 1 | 1 | 0 | none |
| r03-spec_only | 1.0 | 1.0 | 1 | 0 | 0 | none |
| r03-test_verdict | 0.0 | 0.0 | 3 | 2 | 0 | transaction_functional_error, repair_after_feedback_failed |

| Paired round | spec_only | test_verdict | test_diagnostic |
|---|---:|---:|---:|
| 1 | 1.0 | 1.0 | 0.0 |
| 2 | 0.0 | 1.0 | 1.0 |
| 3 | 1.0 | 0.0 | 1.0 |

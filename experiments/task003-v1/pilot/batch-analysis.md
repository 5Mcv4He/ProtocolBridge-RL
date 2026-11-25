# Batch analysis

All started trials remain in the denominator. Null rewards are separate from RTL failures. This is fixed-model inference, not parameter training.

| Policy | Started | Valid submissions | Success | Wilson 95% | Feedback exposed | Edited after feedback | 0 / 1 / null |
|---|---:|---:|---:|---|---:|---:|---|
| spec_only | 3 | 3 | 0 | 0.0–56.2% | 0 | 0 | 3 / 0 / 0 |
| test_verdict | 3 | 3 | 1 | 6.1–79.2% | 1 | 0 | 2 / 1 / 0 |
| test_diagnostic | 3 | 3 | 0 | 0.0–56.2% | 1 | 1 | 3 / 0 / 0 |

| Policy | First candidate public PASS / FAIL / unknown | Public calls | Changed after feedback | Format errors / actions | Tokens | Episode seconds | Request seconds | Compile seconds | Simulation seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| spec_only | 1 / 2 / 0 | 0 | 0 | 0 / 13 | 40206 | 431.5 | 38.2 | 335.4 | 52.2 |
| test_verdict | 1 / 2 / 0 | 2 | 0 | 2 / 18 | 74852 | 529.2 | 53.6 | 334.6 | 135.8 |
| test_diagnostic | 0 / 3 / 0 | 2 | 1 | 1 / 18 | 80326 | 524.7 | 66.8 | 421.9 | 30.9 |

First-candidate public measurement may be post-submit and is not extra feedback. A matching final public PASS is required before comparing public success against private failure. Request wall time includes API/network/SDK latency, not just model compute; compile/simulation durations include shell overhead. Episode time includes post-submit grading. Monetary cost is unavailable.

Quality gate: `{"passed": true, "reasons": []}`.

| Trial | Reward | Held-out | Edits | Public calls | Format errors | Failure labels (overlapping) |
|---|---:|---:|---:|---:|---:|---|
| r01-spec_only | 0.0 | 0.0 | 1 | 0 | 0 | protocol_timing_error |
| r01-test_verdict | 0.0 | 0.0 | 2 | 0 | 0 | transaction_functional_error |
| r01-test_diagnostic | 0.0 | 0.0 | 1 | 0 | 0 | protocol_timing_error |
| r02-test_verdict | 0.0 | 0.0 | 2 | 2 | 0 | transaction_functional_error |
| r02-test_diagnostic | 0.0 | 0.0 | 4 | 2 | 0 | protocol_timing_error, repair_after_feedback_failed |
| r02-spec_only | 0.0 | 0.0 | 1 | 0 | 0 | protocol_timing_error |
| r03-test_diagnostic | 0.0 | 0.0 | 1 | 0 | 1 | action_protocol_error, protocol_timing_error |
| r03-spec_only | 0.0 | 0.0 | 2 | 0 | 0 | transaction_functional_error |
| r03-test_verdict | 1.0 | 1.0 | 1 | 0 | 2 | action_protocol_error |

| Paired round | spec_only | test_verdict | test_diagnostic |
|---|---:|---:|---:|
| 1 | 0.0 | 0.0 | 0.0 |
| 2 | 0.0 | 0.0 | 0.0 |
| 3 | 0.0 | 1.0 | 0.0 |
